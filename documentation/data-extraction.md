# Stage 1: Data Extraction Documentation

## VistaBalayan Tourism Data Analytics and Decision Support Pipeline

## Objective

The objective of the extraction stage is to retrieve tourism data from the VistaBalayan source system and prepare a documented, traceable, and validated dataset for the succeeding Transformation Stage.

The VistaBalayan pipeline processes tourism records including visitor reports, accommodation report and establishment information. PostgreSQL serves as the primary structured data storage, while Python retrieves tourism records for batch processing.

---

# 1. Data Source and Extraction Specifications

## 1.1 Source System

**Source System:** VistaBalayan System

**Purpose:**  
The VistaBalayan system collects and manages tourism information submitted by participating tourist establishments. Establishment staff encode and submit tourism records, which are stored in the database and used for monitoring, reporting, analytics, dashboards, and decision-support functions.

The source records include:

- Visitor reports
- Accommodation reports
- Establishment information


## 1.2 Source Database or File

**Database Management System:** PostgreSQL

**Source Database:** VistaBalayan PostgreSQL Database

**File Format:** CSV

PostgreSQL is used as the primary database for structured tourism information. The source schema includes establishments, visitor reports, accommodation reports, and related tourism records.

## 1.3 Extraction Method

**Extraction Type:** Batch Extraction

**Extraction Tool:** Python

Python retrieves tourism records from PostgreSQL for batch processing.

### Extraction Process

```text
VistaBalayan PostgreSQL Database
              |
              v
       Python Extraction
              |
              v
      Raw Extracted Data
              |
              v
   Extraction Validation
              |
              v
    Transformation Stage
```

### Extraction Schedule

The pipeline performs **daily batch processing**, with weekly or monthly aggregation when required.

### Incremental Extraction

The VistaBalayan pipeline uses incremental extraction to retrieve newly added or updated tourism records from the PostgreSQL source database. The extraction uses the applicable reporting date or timestamp field to identify records within the defined extraction window. This approach minimizes unnecessary retrieval of previously processed records and allows the pipeline to focus on new or updated tourism data during each scheduled batch run.

An incremental extraction rule will use the approved date or timestamp field as the extraction reference. The extracted records will then undergo extraction-level validation before being handed over to the Transformation Stage.


## 1.4 Extraction Scope

The extraction includes the tourism information required by the VistaBalayan data pipeline.

| Source Table / Data | Extraction Purpose |
|---|---|
| `establishments` | Retrieve tourism establishment information |
| `visitor_reports` | Retrieve visitor counts and visitor-origin information |
| `accommodation_reports` | Retrieve accommodation and guest statistics |
| `room_occupancy_details` | Retrieve room-level occupancy information |

The extraction covers the records available in PostgreSQL at the scheduled batch run.

## 1.5 Source Limitations and Assumptions

The following limitations and assumptions apply:

1. Tourism records must be available in PostgreSQL before extraction begins.
2. Python must be able to establish a valid connection to PostgreSQL.
3. Required source tables and columns must exist.
4. The current documentation does not define an incremental extraction watermark.
5. The current documentation does not specify a historical cutoff date.
6. Unexpected database schema changes may cause extraction validation to fail.
7. Database connectivity problems may interrupt an extraction run.

---

# 2. Source Tables and Column Specification

## 2.1 `establishments`

### Purpose

The `establishments` table contains information identifying and classifying tourism establishments.

| Column | Data Type | Key / Constraint | Purpose |
|---|---|---|---|
| `id` | UUID | Primary Key | Unique identifier of the tourism establishment |
| `name` | VARCHAR(150) | NOT NULL | Name of the establishment |
| `type` | VARCHAR(50) | NOT NULL | Establishment classification |
| `total_rooms` | INTEGER | DEFAULT 0 | Total rooms for accommodation establishments |

**Reason for inclusion:** Establishment information is required to associate tourism records with a specific tourism establishment.

## 2.2 `visitor_reports`

### Purpose

The `visitor_reports` table contains visitor information submitted by tourism establishments.

| Column | Data Type | Key / Constraint | Purpose |
|---|---|---|---|
| `id` | UUID | Primary Key | Unique visitor report identifier |
| `establishment_id` | UUID | Foreign Key → `establishments(id)` | Identifies the reporting establishment |
| `report_date` | DATE | NOT NULL | Date covered by the report |
| `male_visitors` | INTEGER | DEFAULT 0 | Number of male visitors |
| `female_visitors` | INTEGER | DEFAULT 0 | Number of female visitors |
| `total_visitors` | INTEGER | NOT NULL | Total number of visitors |
| `residence_category` | VARCHAR(50) | — | Visitor origin category |
| `municipality` | VARCHAR(100) | — | Municipality of origin |
| `province` | VARCHAR(100) | — | Province of origin |
| `country` | VARCHAR(100) | — | Country of origin for foreign visitors |

