{{ config(materialized = 'view') }}

-- 1 row = 1 crawled product

WITH source AS (
    SELECT *
    FROM {{ source('raw', 'products') }}
)

, renamed AS (
    SELECT
        REGEXP_REPLACE(TRIM(product_id), r'\.0+$', '')     AS product_id
        ,{{ clean_string('product_name') }}                AS product_name
        ,{{ clean_string('sku') }}                         AS sku
        ,{{ clean_string('category') }}                    AS category_name
        ,{{ category_group(clean_string('category')) }}    AS category_group_name
        ,{{ clean_string('description') }}                 AS product_description
        ,{{ clean_string('image_url') }}                   AS image_url
        ,{{ clean_string('source_url') }}                  AS representative_url
        ,{{ clean_string('host') }}                        AS representative_host
        ,LOWER(TRIM(success)) = 'true'                     AS is_crawl_success
        ,SAFE_CAST(http_status AS INT64)                   AS http_status
        ,SAFE.TIMESTAMP(crawled_at)                        AS crawled_at
    FROM source
)

SELECT *
FROM renamed
WHERE product_id IS NOT NULL
-- keep the successful crawl first, then the newest
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY product_id
    ORDER BY is_crawl_success DESC, crawled_at DESC
) = 1
