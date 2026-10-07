{{ config(materialized = 'view') }}

-- 1 row = 1 IP address (hashed, PII) with its geolocation

WITH source AS (
    SELECT *
    FROM {{ source('raw', 'ip_locations') }}
)

, renamed AS (
    SELECT
        {{ pii_hash('TRIM(ip)') }}                    AS ip_hash
        ,UPPER({{ clean_string('country_code') }})   AS country_code
        ,{{ clean_string('country_name') }}          AS country_name
        ,{{ clean_string('region_name') }}           AS region_name
        ,{{ clean_string('city_name') }}             AS city_name
        ,SAFE_CAST(latitude AS FLOAT64)              AS latitude
        ,SAFE_CAST(longitude AS FLOAT64)             AS longitude
        ,geo_status
    FROM source
)

SELECT *
FROM renamed
WHERE ip_hash IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY ip_hash ORDER BY geo_status = 'FOUND' DESC) = 1