**Reason for inclusion:** Visitor reports are the primary source for visitor monitoring, visitor trends, and tourism reporting.

## 2.3 `accommodation_reports`

### Purpose

The `accommodation_reports` table contains accommodation-related tourism statistics.

| Column | Data Type | Key / Constraint | Purpose |
|---|---|---|---|
| `id` | UUID | Primary Key | Unique accommodation report identifier |
| `establishment_id` | UUID | Foreign Key → `establishments(id)` | Identifies the reporting establishment |
| `report_date` | DATE | NOT NULL | Date covered by the report |
| `total_rooms` | INTEGER | NOT NULL | Total available rooms |
| `occupied_rooms` | INTEGER | DEFAULT 0 | Number of occupied rooms |
| `guest_check_ins` | INTEGER | DEFAULT 0 | Number of guest check-ins |
| `guest_nights` | INTEGER | DEFAULT 0 | Total guest nights |
| `foreign_guest_check_ins` | INTEGER | DEFAULT 0 | Foreign guest check-ins |
| `foreign_guest_nights` | INTEGER | DEFAULT 0 | Foreign guest nights |

**Reason for inclusion:** Accommodation records are required for monitoring accommodation activity and guest statistics.

## 2.4 `room_occupancy_details`

### Purpose

The `room_occupancy_details` table provides detailed room-level accommodation information.

| Column | Data Type | Key / Constraint | Purpose |
|---|---|---|---|
| `id` | UUID | Primary Key | Unique room occupancy detail identifier |
| `accommodation_report_id` | UUID | Foreign Key → `accommodation_reports(id)` | Identifies the related accommodation report |
| `room_type` | VARCHAR(100) | NOT NULL | Room category |
| `number_of_rooms` | INTEGER | DEFAULT 0 | Number of rooms under the room type |
| `occupied_rooms` | INTEGER | DEFAULT 0 | Occupied rooms under the room type |
| `check_ins` | INTEGER | DEFAULT 0 | Check-ins for the room type |
| `guest_nights` | INTEGER | DEFAULT 0 | Guest nights for the room type |

**Reason for inclusion:** This table provides room-level information needed for accommodation and occupancy analysis.


## 2.6 Source Relationships

| Relationship | Description |
|---|---|
| `establishments` → `visitor_reports` | One establishment can have many visitor reports through `visitor_reports.establishment_id`. |
| `establishments` → `accommodation_reports` | One establishment can have many accommodation reports through `accommodation_reports.establishment_id`. |
| `accommodation_reports` → `room_occupancy_details` | One accommodation report can have many room occupancy detail records through `room_occupancy_details.accommodation_report_id`. |

---

# 3. Extraction Validation and Data Quality Checks

The extraction stage focuses on verifying that the data was successfully retrieved from the source. Data cleaning, standardization, and business transformations are handled in later stages.

## 3.1 Validation Checks

| Check Name | Target | Purpose | Validation Criteria |
|---|---|---|---|
| Source Connection | PostgreSQL database | Verify source accessibility | Connection succeeds |
| Required Tables | All required source tables | Ensure required tables exist | All required tables are found |
| Required Columns | Selected columns | Ensure required fields exist | All required columns exist |
| Identifier Presence | Primary and foreign keys | Ensure records can be identified and related | Required identifiers are present |
| Primary Key Uniqueness | Primary key columns | Detect duplicate identifiers | No duplicate primary keys |
| Record Count | Extracted tables | Verify records were retrieved | Record counts are successfully recorded |
| Extraction Completeness | Extraction result | Detect incomplete extraction | Extraction completes without interruption |
| Foreign Key Availability | Relationship columns | Verify relationships can be maintained | Required foreign-key values are present |
| Extraction Error Check | Extraction process | Detect failures or interruptions | No unhandled extraction error |
| Extraction Status | Pipeline run | Determine result of extraction | Status is recorded as PASS, WARNING, or FAIL |

## 3.2 Validation Result Categories

### PASS

All critical extraction requirements are satisfied.

### WARNING

The extraction completed, but a non-critical condition requires review.

### FAIL

A critical extraction requirement was not satisfied.

Examples of critical failures include:

- PostgreSQL connection failure
- Required table missing
- Required column missing
- Extraction interruption
- Critical identifier unavailable

---

# 4. Extraction Metadata and Log Specification

Each extraction run must generate metadata that allows the team to monitor, troubleshoot, audit, and recover the pipeline.

