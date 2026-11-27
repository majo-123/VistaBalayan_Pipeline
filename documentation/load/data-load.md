
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


# 5. Post-Load Validation and Reconciliation

The Post-Load Validation Stage verifies whether the approved transformed datasets were successfully and accurately written into the VistaBalayan Reporting Database. It checks record counts, primary key uniqueness, referential integrity, required fields, and data consistency between the incoming batch and target tables.

These checks are performed after loading without introducing additional data cleaning or business transformations. Any detected issues are documented and handled according to the error-handling procedures in Section 8.

## 5.1 Post-Load Validation Checklist

| Check Name | Target | Purpose | Validation Criteria | Severity |
|---|---|---|---|---|
| Record Reconciliation | All four target tables | Detect missing, rejected, or extra records during loading. | Records received = records loaded + records rejected. Records rejected during the Transformation Stage are excluded. | Critical |
| Batch Row Count | All four target tables | Confirm that the expected records were loaded for the batch. | Number of records loaded for each table matches the approved transformation handover count, accounting for any load-level rejected records. | Critical |
| Primary Key Uniqueness | `establishments.id`, `visitor_reports.id`, `accommodation_reports.id`, `room_occupancy_details.id` | Prevent duplicate records in the target tables. | Duplicate primary key count = 0. | Critical |
| Referential Integrity | `visitor_reports.establishment_id` | Ensure visitor reports reference valid establishments. | All non-null foreign key values match `establishments.id`. | Critical |
| Referential Integrity | `accommodation_reports.establishment_id` | Ensure accommodation reports reference valid establishments. | All non-null foreign key values match `establishments.id`. | Critical |
| Referential Integrity | `room_occupancy_details.accommodation_report_id` | Ensure room occupancy details reference valid accommodation reports. | All non-null foreign key values match `accommodation_reports.id`. | Critical |
| Required Field Validation | Required columns in all target tables | Ensure required data is not missing after loading. | Number of NULL values in NOT NULL columns = 0. | Critical |
| Visitor Count Reconciliation | `visitor_reports` | Confirm visitor counts were not lost or changed during loading. | Sum of `total_visitors` in the approved input batch equals the sum of `total_visitors` loaded into the target for the same batch. | Critical |
| Accommodation Count Reconciliation | `accommodation_reports` | Confirm accommodation statistics were loaded accurately. | Source batch totals for applicable numeric columns equal their corresponding target totals for the same batch. | Critical |
| Room Occupancy Reconciliation | `room_occupancy_details` | Confirm room-level occupancy information was loaded accurately. | Source batch totals for applicable numeric columns equal their corresponding target totals for the same batch. | Critical |
| Load Error Check | Load execution logs and audit metadata | Identify errors or interruptions during loading. | No unresolved SQL errors, constraint violations, or interrupted operations are recorded for a successful batch. | Critical |
| Batch Status Verification | Proposed `pipeline_audit.load_log` | Confirm that the batch has completed successfully. | Batch status is recorded as `SUCCESS` only after all required post-load checks pass. | Critical |

## 5.2 Reconciliation Rules

The following rules are applied when verifying the loaded data:

- **Record reconciliation:** The number of records received by the Data Load Stage must equal the number of records loaded plus records rejected during loading. Records already rejected during transformation are excluded.
- **Row count verification:** The target record count must match the approved transformation output count, adjusted for any records rejected during loading.
- **Key validation:** Each target table must contain unique primary key values.
- **Referential integrity:** Every dependent record must reference an existing parent record through its foreign key.
- **Required fields:** All columns defined as NOT NULL must contain values.
- **Aggregate reconciliation:** Numeric totals in the approved transformed input must match the corresponding totals in the target database for the same batch.
- **Load completion:** A batch is considered successful only when all critical validation checks pass and no unresolved loading errors remain.


# 6. Load Metadata and Log Specification

The Data Load Stage maintains metadata and execution logs to monitor each batch loading operation and provide traceability between the Extraction, Transformation, and Data Load Stages. These records capture the batch information, target tables, loading results, validation outcomes, and errors encountered during execution.


