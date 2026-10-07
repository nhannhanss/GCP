-- 1 row = 1 distinct country / region / city found by IP geolocation, plus 1 Unknown row.
-- IP addresses are NOT stored here (PII); the fact reaches this table through the same natural key.

WITH geo AS (
    SELECT DISTINCT
        country_code
        ,country_name
        ,region_name
        ,city_name
    FROM {{ ref('stg_ip_locations') }}
    WHERE country_code IS NOT NULL
)

, geo_keyed AS (
    SELECT
        FARM_FINGERPRINT({{ geo_natural_key('country_code', 'region_name', 'city_name') }}) AS geo_key
        ,*
    FROM geo
    WHERE TRUE
    -- the same country/region/city can appear with two spellings of country_name; keep one row per key
    QUALIFY ROW_NUMBER() OVER (PARTITION BY {{ geo_natural_key('country_code', 'region_name', 'city_name') }} ORDER BY country_name) = 1
)

SELECT
    geo_key
    ,country_code
    ,country_name
    ,region_name
    ,city_name
    ,CASE
        WHEN city_name IS NOT NULL THEN 'city'
        WHEN region_name IS NOT NULL THEN 'region'
        ELSE 'country'
    END                                                                                 AS geo_level
    ,FALSE                                                                              AS is_unknown
FROM geo_keyed

UNION ALL

SELECT
    -1
    ,CAST(NULL AS STRING)
    ,'Unknown'
    ,CAST(NULL AS STRING)
    ,CAST(NULL AS STRING)
    ,'unknown'
    ,TRUE
