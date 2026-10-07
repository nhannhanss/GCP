-- Fails if an order comes from a domain that is missing in seeds/store_currency.csv
SELECT
    store_domain
    ,COUNT(*) AS line_cnt
FROM {{ ref('stg_order_lines') }}
WHERE currency_code IS NULL
GROUP BY store_domain
