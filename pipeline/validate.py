#!/usr/bin/env python3
"""Validate the local VistaBalayan SQLite staging database.

This is the second ETL step after pipeline/staging.py. It reads the local
SQLite file only; it does not connect to or modify Supabase/PostgreSQL.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")


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


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def count_blank(conn: sqlite3.Connection, table: str, column: str) -> int:
    return int(
        conn.execute(
            f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NULL OR TRIM("{column}") = \'\''
        ).fetchone()[0]
    )


def count_duplicate_nonblank(conn: sqlite3.Connection, table: str, column: str) -> int:
    rows = conn.execute(
        f'''
        SELECT "{column}", COUNT(*) AS duplicate_count
        FROM "{table}"
        WHERE "{column}" IS NOT NULL AND TRIM("{column}") != ''
        GROUP BY "{column}"
        HAVING COUNT(*) > 1
        '''
    ).fetchall()
    return len(rows)


def count_bad_dates(conn: sqlite3.Connection, table: str, column: str) -> int:
    # SQLite date() parses ISO-like dates. This catches blank-excluded values that are not date-like.
    return int(
        conn.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            WHERE "{column}" IS NOT NULL
              AND TRIM("{column}") != ''
              AND date("{column}") IS NULL
            '''
        ).fetchone()[0]
    )


def status_distribution(conn: sqlite3.Connection, table: str) -> dict[str, int]:
    cols = table_columns(conn, table)
    if "status" not in cols:
        return {}
    rows = conn.execute(
        f'''
        SELECT COALESCE(NULLIF(TRIM("status"), ''), '[blank]') AS status_value, COUNT(*)
        FROM "{table}"
        GROUP BY status_value
        ORDER BY status_value
        '''
    ).fetchall()
    return {str(status): int(count) for status, count in rows}


def validate_sqlite(config_path: Path, sqlite_path: Path | None = None, log_dir: Path | None = None) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = load_config(config_path)
    base = config_path.parent.parent
    sqlite_file = sqlite_path if sqlite_path is not None else base / config["sqlite_output"]
    log_path_dir = log_dir if log_dir is not None else base / config["log_dir"]
    log_path_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "pipeline_name": config.get("pipeline_name"),
        "validation_started_at": utc_now(),
        "sqlite_path": str(sqlite_file),
        "tables": {},
        "checks": [],
    }

    if not sqlite_file.exists():
        result["checks"].append({
            "severity": "FAIL",
            "check": "sqlite_file_exists",
            "details": f"SQLite file not found: {sqlite_file}",
        })
        result["overall_status"] = "FAIL"
        result["validation_finished_at"] = utc_now()
        log_file = log_path_dir / f"metadata_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["log_path"] = str(log_file)
        return result

    with sqlite3.connect(sqlite_file) as conn:
        for table_name, spec in config["tables"].items():
            table = normalize_identifier(table_name)
            table_meta: dict[str, Any] = {"exists": False, "row_count": 0, "columns": []}
            result["tables"][table] = table_meta

            if not table_exists(conn, table):
                result["checks"].append({"severity": "FAIL", "table": table, "check": "table_exists"})
                continue

            columns = table_columns(conn, table)
            row_count = count_rows(conn, table)
            table_meta.update({
                "exists": True,
                "row_count": row_count,
                "columns": columns,
                "status_distribution": status_distribution(conn, table),
            })
            result["checks"].append({
                "severity": "PASS" if row_count > 0 else "WARNING",
                "table": table,
                "check": "row_count_positive",
                "row_count": row_count,
            })

            required_columns = [normalize_identifier(c) for c in spec.get("required_columns", [])]
            missing_required = [c for c in required_columns if c not in columns]
            result["checks"].append({
                "severity": "PASS" if not missing_required else "FAIL",
                "table": table,
                "check": "required_columns_present",
                "missing_columns": missing_required,
            })

            pk = normalize_identifier(spec.get("primary_key", "id"))
            if pk in columns:
                blank_pk = count_blank(conn, table, pk)
                dup_pk = count_duplicate_nonblank(conn, table, pk)
                result["checks"].append({
                    "severity": "PASS" if blank_pk == 0 and dup_pk == 0 else "FAIL",
                    "table": table,
                    "check": "primary_key_quality",
                    "primary_key": pk,
                    "blank_count": blank_pk,
                    "duplicate_value_count": dup_pk,
                })

            for date_column in [normalize_identifier(c) for c in spec.get("date_columns", [])]:
                if date_column not in columns:
                    result["checks"].append({
                        "severity": "WARNING",
                        "table": table,
                        "check": "date_column_present",
                        "column": date_column,
                        "details": "Configured date column is not present in this export.",
                    })
                    continue
                bad_dates = count_bad_dates(conn, table, date_column)
                result["checks"].append({
                    "severity": "PASS" if bad_dates == 0 else "WARNING",
                    "table": table,
                    "check": "date_parseable",
                    "column": date_column,
                    "bad_date_count": bad_dates,
                })

        for table_name, spec in config["tables"].items():
            table = normalize_identifier(table_name)
            if not table_exists(conn, table):
                continue
            columns = table_columns(conn, table)
            for fk in spec.get("foreign_keys", []):
                column = normalize_identifier(fk["column"])
                ref_table = normalize_identifier(fk["references_table"])
                ref_column = normalize_identifier(fk["references_column"])
                if column not in columns or not table_exists(conn, ref_table) or ref_column not in table_columns(conn, ref_table):
                    result["checks"].append({
                        "severity": "FAIL",
                        "table": table,
                        "check": "foreign_key_metadata_present",
                        "column": column,
                        "references": f"{ref_table}.{ref_column}",
                    })
                    continue
                missing_parent_count = int(conn.execute(
                    f'''
                    SELECT COUNT(*)
                    FROM "{table}" child
                    LEFT JOIN "{ref_table}" parent
                      ON child."{column}" = parent."{ref_column}"
                    WHERE child."{column}" IS NOT NULL
                      AND TRIM(child."{column}") != ''
                      AND parent."{ref_column}" IS NULL
                    '''
                ).fetchone()[0])
                result["checks"].append({
                    "severity": "PASS" if missing_parent_count == 0 else "FAIL",
                    "table": table,
                    "check": "foreign_key_relationship",
                    "column": column,
                    "references": f"{ref_table}.{ref_column}",
                    "missing_parent_count": missing_parent_count,
                })

    result["validation_finished_at"] = utc_now()
    result["overall_status"] = "FAIL" if any(c["severity"] == "FAIL" for c in result["checks"]) else "PASS"
    log_file = log_path_dir / f"metadata_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["log_path"] = str(log_file)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate VistaBalayan local SQLite staging metadata and relationships.")
    parser.add_argument("--config", default="pipeline/pipeline_config.json", type=Path)
    parser.add_argument("--sqlite", type=Path, help="Path to staging SQLite database. Defaults to config sqlite_output.")
    parser.add_argument("--log-dir", type=Path)
    args = parser.parse_args()

    result = validate_sqlite(args.config, args.sqlite, args.log_dir)
    print(json.dumps({
        "overall_status": result["overall_status"],
        "sqlite_path": result["sqlite_path"],
        "log_path": result["log_path"],
        "tables": {name: {"row_count": meta.get("row_count", 0)} for name, meta in result["tables"].items()},
        "failed_checks": [c for c in result["checks"] if c["severity"] == "FAIL"],
        "warning_checks": [c for c in result["checks"] if c["severity"] == "WARNING"],
    }, indent=2))
    return 0 if result["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
