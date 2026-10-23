# SPI Inequality Pulse

A Medallion Lakehouse (Bronze -> Silver) on Databricks that tracks how inflation hits different income groups in Pakistan. It combines the weekly **Sensitive Price Indicator (SPI)** from the Pakistan Bureau of Statistics (PBS) with **WFP** global food prices.

## Repository structure
```
notebooks/   Schemas, bronzewfp, silverwfp, bronzepbs, silverpbs, pipelinerunner, validation
src/         fetch_pbs.py, fetch_wfp.py, common.py   (download files and upload them to the Databricks volume)
.github/     weekly GitHub Actions schedule for the fetch scripts
data/samples sample input files
```

## How it works
| Step | Notebook | What it does |
|---|---|---|
| Setup | `Schemas` | Creates every table with explicit column types |
| Raw -> Bronze | `bronzewfp`, `bronzepbs` | Loads raw files as text, adds source and batch info |
| Bronze -> Silver | `silverwfp`, `silverpbs` | Cleans, converts types, removes duplicates, quarantines bad rows, `MERGE INTO` |
| Orchestration | `pipelinerunner` | Runs everything in order with the parameters below |
| Tests | `validation` | Data-quality and idempotency checks (PASS/FAIL) |

Raw files live in the volume `/Volumes/workspace/default/spi_data/samples/`: the WFP CSV (`wfpvam_foodprices.csv`) and the PBS weekly files (`SPI_Report_dd-mm-yyyy.xlsx`, `SPI_Annexure_dd-mm-yyyy.xlsx`).

## How to run
**First time:** pull this repo as a Databricks Git folder, upload the raw files to the volume, open `pipelinerunner`, set `reset_tables = yes` and run all (use `reset_tables = no` afterwards).

**Normal incremental load:** `load_type = incremental`, leave `target_dates` blank, run all. The WFP file is skipped if unchanged, and only PBS weeks that are not in Silver yet are processed.

**Backfill an older period:** `load_type = full_backfill` and either
* `start_date = 01.07.2026`, `end_date = 30.09.2026` (all weeks in that window), or
* `target_dates = 24.09.2026,01.10.2026` (specific weeks).

No code changes are needed. Re-running any period is safe: Bronze replaces that file or week, Silver `MERGE INTO` changes nothing if the data is the same.

Each notebook can also run alone: `bronzewfp` (`wfp_file_path`, `load_type`, `batch_id`), `silverwfp` (`countries`, `lookback_months`, ...), `bronzepbs` and `silverpbs` (`week_ending_dates`, `base_dir`, ...).

## Data models
All tables are in `workspace.default`. Every Bronze and Silver table has `load_timestamp` (TIMESTAMP).

### Bronze
**`bronze_wfp_raw`**, PK `source_file, adm0_id, mkt_id, cm_id, pt_id, um_id, mp_year, mp_month`
| Column | Type |
|---|---|
| adm0_id, adm0_name, adm1_id, adm1_name, mkt_id, mkt_name, cm_id, cm_name, cur_id, cur_name, pt_id, pt_name, um_id, um_name, mp_month, mp_year, mp_price, mp_commoditysource | STRING |
| extra_json (unexpected columns), source_file, source_file_signature, batch_id, load_type | STRING |
| load_timestamp | TIMESTAMP |

**`bronze_pbs_report`**, **`bronze_pbs_annex`** (raw Excel cells), PK `week_ending_date, sheet_name, row_idx`
| Column | Type |
|---|---|
| week_ending_date (dd.mm.yyyy), source_file, sheet_name, c00 ... c24, extra_json, batch_id, load_type | STRING |
| row_idx (Excel row number) | INT |
| load_timestamp | TIMESTAMP |

### Silver
**`silver_wfp_price_observation`**, PK `country, market, commodity_name, unit, price_type, price_date`
| Column | Type |
|---|---|
| country, admin_region, market, commodity_name, category, unit, price_type, currency, ingestion_batch_id, source_file | STRING |
| price | DOUBLE |
| price_date | DATE |
| is_revised_flag | BOOLEAN |
| load_timestamp, last_updated_timestamp | TIMESTAMP |

**`silver_quintile_index`**, PK `week_ending_date, quintile` (Q1-Q5 and Combined)
| Column | Type |
|---|---|
| quintile, income_band, source_file, batch_id | STRING |
| index_value, index_prev_week, index_prev_year, pct_change_wow, pct_change_yoy | DOUBLE |
| week_ending_date | DATE |
| load_timestamp | TIMESTAMP |

**`silver_item_weight_impact`**, PK `week_ending_date, item_name`
| Column | Type |
|---|---|
| item_name, unit, price_direction, source_file, batch_id | STRING |
| price_current, price_prev_week, price_prev_year, pct_change_wow, pct_change_yoy, weight_lowest, weight_combined, impact_lowest, impact_combined | DOUBLE |
| week_ending_date | DATE |
| load_timestamp | TIMESTAMP |

**`silver_city_price_observation`**, PK `week_ending_date, item_sl, city_code`
| Column | Type |
|---|---|
| week_ending_date | DATE |
| item_sl | INT |
| item_name, unit, city, city_code, source_file, batch_id | STRING |
| min_price, avg_price, max_price, price_dispersion_pct | DOUBLE |
| load_timestamp | TIMESTAMP |

### Operations
**`pipeline_execution_logs`**, PK `log_id`: log_id, batch_id, load_type, layer, file_processed, target_table, status (`Success`, `Warning`, `Skipped`, `Failure`), message, error_message (STRING); start_time, end_time (TIMESTAMP); rows_read, rows_inserted, rows_updated, rows_quarantined (BIGINT).

**`quarantine_records`**, PK `quarantine_id`: quarantine_id, batch_id, layer, source_file, record_ref, reason, record_json (STRING); quarantined_at (TIMESTAMP).