| Field | Purpose | Example Value or Format |
|---|---|---|
| `run_id` | Unique identifier for each Data Load execution. | `LOAD_20261020_0400` |
| `transformation_run_id` | Identifies the Transformation Stage execution that produced the input datasets. | `TRF_20261019_2000` |
| `extraction_run_id` | Links the load batch to its original Extraction Stage execution through the transformation metadata. | `EXT_20261019_1930` |
| `batch_id` | Identifies the batch being loaded. | `BATCH_001` |
| `batch_window` | Specifies the reporting date range covered by the batch. | `2026-10-01 to 2026-10-18` |
| `table_name` | Identifies the target table receiving the records. | `reporting.visitor_reports` |
| `load_type` | Specifies the loading strategy applied to the target table. | `INCREMENTAL` |
| `load_start_ts` | Records the date and time when the loading operation starts. | `2026-10-20 04:00:02` |
| `load_end_ts` | Records the date and time when the loading operation finishes. | `2026-10-20 04:03:41` |
| `load_duration_sec` | Measures the total time required to complete the loading operation. | `219` |
| `records_received` | Number of records received from the approved transformed dataset. | `2,400` |
| `records_inserted` | Number of new records inserted into the target table. | `2,300` |
| `records_updated` | Number of existing records updated through the upsert operation. | `100` |
| `records_rejected` | Number of records that failed loading validation or database constraints. | `0` |
| `status` | Indicates the final result of the loading operation. | `SUCCESS` |
| `pre_load_result` | Records the outcome of the pre-load validation checks. | `PASS` |
| `post_load_result` | Records the outcome of the post-load validation checks. | `PASS` |
| `error_code` | Identifies the error encountered during loading, if applicable. | `NULL` |
| `error_message` | Describes the loading error for troubleshooting, if applicable. | `NULL` |
| `load_code_version` | Identifies the version of the Data Load implementation used. | `v1.0.0` |

*Note: The example values are illustrative and do not represent confirmed production execution logs.*


# 7. Log Retention, Rejected Data, and Access

The Data Load Stage maintains loading logs, audit records, and rejected data to support monitoring, troubleshooting, auditing, and batch recovery. These records are stored separately from the main reporting tables to prevent operational logging information from affecting the reporting datasets.

## 7.1 Log and Rejected Data Retention

| Item | Storage Location | Retention Period | Purpose |
|---|---|---|---|
| Operational Load Logs | Proposed `pipeline_audit.load_log` table | 90 days | Supports monitoring, troubleshooting, and investigation of recent loading executions. |
| Audit Records | Proposed `pipeline_audit` schema | 1 year | Maintains historical records of batch executions, validation results, and loading activities for auditing and traceability. |
| Rejected Records | Proposed `pipeline_audit.rejected_records` table or restricted rejection files | 90 days | Preserves records that failed during loading for investigation and correction. |
| Error Details | Proposed `pipeline_audit` schema | 90 days | Stores error codes, error messages, affected tables, and failure details for troubleshooting. |

The retention periods are proposed operational policies and must be finalized before implementation. Logs and rejected records must not be deleted before their retention periods expire or while they are still needed for troubleshooting, auditing, or recovery.

## 7.2 Access Permissions

Access to load logs, audit records, and rejected data is controlled through database roles and permissions.

| User or Role | Read | Write | Delete | Responsibility |
|---|---|---|---|---|
| Pipeline Operator | Yes | Yes | No | Monitors loading executions and reviews validation results and errors. |
| Database Administrator | Yes | Yes | Yes, when authorized | Manages database storage, access permissions, backups, and approved retention operations. |
| Municipal Tourism Officer | Authorized audit summaries only | No | No | Reviews relevant loading and data processing records for monitoring and administrative reference. |
| Public Users | No | No | No | No access to pipeline logs, audit records, or rejected data. |



## 7.3 Rejected Data Management


The following rules apply:

- Rejected records must not be inserted into the reporting tables.
- Each rejected record must be associated with its batch ID, transformation run ID, target table, rejection reason, and rejection timestamp.
- Rejected records must be stored in the proposed `pipeline_audit.rejected_records` table or a restricted rejection file location.
- Rejected records must remain available for investigation and correction during the retention period.
- Corrected records must undergo the Transformation Stage validation and receive an `APPROVED` handover status before being loaded again.
- Rejected records must not be automatically deleted or silently discarded.

Since the proposed loading strategy uses a single transaction for the entire batch, a critical loading failure causes the entire batch to roll back. Rejection details must therefore be captured separately so that the cause of failure can still be investigated after rollback.

## 7.4 Archiving and Deletion Rules

Operational logs, audit records, and rejected data follow defined retention and deletion procedures.

- **Operational logs:** Retained for 90 days and archived when required for ongoing investigations.
- **Audit records:** Retained for at least one year to support historical traceability and administrative review.
- **Rejected data:** Retained for 90 days or longer when required for unresolved issues or recovery.
- **Archiving:** Records needed beyond their operational retention period may be transferred to restricted archival storage.
- **Deletion:** Expired records may be deleted only after confirming that they are no longer required for troubleshooting, auditing, or recovery.
- **Responsibility:** Authorized database administrators perform approved archival and deletion operations.


