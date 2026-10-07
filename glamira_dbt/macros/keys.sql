{#- Shared natural-key / attribute expressions: dims and the fact use the SAME macro,
    so the surrogate key computed in the fact always matches the dim row. -#}

{% macro geo_natural_key(country_code, region_name, city_name) -%}
    CONCAT(COALESCE({{ country_code }}, ''), '|', COALESCE({{ region_name }}, ''), '|', COALESCE({{ city_name }}, ''))
{%- endmacro %}

{% macro customer_id_hash(user_id_db, device_id) -%}
    CASE
        WHEN {{ user_id_db }} IS NOT NULL THEN TO_HEX(SHA256(CONCAT('user:', {{ user_id_db }})))
        WHEN {{ device_id }} IS NOT NULL THEN TO_HEX(SHA256(CONCAT('device:', {{ device_id }})))
    END
{%- endmacro %}

{% macro ua_is_bot(user_agent) -%}
    COALESCE(REGEXP_CONTAINS(LOWER({{ user_agent }}), r'bot|crawler|spider|headless|slurp'), FALSE)
{%- endmacro %}

{% macro ua_device_type(user_agent) -%}
    CASE
        WHEN {{ user_agent }} IS NULL THEN 'Unknown'
        WHEN REGEXP_CONTAINS(LOWER({{ user_agent }}), r'ipad|tablet|kindle|silk|sm-t\d') THEN 'Tablet'
        WHEN REGEXP_CONTAINS(LOWER({{ user_agent }}), r'android') AND NOT REGEXP_CONTAINS(LOWER({{ user_agent }}), r'mobi') THEN 'Tablet'
        WHEN REGEXP_CONTAINS(LOWER({{ user_agent }}), r'mobi|iphone|ipod|android|windows phone') THEN 'Mobile'
        ELSE 'Desktop'
    END
{%- endmacro %}

{% macro device_natural_key(user_agent, resolution) -%}
    CONCAT({{ ua_device_type(user_agent) }}, '|', COALESCE({{ resolution }}, ''), '|', CAST({{ ua_is_bot(user_agent) }} AS STRING))
{%- endmacro %}
