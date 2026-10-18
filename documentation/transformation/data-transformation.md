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



# 3. Data Cleaning Rules

Data cleaning is performed after profiling the extracted VistaBalayan tourism datasets to identify and address data quality issues before standardization and transformation. The cleaning process focuses on missing values, duplicate records, inconsistent text, invalid numeric values, and orphan records that may affect the accuracy and reliability of tourism data analytics.

The cleaning rules apply to the extracted `establishments.csv`, `visitor_reports.csv`, `accommodation_reports.csv`, and `room_occupancy_details.csv` files. Each rule is assigned a unique Rule ID to support traceability, monitoring, and documentation. The issues listed below correspond to the potential issues identified in Section 2 and must be confirmed against actual profiling results before being reported as detected findings.

## 3.1 Data Cleaning Rules Table

| Rule ID and Name | Target — Table and Column | Condition | Action | Justification |
|---|---|---|---|---|
| C-01: Trim Whitespace | All datasets — text columns | A text value contains leading or trailing spaces. | Remove leading and trailing whitespace from text values. Preserve meaningful spaces within names and descriptions. | Prevents inconsistent values and improves matching, grouping, and filtering. |
| C-02: Handle Missing Establishment Names | `establishments.name` | The establishment name is null, empty, or contains only whitespace. | Reject the record from the clean dataset and send it to quarantine for review. Do not assign a fabricated establishment name. | The establishment name is required to identify and manage an establishment correctly. |
| C-03: Handle Missing Establishment Types | `establishments.type` | The establishment type is null, empty, or contains only whitespace. | Quarantine the record for correction instead of assigning an unsupported type. | Establishment type is required for consistent classification and tourism reporting. |
| C-04: Detect Duplicate Establishment IDs | `establishments.id` | The same UUID appears in multiple records. | Keep one record only when the duplicate records are identical. If conflicting records share the same ID, quarantine the conflicting records for review rather than automatically choosing one. Log the duplicate count and affected IDs. | Ensures that each establishment has a unique identifier without discarding potentially important differences. |
| C-05: Detect Duplicate Visitor Reports | `visitor_reports.id` | The same report UUID appears more than once. | Keep one copy if all relevant fields are identical. If the records conflict, quarantine them for review. Log all duplicate detections. | Prevents duplicate reports from inflating visitor totals and affecting analytics. |
| C-06: Validate Visitor Report Dates | `visitor_reports.report_date` | The date is missing or cannot be parsed as a valid date. | Quarantine records with missing or invalid dates. Convert valid, recognizable date formats during standardization under Section 4. | A valid report date is necessary for time-based summaries and trend analysis. |
| C-07: Validate Visitor Counts | `visitor_reports.male_visitors`, `visitor_reports.female_visitors`, `visitor_reports.total_visitors` | A count is negative, fractional, or nonnumeric. | Convert valid whole-number representations to integers. Quarantine invalid values for correction. Do not automatically replace invalid counts with zero. | Prevents inaccurate visitor totals and avoids treating unknown values as confirmed zero counts. |
| C-08: Check Visitor Count Consistency | `visitor_reports.male_visitors`, `visitor_reports.female_visitors`, `visitor_reports.total_visitors` | All three values are present, but `total_visitors` does not equal `male_visitors + female_visitors`. | Flag the record for validation and quarantine it if the discrepancy cannot be resolved using an approved correction process. Log the discrepancy. | Helps maintain consistency between the reported visitor total and its gender-based breakdown. |
| C-09: Validate Visitor Report Establishment References | `visitor_reports.establishment_id` | The establishment ID is missing or does not match an existing `establishments.id`. | Quarantine the orphan report until the correct establishment reference is confirmed. Do not delete it silently. | Ensures visitor reports are associated with valid establishments. |
| C-10: Validate Accommodation Report Dates | `accommodation_reports.report_date` | The report date is missing or invalid. | Quarantine the record for correction. Convert valid dates to the required format under Section 4. | Accurate dates are necessary for accommodation monitoring and periodic reports. |
| C-11: Validate Accommodation Counts | `accommodation_reports.total_rooms`, `accommodation_reports.occupied_rooms`, `accommodation_reports.guest_check_ins`, `accommodation_reports.guest_nights`, `accommodation_reports.foreign_guest_check_ins`, `accommodation_reports.foreign_guest_nights` | A count is negative, fractional, or nonnumeric. | Convert valid whole-number representations to integers. Quarantine invalid values for review rather than replacing them with zero. | Ensures that room occupancy and guest activity statistics remain reliable. |
| C-12: Check Occupied Rooms Against Total Rooms | `accommodation_reports.total_rooms`, `accommodation_reports.occupied_rooms` | `occupied_rooms` exceeds `total_rooms`, or the room counts are otherwise logically inconsistent. | Flag the record for review. Quarantine it if the inconsistency cannot be resolved using the source report. | Prevents impossible or misleading room occupancy calculations. |
| C-13: Validate Accommodation Report Establishment References | `accommodation_reports.establishment_id` | The establishment ID is missing or does not match an existing `establishments.id`. | Quarantine the orphan report until the establishment reference is verified. Record the affected ID and reason. | Maintains referential integrity between establishments and accommodation reports. |
| C-14: Validate Room Occupancy Details References | `room_occupancy_details.accommodation_report_id` | The accommodation report ID is missing or does not match an existing `accommodation_reports.id`. | Quarantine the orphan room occupancy record until its parent report is identified. | Prevents room occupancy details from being associated with nonexistent accommodation reports. |
| C-15: Validate Room Occupancy Counts | `room_occupancy_details.number_of_rooms`, `room_occupancy_details.occupied_rooms`, `room_occupancy_details.check_ins`, `room_occupancy_details.guest_nights` | A count is negative, fractional, or nonnumeric. | Convert valid whole-number representations to integers. Quarantine invalid values for correction. | Ensures that room-level statistics are suitable for aggregation and analysis. |
| C-16: Check Occupied Rooms by Room Type | `room_occupancy_details.number_of_rooms`, `room_occupancy_details.occupied_rooms` | `occupied_rooms` exceeds `number_of_rooms`. | Flag the record for review and quarantine it if the source data cannot resolve the discrepancy. | Prevents room occupancy figures from exceeding the available rooms for a room type. |
| C-17: Standardize Text Whitespace and Invalid Characters | All datasets — text columns | Text contains control characters or invalid characters that are not appropriate for the field. | Remove unnecessary control characters and normalize whitespace. Preserve valid punctuation and characters in establishment names and location values. Quarantine values when the intended content cannot be determined safely. | Improves data consistency without damaging meaningful names or location information. |
| C-18: Validate Establishment Room Counts | `establishments.total_rooms` | The value is negative, fractional, or nonnumeric. | Convert valid whole-number representations to integers. Quarantine invalid values for review. | Ensures that establishment capacity information is valid for accommodation analysis. |

