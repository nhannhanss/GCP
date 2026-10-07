-- Fails if the fact lost or duplicated rows compared to stg_order_lines
SELECT
    fact_cnt
    ,stg_cnt
FROM (
    SELECT
        (SELECT COUNT(*) FROM {{ ref('fact_sales_order_detail') }}) AS fact_cnt
        ,(SELECT COUNT(*) FROM {{ ref('stg_order_lines') }}) AS stg_cnt
)
WHERE fact_cnt != stg_cnt