| Metadata Field | Purpose | Example |
|---|---|---|
| `pipeline_run_id` | Unique identifier for the extraction run | `VB-20260930-001` |
| `table_name` | Identifies the extracted table | `visitor_reports` |
| `extraction_start_timestamp` | Records when extraction started | `2026-09-30 01:00:00` |
| `extraction_end_timestamp` | Records when extraction ended | `2026-09-30 01:02:14` |
| `extraction_status` | Indicates extraction result | `SUCCESS` |
| `records_read` | Number of records read from source | `1250` |
| `records_extracted` | Number of records successfully extracted | `1250` |
| `records_rejected` | Number of records rejected during extraction validation | `0` |
| `extraction_window` | Identifies the extraction range | `2026-09-29 to 2026-09-30` |
| `validation_result` | Records validation outcome | `PASS` |
| `error_message` | Records extraction error when applicable | `NULL` |
| `error_code` | Identifies the extraction error | `NULL` |
| `extraction_duration` | Measures execution time | `00:02:14` |

## 4.1 Use of Metadata and Logs

The metadata and logs will be used for:

- **Monitoring** — determine whether scheduled extraction runs completed successfully.
- **Troubleshooting** — identify the affected table, run, timestamp, or error.
- **Auditing** — maintain a historical record of extraction activities.
- **Recovery** — identify incomplete or failed runs that require retry.
- **Validation** — compare extraction counts and validation results between runs.

---

# 5. Log Retention and Access

## 5.1 Log Retention Period

**Operational log retention:** 1 year.

The retention period provides sufficient history for troubleshooting extraction problems, reviewing pipeline runs, and supporting operational monitoring.


## 5.2 Storage Location

Extraction metadata and operational logs should be stored in a controlled database table or designated pipeline logging storage associated with the VistaBalayan data pipeline.

The exact production logging location is not specified in the current technical metadata and must be finalized during implementation.

## 5.3 Access Permissions

Access to extraction logs should be limited to authorized personnel responsible for:

- Data pipeline maintenance
- System administration
- Data engineering
- Municipal tourism system administration

Public users should not have access to internal extraction logs.

## 5.4 Archiving

Logs that reach the end of their active retention period may be archived when required for auditing or operational history.

Archived logs must remain protected from unauthorized modification.

## 5.5 Deletion Rules

Operational logs must not be deleted before the defined retention period.

Logs must also be retained while they are required for:

- Troubleshooting
- Auditing
- Recovery
- Investigation of failed extraction runs

Deletion should occur only through an authorized retention process.

---

# 6. Extraction Data Contract and Naming Convention

## 6.1 Required Schema

The extraction data contract defines the expected source tables, fields, data types, identifiers, and documented constraints of the VistaBalayan Tourism Data Analytics and Decision Support Pipeline. The source data comes from the VistaBalayan PostgreSQL database and is retrieved using Python for the extraction stage.

| Source Table | Expected Fields | Data Types | Required Identifiers and Constraints |
|---|---|---|---|
| `establishments` | `id`, `name`, `type`, `total_rooms` | UUID, VARCHAR(150), VARCHAR(50), INTEGER | `id` — Primary Key; `name` and `type` — NOT NULL; `total_rooms` — DEFAULT 0 |
| `visitor_reports` | `id`, `establishment_id`, `report_date`, `male_visitors`, `female_visitors`, `total_visitors`, `residence_category`, `municipality`, `province`, `country` | UUID, UUID, DATE, INTEGER, INTEGER, INTEGER, VARCHAR(50), VARCHAR(100), VARCHAR(100), VARCHAR(100) | `id` — Primary Key; `establishment_id` — Foreign Key referencing `establishments.id`; `report_date` — NOT NULL; `total_visitors` — NOT NULL |
| `accommodation_reports` | `id`, `establishment_id`, `report_date`, `total_rooms`, `occupied_rooms`, `guest_check_ins`, `guest_nights`, `foreign_guest_check_ins`, `foreign_guest_nights` | UUID, UUID, DATE, INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, INTEGER | `id` — Primary Key; `establishment_id` — Foreign Key referencing `establishments.id`; `report_date` and `total_rooms` — NOT NULL |
| `room_occupancy_details` | `id`, `accommodation_report_id`, `room_type`, `number_of_rooms`, `occupied_rooms`, `check_ins`, `guest_nights` | UUID, UUID, VARCHAR(100), INTEGER, INTEGER, INTEGER, INTEGER | `id` — Primary Key; `accommodation_report_id` — Foreign Key referencing `accommodation_reports.id`; `room_type` — NOT NULL |

