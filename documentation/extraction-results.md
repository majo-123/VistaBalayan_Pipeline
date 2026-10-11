# Stage 1: Extraction Results

## VistaBalayan Tourism Data Analytics and Decision Support Pipeline

This file records the local Stage 1 extraction and validation results separately from the extraction guide.

---

# 1. Recorded Local Extraction Result

The user's successful local extraction produced:

```json
{
  "overall_status": "PASS",
  "sqlite_output": "C:\\Users\\banco\\VistaBalayan_ETL_Pipeline\\pipeline\\processed\\vistabalayan_staging.sqlite",
  "tables": {
    "establishments": 38,
    "visitor_reports": 2397,
    "accommodation_reports": 1857,
    "room_occupancy_details": 5938
  }
}
```

This confirms that the local CSV-to-SQLite extraction step successfully loaded all four Stage 1 source tables.

---

# 2. Validation Results

The local Stage 1 metadata validation completed successfully:

```text
overall_status: PASS
```

Validated table counts:

- `establishments`: 38
- `visitor_reports`: 2,397
- `accommodation_reports`: 1,857
- `room_occupancy_details`: 5,938

Relationship checks passed with `missing_parent_count: 0` for:

- `visitor_reports.establishment_id` → `establishments.id`
- `accommodation_reports.establishment_id` → `establishments.id`
- `room_occupancy_details.accommodation_report_id` → `accommodation_reports.id`

The command entry point was also checked with:

```text
python3 main.py --help
```
