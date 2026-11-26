
# Stage 3: Data Load Documentation

## Objective

The objective of this stage is to load the approved transformed VistaBalayan datasets into a designated reporting database and verify their completeness, accuracy, and traceability. The loaded datasets will support tourism visitor monitoring, accommodation analysis, establishment performance evaluation, and historical tourism reporting.

This stage uses scheduled batch processing only and does not perform data extraction, cleaning, business transformations, or real-time loading.

## 1. Load Source and Target Specification

### 1.1 Load Input

The Load Stage receives only the approved datasets produced by the Transformation Stage. The current transformation output is stored in `pipeline/processed/vistabalayan_staging.sqlite`, which serves as the handover source for the proposed loading process.

The transformed datasets must be accompanied by metadata containing the transformation run ID, batch ID, batch window, record counts, validation results, and available checksums.

| **Transformed Dataset / Table** | **Target Table** |
| -------------------------------- | -------------------------------- |
| establishments | warehouse.establishments |
| visitor_reports | warehouse.visitor_reports |
| accommodation_reports | warehouse.accommodation_reports |
| room_occupancy_details | warehouse.room_occupancy_details |

**Proposed Input Location:** `pipeline/processed/vistabalayan_staging.sqlite`

The actual input tables and record counts must be identified through the approved Transformation Stage output and its handover metadata.

| **Batch Identifier** | **Specification / Example** |
| --------------------- | --------------------------- |
| Transformation Run ID | TRF-20261009-001 |
| Extraction Run ID | Referenced from the Extraction Stage metadata |
| Batch ID | BATCH-20261009 |
| Batch Window | Inherited from the Extraction Stage |
| Handover Status | APPROVED |
| Snapshot Type | Based on the approved transformation output |

The Transformation Stage must provide the approved datasets with their corresponding validation results and record counts. The loading process must verify that the input matches the handover metadata before proceeding.

The Load Stage must not re-extract source data or repeat any transformation procedures. It must use only the approved Transformation Stage output.

### 1.2 Target System

| **Item** | **Specification** |
| -------------------------- | --------------------------------------------------- |
| Target System | VistaBalayan Reporting Database |
| Purpose | Store validated tourism datasets for reporting, dashboards, and historical analysis |
| Database Management System | PostgreSQL (proposed) |
| Target Database | vistabalayan_warehouse (proposed) |
| Target Schema | warehouse |
| Audit Schema | pipeline_audit |
| Processing Type | Batch Processing |

The proposed reporting database will serve as a separate analytical data store for the ETL pipeline. It will contain validated tourism datasets used for reporting and analysis without directly modifying the operational database of the VistaBalayan application.

The proposed PostgreSQL target is separate from the application's existing PostgreSQL database managed through Supabase.

### 1.3 Load Method

| **Item** | **Specification** |
| ------------------------ | --------------------------------------------------- |
| Load Technology | Python and PostgreSQL SQL |
| Proposed Load Script | `pipeline/load.py` |
| Load Frequency | Daily |
| Proposed Load Schedule | 4:00 AM, Philippine Standard Time |
| Load Method | Bulk loading through PostgreSQL COPY and SQL INSERT |
| Write Strategy | Batch-based loading with transaction control |
| Expected Record Count | Based on the approved Transformation Stage metadata |
| Expected Completion Time | Within 30 minutes |

The loading process begins only after the Transformation Stage has completed its validation and received an approved handover status.

The transformed datasets are first loaded into temporary staging tables for structural and record-count validation. Once the staging data passes the required checks, the validated records are transferred to their corresponding target tables.

Target database changes must be performed within a controlled database transaction to prevent partially completed loads. If a critical validation or database operation fails, the transaction must be rolled back and the batch must not be marked as successfully loaded.

### 1.4 Load Scope and Order

The datasets must be loaded according to their relationships and dependencies. Establishment records should be loaded before visitor and accommodation records that reference them.

| **Load Order** | **Target Table** | **Dependency** |
| -------------- | ------------------------------ | ---------------------------- |
| 1 | establishments | None |
| 2 | visitor_reports | establishments |
| 3 | accommodation_reports | establishments |
| 4 | room_occupancy_details | accommodation_reports |

The expected number of records for each dataset must match the record counts provided in the approved Transformation Stage handover. Valid zero-row datasets may be accepted when confirmed by the handover metadata.

