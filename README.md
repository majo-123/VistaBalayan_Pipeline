# VistaBalayan Tourism Data Analytics and Decision Support Pipeline

## Overview

The **VistaBalayan Tourism Data Analytics and Decision Support Pipeline** is designed to collect, extract, validate, transform, process, and analyze tourism data from the VistaBalayan Tourism System.

The pipeline processes tourism records such as **establishment information, visitor reports, accommodation reports, and room occupancy details**. The source data is stored in the VistaBalayan **PostgreSQL database**, while **Python** is used to retrieve tourism records for batch processing.

The pipeline follows the **Extract, Transform, and Load (ETL)** approach, which consists of three main stages.

```text
VistaBalayan Tourism System
          |
          v
   PostgreSQL Database
          |
          v
   1. Data Extraction
      (Completed)
          |
          v
   2. Data Transformation
      (In Progress)
          |
          v
   3. Data Loading
          |
          v
   Processed Data Storage
```

> **Current Progress:** The Data Extraction stage has been completed. The project is currently focused on **Stage 2: Data Transformation**, which involves cleaning, standardizing, validating, and preparing the extracted tourism records for loading into the designated processed-data storage.

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

**Status:** ✅ Completed

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

**Status:** 🟡 In Progress

**Documentation:** `documentation/data-transformation.md`

---
### Stage 3 — Data Loading

The Data Loading stage transfers validated and transformed tourism data into the designated processed-data storage.

This stage ensures that processed records are stored in an organized and consistent structure suitable for subsequent data retrieval, analysis, and reporting.

The planned activities include:

- Preparing the target tables and storage structure.
- Loading transformed tourism records into the designated processed-data database.
- Maintaining relationships and identifiers across related records.
- Validating the loaded data against the transformed dataset.
- Recording loading results, including record counts and processing status.
- Handling loading errors and preventing unintended duplicate records where applicable.

The specific loading procedures and validation rules will be documented as implementation progresses.

**Status:** ⚪ Not Yet Started

**Documentation:** To be documented during implementation.

---





