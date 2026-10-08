# Bronze & Silver Data Models

## Bronze Layer
**`bronze_wfp_raw`**
*   `adm0_id` (Int), `adm0_name` (Str), `adm1_id` (Int), `adm1_name` (Str), `mkt_id` (Int), `mkt_name` (Str), `cm_id` (Int), `cm_name` (Str), `cur_id` (Int), `cur_name` (Str), `pt_id` (Int), `pt_name` (Str), `um_id` (Int), `um_name` (Str), `mp_month` (Int), `mp_year` (Int), `mp_price` (Double), `mp_commoditysource` (Str).
*   *Metadata:* `load_timestamp` (Timestamp), `source_file` (Str).

**`bronze_pbs_report`** & **`bronze_pbs_annex`**
*   Ingested entirely as string columns to preserve tabular fidelity before Silver parsing.
*   *Metadata:* `load_timestamp` (Timestamp), `source_file` (Str), `week_ending_date` (Date).

## Silver Layer
**`silver_wfp_price_observation`**
Filtered to Pakistan and regional neighbors.
*   `country` (Str), `admin_region` (Str), `market` (Str), `commodity_name` (Str), `category` (Str), `unit` (Str), `price` (Double), `currency` (Str), `price_date` (Date) - Primary Key.
*   *Metadata:* `is_revised_flag` (Boolean), `ingestion_batch_id` (Str), `load_timestamp` (Timestamp).

**`silver_quintile_index`**
*   `quintile` (Str), `index_value` (Double), `pct_change_wow` (Double), `pct_change_yoy` (Double), `week_ending_date` (Date).

**`silver_city_price_observation`**
*   `item_name` (Str), `category` (Str), `city` (Str), `unit` (Str), `min_price` (Double), `max_price` (Double), `avg_price` (Double), `price_dispersion_pct` (Double), `week_ending_date` (Date).