The loading process must preserve primary keys and foreign-key relationships to maintain consistency between establishments, visitor reports, accommodation reports, and room occupancy details.

The proposed target tables must follow the approved Transformation Stage data contract, including the expected column names, data types, and constraints.

### 1.5 Limitations and Assumptions

- Only approved transformed datasets from the Transformation Stage are accepted for loading.
- The Transformation Stage must provide complete handover metadata, including transformation run ID, batch ID, record counts, and validation results.
- The proposed PostgreSQL reporting database must be available before loading begins.
- The proposed database role, `vistabalayan_loader`, must have the required permissions to access staging tables, insert or update target records, and write load audit information.
- The loader must not have unnecessary administrative privileges or permission to modify the operational source database.
- Database credentials must be stored securely using environment variables and must not be included in the repository.
- Loading may be affected by database connection failures, storage limitations, database locks, or large data volumes.
- The proposed daily schedule is intended to minimize interference with normal system operations.
- Missing transformed datasets must not automatically be treated as empty datasets.
- Zero-row datasets may be accepted only when their absence of records is confirmed by the approved transformation metadata.
- Primary keys and foreign-key relationships must be preserved during loading.
- Incompatible data types, invalid values, and duplicate primary keys must be rejected rather than silently converted or overwritten.
- The loading process must retain sufficient audit information to identify the transformation batch, loading status, record counts, and any encountered errors.
- The target database structure and loading configuration must remain consistent with the approved Transformation Stage data contract.
- The proposed target database, schema, loading script, schedule, and write strategy must be verified before actual implementation.


# 2. Target Tables and Column Specification

The Data Load Stage uses four target tables in the proposed VistaBalayan Reporting Database under the `reporting` schema. These tables receive the approved transformed CSV datasets from the Transformation Stage. The target structure preserves the original identifiers and foreign key relationships to maintain data traceability and consistency.

The target tables are classified as staging tables because the pipeline retains the existing relational structure instead of creating separate dimension and fact tables.

## 2.1 Target Table Summary

| Table Name | Type | Primary Key | Foreign Keys | Key Constraints | Purpose |
|---|---|---|---|---|---|
| `reporting.establishments` | Staging | `id` | None | `id` PRIMARY KEY; `name` NOT NULL; `type` NOT NULL; `total_rooms` DEFAULT 0 | Stores tourism establishment information for classification, identification, and reporting. |
| `reporting.visitor_reports` | Staging | `id` | `establishment_id` → `reporting.establishments(id)` | `id` PRIMARY KEY; `report_date` NOT NULL; `total_visitors` NOT NULL; visitor counts DEFAULT 0 | Stores visitor counts and visitor-origin information for tourism monitoring and analysis. |
| `reporting.accommodation_reports` | Staging | `id` | `establishment_id` → `reporting.establishments(id)` | `id` PRIMARY KEY; `report_date` NOT NULL; `total_rooms` NOT NULL; count columns DEFAULT 0 | Stores accommodation reports and guest statistics for occupancy and accommodation analysis. |
| `reporting.room_occupancy_details` | Staging | `id` | `accommodation_report_id` → `reporting.accommodation_reports(id)` | `id` PRIMARY KEY; `room_type` NOT NULL; count columns DEFAULT 0 | Stores room-level occupancy information for detailed accommodation monitoring. |

## 2.2 `reporting.establishments`

**Table Type:** Staging

**Purpose:** Stores information identifying and classifying tourism establishments. It serves as the parent table for visitor and accommodation reports.

| Column | Data Type | Key / Constraint | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier for each establishment. |
| `name` | VARCHAR(150) | NOT NULL | Name of the tourism establishment. |
| `type` | VARCHAR(50) | NOT NULL | Establishment classification, such as hotel, resort, or other tourism service. |
| `address` | TEXT | — | Location or address of the establishment. |
| `status` | TEXT | — | Identifies the establishment's current status. |
| `reporting_mode` | TEXT | — | Identifies the reporting type handled by the establishment. |
| `total_rooms` | INTEGER | DEFAULT 0 | Total number of rooms for accommodation establishments. |

**Load Dependencies:**

- Match Key: `id`
- Batch ID Column: `batch_id` (proposed load-control column; not included in the current transformed CSV contract).
- History Columns: Not applicable. SCD Type 2 is not used because the pipeline preserves establishment records without implementing historical dimension tracking.
- Foreign Key Dependencies: None.
- Indexes: Primary key index on `id`; an index on `type` may be added to support establishment classification queries.

