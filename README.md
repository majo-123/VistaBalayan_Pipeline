# VistaBalayan Tourism Data Analytics and Decision Support Pipeline

## Overview

The **VistaBalayan Tourism Data Analytics and Decision Support Pipeline** is designed to collect, extract, validate, transform, process, and analyze tourism data from the VistaBalayan Tourism System.

The pipeline processes tourism records such as **establishment information, visitor reports, accommodation reports, and room occupancy details**. The source data is stored in the VistaBalayan **PostgreSQL database**, while **Python** is used to retrieve tourism records for batch processing.

The pipeline is organized into several stages:

```text
VistaBalayan Tourism System
          |
          v
   PostgreSQL Database
          |
          v
   1. Data Extraction
          |
          v
   2. Data Transformation
          |
          v
   3. Data Processing / Storage
          |
          v
   4. Data Analytics
          |
          v
   5. Reporting and Decision Support
```

> **Current Progress:** The project is currently at **Stage 1: Data Extraction**. The current work focuses on retrieving tourism records from the VistaBalayan PostgreSQL database and validating the extracted data before it proceeds to the succeeding stages.

---

## Pipeline Stages

### Stage 1 — Data Extraction

The Data Extraction stage retrieves tourism records from the VistaBalayan PostgreSQL database using Python batch processing.

The current extraction scope includes:

- `establishments`
- `visitor_reports`
- `accommodation_reports`
- `room_occupancy_details`

The extracted data undergoes initial validation to verify the source connection, required tables and columns, identifiers, relationships, record counts, and extraction status.

**Status:** 🟡 In Progress

**Documentation:** `documentation/data-extraction.md`

---

### Stage 2 — Data Transformation

The Data Transformation stage will process the extracted tourism data and prepare it for succeeding analytical operations.

Planned activities include:

- Data cleaning
- Data standardization
- Data type handling
- Data integration
- Data aggregation
- Validation of transformed records

**Status:** ⚪ Not Yet Started

---

### Stage 3 — Data Processing / Storage

The Data Processing / Storage stage will organize and store the transformed tourism data in the designated processed-data layer for succeeding analytics and reporting activities.

The specific processing and storage procedures will be documented as the pipeline progresses.

**Status:** ⚪ Not Yet Started



