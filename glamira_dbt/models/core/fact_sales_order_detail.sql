{{
    config(
        partition_by = {'field': 'order_time', 'data_type': 'timestamp', 'granularity': 'month'},
        cluster_by = ['store_key', 'product_key']
    )
}}

-- Grain: 1 row = 1 product line in 1 successful order.
-- Surrogate keys are computed with the same expressions as the dims; a key that cannot be resolved = -1 (Unknown row).

WITH lines AS (
    SELECT *
    FROM {{ ref('stg_order_lines') }}
)

, ip_locations AS (
    SELECT *
    FROM {{ ref('stg_ip_locations') }}
)

, exchange_rates AS (
    SELECT *
    FROM {{ ref('exchange_rates') }}
)

SELECT
    FARM_FINGERPRINT(CONCAT(l.order_id, '-', CAST(l.line_number AS STRING)))   AS sales_order_detail_key
    ,l.order_id
    ,l.line_number
    ,COALESCE(FARM_FINGERPRINT(l.store_id), -1)                                 AS store_key
    ,COALESCE(FARM_FINGERPRINT(l.product_id), -1)                               AS product_key
    ,IF(
        ip.country_code IS NULL
        ,-1
        ,FARM_FINGERPRINT({{ geo_natural_key('ip.country_code', 'ip.region_name', 'ip.city_name') }})
    )                                                                           AS geo_key
    ,FARM_FINGERPRINT({{ device_natural_key('l.user_agent', 'l.resolution') }}) AS device_key
    ,COALESCE(CAST(FORMAT_DATE('%Y%m%d', DATE(l.order_time)) AS INT64), -1)     AS date_key
    ,COALESCE(FARM_FINGERPRINT(l.customer_id_hash), -1)                         AS customer_key
    ,l.order_qty
    ,l.unit_price_local
    ,l.line_amount_local
    ,CAST(ROUND(l.line_amount_local * fx.usd_per_unit, 2) AS NUMERIC)          AS line_amount_usd
    ,l.currency_code
    ,l.order_time
    ,l.source_event_id
FROM lines AS l
LEFT JOIN ip_locations AS ip
    ON l.ip_hash = ip.ip_hash
LEFT JOIN exchange_rates AS fx
    ON l.currency_code = fx.currency_code
