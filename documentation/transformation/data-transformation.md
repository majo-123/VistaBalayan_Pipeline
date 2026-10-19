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


## 2. Data Profiling and Issue Identification

Before defining the cleaning and transformation rules, the extracted data from the VistaBalayan Tourism System is examined to identify potential data quality issues. The profiling process covers the four source datasets: `establishments`, `visitor_reports`, `accommodation_reports`, and `room_occupancy_details`.

The purpose of data profiling is to identify issues involving missing values, duplicate identifiers, inconsistent formats, invalid numeric values, and incorrect relationships between datasets. These findings help determine the appropriate cleaning, standardization, validation, or rejection procedures to be applied before the data proceeds to the Load stage.

For each identified or anticipated issue, the affected table and column, issue type, sample value, approximate percentage of affected records, and planned treatment are documented. Since the percentages below are preliminary estimates rather than measured profiling results, they should be updated when actual profiling results become available. The rule references should correspond to the specific rules documented in Sections 3, 4, and 5.

### 2.1 Data Profiling and Issue Identification Table

| Table or File | Column Affected | Issue Type | Example of the Issue | Approximate Affected Records | Planned Treatment |
|---|---|---|---|---|---|
| `establishments.csv` | `name` | Missing values | Empty or null establishment name | 1–3% (estimated) | Flag records with missing required names for review or quarantine according to the required-field validation rule in Section 3. |
| `establishments.csv` | `type` | Inconsistent formats | `Hotel`, `HOTEL`, `hotel` | 5–10% (estimated) | Standardize text casing and map establishment types to consistent reference values under Section 4. |
| `establishments.csv` | `id` | Duplicate values | The same UUID appears more than once | 0–1% (estimated) | Check identifier uniqueness and flag duplicate records for investigation under Section 3. |
| `visitor_reports.csv` | `report_date` | Mixed date formats | `2026/10/18`, `2026-10-18` | 1–5% (estimated) | Standardize valid dates to ISO 8601 format (`YYYY-MM-DD`) under Section 4. |
| `visitor_reports.csv` | `male_visitors`, `female_visitors`, `total_visitors` | Invalid numeric values | `-5`, `2.5`, `abc` | 1–3% (estimated) | Validate integer and nonnegative count requirements; flag invalid records under Sections 3 and 4. |
| `visitor_reports.csv` | `establishment_id` | Invalid foreign-key reference | An ID that does not exist in `establishments.csv` | 0–2% (estimated) | Validate establishment references and flag unmatched IDs under Section 3. |
| `visitor_reports.csv` | `municipality`, `province`, `country`, if present | Inconsistent formats | `Balayan`, `BALAYAN`, `balayan` | 5–15% (estimated) | Standardize text formatting and apply reference-value mappings where applicable under Section 4. |
| `accommodation_reports.csv` | `total_rooms`, `occupied_rooms`, `guest_check_ins`, `guest_nights`, if present | Invalid numeric values | Negative counts or decimal values where integers are required | 1–3% (estimated) | Validate numeric types and nonnegative count requirements; flag invalid records under Sections 3 and 4. |
| `accommodation_reports.csv` | `report_date` | Missing or invalid values | Empty report date or an unparseable date | 1–3% (estimated) | Apply required-field and date validation under Sections 3 and 4. |
| `room_occupancy_details.csv` | `room_type` | Inconsistent formats | `Deluxe`, `DELUXE`, `deluxe` | 5–10% (estimated) | Standardize room-type labels while preserving their intended meaning under Section 4. |
| `room_occupancy_details.csv` | `accommodation_report_id` | Invalid foreign-key reference | An ID that does not exist in `accommodation_reports.csv` | 0–2% (estimated) | Validate the relationship between room occupancy details and accommodation reports under Section 3. |
| `room_occupancy_details.csv` | `number_of_rooms`, `occupied_rooms`, `check_ins`, `guest_nights`, if present | Invalid numeric values | Negative room counts or decimal check-in counts where integers are required | 1–3% (estimated) | Validate numeric types and nonnegative count requirements under Sections 3 and 4. |

The estimated percentages provide preliminary targets for identifying and discussing possible data quality issues. They do not represent confirmed defects in the extracted records. During implementation, the profiling results should be used to replace these estimates with observed counts or percentages.

The identified issues will guide the cleaning rules in Section 3, the standardization and transformation rules in Section 4, and the validation and reconciliation procedures in Section 5. Records that cannot be corrected reliably should be flagged, rejected, or quarantined according to the applicable rules.

# 3. Data Cleaning Rules

Data cleaning is performed after profiling the extracted VistaBalayan tourism datasets to identify and address data quality issues before standardization and transformation. The cleaning process focuses on missing values, duplicate records, inconsistent text, invalid numeric values, and orphan records that may affect the accuracy and reliability of tourism data analytics.

The cleaning rules apply to the extracted `establishments.csv`, `visitor_reports.csv`, `accommodation_reports.csv`, and `room_occupancy_details.csv` files. Each rule is assigned a unique Rule ID to support traceability, monitoring, and documentation. The issues listed below correspond to the potential issues identified in Section 2 and must be confirmed against actual profiling results before being reported as detected findings.

## 3.1 Data Cleaning Rules Table

