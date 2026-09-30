-- =====================================================================
-- Project 06 — Data Profiling trên BigQuery (dataset raw)
-- =====================================================================


-- ---------------------------------------------------------------------
-- 0. METADATA: bảng, số dòng, dung lượng, cột, kiểu dữ liệu
-- ---------------------------------------------------------------------
SELECT table_id AS table_name, row_count, ROUND(size_bytes / 1e9, 2) AS size_gb
FROM raw.__TABLES__
ORDER BY table_name;

SELECT table_name, ordinal_position, column_name, data_type, is_nullable
FROM raw.INFORMATION_SCHEMA.COLUMNS
ORDER BY table_name, ordinal_position;


-- ---------------------------------------------------------------------
-- 1. EVENTS — NULL / rỗng / distinct theo từng cột
-- ---------------------------------------------------------------------
WITH u AS (
  SELECT col, val
  FROM (SELECT * EXCEPT (payload, _run_id, _exported_at) FROM raw.events)
  UNPIVOT INCLUDE NULLS (val FOR col IN (
    event_id, collection, time_stamp, local_time, ip, user_agent, resolution,
    user_id_db, device_id, api_version, store_id, current_url, referrer_url,
    email_address, product_id, viewing_product_id, order_id, cat_id, collect_id))
)
SELECT
  col                                              AS column_name,
  COUNT(*)                                         AS total_rows,
  COUNTIF(val IS NULL)                             AS null_count,
  ROUND(100 * COUNTIF(val IS NULL) / COUNT(*), 2)  AS null_pct,
  COUNTIF(TRIM(val) = '')                          AS empty_string_count,
  APPROX_COUNT_DISTINCT(val)                       AS distinct_approx
FROM u
GROUP BY col
ORDER BY null_pct DESC;


-- ---------------------------------------------------------------------
-- 2. EVENTS — phân bố loại event
-- ---------------------------------------------------------------------
SELECT
  collection,
  COUNT(*) AS n,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM raw.events
GROUP BY collection
ORDER BY n DESC;


-- ---------------------------------------------------------------------
-- 3. EVENTS — constraint: event_id là khóa chính?
-- ---------------------------------------------------------------------
SELECT
  COUNT(*)                 AS total_rows,
  COUNT(DISTINCT event_id) AS distinct_event_id,
  COUNT(*) - COUNT(DISTINCT event_id) AS duplicate_rows   -- phải = 0
FROM raw.events;


-- ---------------------------------------------------------------------
-- 4. EVENTS — kiểm tra tính nhất quán kiểu dữ liệu (cột STRING ép được sang kiểu mong muốn?)
-- ---------------------------------------------------------------------
SELECT
  COUNTIF(time_stamp IS NOT NULL AND SAFE_CAST(time_stamp AS INT64) IS NULL)          AS time_stamp_not_int,
  COUNTIF(store_id   IS NOT NULL AND SAFE_CAST(store_id   AS INT64) IS NULL)          AS store_id_not_int,
  COUNTIF(product_id IS NOT NULL AND SAFE_CAST(product_id AS INT64) IS NULL)          AS product_id_not_int,
  COUNTIF(user_id_db IS NOT NULL AND user_id_db != ''
          AND SAFE_CAST(user_id_db AS INT64) IS NULL)                                 AS user_id_db_not_int,
  COUNTIF(ip IS NOT NULL AND NET.SAFE_IP_FROM_STRING(ip) IS NULL)                     AS ip_invalid,
  COUNTIF(email_address IS NOT NULL AND email_address != ''
          AND NOT REGEXP_CONTAINS(email_address, r'^[^@\s]+@[^@\s]+\.[^@\s]+$'))      AS email_invalid
FROM raw.events;

-- Khoảng thời gian dữ liệu
SELECT
  MIN(TIMESTAMP_SECONDS(SAFE_CAST(time_stamp AS INT64))) AS first_event,
  MAX(TIMESTAMP_SECONDS(SAFE_CAST(time_stamp AS INT64))) AS last_event
FROM raw.events;


-- ---------------------------------------------------------------------
-- 5. EVENTS — kiểu dữ liệu GỐC trong MongoDB (đọc từ payload, mẫu 5%)
--    Cho thấy field nào lúc là number lúc là string, option lúc object lúc array...
-- ---------------------------------------------------------------------
WITH s AS (
  SELECT collection, SAFE.PARSE_JSON(payload) AS j
  FROM raw.events TABLESAMPLE SYSTEM (5 PERCENT)
)
SELECT 'product_id' AS field, JSON_TYPE(JSON_QUERY(j, '$.product_id')) AS json_type, COUNT(*) AS n
FROM s WHERE JSON_QUERY(j, '$.product_id') IS NOT NULL GROUP BY 1, 2
UNION ALL
SELECT 'store_id', JSON_TYPE(JSON_QUERY(j, '$.store_id')), COUNT(*)
FROM s WHERE JSON_QUERY(j, '$.store_id') IS NOT NULL GROUP BY 1, 2
UNION ALL
SELECT 'user_id_db', JSON_TYPE(JSON_QUERY(j, '$.user_id_db')), COUNT(*)
FROM s WHERE JSON_QUERY(j, '$.user_id_db') IS NOT NULL GROUP BY 1, 2
UNION ALL
SELECT 'time_stamp', JSON_TYPE(JSON_QUERY(j, '$.time_stamp')), COUNT(*)
FROM s WHERE JSON_QUERY(j, '$.time_stamp') IS NOT NULL GROUP BY 1, 2
UNION ALL
SELECT 'option', JSON_TYPE(JSON_QUERY(j, '$.option')), COUNT(*)
FROM s WHERE JSON_QUERY(j, '$.option') IS NOT NULL GROUP BY 1, 2
UNION ALL
SELECT 'cart_products', JSON_TYPE(JSON_QUERY(j, '$.cart_products')), COUNT(*)
FROM s WHERE JSON_QUERY(j, '$.cart_products') IS NOT NULL GROUP BY 1, 2
ORDER BY field, n DESC;