**Reason for Inclusion:** Establishment information is required to identify tourism establishments and connect visitor and accommodation reports to their corresponding establishments.

## 2.3 `reporting.visitor_reports`

**Table Type:** Staging

**Purpose:** Stores visitor arrival reports submitted by tourist establishments. The records support visitor monitoring, visitor-origin analysis, and tourism reporting.

| Column | Data Type | Key / Constraint | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier for each visitor report. |
| `establishment_id` | UUID | FOREIGN KEY → `establishments.id` | Identifies the establishment that submitted the report. |
| `report_date` | DATE | NOT NULL | Date covered by the visitor report. |
| `male_visitors` | INTEGER | DEFAULT 0 | Number of male visitors. |
| `female_visitors` | INTEGER | DEFAULT 0 | Number of female visitors. |
| `total_visitors` | INTEGER | NOT NULL | Total number of visitors. |
| `residence_category` | VARCHAR(50) | — | Visitor origin category, such as local, domestic, or foreign. |
| `municipality` | VARCHAR(100) | — | Municipality of visitor origin, if available. |
| `province` | VARCHAR(100) | — | Province of visitor origin, if available. |
| `country` | VARCHAR(100) | — | Country of visitor origin, if available. |

**Load Dependencies:**

- Match Key: `id`
- Batch ID Column: `batch_id` (proposed load-control column; not included in the current transformed CSV contract).
- History Columns: Not applicable. SCD Type 2 is not implemented.
- Foreign Key: `establishment_id` references `reporting.establishments(id)`.
- Indexes: Primary key index on `id`; indexes on `establishment_id` and `report_date` may be added for report retrieval and date-based analysis.

**Reason for Inclusion:** Visitor reports provide the primary data needed to monitor visitor volume, compare reporting periods, and analyze visitor origins.

## 2.4 `reporting.accommodation_reports`

**Table Type:** Staging

**Purpose:** Stores accommodation-related tourism reports submitted by establishments. These records support accommodation monitoring, guest statistics, and occupancy analysis.

| Column | Data Type | Key / Constraint | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier for each accommodation report. |
| `establishment_id` | UUID | FOREIGN KEY → `establishments.id` | Identifies the accommodation establishment that submitted the report. |
| `report_date` | DATE | NOT NULL | Date covered by the accommodation report. |
| `total_rooms` | INTEGER | NOT NULL | Total available rooms reported for the period. |
| `occupied_rooms` | INTEGER | DEFAULT 0 | Number of occupied rooms. |
| `guest_check_ins` | INTEGER | DEFAULT 0 | Number of guest check-ins during the report period. |
| `guest_nights` | INTEGER | DEFAULT 0 | Total guest nights during the report period. |
| `foreign_guest_check_ins` | INTEGER | DEFAULT 0 | Number of foreign guest check-ins. |
| `foreign_guest_nights` | INTEGER | DEFAULT 0 | Number of foreign guest nights. |

**Load Dependencies:**

- Match Key: `id`
- Batch ID Column: `batch_id` (proposed load-control column; not included in the current transformed CSV contract).
- History Columns: Not applicable. SCD Type 2 is not implemented.
- Foreign Key: `establishment_id` references `reporting.establishments(id)`.
- Indexes: Primary key index on `id`; indexes on `establishment_id` and `report_date` may be added for accommodation reporting and historical retrieval.

**Reason for Inclusion:** Accommodation reports provide the room capacity, occupancy, and guest statistics required for accommodation performance monitoring and tourism analysis.

## 2.5 `reporting.room_occupancy_details`

**Table Type:** Staging

**Purpose:** Stores detailed room occupancy information associated with accommodation reports. It provides room-level data for analyzing room availability, occupancy, check-ins, and guest nights.

| Column | Data Type | Key / Constraint | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier for each room occupancy detail record. |
| `accommodation_report_id` | UUID | FOREIGN KEY → `accommodation_reports.id` | Identifies the related accommodation report. |
| `room_type` | VARCHAR(100) | NOT NULL | Type or category of room. |
| `number_of_rooms` | INTEGER | DEFAULT 0 | Number of rooms under the room type. |
| `occupied_rooms` | INTEGER | DEFAULT 0 | Number of occupied rooms under the room type. |
| `check_ins` | INTEGER | DEFAULT 0 | Number of check-ins for the room type. |
| `guest_nights` | INTEGER | DEFAULT 0 | Number of guest nights for the room type. |