| Rule ID and Name | Target | Condition | Action | Justification |
|---|---|---|---|---|
| C-01: Trim Whitespace | All text columns in all four datasets | A text value contains leading or trailing whitespace. | Remove leading and trailing whitespace while preserving meaningful internal spaces. | Prevents mismatches during comparisons, filtering, and record matching. |
| C-02: Required Establishment Name | `establishments.name` | The establishment name is missing, null, or blank after trimming. | Reject the affected record to quarantine for review. | An establishment name is necessary to identify and manage tourism establishments. |
| C-03: Required Establishment Type | `establishments.type` | The establishment type is missing, null, or blank after trimming. | Reject the affected record to quarantine for review. | Establishment type supports tourism categorization and reporting. |
| C-04: Duplicate Establishment ID | `establishments.id` | Multiple records share the same establishment ID. | If the records are identical, retain one record and count the duplicate copies removed. If values conflict, quarantine the conflicting records for review. | Prevents duplicate establishment entries without arbitrarily discarding conflicting information. |
| C-05: Duplicate Visitor Report ID | `visitor_reports.id` | Multiple records share the same visitor report ID. | Retain one copy when duplicate records are identical. Quarantine conflicting records instead of automatically choosing one. | Maintains report uniqueness and prevents inaccurate visitor totals. |
| C-06: Required Visitor Report Date | `visitor_reports.report_date` | The report date is missing, null, blank, or invalid. | Quarantine the affected record if the date cannot be reliably recovered from the source. | A valid reporting date is necessary for chronological analysis and period-based reports. |
| C-07: Invalid Visitor Counts | Visitor count columns in `visitor_reports`, including total, male, and female visitor counts | A count is negative, nonnumeric, or contains a fractional value when only whole visitors are permitted. | Correct only when the source representation can be safely interpreted as a valid whole number. Otherwise, quarantine the record. Do not replace missing or invalid counts with zero automatically. | Prevents inaccurate visitor totals and avoids inventing values not supported by the source data. |
| C-08: Visitor Count Consistency | Total, male, and female visitor count columns in `visitor_reports` | All relevant counts are present, but the total does not equal the male count plus the female count. | Flag the record for review and quarantine it if the inconsistency cannot be resolved using the source data. | Helps ensure that reported visitor totals are internally consistent. |
| C-09: Orphan Visitor Report | `visitor_reports.establishment_id` | The establishment ID is missing or does not match an existing `establishments.id`. | Quarantine the affected visitor report and log the unmatched foreign key. | Ensures each visitor report is associated with a valid establishment. |
| C-10: Required Accommodation Report Date | `accommodation_reports.report_date` | The report date is missing, null, blank, or invalid. | Quarantine the affected record if the date cannot be reliably recovered from the source. | Enables accurate accommodation reporting and time-based analysis. |
| C-11: Invalid Accommodation Counts | `accommodation_reports.total_rooms`, `occupied_rooms`, `guest_check_ins`, `guest_nights`, `foreign_guest_check_ins`, and `foreign_guest_nights` | A count is negative, nonnumeric, or fractional when a whole-number value is required. | Correct safely interpretable values; otherwise, quarantine the affected record. Do not silently substitute zero. | Prevents invalid accommodation figures from affecting occupancy and visitor analysis. |
| C-12: Accommodation Count Consistency | `accommodation_reports.total_rooms` and `occupied_rooms` | Occupied rooms exceed total rooms, or the values are otherwise inconsistent. | Flag the record and quarantine it if the inconsistency cannot be resolved from the source data. | Prevents implausible room occupancy figures from affecting tourism analytics. |
| C-13: Orphan Accommodation Report | `accommodation_reports.establishment_id` | The establishment ID is missing or does not match an existing `establishments.id`. | Quarantine the affected accommodation report and log the unmatched foreign key. | Ensures accommodation reports are linked to valid establishments. |
| C-14: Orphan Room Occupancy Record | `room_occupancy_details.accommodation_report_id` | The accommodation report ID is missing or does not match an existing `accommodation_reports.id`. | Quarantine the affected room occupancy record and log the unmatched foreign key. | Maintains referential integrity between room occupancy details and their parent reports. |
| C-15: Invalid Room Occupancy Counts | `room_occupancy_details.number_of_rooms`, `occupied_rooms`, `check_ins`, and `guest_nights` | A count is negative, nonnumeric, or fractional when a whole-number value is required. | Correct safely interpretable values; otherwise, quarantine the affected record. | Ensures room occupancy data contains valid count values for analysis. |
| C-16: Room Occupancy Consistency | `room_occupancy_details.number_of_rooms` and `occupied_rooms` | The occupied room count exceeds the total number of rooms recorded for the same detail. | Flag the record and quarantine it if the inconsistency cannot be resolved from the source data. | Prevents inconsistent room-level figures from distorting occupancy analysis. |
| C-17: Invalid Characters and Whitespace | All text columns in all four datasets | Text contains unwanted control characters or irregular whitespace that interferes with processing. | Remove inappropriate control characters and normalize whitespace where safe. Preserve valid letters, punctuation, and meaningful characters. Quarantine ambiguous values that cannot be corrected safely. | Improves data consistency without damaging legitimate establishment names or other text values. |
| C-18: Invalid Establishment Room Count | `establishments.total_rooms` | The room count is negative, nonnumeric, or fractional when a whole-number value is required. | Correct safely interpretable values; otherwise, quarantine the affected record. | Ensures establishment room capacity is suitable for accommodation-related analysis. |

