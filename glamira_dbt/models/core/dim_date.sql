-- 1 row = 1 calendar day covering every order date, plus 1 Unknown row (date_key = -1)

WITH bounds AS (
    SELECT
        MIN(DATE(order_time)) AS min_date
        ,MAX(DATE(order_time)) AS max_date
    FROM {{ ref('stg_checkout_orders') }}
)

, days AS (
    SELECT full_date
    FROM bounds
    CROSS JOIN UNNEST(GENERATE_DATE_ARRAY(DATE_TRUNC(min_date, YEAR), LAST_DAY(max_date, YEAR))) AS full_date
)

SELECT
    CAST(FORMAT_DATE('%Y%m%d', full_date) AS INT64)        AS date_key
    ,full_date
    ,EXTRACT(DAY FROM full_date)                           AS day_of_month
    ,MOD(EXTRACT(DAYOFWEEK FROM full_date) + 5, 7) + 1     AS day_of_week      -- 1 = Monday ... 7 = Sunday
    ,FORMAT_DATE('%A', full_date)                          AS day_name
    ,EXTRACT(ISOWEEK FROM full_date)                       AS week_of_year
    ,EXTRACT(MONTH FROM full_date)                         AS month_number
    ,FORMAT_DATE('%B', full_date)                          AS month_name
    ,FORMAT_DATE('%Y-%m', full_date)                       AS year_month
    ,EXTRACT(QUARTER FROM full_date)                       AS quarter_number
    ,CONCAT('Q', CAST(EXTRACT(QUARTER FROM full_date) AS STRING)) AS quarter_name
    ,EXTRACT(YEAR FROM full_date)                          AS year
    ,EXTRACT(DAYOFWEEK FROM full_date) IN (1, 7)           AS is_weekend
    ,FALSE                                                 AS is_unknown
FROM days

UNION ALL

SELECT
    -1
    ,CAST(NULL AS DATE)
    ,CAST(NULL AS INT64)
    ,CAST(NULL AS INT64)
    ,'Unknown'
    ,CAST(NULL AS INT64)
    ,CAST(NULL AS INT64)
    ,'Unknown'
    ,'Unknown'
    ,CAST(NULL AS INT64)
    ,'Unknown'
    ,CAST(NULL AS INT64)
    ,FALSE
    ,TRUE
