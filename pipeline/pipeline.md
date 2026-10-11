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
