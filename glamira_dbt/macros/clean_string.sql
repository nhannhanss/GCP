{#- Trim, then turn '' and '-' into NULL -#}
{% macro clean_string(col) -%}
    NULLIF(NULLIF(TRIM({{ col }}), ''), '-')
{%- endmacro %}