### 3.2 Handling Missing and Null Values

Missing values are handled according to the purpose and requirements of each field. Required fields, such as establishment names, establishment types, and report dates, must contain valid information. Records with missing required values should be quarantined when the missing information cannot be reliably recovered.

Optional fields, such as `municipality`, `province`, and `country`, may remain null when the source does not provide the information and the field is not required for processing. Missing values must not automatically be replaced with zero, an empty string, or an assumed value because doing so could misrepresent the original tourism data.

### 3.3 Duplicate Detection and Removal

Duplicate detection uses the primary identifiers of each dataset: `establishments.id`, `visitor_reports.id`, `accommodation_reports.id`, and the primary identifier of `room_occupancy_details`.

When records have the same identifier and identical values, one copy is retained and the number of duplicate copies removed is recorded. When records share an identifier but contain conflicting values, the pipeline must not arbitrarily select the latest record unless a reliable update timestamp and an approved selection rule are available. Conflicting records should be quarantined for review.

Records with different identifiers must not be treated as duplicates solely because some of their field values are similar.

### 3.4 Invalid Values and Orphan Records

Invalid values are evaluated according to the expected meaning of each field. Counts must be valid, nonnegative whole numbers where applicable, and room occupancy values must satisfy the relevant consistency checks. Values that can be safely interpreted may be corrected; values that remain invalid must be flagged and quarantined.

Orphan records are records whose foreign keys do not match an existing parent record. These include visitor reports and accommodation reports without a matching establishment, as well as room occupancy details without a matching accommodation report. The pipeline must not create missing parent records or silently delete orphan records. Each affected record must be counted, logged, and made available for review.

### 3.5 Cleaning Audit Trail and Logging

Every cleaning action must be traceable. Records that are corrected, deduplicated, rejected, or quarantined must be counted and logged so the project team can review the outcome of each rule.

The cleaning log should capture the rule ID, dataset name, affected record identifier, detected issue, action taken, processing timestamp, and outcome. Summary counts should distinguish records retained, corrected, quarantined, and removed as confirmed duplicates. These records support the logging and error-handling requirements described in Sections 7 and 8.

The exact logging fields and quarantine mechanism must be confirmed against the actual pipeline implementation. If a feature has not yet been implemented, it should be identified as a planned requirement rather than reported as an existing capability.

### 3.6 Relationship to Data Profiling

Section 2 identifies potential data quality issues through data profiling, while this section defines the cleaning response for each issue. The rule IDs provide a traceable link between identified problems and the actions intended to address them.

After cleaning, the pipeline should record the number of records processed, corrected, retained, quarantined, and removed as duplicates. These results can then be used in Section 4 for standardization and data type conversion, as well as in the validation and reconciliation process. Any estimated issue percentages from Section 2 must be distinguished from actual counts measured during execution.

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


## 5. Business Transformation Rules

This stage transforms cleaned VistaBalayan tourism data into business-ready data for visitor monitoring, accommodation analysis, and monthly tourism reporting. The rules include derived columns, joins, aggregations, and filtering. Each rule is applied after data cleaning, and records excluded by business rules are counted and logged with their corresponding reasons.

### 5.1 Business Transformation Rules

| Rule ID | Input Columns | Logic or Formula | Output Column | Business Reason |
|---|---|---|---|---|
| B-01 | `male_visitors`, `female_visitors` | Calculate the sum of male and female visitors. Compare the result with the recorded `total_visitors`. | `calculated_total_visitors` | Supports visitor count validation and consistent reporting. |
| B-02 | `report_date` | Extract the year and month from the report date. | `report_year`, `report_month` | Enables monthly and yearly tourism reporting. |
| B-03 | `report_date` | Extract the calendar date from the valid report date. | `report_day` | Supports daily visitor monitoring and daily aggregation. |
| B-04 | `establishment_id` | Join visitor reports with establishment records using `establishment_id`. Use an inner join for business-ready records; log unmatched reports as excluded records. | `establishment_name`, `establishment_type` | Identifies the establishment associated with each visitor report. |
| B-05 | `establishment_id` | Join accommodation reports with establishment records using `establishment_id`. Use an inner join for business-ready records; log unmatched reports as excluded records. | `establishment_name`, `establishment_type` | Connects accommodation information to the correct establishment. |
| B-06 | `total_rooms`, `occupied_rooms` | Calculate `(occupied_rooms / total_rooms) × 100` when `total_rooms` is greater than zero. | `occupancy_rate` | Measures room utilization for accommodation analysis. |
| B-07 | `number_of_rooms`, `occupied_rooms` | Calculate `(occupied_rooms / number_of_rooms) × 100` when `number_of_rooms` is greater than zero. | `room_type_occupancy_rate` | Supports analysis of occupancy by room type. |
| B-08 | `report_year`, `report_month`, `establishment_id`, `total_visitors` | Group valid visitor reports by year, month, and establishment. Sum `total_visitors`. | `monthly_visitors` | Summarizes visitor counts per establishment for monthly reporting. |
| B-09 | `report_year`, `report_month`, `establishment_id`, `occupied_rooms`, `total_rooms` | Group accommodation reports by year, month, and establishment. Aggregate occupied rooms and total rooms using sums, then calculate the monthly occupancy rate from the aggregated values. | `monthly_occupied_rooms`, `monthly_total_rooms`, `monthly_occupancy_rate` | Provides monthly accommodation and room utilization summaries. |
| B-10 | `report_year`, `report_month`, `municipality`, `province`, `country`, `total_visitors` | Group visitor records by year, month, and visitor origin. Sum `total_visitors`. | `monthly_visitors_by_origin` | Identifies visitor origins and supports monthly origin comparisons. |
| B-11 | `total_rooms`, `occupied_rooms`, `number_of_rooms` | Exclude records with invalid negative counts or occupied rooms exceeding the corresponding total rooms. Count and log each exclusion with its reason. | Filtered business-ready records | Prevents invalid occupancy data from affecting tourism reports. |
| B-12 | `report_date`, `establishment_id` | Exclude records identified as invalid or ineligible under approved business rules. Record the number of excluded records and the reason. | Filtered business-ready records | Ensures reports use eligible and verified tourism data. |

