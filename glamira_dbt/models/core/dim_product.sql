-- 1 row = 1 product_id that appears in an order (with crawled info when available), plus 1 Unknown row

WITH ordered_products AS (
    SELECT DISTINCT product_id
    FROM {{ ref('stg_order_lines') }}
    WHERE product_id IS NOT NULL
)

, crawled AS (
    SELECT *
    FROM {{ ref('stg_products') }}
    WHERE is_crawl_success
)

SELECT
    FARM_FINGERPRINT(o.product_id)                      AS product_key
    ,o.product_id
    ,COALESCE(c.product_name, 'Unknown')                AS product_name
    ,c.category_name
    ,COALESCE(c.category_group_name, 'Unknown')         AS category_group_name
    ,c.product_description
    ,c.image_url
    ,c.representative_url
    ,c.representative_host
    ,IF(c.product_id IS NULL, 0, 1)                     AS source_url_count
    ,FALSE                                              AS is_unknown
FROM ordered_products AS o
LEFT JOIN crawled AS c
    ON o.product_id = c.product_id

UNION ALL

SELECT
    -1
    ,CAST(NULL AS STRING)
    ,'Unknown'
    ,CAST(NULL AS STRING)
    ,'Unknown'
    ,CAST(NULL AS STRING)
    ,CAST(NULL AS STRING)
    ,CAST(NULL AS STRING)
    ,CAST(NULL AS STRING)
    ,0
    ,TRUE