## 3.2 Missing and Null Value Handling

Missing values are handled according to the purpose and requirements of each field. Required identifiers, establishment names, establishment types, and report dates must not be replaced with invented values. Records missing these required fields are quarantined for review.

For count fields, a value of zero is valid only when the source data explicitly indicates that no visitors, rooms, check-ins, or guest nights were recorded. Null values must not automatically be converted to zero because a missing value may indicate incomplete reporting rather than the absence of activity.

Optional location fields, such as `municipality`, `province`, and `country`, may remain null when the information is unavailable. If a later transformation requires these fields, the pipeline must use an approved reference or mark the value as unknown without inventing a location.

## 3.3 Duplicate Detection and Record Retention

Duplicate detection is performed using the primary identifier of each dataset: `establishments.id`, `visitor_reports.id`, `accommodation_reports.id`, and `room_occupancy_details.id`.

When duplicate records have identical values across all relevant fields, the pipeline retains one copy and records the number of duplicate records removed. When records share an identifier but contain conflicting information, the pipeline does not automatically select the latest record because the documented source schema does not establish a reliable update timestamp for these datasets. Conflicting records are quarantined for review.

Records with different IDs are not automatically treated as duplicates merely because their other values are similar. Any additional business-level duplicate detection must use a documented rule and be verified before records are removed.

