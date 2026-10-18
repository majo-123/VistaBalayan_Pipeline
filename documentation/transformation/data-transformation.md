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