-- Field nào có trong event nào (schema theo từng collection, mẫu 5%)
WITH s AS (
  SELECT collection, SAFE.PARSE_JSON(payload) AS j
  FROM raw.events TABLESAMPLE SYSTEM (5 PERCENT)
)
SELECT collection, key, COUNT(*) AS n
FROM s, UNNEST(JSON_KEYS(j, 1)) AS key
GROUP BY collection, key
ORDER BY collection, n DESC;


-- ---------------------------------------------------------------------
-- 6. IP_LOCATIONS — null / distinct / khóa / chất lượng geo
-- ---------------------------------------------------------------------
WITH u AS (
  SELECT col, val
  FROM (SELECT * EXCEPT (_run_id, _exported_at) FROM raw.ip_locations)
  UNPIVOT INCLUDE NULLS (val FOR col IN (
    ip, country_code, country_name, region_name, city_name,
    latitude, longitude, event_count, geo_status))
)
SELECT col AS column_name, COUNT(*) AS total_rows,
       COUNTIF(val IS NULL) AS null_count,
       ROUND(100 * COUNTIF(val IS NULL) / COUNT(*), 2) AS null_pct,
       APPROX_COUNT_DISTINCT(val) AS distinct_approx
FROM u GROUP BY col ORDER BY null_pct DESC;

SELECT
  COUNT(*) AS total, COUNT(DISTINCT ip) AS distinct_ip,             -- phải bằng nhau
  COUNTIF(latitude  IS NOT NULL AND SAFE_CAST(latitude  AS FLOAT64) IS NULL) AS lat_not_float,
  COUNTIF(longitude IS NOT NULL AND SAFE_CAST(longitude AS FLOAT64) IS NULL) AS lon_not_float,
  COUNTIF(SAFE_CAST(event_count AS INT64) IS NULL) AS event_count_not_int
FROM raw.ip_locations;

SELECT geo_status, COUNT(*) AS n_ips,
       SUM(SAFE_CAST(event_count AS INT64)) AS n_events
FROM raw.ip_locations GROUP BY 1 ORDER BY 2 DESC;

SELECT country_name, SUM(SAFE_CAST(event_count AS INT64)) AS n_events
FROM raw.ip_locations WHERE geo_status = 'FOUND'
GROUP BY 1 ORDER BY 2 DESC LIMIT 15;


-- ---------------------------------------------------------------------
-- 7. PRODUCTS — null / distinct / khóa / kiểu dữ liệu
-- ---------------------------------------------------------------------
WITH u AS (
  SELECT col, val
  FROM (SELECT * EXCEPT (_run_id, _exported_at) FROM raw.products)
  UNPIVOT INCLUDE NULLS (val FOR col IN (
    product_id, product_name, sku, price, currency, category,
    image_url, description, source_url, host, crawled_at))
)
SELECT col AS column_name, COUNT(*) AS total_rows,
       COUNTIF(val IS NULL) AS null_count,
       ROUND(100 * COUNTIF(val IS NULL) / COUNT(*), 2) AS null_pct,
       APPROX_COUNT_DISTINCT(val) AS distinct_approx
FROM u GROUP BY col ORDER BY null_pct DESC;

SELECT
  COUNT(*) AS total, COUNT(DISTINCT product_id) AS distinct_product_id,   -- phải bằng nhau
  COUNTIF(SAFE_CAST(product_id AS INT64) IS NULL) AS product_id_not_int,
  COUNTIF(price IS NOT NULL AND SAFE_CAST(price AS FLOAT64) IS NULL) AS price_not_numeric,
  COUNTIF(SAFE_CAST(crawled_at AS TIMESTAMP) IS NULL) AS crawled_at_not_timestamp
FROM raw.products;

SELECT category, COUNT(*) AS n
FROM raw.products GROUP BY 1 ORDER BY 2 DESC LIMIT 20;


-- ---------------------------------------------------------------------
-- 8. RELATIONSHIPS (khóa ngoại logic giữa các bảng)
-- ---------------------------------------------------------------------
-- events.ip -> ip_locations.ip
SELECT
  COUNT(*)                          AS events_with_ip,
  COUNTIF(l.ip IS NOT NULL)         AS matched_ip,
  COUNTIF(l.geo_status = 'FOUND')   AS matched_with_location,
  ROUND(100 * COUNTIF(l.geo_status = 'FOUND') / COUNT(*), 2) AS location_coverage_pct
FROM raw.events e
LEFT JOIN raw.ip_locations l ON e.ip = l.ip
WHERE e.ip IS NOT NULL;

-- events.product_id -> products.product_id
WITH p AS (
  SELECT DISTINCT product_id FROM raw.events
  WHERE product_id IS NOT NULL AND product_id != ''
)
SELECT
  COUNT(*)                            AS distinct_product_id_in_events,
  COUNTIF(pr.product_id IS NOT NULL)  AS found_in_products,
  ROUND(100 * COUNTIF(pr.product_id IS NOT NULL) / COUNT(*), 2) AS product_coverage_pct
FROM p LEFT JOIN raw.products pr USING (product_id);