## 7.5 Backup and Recovery

Before major loading operations or significant target database changes, a database backup or snapshot is recommended to support recovery in case of unexpected failures.

The following backup rules apply:

- The target PostgreSQL database should have a recent recoverable backup before major loading operations.
- Backup copies must be stored separately from the active reporting database.
- Backup access must be restricted to authorized database administrators.
- Recovery procedures must be tested to ensure that backups can be restored when needed.
- Failed batch transactions are rolled back before retrying, preventing partial records from remaining in the target tables.

## 7.6 Retention and Access Policy

The Data Load Stage follows these retention and access principles:

1. Operational logs, audit records, and rejected data must be retained according to their defined retention periods.
2. Records required for unresolved troubleshooting, auditing, or recovery must not be deleted even after the normal retention period has expired.
3. Only authorized personnel may access or modify pipeline logs and rejected data.
4. Deletion and archival operations must be performed by authorized database administrators.
5. Backups must be maintained separately from the active reporting database.
6. Retention, archival, and deletion activities must be documented for accountability.

These policies ensure that VistaBalayan load logs and rejected records remain available for operational monitoring, historical auditing, troubleshooting, and recovery.

# 8. Load Acceptance, Rollback, and Completion Rules

The Load Acceptance, Rollback, and Completion Stage defines the conditions for determining whether a batch has been successfully loaded into the VistaBalayan Reporting Database. It establishes the acceptance criteria, manual review requirements, failure handling procedures, and completion notifications to ensure that only validated data becomes available for reporting and analysis.

## 8.1 Decision Rules

The following rules determine the final status of each batch:

| Overall Condition | Acceptance Decision | Pipeline Action | Decision Type |
|---|---|---|---|
| All target tables pass critical pre-load and post-load validation checks, and record reconciliation matches. | `APPROVED` | Commit the transaction, mark the batch as complete, and make the loaded data available for reporting. | Automatic |
| All critical checks pass, but one or more non-critical warnings require confirmation. | `MANUAL_REVIEW` | Hold publication, record the warnings, and notify the responsible personnel for review. | Manual |
| One or more critical validation checks fail before or after loading. | `REJECTED` | Roll back the entire batch transaction, record the failure details, and stop the loading process. | Automatic |
| Database connection, storage, or temporary system availability issues prevent loading. | `FAILED` | Roll back the transaction, record the error, and perform the allowed retry procedure. | Automatic |

## 8.2 Validation Summary and Final Decision

The following example illustrates how the overall batch decision is determined based on the validation results of the four target tables.

| Validation Summary | Result |
|---|---|
| `reporting.establishments` load | PASS |
| `reporting.visitor_reports` load | PASS |
| `reporting.accommodation_reports` load | PASS |
| `reporting.room_occupancy_details` load | PASS |
| Pre-load validation | PASS |
| Post-load validation | PASS |
| Record reconciliation | PASS |
| Overall Load | APPROVED |

The final batch status is determined by the combined validation results. A batch is approved only when all critical checks pass, record reconciliation matches, and the transaction is successfully committed. Batches requiring review or experiencing critical failures must follow the corresponding manual review or rejection procedures before their data can be made available for reporting.

# 9. Common Load Problems and Mitigation

The Data Load Stage may encounter several operational and technical problems while transferring approved transformed tourism datasets into the VistaBalayan Reporting Database. These problems may affect batch completion, data accuracy, referential integrity, database availability, and reporting reliability.

This section identifies potential loading problems based on the proposed PostgreSQL target database, Python-based loading script, incremental loading strategy, and scheduled batch processing. Each problem includes its possible causes, impact on the loading process, and proposed mitigation to support reliable data loading, troubleshooting, and recovery.

The following problems and mitigation procedures are considered in the design of the Data Load Stage.

## 9.1 Common Load Problems and Mitigation Table

