# SPI Inequality Pulse: Tracking Inflation's Real Impact

Inflation is rarely experienced equally. A standard 15% national inflation rate might mean a minor budget adjustment for the top income bracket, but it can represent a devastating loss of purchasing power for the lowest-income households. 

This project builds a robust data engineering pipeline to uncover that reality. By combining Pakistan's official Weekly Sensitive Price Indicator (SPI) with World Food Programme (WFP) global market data, this Medallion Lakehouse tracks how price hikes, price dispersion, and subsidies specifically impact different income groups across Pakistan's urban centers.

## The Architecture
The project uses a standard Medallion architecture built on **Databricks** (Serverless Free Edition) and **PySpark**, ensuring idempotent data processing and strict audit logging.

*   **Data Ingestion (External):** GitHub Actions orchestrate weekly fetches of raw Excel reports and CSVs, landing them in a structured directory.
*   **Bronze Layer (Raw & Untyped):** Raw tabular data is ingested directly into Delta tables as strings. This prevents schema-inference crashes caused by the complex narrative headers often found in government reports.
*   **Silver Layer (Cleaned & Conformed):** Data is parsed using safe casting (`try_cast`) to filter out text, structured into strict schemas, and merged. WFP data uses `MERGE INTO` for true upserts, while PBS data relies on `replaceWhere` for idempotent weekly partition replacements.
*   **Gold Layer (Analytics - *Upcoming*):** Aggregated views tracking the week-over-week purchasing power parity of Pakistan's five income quintiles.

## Data Sources
1.  **Pakistan Bureau of Statistics (PBS):** Weekly SPI reports detailing price changes for 51 essential items across 17 cities and 5 income quintiles.
2.  **World Food Programme (WFP):** Global food price databases used as a regional benchmark for commodity prices.

## Repository Structure
*   `/notebooks`: PySpark code handling the Bronze and Silver transformations, alongside the master orchestrator.
*   `/data/samples`: Sample files for local testing and pipeline verification.
*   `/docs`: Data dictionaries and schema definitions.
*   `/src`: Python scripts for external data fetching.
*   `.github/workflows`: CI/CD and automated scraping schedules.

## Running the Pipeline
The pipeline is orchestrated via the `pipelinerunner` notebook to manage Databricks Free Tier concurrency limits.

1.  **Incremental Weekly Load:** Pass the target week's date (e.g., `24.09.2026`) into the master orchestrator. The pipeline will process the new files and append/upsert them safely.
2.  **Historical Backfills:** Pass any historical date into the orchestrator. Because the writes are idempotent, it will safely recalculate and replace that specific week's data without corrupting the rest of the historical log or duplicating rows.

