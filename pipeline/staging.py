#!/usr/bin/env python3
"""VistaBalayan CSV-export extraction runner.

Flow: Supabase/PostgreSQL export files -> Python extraction/validation -> SQLite staging DB.
The script is read-only with respect to Supabase/PostgreSQL. It reads local CSV exports and
writes a local SQLite staging database plus a JSON run log.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def increase_csv_field_limit() -> None:
    """Allow large Supabase CSV fields such as long descriptions, image data, or JSON blobs."""
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = limit // 10


increase_csv_field_limit()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_identifier(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name.strip())
    if not safe or safe[0].isdigit():
        safe = f"_{safe}"
    return safe.lower()


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header row: {path}")
        columns = [normalize_identifier(c) for c in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for raw in reader:
            row: dict[str, str] = {}
            for original, normalized in zip(reader.fieldnames, columns):
                value = raw.get(original, "")
                row[normalized] = "" if value is None else str(value).strip()
            if any(value != "" for value in row.values()):
                rows.append(row)
    return columns, rows


def create_table(conn: sqlite3.Connection, table: str, columns: list[str]) -> None:
    quoted_cols = ", ".join(f'"{col}" TEXT' for col in columns)
    conn.execute(f'DROP TABLE IF EXISTS "{table}"')
    conn.execute(f'CREATE TABLE "{table}" ({quoted_cols})')


def insert_rows(conn: sqlite3.Connection, table: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    placeholders = ", ".join("?" for _ in columns)
    quoted_cols = ", ".join(f'"{col}"' for col in columns)
    values = [[row.get(col, "") for col in columns] for row in rows]
    conn.executemany(f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders})', values)


def validate_table(table: str, spec: dict[str, Any], columns: list[str], rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    required = [normalize_identifier(col) for col in spec.get("required_columns", [])]
    missing_columns = [col for col in required if col not in columns]
    if missing_columns:
        issues.append({"severity": "FAIL", "table": table, "check": "required_columns", "details": missing_columns})

    pk = normalize_identifier(spec.get("primary_key", "id"))
    if pk in columns:
        seen: set[str] = set()
        duplicates: set[str] = set()
        blanks = 0
        for row in rows:
            value = row.get(pk, "")
            if not value:
                blanks += 1
            elif value in seen:
                duplicates.add(value)
            seen.add(value)
        if blanks:
            issues.append({"severity": "FAIL", "table": table, "check": "blank_primary_key", "count": blanks})
        if duplicates:
            issues.append({"severity": "FAIL", "table": table, "check": "duplicate_primary_key", "count": len(duplicates)})
    return issues


def validate_relationships(conn: sqlite3.Connection, loaded_tables: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for table, spec in loaded_tables.items():
        for fk in spec.get("foreign_keys", []):
            column = normalize_identifier(fk["column"])
            ref_table = normalize_identifier(fk["references_table"])
            ref_column = normalize_identifier(fk["references_column"])
            if ref_table not in loaded_tables:
                issues.append({
                    "severity": "WARNING",
                    "table": table,
                    "check": "foreign_key_reference_table_loaded",
                    "details": f"Reference table not loaded: {ref_table}",
                })
                continue
            count_sql = f'''
                SELECT COUNT(*)
                FROM "{table}" child
                LEFT JOIN "{ref_table}" parent
                  ON child."{column}" = parent."{ref_column}"
                WHERE child."{column}" IS NOT NULL
                  AND child."{column}" != ''
                  AND parent."{ref_column}" IS NULL
            '''
            missing = conn.execute(count_sql).fetchone()[0]
            issues.append({
                "severity": "PASS" if missing == 0 else "FAIL",
                "table": table,
                "check": "foreign_key_relationship",
                "column": column,
                "references": f"{ref_table}.{ref_column}",
                "missing_parent_count": missing,
            })
    return issues


def run(config_path: Path, raw_dir: Path | None = None, sqlite_output: Path | None = None, log_dir: Path | None = None) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = load_config(config_path)
    base = config_path.parent.parent
    raw_path = raw_dir if raw_dir is not None else (base / config["raw_data_dir"])
    sqlite_path = sqlite_output if sqlite_output is not None else (base / config["sqlite_output"])
    log_path_dir = log_dir if log_dir is not None else (base / config["log_dir"])
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    log_path_dir.mkdir(parents=True, exist_ok=True)

    pipeline_run_id = "EXT_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_log: dict[str, Any] = {
        "pipeline_name": config.get("pipeline_name"),
        "pipeline_run_id": pipeline_run_id,
        "run_started_at": utc_now(),
        "raw_data_dir": str(raw_path),
        "sqlite_output": str(sqlite_path),
        "tables": {},
        "issues": [],
    }
    loaded_specs: dict[str, dict[str, Any]] = {}

    with sqlite3.connect(sqlite_path) as conn:
        for table_name, spec in config["tables"].items():
            table = normalize_identifier(table_name)
            csv_path = raw_path / spec["file"]
            if not csv_path.exists():
                run_log["tables"][table] = {"status": "SKIPPED", "reason": f"missing file: {csv_path}"}
                run_log["issues"].append({"severity": "FAIL", "table": table, "check": "source_file_exists", "details": str(csv_path)})
                continue
            columns, rows = read_csv_rows(csv_path)
            create_table(conn, table, columns)
            insert_rows(conn, table, columns, rows)
            table_issues = validate_table(table, spec, columns, rows)
            run_log["issues"].extend(table_issues)
            loaded_specs[table] = spec
            run_log["tables"][table] = {
                "status": "LOADED",
                "source_file": str(csv_path),
                "columns": columns,
                "records_extracted": len(rows),
                "validation_status": "FAIL" if any(i["severity"] == "FAIL" for i in table_issues) else "PASS",
            }
        run_log["issues"].extend(validate_relationships(conn, loaded_specs))
        conn.commit()

    run_log["run_finished_at"] = utc_now()
    run_log["overall_status"] = "FAIL" if any(i["severity"] == "FAIL" for i in run_log["issues"]) else "PASS"
    handover_path = base / "documentation" / "transformation" / "stage1-handover.md"
    handover_path.parent.mkdir(parents=True, exist_ok=True)
    decision = "APPROVED FOR TRANSFORMATION" if run_log["overall_status"] == "PASS" else "REJECTED"
    handover_path.write_text(
        "# Stage 1 Handover for Stage 2\n\n"
        "This file is generated by `build-sqlite` after Stage 1 validation.\n\n"
        f"Stage 1 Decision: {decision}\n"
        f"pipeline_run_id: {pipeline_run_id}\n",
        encoding="utf-8",
    )
    run_log["handover_path"] = str(handover_path)
    log_file = log_path_dir / f"extraction_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(run_log, indent=2), encoding="utf-8")
    run_log["log_path"] = str(log_file)
    return run_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Load VistaBalayan CSV exports into a local SQLite staging database.")
    parser.add_argument("--config", default="pipeline/pipeline_config.json", type=Path)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--sqlite-output", type=Path)
    parser.add_argument("--log-dir", type=Path)
    args = parser.parse_args()
    result = run(args.config, args.raw_dir, args.sqlite_output, args.log_dir)
    print(json.dumps({
        "overall_status": result["overall_status"],
        "pipeline_run_id": result["pipeline_run_id"],
        "handover_path": result["handover_path"],
        "sqlite_output": result["sqlite_output"],
        "log_path": result["log_path"],
        "tables": {name: meta.get("records_extracted", 0) for name, meta in result["tables"].items()},
    }, indent=2))
    return 0 if result["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