**Load Dependencies:**

- Match Key: `id`
- Batch ID Column: `batch_id` (proposed load-control column; not included in the current transformed CSV contract).
- History Columns: Not applicable. SCD Type 2 is not implemented.
- Foreign Key: `accommodation_report_id` references `reporting.accommodation_reports(id)`.
- Indexes: Primary key index on `id`; an index on `accommodation_report_id` may be added to support report-level occupancy retrieval.

**Reason for Inclusion:** Room occupancy details provide more specific accommodation information and support room-type occupancy analysis.

## 2.6 Keys, Relationships, and Load Considerations

The target tables preserve the primary and foreign key relationships established in the source and transformation stages.

| Relationship | Key Relationship | Purpose |
|---|---|---|
| Establishments → Visitor Reports | `visitor_reports.establishment_id` → `establishments.id` | Connects visitor reports to their reporting establishments. |
| Establishments → Accommodation Reports | `accommodation_reports.establishment_id` → `establishments.id` | Connects accommodation reports to their establishments. |
| Accommodation Reports → Room Occupancy Details | `room_occupancy_details.accommodation_report_id` → `accommodation_reports.id` | Connects room occupancy records to their parent accommodation reports. |

The loading order follows the parent-to-child relationships:

1. `reporting.establishments`
2. `reporting.visitor_reports`
3. `reporting.accommodation_reports`
4. `reporting.room_occupancy_details`

The original UUID identifiers are retained as primary keys. No additional surrogate keys or SCD Type 2 history columns are defined because the current pipeline does not implement a dimensional model or historical dimension tracking.

# 3. Load Strategy and Rules

The Data Load Stage uses incremental loading to transfer approved transformed datasets into the VistaBalayan Reporting Database. Existing records are identified using their original primary keys. New records are inserted, while existing records are updated through upsert operations. The process follows the parent-child table relationships and uses a single transaction for the entire batch to prevent partial loading.

## 3.1 Load Strategy per Target Table

| Table | Load Type | Write Logic | Match Key | On Failure |
|---|---|---|---|---|
| `reporting.establishments` | Incremental | Upsert (SCD Type 1) | `id` | Roll back entire batch, stop batch |
| `reporting.visitor_reports` | Incremental | Upsert (SCD Type 1) | `id` | Roll back entire batch, stop batch |
| `reporting.accommodation_reports` | Incremental | Upsert (SCD Type 1) | `id` | Roll back entire batch, stop batch |
| `reporting.room_occupancy_details` | Incremental | Upsert (SCD Type 1) | `id` | Roll back entire batch, stop batch |

## 3.2 Handling of Changing Data

The target tables use SCD Type 1, where existing records are overwritten with the latest approved transformed values. Previous versions are not retained because the current pipeline does not implement historical dimension tracking or SCD Type 2 columns.

The following rules apply:

- **New records:** Inserted when their primary key does not exist in the target table.
- **Existing records:** Updated when the same primary key is found.
- **Deleted or inactive records:** Retained with their existing status values. The load process does not automatically delete records.
- **Late-arriving records:** Loaded using their original identifiers and report dates when included in an approved transformation batch.
- **Schema differences:** The batch is rejected when required columns are missing, data types are incompatible, or the input schema does not match the target specification.

## 3.3 Load Order and Dependencies

The target tables are loaded according to their foreign key relationships to ensure that parent records are available before dependent records.

| Load Order | Target Table | Dependency |
|---|---|---|
| 1 | `reporting.establishments` | No foreign key dependency. |
| 2 | `reporting.visitor_reports` | References `reporting.establishments(id)`. |
| 3 | `reporting.accommodation_reports` | References `reporting.establishments(id)`. |
| 4 | `reporting.room_occupancy_details` | References `reporting.accommodation_reports(id)`. |

Records with missing or unmatched foreign key references are rejected during validation. The pipeline does not automatically create Unknown records because it preserves the original source identifiers and relationships.

## 3.4 Transaction and Rollback Handling

The entire batch is loaded within one database transaction. The transaction is committed only after all four target tables have been loaded successfully and their required constraints have been satisfied.

If a critical error occurs during loading, the entire transaction is rolled back and the batch is stopped. This prevents partially loaded records from remaining in the target database. The error details and affected batch are recorded in the proposed pipeline audit metadata.

