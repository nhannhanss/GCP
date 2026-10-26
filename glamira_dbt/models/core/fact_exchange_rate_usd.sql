-- Grain: 1 row = 1 currency on 1 calendar day, with its rate to USD.
-- The source (seed exchange_rates) holds one approximate 2020 average per currency, so every day of
-- the year gets the same rate today; replacing the seed with daily rates needs no change downstream.

WITH dates AS (
    SELECT
        date_key
        ,full_date
    FROM {{ ref('dim_date') }}
    WHERE NOT is_unknown
)

, rates AS (
    SELECT *
    FROM {{ ref('stg_exchange_rates') }}
)

SELECT
    FARM_FINGERPRINT(CONCAT(CAST(d.date_key AS STRING), '-', r.currency_code))  AS exchange_rate_key
    ,d.date_key
    ,FARM_FINGERPRINT(r.currency_code)                                          AS currency_key
    ,r.currency_code
    ,CAST(r.usd_per_unit AS NUMERIC)                                            AS exchange_rate_to_usd
FROM dates AS d
CROSS JOIN rates AS r