### 5.2 Joins and Aggregations

Visitor reports are joined with establishment records using `establishment_id`. Accommodation reports are joined with establishment records using the same key, while room occupancy details are linked to accommodation reports through `accommodation_report_id`. These relationships provide establishment and room-level context for tourism analysis.

Monthly visitor summaries are grouped by reporting year, reporting month, and establishment. Visitor-origin summaries are grouped by reporting year, reporting month, and origin. Monthly accommodation summaries use the reporting year, reporting month, and establishment as grouping keys. Counts are aggregated using `SUM()`. Occupancy rates are calculated from aggregated occupied-room and total-room counts rather than averaging individual report percentages.

Records without valid matching parent records are excluded from the corresponding business-ready output and logged. They are not silently deleted from the extracted source data.

### 5.3 Filtering and Conditional Logic

Only records that pass the cleaning rules and satisfy the applicable business conditions are included in the transformed output. Negative visitor counts, invalid room counts, occupied rooms exceeding total rooms, and records with unresolved required relationships are excluded and logged with the relevant rule ID and reason.

Occupancy rates are calculated only when the applicable total-room value is greater than zero. When the denominator is zero, the occupancy rate is left as `NULL` and the condition is logged rather than dividing by zero or reporting an inaccurate percentage.

No cancellation or other exclusion status is assumed because such a field is not included in the documented source schema. If additional business exclusions are established, they must be applied during this stage and their counts and reasons recorded.

### 5.4 Dimensional Modeling

The pipeline may organize the transformed data into dimensions and fact tables if dimensional modeling is required by the implementation. A possible structure includes `dim_establishment`, `dim_date`, `fact_visitor_reports`, and `fact_accommodation_reports`. Dimension tables describe establishments and dates, while fact tables store visitor and accommodation measurements.

Surrogate keys may be generated for dimension records when required by the selected target schema. The establishment's source UUID can be retained as a business key for traceability. Changes to establishment attributes should follow the approved update policy; historical versions should only be maintained if Slowly Changing Dimension Type 2 is implemented. These dimensional structures are proposed unless they are already part of the actual pipeline implementation.

### 5.5 Business Transformation Output

The transformed datasets are intended to support daily monitoring, monthly tourism reports, visitor-origin analysis, and accommodation occupancy analysis. Each transformation must be traceable through its rule ID, input data, output columns, and logged exclusions or failures. The resulting datasets are passed to the next pipeline stage for loading or storage according to the project's configured target database.


## 6. Transformed Data Contract and Naming Convention

The transformation contract defines the structure and format of the data that will be received by the Load Stage. Unlike the extraction contract, which describes the data retrieved from the VistaBalayan source system, this contract identifies the target columns, data types, and transformations applied during processing. It may include standardized fields and derived columns needed for reporting and analysis.

