-- 1 row = 1 store_id (a language/market version of a glamira site), plus 1 Unknown row

WITH store_domains AS (
    SELECT
        store_id
        ,store_domain
        ,COUNT(*) AS order_cnt
    FROM {{ ref('stg_checkout_orders') }}
    WHERE store_id IS NOT NULL
    GROUP BY store_id, store_domain
)

, main_domain AS (
    SELECT
        store_id
        ,store_domain
    FROM store_domains
    WHERE TRUE
    QUALIFY ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY order_cnt DESC, store_domain) = 1
)

SELECT
    FARM_FINGERPRINT(m.store_id)    AS store_key
    ,m.store_id
    ,m.store_domain
    ,sc.market_country_code
    ,sc.currency_code
    ,FALSE                          AS is_unknown
FROM main_domain AS m
LEFT JOIN {{ ref('store_currency') }} AS sc
    ON m.store_domain = sc.store_domain

UNION ALL

SELECT
    -1
    ,CAST(NULL AS STRING)
    ,'Unknown'
    ,CAST(NULL AS STRING)
    ,CAST(NULL AS STRING)
    ,TRUE
