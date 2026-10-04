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

The current technical metadata does not specify a dedicated incremental extraction field or watermark. Therefore, the extraction is documented as a **batch extraction**.

An incremental extraction rule may be defined in a future implementation once an approved timestamp or reporting-date field is established.

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