| Source Column | Target Column | Source Type | Target Type | Transformation Applied |
|---|---|---|---|---|
| `establishments.name` | `establishment_name` | TEXT | TEXT | Trim leading and trailing whitespace (C-01) |
| `establishments.type` | `establishment_type` | TEXT | TEXT | Standardize establishment type values (S-03) |
| `establishments.total_rooms` | `total_rooms` | INTEGER/TEXT | INTEGER | Convert to integer and validate nonnegative values (C-18, S-04) |
| `visitor_reports.report_date` | `report_date` | DATE/TEXT | TEXT (YYYY-MM-DD) | Standardize date format (C-06, S-05) |
| `visitor_reports.male_visitors` | `male_visitors` | INTEGER/TEXT | INTEGER | Validate and convert to a nonnegative integer (C-07, S-06) |
| `visitor_reports.female_visitors` | `female_visitors` | INTEGER/TEXT | INTEGER | Validate and convert to a nonnegative integer (C-07, S-06) |
| `visitor_reports.total_visitors` | `total_visitors` | INTEGER/TEXT | INTEGER | Validate against the sum of male and female visitors (C-08, S-07) |
| `visitor_reports.male_visitors`, `visitor_reports.female_visitors` | `calculated_total_visitors` | INTEGER/TEXT | INTEGER | Derive the total by adding male and female visitors (B-01) |
| `visitor_reports.report_date` | `report_year` | DATE/TEXT | INTEGER | Extract the year from the reporting date (B-02) |
| `visitor_reports.report_date` | `report_month` | DATE/TEXT | INTEGER | Extract the month from the reporting date (B-02) |
| `visitor_reports.report_date` | `report_day` | DATE/TEXT | INTEGER | Extract the day from the reporting date (B-03) |
| `visitor_reports.origin_municipality` | `origin_municipality` | TEXT | TEXT | Trim whitespace and standardize municipality names (S-09) |
| `visitor_reports.origin_province` | `origin_province` | TEXT | TEXT | Trim whitespace and standardize province names (S-10) |
| `visitor_reports.origin_country` | `origin_country` | TEXT | TEXT | Trim whitespace and standardize country names (S-11) |
| `accommodation_reports.report_date` | `report_date` | DATE/TEXT | TEXT (YYYY-MM-DD) | Standardize date format (C-10, S-05) |
| `accommodation_reports.total_rooms` | `total_rooms` | INTEGER/TEXT | INTEGER | Validate and convert room counts to nonnegative integers (C-11, S-12) |
| `accommodation_reports.occupied_rooms` | `occupied_rooms` | INTEGER/TEXT | INTEGER | Validate occupied-room counts against total rooms (C-12, S-13) |
| `accommodation_reports.check_ins` | `check_ins` | INTEGER/TEXT | INTEGER | Validate and convert check-in counts (C-11, S-12) |
| `accommodation_reports.guest_nights` | `guest_nights` | INTEGER/TEXT | INTEGER | Validate and convert guest-night counts (C-11, S-12) |
| `accommodation_reports.total_rooms`, `accommodation_reports.occupied_rooms` | `occupancy_rate` | INTEGER/TEXT | DECIMAL | Calculate the percentage of occupied rooms from total rooms (B-06) |
| `room_occupancy_details.room_type` | `room_type` | TEXT | TEXT | Trim whitespace and standardize room-type labels |
| `room_occupancy_details.number_of_rooms` | `number_of_rooms` | INTEGER/TEXT | INTEGER | Validate and convert to a nonnegative integer (C-15, S-14) |
| `room_occupancy_details.occupied_rooms` | `occupied_rooms` | INTEGER/TEXT | INTEGER | Validate occupied rooms against the number of rooms (C-16, S-15) |
| `room_occupancy_details.check_ins` | `check_ins` | INTEGER/TEXT | INTEGER | Validate and convert check-in counts (S-14) |
| `room_occupancy_details.guest_nights` | `guest_nights` | INTEGER/TEXT | INTEGER | Validate and convert guest-night counts (S-14) |
| `room_occupancy_details.number_of_rooms`, `room_occupancy_details.occupied_rooms` | `room_type_occupancy_rate` | INTEGER/TEXT | DECIMAL | Calculate the occupancy percentage for each room type (B-07) |
| `establishments.id` | `establishment_id` | UUID/TEXT | TEXT | Preserve the source identifier for traceability and joins |
| `visitor_reports.establishment_id` | `establishment_id` | UUID/TEXT | TEXT | Preserve the foreign key linking visitor reports to establishments |
| `accommodation_reports.establishment_id` | `establishment_id` | UUID/TEXT | TEXT | Preserve the foreign key linking accommodation reports to establishments |
| `room_occupancy_details.accommodation_report_id` | `accommodation_report_id` | UUID/TEXT | TEXT | Preserve the foreign key linking room occupancy details to accommodation reports |

**Note:** Target column names and data types describe the proposed transformation contract. Derived columns such as `calculated_total_visitors`, `report_year`, `report_month`, `report_day`, `occupancy_rate`, and `room_type_occupancy_rate` should be included in the final contract only if they are actually generated by the transformation code. In the SQLite output, dates and UUID identifiers may be stored as `TEXT`, depending on the implemented schema.

## 7. Transformation Validation and Data Quality Checks

Transformation validation verifies that the processed VistaBalayan tourism data is correct, complete, consistent, and suitable for the succeeding Load Stage. These checks focus on the transformed output, including record reconciliation, required fields, key uniqueness, referential integrity, data type conformity, business rules, joins, and aggregated results. Extraction-stage checks that only verify source connectivity or extraction execution are excluded from this section.