## 3.4 Invalid Values and Orphan Records

Invalid values include negative counts, fractional values in whole-number fields, unparseable dates, and logically inconsistent room or visitor counts. The pipeline validates these values and quarantines records that cannot be corrected safely. Valid values are retained and converted according to the standardization rules in Section 4.

Orphan records are records whose foreign-key values do not match an existing parent record. Visitor reports and accommodation reports must reference a valid establishment. Room occupancy details must reference a valid accommodation report. The pipeline quarantines orphan records until the reference can be verified or corrected. It must not create missing parent records or silently delete orphan records.

## 3.5 Cleaning Audit Trail and Logging

Every cleaning operation must be traceable. The pipeline records the rule ID, source dataset, affected record identifier when available, issue detected, action taken, processing timestamp, and processing outcome. Counts of records retained, corrected, quarantined, or removed must be maintained for reporting.

Records rejected from the clean output must be retained in a quarantine location or an equivalent recoverable record store. Duplicate removals must also be counted and logged. No record may be silently dropped during cleaning. Detailed logging requirements and processing metrics are documented in Sections 7 and 8.

## 3.6 Relationship to Data Profiling

The cleaning rules in this section are intended to address the potential issues described in Section 2. Before finalizing the pipeline, the data profiling process must confirm which issues actually exist in the extracted datasets. Rules that are not triggered should be recorded as checks performed with zero affected records, where applicable. Actual counts and percentages must be calculated from profiling and cleaning logs rather than estimated.


# 4. Standardization and Data Type Rules

Standardization ensures that the extracted VistaBalayan tourism datasets use consistent data types, formats, and reference values before being loaded into the processed database. This stage follows the cleaning rules defined in Section 3 and applies consistent representations to establishment information, visitor reports, accommodation reports, and room occupancy details.

The transformation process uses Python to validate and convert extracted CSV values according to the expected PostgreSQL data types and the business requirements of the VistaBalayan Tourism Data Analytics and Decision Support Pipeline. Original source values are not silently overwritten when conversion fails. Invalid records are logged and sent to quarantine for review in accordance with the cleaning and logging procedures.

## 4.1 Data Types

The following table defines the target data types for the important columns in the VistaBalayan datasets. The types are based on the documented source schema. UUIDs are retained as identifiers, dates are converted to valid date values, and count fields are represented as integers.


## 4.1 Data Types

The following table defines the target data types for important columns in the VistaBalayan datasets and specifies how the pipeline handles values that cannot be converted or validated successfully.


# 4. Standardization and Data Type Rules

Standardization ensures that the extracted VistaBalayan tourism datasets use consistent data types, formats, and reference values before they are loaded into the processed database. This stage follows the cleaning rules in Section 3 and applies consistent representations to establishment information, visitor reports, accommodation reports, and room occupancy details.

The transformation process uses Python to validate and convert values from the extracted CSV files according to the expected data types and business requirements of the VistaBalayan Tourism Data Analytics and Decision Support Pipeline. Values that cannot be converted or validated are flagged for review, logged, and excluded from the clean dataset until they are corrected and validated. Records are not silently deleted.

## 4.1 Data Types

The following table defines the target data types for the important columns in the VistaBalayan datasets and specifies what happens when a value cannot be converted or validated.