The expected fields and data types follow the source schema documented for VistaBalayan. Primary keys identify individual records, while documented foreign keys establish relationships between tables. Fields marked `NOT NULL` and fields with documented defaults must be checked against the source schema.

## 6.2 Naming Convention

The VistaBalayan extraction pipeline follows consistent naming rules to maintain readability and consistency across the PostgreSQL source tables, Python extraction scripts, and extracted datasets.

| Naming Rule | Specification |
|---|---|
| Column Naming Format | Use lowercase letters and `snake_case`, where multiple words are separated by underscores. Examples include `report_date`, `total_visitors`, and `accommodation_report_id`. |
| Abbreviations | Avoid unnecessary abbreviations and use descriptive names that represent the stored data. Existing source column names should be retained unless a justified mapping is documented. |
| Naming Consistency | Use the same column names consistently in the pipeline documentation, Python extraction scripts, and corresponding output fields. |
| Primary Key Naming | The documented tables use `id` as the primary key, such as `establishments.id`, `visitor_reports.id`, `accommodation_reports.id`, and `room_occupancy_details.id`. |
| Foreign Key Naming | Use the referenced entity name followed by `_id` for documented foreign-key fields. Examples include `establishment_id` and `accommodation_report_id`. |
| Date Field Naming | Use `_date` for fields that store dates, such as `report_date`. Retain the documented source field names. |

These naming conventions help keep extracted fields identifiable and consistent throughout the pipeline. Any approved changes to field names must be recorded in the source-to-standardized field mapping.

## 6.3 Source-to-Standardized Field Mapping

The source-to-standardized field mapping documents how source columns are represented in the extracted datasets. The VistaBalayan pipeline retains the documented source column names and data types unless a justified and documented transformation is required. The following table provides representative mappings from the documented source tables.

| Source Column | Standardized Column | Source Type | Target Type | Mapping Type |
|---|---|---|---|---|
| `establishments.id` | `id` | UUID | UUID | Direct mapping |
| `establishments.name` | `name` | VARCHAR(150) | VARCHAR(150) | Direct mapping |
| `establishments.type` | `type` | VARCHAR(50) | VARCHAR(50) | Direct mapping |
| `visitor_reports.id` | `id` | UUID | UUID | Direct mapping |
| `visitor_reports.establishment_id` | `establishment_id` | UUID | UUID | Direct mapping |
| `visitor_reports.report_date` | `report_date` | DATE | DATE | Direct mapping |
| `visitor_reports.total_visitors` | `total_visitors` | INTEGER | INTEGER | Direct mapping |
| `accommodation_reports.id` | `id` | UUID | UUID | Direct mapping |
| `accommodation_reports.report_date` | `report_date` | DATE | DATE | Direct mapping |
| `accommodation_reports.occupied_rooms` | `occupied_rooms` | INTEGER | INTEGER | Direct mapping |
| `room_occupancy_details.accommodation_report_id` | `accommodation_report_id` | UUID | UUID | Direct mapping |
| `room_occupancy_details.room_type` | `room_type` | VARCHAR(100) | VARCHAR(100) | Direct mapping |
| `room_occupancy_details.guest_nights` | `guest_nights` | INTEGER | INTEGER | Direct mapping |

The standardized column names must remain consistent throughout the extraction documentation, scripts, and output datasets. If a source column is renamed or its data type is converted, the mapping must be updated to identify the source field, standardized field, source type, target type, and mapping operation.

**Note:** The target types above represent direct mappings based on the documented source types. They should be verified against the actual extraction output requirements. The table provides representative examples rather than a complete mapping of every column.

### 6.4 Schema Consistency

The extraction process will check whether the source tables, column names, data types, required identifiers, and documented constraints match the data contract. Unexpected changes will be handled as follows:

- **Column Name Changes:** If a required column is renamed or unavailable, the issue will be flagged and recorded in the extraction log. Extraction must not proceed if the affected column is necessary for the process.
- **Data Type Changes:** If a column's data type differs from the documented schema, the change will be flagged for review to determine its effect on extraction and the expected output.
- **Missing Required Fields:** If a required column or identifier is missing, schema validation will fail, and the issue will be recorded in the extraction log.
- **Unexpected Additional Columns:** Additional columns will not automatically be included in the output unless they are reviewed and approved.
- **Foreign-Key Relationships:** The documented relationships between `visitor_reports`, `accommodation_reports`, `room_occupancy_details`, and `establishments` must be checked against the source schema.
- **Approved Schema Changes:** Approved changes will be documented and reflected in the Python extraction script when necessary.

Schema validation results and related errors will be recorded in the extraction logs to maintain consistency between the source database, extraction script, and output dataset.

---