| Check Name | Target | Purpose | Validation Criteria | Severity |
|---|---|---|---|---|
| Record Reconciliation | All transformed output tables | Identify records that may have been lost or incorrectly excluded during transformation. | For row-level cleaning, `input_count = retained_count + rejected_count`. Modified and retained records remain part of `retained_count`. Any documented duplicate handling, splits, or other record changes must be accounted for separately. | Critical |
| Rejected Record Tracking | Records rejected during transformation | Ensure invalid records are documented instead of silently removed. | Every rejected record must have a recorded rejection reason, and the rejected count must agree with the transformation logs or rejection records. | Critical |
| Required Column Null Check | Required columns in `establishments`, `visitor_reports`, `accommodation_reports`, and `room_occupancy_details` | Ensure required fields contain usable values after transformation. | Required identifiers, reporting dates, and essential relationship keys must not be null or blank. Optional fields may remain null when permitted by the target schema. | Critical |
| Primary Key Uniqueness | Primary keys in all transformed output tables | Prevent duplicate records from being treated as separate entities. | Duplicate count for each defined primary key must equal zero. | Critical |
| Referential Integrity | `establishment_id` in visitor and accommodation reports; `accommodation_report_id` in room occupancy details | Ensure related records reference existing parent records. | Every non-null foreign key must match an existing parent identifier in the corresponding transformed table. Unmatched records must be rejected, corrected, or explicitly reported. | Critical |
| Data Type Conformance | Dates, visitor counts, room counts, check-ins, and guest nights | Ensure transformed values follow the expected target data types. | Dates must follow the agreed `YYYY-MM-DD` format. Count fields must contain valid, nonnegative integers. Values that cannot be converted must be rejected or reported according to the transformation rules. | Critical |
| Date Format Validation | `report_date` in visitor and accommodation reports | Ensure dates can be used consistently for grouping and analysis. | Every non-null reporting date must be a valid calendar date in the agreed `YYYY-MM-DD` format. | Critical |
| Visitor Count Validation | `male_visitors`, `female_visitors`, and `total_visitors` in `visitor_reports` | Prevent invalid visitor counts and inconsistent totals. | Visitor counts must be nonnegative integers. Where the total is defined as the sum of male and female visitors, `total_visitors = male_visitors + female_visitors`. Any mismatch must be corrected or flagged. | Critical |
| Room Count Validation | `total_rooms` and `occupied_rooms` in `accommodation_reports` | Prevent impossible room occupancy values. | Room counts must be nonnegative integers, and `occupied_rooms` must not exceed `total_rooms`. Records with inconsistent values must be corrected or flagged. | Critical |
| Room Occupancy Detail Validation | `number_of_rooms` and `occupied_rooms` in `room_occupancy_details` | Ensure room-level occupancy data is logically valid. | Room counts must be nonnegative integers, and occupied rooms must not exceed the number of rooms for the corresponding room type. | Critical |
| Establishment Join Validation | Joins between `establishments` and visitor or accommodation reports | Detect missing establishment matches and incorrect join results. | Each report must match the intended establishment when an establishment reference is required. Unmatched records must be counted and investigated. | Critical |
| Join Cardinality Validation | Joined visitor, accommodation, and room occupancy datasets | Prevent unexpected row multiplication or loss during joins. | The number of joined rows must match the expected result based on the documented join relationship. One-to-many relationships must be accounted for, and unexpected duplicate multiplication must equal zero. | Critical |
| Filtering Audit | Records excluded by transformation filters | Ensure excluded records are accounted for and have documented reasons. | Every excluded record must be counted and associated with a defined filtering condition or exclusion reason. No record may be silently dropped. | Critical |
| Aggregation Reconciliation | Visitor totals and other derived summary measures | Verify that aggregation preserves the measures contributed by valid input records. | For each defined aggregation, the output measure must equal the sum of its eligible contributing input measures, subject to documented exclusions and grouping rules. | Critical |
| Monthly Visitor Summary Check | Monthly visitor totals, if generated | Ensure monthly summaries accurately represent the underlying visitor reports. | Each monthly total must equal the sum of eligible visitor totals assigned to that month and year. The sum across monthly groups must reconcile with the eligible input total. | Critical |
| Occupancy Rate Validation | `occupancy_rate` and `room_type_occupancy_rate`, if generated | Ensure calculated occupancy percentages are mathematically valid. | When the denominator is greater than zero, occupancy rate must equal `(occupied_rooms / total_rooms) × 100`. A zero denominator must be handled explicitly to prevent division errors. | Critical |
| Business Rule Validation | All transformed tourism datasets | Ensure transformed values comply with documented tourism data rules. | Visitor counts, room counts, check-ins, and guest nights must not be negative. Derived values must follow their documented formulas, and invalid records must be corrected, rejected, or flagged. | Critical |
| Transformation Output Verification | All transformed output tables | Confirm that expected output datasets and required columns are produced. | Each expected output table must exist, and its required columns must match the transformation contract. Missing tables or required columns must stop the pipeline. | Critical |
| Non-Critical Standardization Warning | Establishment types, room types, and visitor-origin fields | Identify values that remain inconsistent or cannot be matched to standard labels. | Unrecognized values must be logged or flagged for review. They may remain in the output only when the documented transformation rules permit it. | Non-critical |

### 7.1 Record Reconciliation Rules

Record reconciliation will be used to account for changes made during transformation. For row-level cleaning, the required relationship is:

`Input Records = Retained Records + Rejected Records`

Records that are cleaned or standardized and then retained are counted as retained, not rejected. The number of modified records may be recorded separately for monitoring purposes.

For aggregation, validation will compare the measures contributed by eligible input records with the resulting aggregated measures. For joins, validation will examine expected join relationships, unmatched records, and unexpected row multiplication. For filtering, excluded records and their reasons will be documented.

### 7.2 Validation Severity

**Critical** checks must pass before the transformed dataset is accepted for loading. A critical failure must stop the pipeline or prevent the affected output from being approved until the issue is resolved.

