-- 1 row = 1 currency used by a glamira store (How the customer paid), plus 1 Unknown row.
-- The rate itself lives in fact_exchange_rate_usd (it can change by day).

SELECT
    FARM_FINGERPRINT(currency_code)     AS currency_key
    ,currency_code
    ,currency_name
    ,currency_symbol
    ,FALSE                              AS is_unknown
FROM {{ ref('stg_exchange_rates') }}

UNION ALL

SELECT
    -1
    ,CAST(NULL AS STRING)
    ,'Unknown'
    ,CAST(NULL AS STRING)
    ,TRUE