| Rule ID | Column | Source Format | Standard Format | On Failure |
|---|---|---|---|---|
| S-01 | `establishments.id` | UUID stored as text | UUID | Reject and log |
| S-02 | `establishments.name` | Text with leading or trailing spaces | Trimmed text, VARCHAR(150) | Reject and log if missing or invalid |
| S-03 | `establishments.type` | `hotel`, `HOTEL`, `Hotel` | Approved establishment type | Set to `UNKNOWN` if permitted; otherwise reject and log |
| S-04 | `establishments.total_rooms` | Numeric text | INTEGER | Reject and log |
| S-05 | `visitor_reports.report_date` | `MM/DD/YYYY` or `YYYY/MM/DD` | `YYYY-MM-DD` (DATE) | Reject and log |
| S-06 | `visitor_reports.male_visitors` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-07 | `visitor_reports.female_visitors` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-08 | `visitor_reports.total_visitors` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-09 | `visitor_reports.municipality` | Text with inconsistent casing or spaces | Standard municipality name | Set to `UNKNOWN` if allowed; otherwise retain NULL or reject according to the field requirement |
| S-10 | `visitor_reports.province` | Text with inconsistent casing or spaces | Standard province name | Set to `UNKNOWN` if allowed; otherwise retain NULL or reject according to the field requirement |
| S-11 | `visitor_reports.country` | Country name or alias | Standard country name | Set to `UNKNOWN` if allowed; otherwise retain NULL or reject according to the field requirement |
| S-12 | `visitor_reports.establishment_id` | UUID stored as text | UUID referencing an existing establishment | Reject and log |
| S-13 | `accommodation_reports.id` | UUID stored as text | UUID | Reject and log |
| S-14 | `accommodation_reports.report_date` | `MM/DD/YYYY` or `YYYY/MM/DD` | `YYYY-MM-DD` (DATE) | Reject and log |
| S-15 | `accommodation_reports.total_rooms` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-16 | `accommodation_reports.occupied_rooms` | Numeric text | INTEGER, nonnegative and not greater than total rooms | Reject and log |
| S-17 | `accommodation_reports.guest_check_ins` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-18 | `accommodation_reports.guest_nights` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-19 | `accommodation_reports.foreign_guest_check_ins` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-20 | `accommodation_reports.foreign_guest_nights` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-21 | `room_occupancy_details.id` | UUID stored as text | UUID | Reject and log |
| S-22 | `room_occupancy_details.accommodation_report_id` | UUID stored as text | UUID referencing an existing accommodation report | Reject and log |
| S-23 | `room_occupancy_details.room_type` | Text with inconsistent casing or spaces | Approved room-type value | Map to the standard value; reject and log if unrecognized and required |
| S-24 | `room_occupancy_details.number_of_rooms` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-25 | `room_occupancy_details.occupied_rooms` | Numeric text | INTEGER, nonnegative and not greater than number of rooms | Reject and log |
| S-26 | `room_occupancy_details.check_ins` | Numeric text | INTEGER, nonnegative | Reject and log |
| S-27 | `room_occupancy_details.guest_nights` | Numeric text | INTEGER, nonnegative | Reject and log |

## 4.2 Formats

All valid report dates are standardized to ISO 8601 format (`YYYY-MM-DD`), such as `2026-10-18`. Valid and unambiguous date formats are converted, while invalid dates are rejected and logged.

Visitor counts, room counts, check-ins, and guest nights must be nonnegative integers. Fractional, negative, or nonnumeric values are rejected and logged instead of being rounded or automatically replaced with zero.

Text fields are trimmed to remove unnecessary whitespace. Establishment names and location names retain their official spelling, while establishment types, room types, and residence categories are standardized using approved mappings. The current datasets contain no currency or decimal-valued fields, so currency conversion and rounding rules are not applicable.

## 4.3 Reference Values and Codes

Inconsistent values are mapped to approved standard values when their meanings are equivalent. For example, `hotel`, `HOTEL`, and `Hotel` may be standardized to `HOTEL`. Room types, residence categories, and location names follow verified reference values.

Unrecognized or ambiguous values are rejected and logged when they are required, or retained as `NULL` when optional and permitted by the target schema. UUID references are validated to ensure that visitor and accommodation reports reference existing establishments and room occupancy details reference existing accommodation reports.

## 4.4 Handling of Conversion Failures

Values that cannot be converted or validated are rejected from the clean output and logged with the rule ID, dataset, affected column, original value, and reason for failure. Missing required values, invalid dates, malformed UUIDs, and invalid numeric counts follow the cleaning rules in Section 3.

Rejected records are not silently deleted. They must be recorded for review and may be corrected and processed again after verification. The pipeline maintains counts of successful conversions, failed conversions, and rejected records for reporting and auditing under Sections 7 and 8.

