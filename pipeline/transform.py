"""Stage 2 transformation of the local VistaBalayan Stage 1 handover."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATASETS = (
    "establishments",
    "visitor_reports",
    "accommodation_reports",
    "room_occupancy_details",
)
OUTPUT_FILENAMES = {
    dataset: f"{dataset}_transformed.csv" for dataset in DATASETS
}
OUTPUT_COLUMNS = {
    "establishments": ("establishment_id", "establishment_name", "establishment_type", "establishment_status"),
    "visitor_reports": ("visitor_report_id", "establishment_id", "report_date", "report_status"),
    "accommodation_reports": ("accommodation_report_id", "establishment_id", "report_date", "report_status"),
    "room_occupancy_details": ("room_occupancy_detail_id", "accommodation_report_id"),
}
QUARANTINE_FILENAME = "transformation_quarantine.csv"
MAX_REJECTION_RATE_PERCENT = 1
PRIMARY_KEYS = {
    "establishments": "id",
    "visitor_reports": "id",
    "accommodation_reports": "id",
    "room_occupancy_details": "id",
}
REQUIRED = {
    "establishments": ("id", "name", "type", "status"),
    "visitor_reports": ("id", "establishment_id", "report_date", "status"),
    "accommodation_reports": ("id", "establishment_id", "report_date", "status"),
    "room_occupancy_details": ("id", "accommodation_report_id"),
}
PARENT_KEYS = {
    "visitor_reports": ("establishment_id", "establishments", "id"),
    "accommodation_reports": ("establishment_id", "establishments", "id"),
    "room_occupancy_details": ("accommodation_report_id", "accommodation_reports", "id"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def snake(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value or "")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value or "unnamed_column"


def parse_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate).date().isoformat()
    except ValueError:
        pass
    for fmt in ("%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


STANDARDIZATION_RULES_VERSION = "stage2-v1"


NUMERIC_FIELDS = {
    # Visitor-report measures.
    "female_visitors",
    "male_visitors",
    "total_female",
    "total_guests",
    "total_male",
    "total_visitors",
    "visitor_count",
    # Accommodation-report measures.
    "foreign_guest_check_ins",
    "foreign_guest_nights",
    "guest_check_ins",
    "guest_nights",
    "room_usage_count",
    "rooms_occupied",
    "short_stay_check_ins",
    "total_check_ins",
    "total_guest_nights",
    "total_occupied_rooms",
    "total_rooms",
    # Room-occupancy-detail measures.
    "check_ins",
    "number_of_rooms",
    "occupied_rooms",
}


def is_numeric_field(name: str) -> bool:
    """Return whether a field is a known numeric measure.

    Do not infer numeric type from broad substrings such as ``guest`` or
    ``room_``: VistaBalayan also has text fields such as ``guest_name``,
    ``guest_group_name``, ``room_code``, and ``room_type``.
    """
    return name in NUMERIC_FIELDS


def parse_nonnegative_int(value: Any) -> int | None:
    """Parse an operational count without rounding or inventing a value."""
    text = str(value).strip()
    if not text:
        return None
    if not re.fullmatch(r"\d+", text):
        return None
    return int(text)


def read_rows(sqlite_path: Path, raw_dir: Path, dataset: str) -> list[dict[str, Any]]:
    if sqlite_path.exists():
        with sqlite3.connect(sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            try:
                return [dict(row) for row in conn.execute(f"SELECT * FROM {dataset}")]
            except sqlite3.Error:
                pass
    path = raw_dir / f"{dataset}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing Stage 1 input: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], required_columns: tuple[str, ...] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns: list[str] = list(required_columns)
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def contract_row(dataset: str, row: dict[str, Any]) -> dict[str, Any]:
    names = {
        "establishments": {"id": "establishment_id", "name": "establishment_name", "type": "establishment_type", "status": "establishment_status"},
        "visitor_reports": {"id": "visitor_report_id", "status": "report_status"},
        "accommodation_reports": {"id": "accommodation_report_id", "status": "report_status"},
        "room_occupancy_details": {"id": "room_occupancy_detail_id"},
    }[dataset]
    return {names.get(key, key): value for key, value in row.items()}


def profile(rows: list[dict[str, Any]], dataset: str) -> dict[str, Any]:
    normalized = [{snake(k): v for k, v in row.items()} for row in rows]
    key = PRIMARY_KEYS[dataset]
    seen: set[str] = set()
    duplicates = 0
    blank_required = {field: 0 for field in REQUIRED[dataset]}
    invalid_dates = 0
    invalid_numeric = {field: 0 for field in sorted(NUMERIC_FIELDS)}
    whitespace_values = 0
    whitespace_by_field: dict[str, int] = {}
    for row in normalized:
        value = str(row.get(key, "") or "").strip()
        if value and value in seen:
            duplicates += 1
        if value:
            seen.add(value)
        for field in REQUIRED[dataset]:
            if not str(row.get(field, "") or "").strip():
                blank_required[field] += 1
        for field, raw_value in row.items():
            if isinstance(raw_value, str) and raw_value != raw_value.strip():
                whitespace_values += 1
                whitespace_by_field[field] = whitespace_by_field.get(field, 0) + 1
            if field in NUMERIC_FIELDS and str(raw_value or "").strip():
                if parse_nonnegative_int(raw_value) is None:
                    invalid_numeric[field] += 1
        if "report_date" in row and str(row.get("report_date") or "").strip() and parse_date(row.get("report_date")) is None:
            invalid_dates += 1
    return {
        "records_read": len(rows),
        "columns": sorted({snake(k) for row in rows for k in row}),
        "blank_required": blank_required,
        "duplicate_primary_key_count": duplicates,
        "invalid_report_date_count": invalid_dates,
        "invalid_numeric_counts": {k: v for k, v in invalid_numeric.items() if v},
        "whitespace_value_count": whitespace_values,
        "whitespace_value_counts": whitespace_by_field,
        "status_values": sorted({str(row.get("status", "")).strip() for row in normalized if str(row.get("status", "")).strip()}),
        "type_values": sorted({str(row.get("type", "")).strip() for row in normalized if str(row.get("type", "")).strip()}),
    }


def quarantine(run_id: str, batch_id: str, dataset: str, row: dict[str, Any], rule_id: str, reason: str) -> dict[str, Any]:
    key = PRIMARY_KEYS.get(dataset, "id")
    return {
        "run_id": run_id,
        "batch_id": batch_id,
        "source_dataset": dataset,
        "source_record_key": str(row.get(key, row.get(snake(key), "")) or ""),
        "original_record": json.dumps(row, ensure_ascii=False, sort_keys=True, default=str),
        "rule_id": rule_id,
        "quarantine_reason": reason,
        "quarantined_at": now_iso(),
    }


def stage1_handover(path: Path) -> tuple[str | None, str | None]:
    """Read the generated Stage 1 decision and lineage without source access."""
    if not path.exists():
        return None, None
    text = path.read_text(encoding="utf-8")
    decision_match = re.search(r"Stage 1 Decision:\s*([^\r\n]+)", text, flags=re.IGNORECASE)
    run_match = re.search(r"pipeline_run_id:\s*([^\r\n]+)", text, flags=re.IGNORECASE)
    decision = decision_match.group(1).strip().upper() if decision_match else None
    parent_run_id = run_match.group(1).strip() if run_match else None
    return decision, parent_run_id


def transform_rows(rows: list[dict[str, Any]], dataset: str, run_id: str, batch_id: str, parent_values: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    output: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    modified = 0
    key = PRIMARY_KEYS[dataset]
    seen: set[str] = set()
    for source in rows:
        row = {snake(k): v for k, v in source.items()}
        changed = False
        for field, value in list(row.items()):
            if isinstance(value, str):
                trimmed = value.strip()
                changed |= trimmed != value
                row[field] = trimmed
        identifier = str(row.get(key, "") or "").strip()
        if not identifier:
            rejected.append(quarantine(run_id, batch_id, dataset, source, "C-02", f"missing required identifier: {key}"))
            continue
        if identifier in seen:
            rejected.append(quarantine(run_id, batch_id, dataset, source, "C-03", f"duplicate primary key: {key}={identifier}"))
            continue
        seen.add(identifier)
        missing = [field for field in REQUIRED[dataset] if not str(row.get(field, "") or "").strip()]
        if missing:
            rejected.append(quarantine(run_id, batch_id, dataset, source, "C-02", f"missing required fields: {', '.join(missing)}"))
            continue
        if dataset in PARENT_KEYS:
            foreign_key, _, _ = PARENT_KEYS[dataset]
            if str(row.get(foreign_key, "")).strip() not in parent_values:
                rejected.append(quarantine(run_id, batch_id, dataset, source, "C-08", f"missing parent for {foreign_key}"))
                continue
        if "report_date" in row:
            parsed = parse_date(row["report_date"])
            if parsed is None:
                rejected.append(quarantine(run_id, batch_id, dataset, source, "C-05", "invalid report_date"))
                continue
            changed |= parsed != row["report_date"]
            row["report_date"] = parsed
            row["report_year"] = parsed[:4]
            row["report_month"] = parsed[5:7]
        numeric_error_field = None
        for field, value in list(row.items()):
            if field in ("id", "establishment_id", "accommodation_report_id") or not is_numeric_field(field) or str(value or "").strip() == "":
                continue
            number = parse_nonnegative_int(value)
            if number is None:
                numeric_error_field = field
                break
            changed |= str(value).strip() != str(number)
            row[field] = number
        if numeric_error_field:
            rejected.append(quarantine(run_id, batch_id, dataset, source, "C-06", f"invalid or negative numeric measure: {numeric_error_field}"))
            continue
        if changed:
            modified += 1
        output.append(row)
    return output, rejected, {"records_output": len(output), "records_rejected": len(rejected), "records_modified": modified}


def run(sqlite_path: Path, raw_dir: Path, output_dir: Path, log_dir: Path, run_id: str | None = None,
        parent_run_id: str | None = None, stage1_results: Path = Path("documentation/extraction-results.md")) -> dict[str, Any]:
    run_id = run_id or "TRN_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    batch_id = "BATCH_" + run_id.removeprefix("TRN_")
    start = now_iso()
    decision, handover_parent_run_id = stage1_handover(stage1_results)
    if decision != "APPROVED FOR TRANSFORMATION":
        result = {
            "overall_status": "FAIL", "status": "FAILED", "run_id": run_id,
            "error_code": "STAGE1_NOT_APPROVED",
            "error_message": f"Stage 1 decision is {decision or 'missing'}; expected APPROVED FOR TRANSFORMATION",
            "stage1_results": str(stage1_results),
        }
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"transformation_{run_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    if not parent_run_id:
        result = {
            "overall_status": "FAIL", "status": "FAILED", "run_id": run_id,
            "error_code": "PARENT_RUN_ID_REQUIRED",
            "error_message": "The actual Stage 1 parent_run_id is required for a production transformation run",
            "stage1_results": str(stage1_results),
        }
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"transformation_{run_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    if not handover_parent_run_id:
        result = {
            "overall_status": "FAIL", "status": "FAILED", "run_id": run_id,
            "error_code": "STAGE1_RUN_ID_MISSING",
            "error_message": "The Stage 1 handover does not contain pipeline_run_id",
            "stage1_results": str(stage1_results),
        }
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"transformation_{run_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    if parent_run_id != handover_parent_run_id:
        result = {
            "overall_status": "FAIL", "status": "FAILED", "run_id": run_id,
            "error_code": "PARENT_RUN_ID_MISMATCH",
            "error_message": f"--parent-run-id {parent_run_id} does not match handover pipeline_run_id {handover_parent_run_id}",
            "stage1_results": str(stage1_results),
            "parent_run_id": parent_run_id,
            "handover_parent_run_id": handover_parent_run_id,
        }
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"transformation_{run_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    all_rows: dict[str, list[dict[str, Any]]] = {}
    profiles: dict[str, Any] = {}
    try:
        for dataset in DATASETS:
            all_rows[dataset] = read_rows(sqlite_path, raw_dir, dataset)
            profiles[dataset] = profile(all_rows[dataset], dataset)
    except (FileNotFoundError, sqlite3.Error) as exc:
        result = {"overall_status": "FAIL", "status": "FAILED", "run_id": run_id, "error_code": "INPUT_MISSING", "error_message": str(exc)}
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"transformation_{run_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    transformed: dict[str, list[dict[str, Any]]] = {}
    quarantine_rows: list[dict[str, Any]] = []
    stats: dict[str, Any] = {}
    accepted_establishments, rejected, counts = transform_rows(all_rows["establishments"], "establishments", run_id, batch_id, set())
    transformed["establishments"] = accepted_establishments
    quarantine_rows.extend(rejected)
    stats["establishments"] = {"records_read": len(all_rows["establishments"]), **counts}
    establishment_ids = {str(r.get("id", "")).strip() for r in accepted_establishments}
    accommodation_ids: set[str] = set()
    for dataset, parents in (("visitor_reports", establishment_ids), ("accommodation_reports", establishment_ids)):
        accepted, rejected, counts = transform_rows(all_rows[dataset], dataset, run_id, batch_id, parents)
        transformed[dataset] = accepted
        quarantine_rows.extend(rejected)
        stats[dataset] = {"records_read": len(all_rows[dataset]), **counts}
        if dataset == "accommodation_reports":
            accommodation_ids = {str(r.get("id", "")).strip() for r in accepted}
    dataset = "room_occupancy_details"
    accepted, rejected, counts = transform_rows(all_rows[dataset], dataset, run_id, batch_id, accommodation_ids)
    transformed[dataset] = accepted
    quarantine_rows.extend(rejected)
    stats[dataset] = {"records_read": len(all_rows[dataset]), **counts}

    output_dir.mkdir(parents=True, exist_ok=True)
    for dataset, rows in transformed.items():
        write_csv(output_dir / OUTPUT_FILENAMES[dataset], [contract_row(dataset, row) for row in rows], OUTPUT_COLUMNS[dataset])
    write_csv(output_dir / QUARANTINE_FILENAME, quarantine_rows)
    validation = validate_outputs(transformed, quarantine_rows, stats, output_dir=output_dir)
    result = {
        "overall_status": validation["overall_status"],
        "status": "SUCCESS" if validation["overall_status"] != "FAIL" else "FAILED",
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "lineage_warning": None,
        "batch_id": batch_id,
        "start_timestamp": start,
        "end_timestamp": now_iso(),
        "profiles": profiles,
        "datasets": stats,
        "quarantine_count": len(quarantine_rows),
        "validation": validation,
        "acceptance_decision": validation["acceptance_decision"],
        "output_dir": str(output_dir),
        "rules_version": STANDARDIZATION_RULES_VERSION,
    }
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"transformation_{run_id}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result


def validate_output_headers(output_dir: Path) -> dict[str, str]:
    checks: dict[str, str] = {}
    for dataset, required_columns in OUTPUT_COLUMNS.items():
        path = output_dir / OUTPUT_FILENAMES[dataset]
        try:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                headers = set(next(csv.reader(handle), []))
            checks[f"{dataset}.output_headers"] = "PASS" if set(required_columns).issubset(headers) else "FAIL"
        except (OSError, StopIteration):
            checks[f"{dataset}.output_headers"] = "FAIL"
    return checks


def validate_outputs(transformed: dict[str, list[dict[str, Any]]], quarantine_rows: list[dict[str, Any]], stats: dict[str, Any], output_dir: Path | None = None) -> dict[str, Any]:
    checks: dict[str, str] = {}
    critical_failures: list[str] = []
    for dataset, rows in transformed.items():
        key = PRIMARY_KEYS[dataset]
        unique = len({str(row.get(key, "")) for row in rows}) == len(rows)
        checks[f"{dataset}.key_uniqueness"] = "PASS" if unique else "FAIL"
        if not unique:
            critical_failures.append(f"{dataset}.key_uniqueness")
        reconciliation = stats[dataset]["records_read"] == stats[dataset]["records_output"] + stats[dataset]["records_rejected"]
        checks[f"{dataset}.reconciliation"] = "PASS" if reconciliation else "FAIL"
        if not reconciliation:
            critical_failures.append(f"{dataset}.reconciliation")
        for row in rows:
            if any(not str(row.get(field, "") or "").strip() for field in REQUIRED[dataset]):
                critical_failures.append(f"{dataset}.required_fields")
                checks[f"{dataset}.required_fields"] = "FAIL"
                break
        else:
            checks.setdefault(f"{dataset}.required_fields", "PASS")
        date_ok = all("report_date" not in row or parse_date(row.get("report_date")) == row.get("report_date") for row in rows)
        checks[f"{dataset}.date_conformance"] = "PASS" if date_ok else "FAIL"
        if not date_ok:
            critical_failures.append(f"{dataset}.date_conformance")
        numeric_ok = all(
            not is_numeric_field(field) or str(value or "").strip() == "" or (str(value).lstrip("-").isdigit() and int(value) >= 0)
            for row in rows for field, value in row.items()
        )
        checks[f"{dataset}.numeric_conformance"] = "PASS" if numeric_ok else "FAIL"
        if not numeric_ok:
            critical_failures.append(f"{dataset}.numeric_conformance")
    if output_dir is not None:
        header_checks = validate_output_headers(output_dir)
        checks.update(header_checks)
        critical_failures.extend(name for name, status in header_checks.items() if status == "FAIL")
    establishment_ids = {str(row["id"]) for row in transformed["establishments"]}
    for dataset in ("visitor_reports", "accommodation_reports"):
        orphan = sum(str(row.get("establishment_id")) not in establishment_ids for row in transformed[dataset])
        checks[f"{dataset}.referential_integrity"] = "PASS" if orphan == 0 else "FAIL"
        if orphan:
            critical_failures.append(f"{dataset}.referential_integrity")
    accommodation_ids = {str(row["id"]) for row in transformed["accommodation_reports"]}
    orphan = sum(str(row.get("accommodation_report_id")) not in accommodation_ids for row in transformed["room_occupancy_details"])
    checks["room_occupancy_details.referential_integrity"] = "PASS" if orphan == 0 else "FAIL"
    if orphan:
        critical_failures.append("room_occupancy_details.referential_integrity")
    invalid_quarantine = [row for row in quarantine_rows if not row.get("rule_id") or not row.get("quarantine_reason")]
    checks["quarantine.accounting"] = "PASS" if not invalid_quarantine else "FAIL"
    if invalid_quarantine:
        critical_failures.append("quarantine.accounting")
    total_read = sum(item["records_read"] for item in stats.values())
    rejection_rate = (len(quarantine_rows) / total_read * 100) if total_read else 0
    checks["rejection_rate"] = "PASS" if rejection_rate <= MAX_REJECTION_RATE_PERCENT else "WARNING"
    overall = "FAIL" if critical_failures else ("WARNING" if rejection_rate > MAX_REJECTION_RATE_PERCENT else "PASS")
    acceptance = {"PASS": "APPROVED FOR LOAD", "WARNING": "MANUAL REVIEW", "FAIL": "REJECTED"}[overall]
    return {"overall_status": overall, "acceptance_decision": acceptance, "checks": checks, "critical_failures": critical_failures, "rejection_rate_percent": round(rejection_rate, 4), "records_read": total_read, "records_rejected": len(quarantine_rows)}