**Non-critical** checks produce warnings for review. They may allow processing to continue when the documented transformation rules permit it and the issue does not compromise the reliability of the output.

**Implementation note:** These checks define the required validation criteria. The final documentation should identify which checks are actually implemented in `pipeline/transform.py` and which remain planned. Derived fields and aggregated outputs should only be validated if the transformation code generates them.


## 8. Transformation Metadata and Log Specification

Transformation metadata and logs will be used to monitor each VistaBalayan transformation batch, track processing results, identify errors, and maintain traceability between extracted source data and transformed output. Each run should have a unique `run_id` linked to the corresponding extraction run through `parent_run_id`. This reference allows the transformation stage to trace its input without duplicating the extraction-stage metadata.

The following table specifies the metadata and log fields required for each transformation run.

| Field | Purpose | Example |
|---|---|---|
| `run_id` | Unique identifier assigned to each transformation pipeline run. | `TRF_20261019_2000` |
| `parent_run_id` | References the extraction run that supplied the input data. | `EXT_20261019_1930` |
| `batch_id` | Identifies a specific transformation batch within a pipeline run. | `BATCH_001` |
| `batch_window` | Records the reporting date range or processing window covered by the batch. | `2026-10-01 to 2026-10-18` |
| `table_name` | Identifies the source dataset or table being transformed. | `visitor_reports` |
| `transformation_start_time` | Records when transformation processing begins. | `2026-10-19 20:00:00` |
| `transformation_end_time` | Records when transformation processing finishes. | `2026-10-19 20:00:08` |
| `status` | Indicates the final result of the transformation run or batch. | `SUCCESS`, `FAILED`, or `PARTIAL_SUCCESS` |
| `records_read` | Number of input records received for transformation. | `2,400` |
| `records_output` | Number of records retained and produced in the transformed output. | `2,350` |
| `records_rejected` | Number of input records rejected or quarantined because they failed applicable transformation rules. | `50` |
| `records_modified` | Total number of retained records modified by cleaning or transformation rules. This metric is recorded separately and is not included in the reconciliation equation. | `C-01: 120; S-03: 35` |
| `rules_applied` | Records the rule identifiers and the number of records affected by each cleaning or transformation rule. | `C-01: 120; S-03: 35; B-01: 2,350` |
| `validation_results` | Stores the outcome of validation checks performed on the transformed output. | `PASS: 15; FAIL: 0; WARNING: 2` |
| `error_code` | Identifies the category of an error when a transformation operation fails. | `TRANSFORM_TYPE_ERROR` |
| `error_message` | Describes the error encountered and provides information for troubleshooting. | `Invalid date format in visitor_reports.report_date` |
| `transformation_duration_seconds` | Records the total elapsed time between transformation start and end. | `8.25` |
| `transformation_code_version` | Identifies the version or Git commit of the transformation code used for the run. | `v1.0.0` or `git: a1b2c3d` |
| `rules_version` | Identifies the version of the documented cleaning and transformation rules applied. | `rules-v1.0` |

**Note:** The example values are illustrative and do not represent confirmed execution logs. The `parent_run_id` should reference an actual extraction run identifier when extraction metadata is available. If the current extraction process does not generate run IDs, this field must be added to the pipeline metadata design.

### 8.1 Record Reconciliation in Transformation Logs

The transformation logs will record input, output, and rejected record counts so that each batch can be reconciled using the following equation:

`records_read = records_output + records_rejected`

This equation applies to row-level transformation when each input record is either retained as one output record or rejected. Records that are cleaned and retained are included in `records_output`, even when their values change. Therefore, `records_modified` is monitored separately and must not be added to `records_rejected`.

For aggregation, joins, filtering, or transformations that split or combine records, additional reconciliation details must be recorded. These may include contributing input counts, output counts, excluded records, unmatched join records, and input-versus-output measures. This ensures that changes in record counts are explainable rather than automatically treated as data loss.

### 8.2 Use of Transformation Metadata and Logs

The metadata and logs support the following activities:

- **Monitoring:** Track the status, processing duration, record counts, and validation outcomes of each transformation run.
- **Troubleshooting:** Use error codes, error messages, rejected-record counts, and rule-level statistics to identify the cause of processing failures or inconsistent results.
- **Auditing:** Maintain a traceable record of when transformation occurred, which datasets were processed, which rules were applied, and which code version was used.
- **Data lineage:** Connect the transformation run to its parent extraction run through `parent_run_id`, while using `run_id`, `batch_id`, and `table_name` to identify the specific processing activity and output.
- **Recovery:** Identify failed or incomplete batches, review their last recorded status, and determine which inputs and transformations need to be rerun. Recovery procedures should avoid unintentionally duplicating previously produced output.

### 8.3 Log Retention and Access

Transformation logs should be retained for at least 30 days after each transformation run to support troubleshooting, auditing, and recovery of failed batches. Access should be restricted to authorized project team members. Logs may be retained longer when required for an ongoing investigation, audit, or recovery activity.

### 8.4 Implementation Considerations

The fields in this section define the required transformation logging specification. Before describing them as implemented, the team should verify whether the current transformation code actually records each field. Metadata that is not yet generated, including extraction linkage, rule-level modification counts, validation summaries, code versions, and batch recovery information, should be identified as planned until implemented.


