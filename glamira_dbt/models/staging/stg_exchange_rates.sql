{{ config(materialized = 'view') }}

-- 1 row = 1 currency with its approximate 2020 average rate to USD (from seed exchange_rates)

SELECT
    UPPER(TRIM(currency_code))                  AS currency_code
    ,{{ clean_string('currency_name') }}        AS currency_name
    ,{{ clean_string('currency_symbol') }}      AS currency_symbol
    ,CAST(usd_per_unit AS NUMERIC)              AS usd_per_unit
FROM {{ ref('exchange_rates') }}
WHERE currency_code IS NOT NULL
