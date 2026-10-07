-- Fails if the mart's joins changed the total revenue compared with the fact
SELECT
    fact_usd
    ,mart_usd
FROM (
    SELECT
        (SELECT SUM(line_amount_usd) FROM {{ ref('fact_sales_order_detail') }}) AS fact_usd
        ,(SELECT SUM(line_amount_usd) FROM {{ ref('mart_sales') }}) AS mart_usd
)
WHERE ABS(COALESCE(fact_usd, 0) - COALESCE(mart_usd, 0)) > 0.01