## 3.5 Rerun and Idempotency

The loading process uses upsert operations with the original primary key (`id`) as the match key. This prevents duplicate records when the same transformed batch is processed more than once.

- **Successful rerun:** Existing records are updated instead of duplicated.
- **Failed batch:** The transaction is rolled back before the batch is retried.
- **Corrected batch:** The corrected approved dataset is processed again using the same match keys.
- **Batch tracking:** The batch ID and transformation run ID are recorded in the audit metadata for traceability.

The process does not use delete-by-batch-ID because the current transformed CSV datasets do not contain a `batch_id` column.


# 4. Pre-Load Validation Checks

The Pre-Load Validation Stage performs checks before writing approved transformed datasets into the VistaBalayan Reporting Database. These checks ensure that the target database is accessible, the target tables match the expected data structure, and the incoming datasets satisfy the requirements of the Transformation Stage handover. Loading proceeds only when all critical checks pass.

## 4.1 Pre-Load Validation Checklist

| Check Name | Target | Purpose | Validation Criteria | Severity |
|---|---|---|---|---|
| Target Connection | PostgreSQL reporting database | Ensure the target database is accessible before loading. | Database connection succeeds within the configured timeout. | Critical |
| Write Permissions | Loading database account | Ensure the loading account can write to the target schema and tables. | Account has the required INSERT and UPDATE privileges on all four target tables. | Critical |
| Target Table Existence | `reporting` schema | Ensure all required target tables are available. | `establishments`, `visitor_reports`, `accommodation_reports`, and `room_occupancy_details` exist. | Critical |
| Schema Match | All target tables | Prevent column and data type mismatches during loading. | All required columns exist and their data types match the approved target data contract. | Critical |
| Handover Completeness | Transformation handover metadata | Ensure all required input files and metadata are provided. | Four transformed CSV files, transformation run ID, extraction run ID, batch ID, batch window, record counts, and validation summary are available. | Critical |
| Handover Status | Transformation handover metadata | Ensure only approved transformed datasets are loaded. | Handover status is `APPROVED`. | Critical |
| Input Record Count | Four transformed CSV datasets | Confirm that incoming records match the approved transformation metadata. | Actual CSV record counts match the corresponding expected output record counts in the handover metadata. | Critical |
| Primary Key Validation | All target tables | Prevent duplicate or missing record identifiers. | Primary key values are present and unique within each input dataset. | Critical |
| Foreign Key Validation | Visitor, accommodation, and room occupancy tables | Ensure dependent records reference existing parent records. | Every `establishment_id` matches an establishment record, and every `accommodation_report_id` matches an accommodation report record. | Critical |
| Required Field Validation | All target tables | Prevent records with missing required values. | All columns defined as NOT NULL contain valid values. | Critical |
| Data Type Validation | All transformed CSV datasets | Prevent incompatible values from being written into target columns. | Incoming values can be converted to their corresponding target data types without errors. | Critical |
| Storage Availability | PostgreSQL reporting database | Ensure sufficient storage is available for the incoming batch. | Available database storage meets the estimated storage requirement for the batch. | Critical |
| Duplicate Batch Check | Proposed `pipeline_audit.load_log` | Prevent an already successful batch from being loaded again unintentionally. | The batch ID has no existing load record with `SUCCESS` status. | Critical |
| Batch Metadata Consistency | Transformation handover metadata | Ensure batch identification and reporting period are consistent. | Transformation run ID, parent extraction run ID, batch ID, and batch window are present and consistent across the handover. | Critical |

## 4.2 Validation Rules and Load Decision

The load process follows these rules after performing the pre-load checks:

- **Critical checks:** Any failed critical check stops the loading process. No records are written to the target tables.
- **Non-critical checks:** Warnings are recorded in the pipeline audit metadata but do not stop loading when the required conditions are satisfied.
- **Handover approval:** Only datasets with `APPROVED` status are accepted. Datasets marked `MANUAL_REVIEW`, `REJECTED`, or `FAILED` are not eligible for loading.
- **Record count verification:** The actual number of records in each transformed CSV file must match the expected output count in the approved handover metadata.
- **Duplicate batch prevention:** A batch previously recorded with `SUCCESS` status must not be loaded again as a new batch execution.
- **Validation failure:** Failed checks must be recorded with the affected target, validation result, and error details for correction before retrying.

