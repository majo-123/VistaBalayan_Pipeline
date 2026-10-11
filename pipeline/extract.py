"""Batch CSV extraction for the VistaBalayan ETL pipeline."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .database import DEFAULT_TABLES, SupabaseRestClient


def increase_csv_field_limit() -> None:
    """Allow very large Supabase text/JSON/image fields in CSV operations."""

    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


increase_csv_field_limit()


class BatchClient(Protocol):
    config: Any

    def fetch_rows(self, table: str, offset: int = 0, limit: int | None = None) -> list[dict[str, Any]]:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_identifier(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(name).strip())
    if not safe or safe[0].isdigit():
        safe = f"_{safe}"
    return safe.lower()


def normalize_rows(rows: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, str]]]:
    """Normalize row keys/values so CSV exports are consistent."""

    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            column = normalize_identifier(key)
            if column not in seen:
                seen.add(column)
                columns.append(column)

    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized: dict[str, str] = {}
        for key, value in row.items():
            column = normalize_identifier(key)
            if value is None:
                normalized[column] = ""
            elif isinstance(value, (dict, list)):
                normalized[column] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            else:
                normalized[column] = str(value)
        normalized_rows.append(normalized)
    return columns, normalized_rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_table_to_csv(client: BatchClient, table: str, output_dir: Path, batch_size: int | None = None) -> dict[str, Any]:
    """Extract one Supabase table in batches and save it as a CSV file."""

    effective_batch_size = batch_size or int(getattr(client.config, "batch_size", 1000))
    offset = 0
    raw_rows: list[dict[str, Any]] = []
    batches = 0

    while True:
        batch = client.fetch_rows(table, offset=offset, limit=effective_batch_size)
        if not batch:
            break
        raw_rows.extend(batch)
        batches += 1
        if len(batch) < effective_batch_size:
            break
        offset += effective_batch_size

    columns, rows = normalize_rows(raw_rows)
    output_path = output_dir / f"{table}.csv"
    write_csv(output_path, columns, rows)
    return {
        "table": table,
        "status": "PASS",
        "output_csv": str(output_path),
        "records_extracted": len(rows),
        "columns": columns,
        "batches": batches,
    }


def export_all_tables(
    client: SupabaseRestClient,
    output_dir: Path = Path("pipeline/raw"),
    tables: tuple[str, ...] = DEFAULT_TABLES,
    batch_size: int | None = None,
    log_dir: Path = Path("documentation/logs"),
) -> dict[str, Any]:
    """Extract all Stage 1 source tables from Supabase into local CSV files."""

    log_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "run_started_at": utc_now(),
        "output_dir": str(output_dir),
        "tables": {},
        "issues": [],
    }
    for table in tables:
        try:
            result["tables"][table] = export_table_to_csv(client, table, output_dir, batch_size)
        except Exception as exc:  # noqa: BLE001 - keep extracting other tables and log exact failure.
            result["tables"][table] = {"table": table, "status": "FAIL", "error": str(exc)}
            result["issues"].append({"severity": "FAIL", "table": table, "details": str(exc)})

    result["run_finished_at"] = utc_now()
    result["overall_status"] = "FAIL" if result["issues"] else "PASS"
    log_file = log_dir / f"csv_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["log_path"] = str(log_file)
    return result