## 9. Log Retention, Rejected Data, and Access

The VistaBalayan transformation stage will maintain transformation logs and rejected records to support troubleshooting, auditing, data quality monitoring, and recovery of failed batches. Transformation logs will document cleaning actions, conversion errors, validation failures, processing results, and record counts. Rejected records will be stored separately from successfully transformed data so that invalid records can be reviewed without compromising the quality of the output.

### 9.1 Log and Rejected Data Retention

| Requirement | Specification |
|---|---|
| Transformation Log Retention Period | Transformation logs are proposed to be retained for at least 30 days after each transformation run. This period allows the project team to review recent processing activities, investigate errors, and recover failed or incomplete batches. |
| Transformation Log Storage Location | Transformation logs should be stored in a designated project-controlled logging directory, such as `pipeline/logs/`, or in a centralized logging system if implemented. |
| Quarantine Storage Location | Rejected records should be stored separately from valid transformed output in a designated quarantine directory, such as `pipeline/quarantine/`, or in a dedicated quarantine table if database-based storage is implemented. |
| Quarantine Retention Period | Rejected records should be retained for at least 30 days after the related transformation run to allow investigation, correction, and possible reprocessing. |
| Access Permissions | Authorized project team members may read logs and quarantine records for monitoring and troubleshooting. Only designated personnel should be permitted to create, update, or delete these records according to their assigned responsibilities. |
| Archiving Requirements | Logs and rejected records that must be retained beyond the operational retention period should be archived in approved project-controlled storage, where applicable. Archived records should remain traceable to their original run and batch. |
| Deletion Rules | Logs and rejected records must not be deleted before the defined retention period or while they are needed for troubleshooting, auditing, or recovery. Deletion should occur only after the retention requirements have been met and the records are no longer required. |
| Responsible Process | The designated project team member responsible for pipeline maintenance should review retention requirements and authorize or perform deletion according to the documented procedure. |
| Sensitive Data Handling | Logs and quarantine records should contain only the information necessary for monitoring and investigation. Unnecessary personal, confidential, or sensitive source data should not be copied into log messages. |

### 9.2 Separation of Extraction and Transformation Records

Although the extraction and transformation stages may use a shared logging system, their records must remain distinguishable because they document different activities.

| Record Type | Information Recorded | Ownership and Retention |
|---|---|---|
| Extraction Logs | Source retrieval errors, extraction start and end times, extracted record counts, and source-to-staging reconciliation results. | Managed by the extraction stage. Retained according to the extraction-stage retention policy. |
| Transformation Logs | Cleaning actions, conversion errors, validation results, transformation status, record counts, rule-level statistics, and processing failures. | Managed by the transformation stage. Retained for at least 30 days after each transformation run. |
| Transformation Quarantine | Records that could not be safely transformed, including the rejection reason, associated `batch_id`, and applicable `rule_id`. | Managed by the transformation stage. Retained for at least 30 days after the related transformation run, subject to investigation, audit, and recovery requirements. |
| Audit Records | Records of significant processing events, access, administrative actions, or changes that require longer-term traceability. | Managed by the designated project owner. Retention should follow the applicable project or institutional requirements and may exceed the operational log retention period. |

### 9.3 Quarantine Record Requirements

Each quarantined record should contain enough information to identify and investigate the transformation failure. The quarantine structure should include the following fields where applicable:

| Field | Purpose | Example |
|---|---|---|
| `quarantine_id` | Uniquely identifies the quarantined record. | `QTN_0001` |
| `run_id` | Identifies the transformation run in which the failure occurred. | `TRF_20261019_2000` |
| `batch_id` | Identifies the batch associated with the rejected record. | `BATCH_001` |
| `source_table` | Identifies the original dataset or table. | `visitor_reports` |
| `source_record_id` | References the source record for traceability, when available. | `VR_1025` |
| `rule_id` | Identifies the cleaning or transformation rule that failed. | `C-06` |
| `rejection_reason` | Explains why the record could not be safely transformed. | `Invalid reporting date` |
| `rejected_at` | Records the date and time when the record was rejected. | `2026-10-19 20:00:05` |
| `reprocessing_status` | Tracks whether the record is awaiting review, corrected, or reprocessed. | `PENDING_REVIEW` |

The examples above are illustrative. The quarantine fields should be implemented according to the actual transformation code and storage design. If the pipeline does not currently generate a quarantine table or file, this specification represents the proposed design rather than an existing feature.

### 9.4 Archiving and Deletion Procedure

Before deleting operational logs or quarantined records, the responsible project team member should verify that the minimum retention period has elapsed and that no active troubleshooting, audit, or recovery activity requires the records. Records that must be retained longer should be archived in approved storage, with their run identifiers, batch identifiers, and related metadata preserved.

Deletion should follow an authorized and documented process. Records must not be removed merely because a transformation run has completed or because a newer batch has been processed. Any applicable audit records should follow their separate retention requirements.

**Implementation note:** The 30-day retention period is a proposed project policy. The actual storage paths, access controls, automated deletion procedures, and quarantine mechanisms must be verified against the current repository before they are documented as implemented.
