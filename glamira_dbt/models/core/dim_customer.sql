-- 1 row = 1 customer, plus 1 Unknown row.
-- Registered customers are identified by user_id_db, guests by device_id.
-- Only a SHA-256 hash of the identifier is stored (PII); email is not kept.

WITH customers AS (
    SELECT
        {{ customer_id_hash('user_id_db', 'device_id') }}   AS customer_id_hash
        ,LOGICAL_OR(user_id_db IS NOT NULL)                 AS is_registered
    FROM {{ ref('stg_checkout_orders') }}
    WHERE COALESCE(user_id_db, device_id) IS NOT NULL
    GROUP BY customer_id_hash
)

SELECT
    FARM_FINGERPRINT(customer_id_hash)                  AS customer_key
    ,customer_id_hash
    ,IF(is_registered, 'Registered', 'Guest')           AS customer_type
    ,is_registered
FROM customers

UNION ALL

SELECT
    -1
    ,CAST(NULL AS STRING)
    ,'Unknown'
    ,FALSE
