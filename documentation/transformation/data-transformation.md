# Stage 2: Data Transformation Documentation

## Objective

The objective of Stage 2 is to transform the approved Stage 1 handover into cleaned, standardized, traceable, and business-ready CSV datasets for the Load stage.

## Stage 1 Handover Reference

Stage 2 consumes the approved Stage 1 handover described in:

- [Stage 1 extraction and handover contract](../extraction//data-extraction.md)
- [Verified Stage 1 extraction results](../extraction//extraction-results.md)

The verified Stage 1 source datasets are:

- `establishments` — 38 records
- `visitor_reports` — 2,400 records
- `accommodation_reports` — 1,857 records
- `room_occupancy_details` — 5,938 records

Stage 1 validation passed, including the following relationships:

- `visitor_reports.establishment_id` → `establishments.id`
- `accommodation_reports.establishment_id` → `establishments.id`
- `room_occupancy_details.accommodation_report_id` → `accommodation_reports.id`

Stage 2 must stop before transformation if the Stage 1 decision is `MANUAL REVIEW` or `REJECTED`.

---

## 1. Transformation Input and Processing Specification

### 1.1 Input Source

Stage 2 accepts the locally staged output produced by Stage 1. The preferred input is:

```text
pipeline/processed/vistabalayan_staging.sqlite
```

If the SQLite handover is unavailable, the transformer falls back to these four Stage 1 CSV files:

```text
pipeline/raw/establishments.csv
pipeline/raw/visitor_reports.csv
pipeline/raw/accommodation_reports.csv
pipeline/raw/room_occupancy_details.csv
```

The input is not copied from the live source database. It is the extracted and validated Stage 1 handover.

The production handover must provide the actual Stage 1 `pipeline_run_id`. The current implementation records `EXT_FROM_STAGE1_HANDOVER` as a documented placeholder when no run ID is supplied to the transform command; this placeholder must be replaced by the actual upstream run ID for a production lineage record.

### 1.2 Transformation Command

From the repository root:

```powershell
py main.py transform
```

Optional paths and run identifier:

```powershell
py main.py transform `
  --sqlite-path pipeline/processed/vistabalayan_staging.sqlite `
  --raw-dir pipeline/raw `
  --output-dir pipeline/transformed `
  --log-dir documentation/transformation/logs `
  --run-id TRN_YYYYMMDD_HHMMSS
```

The command is implemented by `pipeline/transform.py` and uses Python's standard library, SQLite, and CSV support.

### 1.3 Batch Processing Method

- Processing mode: local batch transformation.
- Batch unit: one Stage 1 handover run containing the four related datasets.
- Batch identifier: generated as `BATCH_<run timestamp>` from the transformation run ID.
- Schedule: no scheduler is included in this repository; an external Windows Task Scheduler, CI job, or operator-run schedule may invoke the command.
- Restart behavior: rerun the same input handover with a new or explicitly supplied `run_id`; outputs are rewritten in the configured output directory.
- Idempotency: the transformation is deterministic for the same input and rules version, and it rewrites the output files rather than appending to them. The run ID and output directory must be controlled by the operator to avoid mixing separate runs.

### 1.4 Transformation Scope

The four Stage 1 datasets are transformed in parent-to-child order:

1. `establishments`
2. `visitor_reports`
3. `accommodation_reports`
4. `room_occupancy_details`

The stage performs profiling, column normalization, whitespace cleanup, date standardization, explicit numeric conversion, required-field checks, primary-key duplicate detection, foreign-key checks, quarantine, reconciliation, and output validation.

### 1.5 Dependencies and Assumptions

- The Stage 1 handover has passed its required acceptance gate.
- Parent records are available before child records are checked.
- Source IDs and relationship columns remain available for lineage and joins.
- The input schema can contain additional source columns; they are retained unless renamed by the output contract.
- Numeric detection uses an explicit allowlist. Text fields such as `guest_name`, `guest_group_name`, `room_code`, and `room_type` are never treated as numeric merely because their names contain `guest` or `room`.
- No target database, warehouse, dimensional model, or surrogate-key load is created in this stage.


# 2. Data Profiling and Issue Identification

Data profiling is performed on the data extracted from the VistaBalayan Tourism System before applying standardization and transformation rules. The profiling process examines the four source datasets: `establishments`, `visitor_reports`, `accommodation_reports`, and `room_occupancy_details`.

The purpose is to identify potential data quality issues, including missing values, duplicate records, inconsistent formats, invalid business values, and incorrect data types. Each identified issue is documented with its affected table and column, a sample value, the number or percentage of affected records, and the planned treatment based on the rules defined in the succeeding sections.

## 2.1 Data Profiling and Issue Identification Table

The following table identifies the data quality issues that should be examined in the extracted VistaBalayan datasets. The examples are illustrative and must be verified against the actual extracted records. Affected record counts and percentages must be completed after profiling.

| Table or File | Column Affected | Issue Type | Example of the Issue | Estimated Affected Records | Planned Treatment |
|---|---|---|---|---|---|
| `establishments.csv` | `name` | Missing values | Empty or null establishment name | 1–3% (estimated) | Apply the required-field validation rule in Section 3. Records with missing establishment names will be flagged for review. |
| `establishments.csv` | `type` | Inconsistent formats | `Hotel`, `HOTEL`, `hotel` | 5–10% (estimated) | Standardize text casing and map establishment types to consistent reference values under Section 4. |
| `establishments.csv` | `id` | Duplicate values | The same UUID appears more than once | 0–1% (estimated) | Check identifier uniqueness and flag duplicate records for investigation under Section 3. |
| `visitor_reports.csv` | `report_date` | Inconsistent date formats | `2026/10/18`, `2026-10-18` | 1–5% (estimated) | Convert valid dates to ISO 8601 format (`YYYY-MM-DD`) under Section 4. |
| `visitor_reports.csv` | `male_visitors`, `female_visitors`, `total_visitors` | Invalid numeric values | `-5`, `2.5`, `abc` | 1–3% (estimated) | Convert values to integers and validate that visitor counts are nonnegative. Flag invalid records under Sections 3 and 4. |
| `visitor_reports.csv` | `establishment_id` | Invalid reference values | An ID that does not exist in `establishments.csv` | 0–2% (estimated) | Validate establishment references and flag unmatched IDs for review under Section 3. |
| `visitor_reports.csv` | `municipality`, `province`, `country` | Inconsistent text formats | `Balayan`, `BALAYAN`, `balayan` | 5–15% (estimated) | Standardize text formatting and apply reference-value mappings where applicable under Section 4. |
| `accommodation_reports.csv` | `total_rooms`, `occupied_rooms`, `guest_check_ins`, `guest_nights` | Invalid numeric values | Negative counts or non-integer values | 1–3% (estimated) | Convert values to integers and validate nonnegative counts. Flag invalid records under Sections 3 and 4. |
| `accommodation_reports.csv` | `report_date` | Missing values | Empty report date | 1–3% (estimated) | Validate required dates and flag records with missing dates for review under Sections 3 and 4. |
| `room_occupancy_details.csv` | `room_type` | Inconsistent text formats | `Deluxe`, `DELUXE`, `deluxe` | 5–10% (estimated) | Standardize room-type labels using consistent casing and reference values under Section 4. |
| `room_occupancy_details.csv` | `accommodation_report_id` | Invalid reference values | An ID that does not exist in `accommodation_reports.csv` | 0–2% (estimated) | Validate the relationship between room occupancy details and accommodation reports under Section 3. |
| `room_occupancy_details.csv` | `number_of_rooms`, `occupied_rooms`, `check_ins`, `guest_nights` | Invalid numeric values | Negative room count or decimal check-in count | 1–3% (estimated) | Convert values to integers, validate nonnegative counts, and flag invalid records under Sections 3 and 4. |

