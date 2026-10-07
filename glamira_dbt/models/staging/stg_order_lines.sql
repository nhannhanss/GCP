{{ config(materialized = 'view') }}

-- 1 row = 1 product line inside 1 order (grain of fact_sales_order_detail)

WITH orders AS (
    SELECT *
    FROM {{ ref('stg_checkout_orders') }}
)

, store_currency AS (
    SELECT *
    FROM {{ ref('store_currency') }}
)

, lines AS (
    SELECT
        o.order_id
        ,line_offset + 1                                                         AS line_number
        ,o.source_event_id
        ,o.order_time
        ,o.store_id
        ,o.store_domain
        ,o.user_id_db
        ,o.device_id
        ,o.email_address
        ,o.ip
        ,o.user_agent
        ,o.resolution
        ,REGEXP_REPLACE(JSON_VALUE(item, '$.product_id'), r'\.0+$', '')          AS product_id
        ,SAFE_CAST(SAFE_CAST(JSON_VALUE(item, '$.amount') AS FLOAT64) AS INT64)  AS order_qty
        ,JSON_VALUE(item, '$.price')                                             AS price_raw
        ,{{ clean_string("JSON_VALUE(item, '$.currency')") }}                    AS currency_symbol
        ,(
            SELECT JSON_VALUE(opt, '$.value_label')
            FROM UNNEST(JSON_QUERY_ARRAY(item, '$.option')) AS opt
            WHERE JSON_VALUE(opt, '$.option_label') = 'alloy'
            LIMIT 1
        )                                                                        AS alloy_name
        ,(
            SELECT JSON_VALUE(opt, '$.value_label')
            FROM UNNEST(JSON_QUERY_ARRAY(item, '$.option')) AS opt
            WHERE JSON_VALUE(opt, '$.option_label') = 'diamond'
            LIMIT 1
        )                                                                        AS diamond_name
    FROM orders AS o
    CROSS JOIN UNNEST(JSON_QUERY_ARRAY(o.payload, '$.cart_products')) AS item WITH OFFSET AS line_offset
)

SELECT
    l.order_id
    ,l.line_number
    ,l.source_event_id
    ,l.order_time
    ,l.store_id
    ,l.store_domain
    ,l.user_id_db
    ,l.device_id
    ,l.email_address
    ,l.ip
    ,l.user_agent
    ,l.resolution
    ,l.product_id
    ,l.order_qty
    ,l.price_raw
    ,CAST(ROUND({{ parse_price('l.price_raw') }}, 2) AS NUMERIC)                 AS unit_price_local
    ,CAST(ROUND(l.order_qty * {{ parse_price('l.price_raw') }}, 2) AS NUMERIC)   AS line_amount_local
    ,l.currency_symbol
    ,sc.currency_code
    ,l.alloy_name
    ,l.diamond_name
FROM lines AS l
LEFT JOIN store_currency AS sc
    ON l.store_domain = sc.store_domain
