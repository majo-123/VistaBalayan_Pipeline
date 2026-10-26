# VistaBalayan Tourism Data Analytics and Decision Support Pipeline


The current milestone is **Stage 1: Data Extraction**. The pipeline extracts these four VistaBalayan tables:

- `establishments`
- `visitor_reports`
- `accommodation_reports`
- `room_occupancy_details`

Important Stage 1 code files:

- `pipeline/database.py` — connection loading and Supabase/PostgREST connection test.
- `pipeline/extract.py` — batch extraction to CSV files.
- `main.py` — command-line pipeline runner.
- `pipeline/staging.py` — CSV-to-SQLite staging builder.
- `pipeline/validate.py` — metadata and relationship validator.

Supporting Stage 1 files:

- `pipeline/pipeline_config.json` — table/file/relationship configuration.
- `requirements.txt` — setup compatibility file; Stage 1 code uses Python standard library only.
- `documentation/data-extraction.md` — Stage 1 extraction guide and command procedure.
- `documentation/extraction-results.md` — recorded local extraction and validation results.
- `documentation/logs/` — local generated JSON/log output folder.

Generated CSV files, documentation logs, and SQLite files are ignored by Git.

---

## Windows setup / daily start

Create the virtual environment and install requirements once:

```powershell
cd C:\Users\banco\VistaBalayan_ETL_Pipeline
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

After that, you do **not** need to recreate `.venv` or reinstall requirements every time. In a new PowerShell window, just go to the project folder and activate the existing environment:

```powershell
cd C:\Users\banco\VistaBalayan_ETL_Pipeline
.\.venv\Scripts\Activate.ps1
```

Then run the pipeline commands below in that same activated PowerShell window.

---

## Main commands

Place the exported CSV files inside `pipeline/raw/`:

```text
pipeline/raw/establishments.csv
pipeline/raw/visitor_reports.csv
pipeline/raw/accommodation_reports.csv
pipeline/raw/room_occupancy_details.csv
```


### Build SQLite staging database from CSV exports

```powershell
py main.py build-sqlite
```

This creates:

```text
pipeline/processed/vistabalayan_staging.sqlite
```

### Validate metadata and relationships

```powershell
py main.py validate
```

---

## Local extraction result

The recorded extraction and validation outputs are kept separately from the guide:

```text
documentation/extraction-results.md
```

---

## Stage 2: Transform the approved Stage 1 handover

Stage 2 runs locally against the SQLite staging database and the Stage 1 CSV exports. It does not write to Supabase or any production database.

Run Stage 1 first:

```powershell
py main.py build-sqlite --raw-dir pipeline/raw --sqlite-output pipeline/processed/vistabalayan_staging.sqlite --log-dir documentation/logs
py main.py validate --sqlite-output pipeline/processed/vistabalayan_staging.sqlite --log-dir documentation/logs
```

A successful `build-sqlite` automatically creates:

```text
documentation/transformation/stage1-handover.md
```

The handover contains the real generated `pipeline_run_id`. Do not invent or manually edit an `EXT_...` value. Read the generated ID in PowerShell:

```powershell
$parentRunId = ((Get-Content documentation/transformation/stage1-handover.md | Select-String "pipeline_run_id:").ToString().Split(":", 2)[1].Trim())
```

Continue only when validation returns `"overall_status": "PASS"`, then run Stage 2 with the exact generated parent ID:

```powershell
py main.py transform --sqlite-output pipeline/processed/vistabalayan_staging.sqlite --raw-dir pipeline/raw --transform-output pipeline/transformed --log-dir documentation/transformation/logs --parent-run-id $parentRunId --stage1-results documentation/transformation/stage1-handover.md
```

Stage 2 automatically generates its own `TRN_YYYYMMDD_HHMMSS` run ID when `--run-id` is omitted. A successful clean run returns:

```text
"overall_status": "PASS"
"acceptance_decision": "APPROVED FOR LOAD"
```

Stage 2 writes:

```text
pipeline/transformed/establishments_transformed.csv
pipeline/transformed/visitor_reports_transformed.csv
pipeline/transformed/accommodation_reports_transformed.csv
pipeline/transformed/room_occupancy_details_transformed.csv
pipeline/transformed/transformation_quarantine.csv
documentation/transformation/logs/transformation_<TRN run ID>.json
```

The Stage 2 command requires the handover ID and rejects a missing or mismatched `--parent-run-id`. Quarantined records remain in `transformation_quarantine.csv` with a rule ID and reason; Stage 2 returns `MANUAL REVIEW` when the rejection rate exceeds the configured threshold.
