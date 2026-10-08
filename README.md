# SPI Inequality Pulse - Phase 2 (Medallion Lakehouse)

A PySpark-based Medallion Lakehouse tracking inflation inequality and subsidy impacts across Pakistan's income quintiles using PBS and WFP data.

## Phase 2 Deliverables
This phase implements the **Bronze** and **Silver** layers of the pipeline using Databricks Free Edition Serverless compute. 
* **Strict Schema Enforcement:** `inferSchema=True` is disabled. Schemas are explicitly defined for WFP data and safely cast for PBS data using `try_cast` to handle narrative text.
* **Idempotency:** The pipeline uses Delta Lake `MERGE INTO` (WFP) and `replaceWhere` (PBS). Running the same week multiple times will not duplicate rows.
* **Audit Logging:** Every notebook logs execution metadata (layer, rows processed, status, timestamps) to a central `pipeline_execution_logs` Delta table.

## Execution Guide (Incremental vs. Backfill)
The pipeline is orchestrated via `06_pipeline_runner` (or your master `%run` notebook).
1. **Incremental Load:** Set the `week_ending_date` parameter to the newest week (e.g., `24.09.2026`) and execute the notebook.
2. **Parameterized Backfill:** To run historical dates, simply change the `week_ending_date` parameter to the target historical date and run the master notebook. The idempotent write logic will safely overwrite or merge the historical partition without affecting other dates.