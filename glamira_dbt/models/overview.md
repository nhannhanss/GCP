{% docs __overview__ %}
# Glamira – dbt transformation layer (Project 07)

Turns the raw BigQuery layer from Project 06 (`raw.events`, `raw.ip_locations`, `raw.products`)
into a star schema for sales analysis and a flat mart for Looker Studio / Data Studio.

| Layer | Dataset | Materialization | Purpose |
|---|---|---|---|
| staging | `staging` | view | Clean 1-to-1 copies of raw: cast types, parse prices, remove test stores and duplicates, hash PII |
| core | `core` | table | Star schema: `fact_sales_order_detail` + 6 dimensions |
| mart | `mart` | table | `mart_sales`: fact joined with every dimension, used by the dashboard |

**Grain of the fact:** 1 row = 1 product line in 1 successful order (`checkout_success`).

**Unknown members:** every dimension has a row with key `-1` (`is_unknown = TRUE`); a foreign key that
cannot be resolved points there, so the fact never loses rows.

**PII:** email, IP, user_id_db and device_id are replaced by salted SHA-256 hashes in staging;
only the `raw` dataset holds the original values.
{% enddocs %}
