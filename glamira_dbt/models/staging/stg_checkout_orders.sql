{{ config(materialized = 'view') }}

-- 1 row = 1 successful order (deduplicated, test/dev stores removed)

WITH source AS (
    SELECT *
    FROM {{ source('raw', 'events') }}
    WHERE collection = 'checkout_success'
)

, renamed AS (
    SELECT
        event_id                                                                AS source_event_id
        ,REGEXP_REPLACE(TRIM(order_id), r'\.0+$', '')                           AS order_id
        ,TIMESTAMP_SECONDS(SAFE_CAST(SAFE_CAST(time_stamp AS FLOAT64) AS INT64)) AS order_time
        ,{{ clean_string('store_id') }}                                         AS store_id
        ,LOWER(REGEXP_EXTRACT(current_url, r'^https?://([^/:?#]+)'))            AS store_domain
        ,{{ clean_string('user_id_db') }}                                       AS user_id_db
        ,{{ clean_string('device_id') }}                                        AS device_id
        ,LOWER({{ clean_string('email_address') }})                             AS email_address
        ,{{ clean_string('ip') }}                                               AS ip
        ,{{ clean_string('user_agent') }}                                       AS user_agent
        ,{{ clean_string('resolution') }}                                       AS resolution
        ,payload
    FROM source
)

SELECT *
FROM renamed
WHERE order_id IS NOT NULL
    AND store_domain IS NOT NULL
    -- remove orders placed on staging / dev / local environments
    AND NOT REGEXP_CONTAINS(store_domain, r'^(stage|dev\d*)\.|\.local$')
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY order_time, source_event_id) = 1
