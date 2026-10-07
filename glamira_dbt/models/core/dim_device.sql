-- 1 row = 1 combination of device type + screen resolution + bot flag, plus 1 Unknown row

WITH devices AS (
    SELECT DISTINCT
        {{ device_natural_key('user_agent', 'resolution') }}   AS device_natural_key
        ,{{ ua_device_type('user_agent') }}                    AS device_type
        ,resolution                                            AS resolution_name
        ,{{ ua_is_bot('user_agent') }}                         AS is_bot
    FROM {{ ref('stg_checkout_orders') }}
)

SELECT
    FARM_FINGERPRINT(device_natural_key)                                        AS device_key
    ,device_type
    ,resolution_name
    ,SAFE_CAST(SPLIT(resolution_name, 'x')[SAFE_OFFSET(0)] AS INT64)            AS screen_width
    ,SAFE_CAST(SPLIT(resolution_name, 'x')[SAFE_OFFSET(1)] AS INT64)            AS screen_height
    ,is_bot
    ,FALSE                                                                      AS is_unknown
FROM devices

UNION ALL

SELECT
    -1
    ,'Unknown'
    ,CAST(NULL AS STRING)
    ,CAST(NULL AS INT64)
    ,CAST(NULL AS INT64)
    ,FALSE
    ,TRUE