| Problem | Possible Cause | Impact on the Load Process | Proposed Solution or Mitigation |
|---|---|---|---|
| **Database Connection Failure** | The PostgreSQL reporting database is unavailable, network connectivity is interrupted, or database connection credentials are incorrect. | The loading script cannot establish a connection to the target database. The batch cannot proceed, and no records are transferred. | Configure connection timeouts and controlled retry attempts. Verify database availability, network connectivity, and environment-based credentials before executing the load. Record connection failures in the pipeline audit logs. |
| **Schema or Column Mismatch** | The transformed CSV datasets contain missing columns, unexpected column names, or incompatible data types compared with the target table structure. | The loading operation may fail during data insertion or cause records to be rejected because the input does not follow the approved target data contract. | Perform schema validation before loading. Compare incoming column names and data types against the target table specifications. Reject the batch when required columns or data structures do not match, and coordinate corrections with the Transformation Stage. |
| **Duplicate Records During Batch Rerun** | The same transformation batch is submitted more than once, or the previous loading execution is repeated without checking its completion status. | Duplicate records may affect tourism reports and produce inaccurate visitor totals or accommodation statistics if duplicate identifiers are not properly handled. | Use the original primary key (`id`) as the matching key for UPSERT operations. Check the batch ID against the pipeline audit log before loading. Prevent an already successful batch from being executed as a new batch. |
| **Foreign Key Constraint Violation** | Visitor or accommodation reports reference establishment IDs that do not exist in the target table, or room occupancy details reference missing accommodation reports. | The database rejects dependent records because their parent records are unavailable. This can cause the loading transaction to fail. | Follow the required parent-to-child loading order: establishments, visitor reports, accommodation reports, and room occupancy details. Validate foreign key references before insertion and record unmatched references for investigation. Do not automatically create unknown parent records. |
| **Partial Load Due to Unexpected Interruption** | The loading script stops unexpectedly because of a server crash, application termination, or database interruption during batch execution. | Some datasets may be written before the interruption, resulting in incomplete or inconsistent target data if transaction control is not properly implemented. | Execute the entire batch within a controlled database transaction. Commit only after all four target tables pass the required checks. Roll back the transaction when a critical error occurs, then investigate and retry the failed batch. |
| **Input Record Count Mismatch** | The transformed CSV files are incomplete, records are missing, or the actual record count differs from the approved Transformation Stage metadata. | The reporting database may receive incomplete tourism information, affecting the accuracy of visitor monitoring and historical reports. | Compare the actual input record counts with the expected counts in the approved handover metadata before loading. Stop the process when counts do not match and request verification of the transformed output. |
| **Invalid Data Types or Missing Required Values** | Transformed datasets contain invalid UUIDs, incorrect date formats, non-numeric values in integer columns, or missing values in required fields. | The database may reject records because they violate the target table's data types or NOT NULL constraints. Loading may be interrupted by validation or database errors. | Validate data types, UUID formats, date values, and required fields before insertion. Reject incompatible records or batches according to the validation rules, record the specific errors, and request corrected approved datasets from the Transformation Stage. |
| **Target Database Lock or Resource Contention** | Another database operation is accessing the target tables, long-running queries are executing, or multiple processes are attempting to modify the same records. | The loading process may experience delays, lock waits, transaction timeouts, or unsuccessful database operations. | Schedule batch loading during off-peak hours, maintain the proposed 4:00 AM execution schedule, and configure appropriate database statement and lock timeouts. Monitor long-running database transactions and retry when the target database becomes available. |
| **Insufficient Database Storage** | The reporting database has limited available storage, accumulated historical records, or insufficient space for temporary staging tables and incoming datasets. | The loading operation may fail during bulk insertion or transaction execution. The batch may not complete and must not be marked as successful. | Monitor available database storage before loading. Estimate the storage requirements of incoming datasets, maintain sufficient database capacity, and review storage utilization regularly. Record storage-related failures and retry after the issue is resolved. |
| **Slow Batch Loading Performance** | Large transformed datasets, inefficient SQL operations, row-by-row insertion, or excessive database resource usage increase loading time. | The batch may exceed its expected completion time of 30 minutes, delay reporting availability, and interfere with other database operations. | Use PostgreSQL COPY for bulk loading into temporary staging tables and SQL INSERT with UPSERT logic for transferring validated records into target tables. Monitor execution duration and optimize database queries and indexes when necessary. |
| **Audit Log or Metadata Recording Failure** | The pipeline audit schema is unavailable, the loading account lacks write permissions, or an error occurs while recording batch execution details. | Batch execution results may not be properly recorded, making it difficult to trace loading activities, identify failures, and verify whether a batch was successfully completed. | Verify audit schema availability and write permissions before loading. Record the run ID, transformation run ID, batch ID, record counts, execution timestamps, and validation results. Do not mark a batch as successful without the required audit information. |
| **Incorrect or Incomplete Batch Handover** | The Transformation Stage provides missing datasets, incomplete metadata, an unapproved handover status, or inconsistent batch identifiers. | The loading process may use incomplete or unverified input, resulting in inaccurate records or loss of traceability between pipeline stages. | Require all four transformed datasets and complete handover metadata before loading. Verify the transformation run ID, extraction run ID, batch ID, batch window, record counts, validation results, and APPROVED handover status. Stop loading when required information is missing or inconsistent. |