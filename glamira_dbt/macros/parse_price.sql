{#-
    Parse a price string in either format into NUMERIC:
      EU  : '1.234,56' / '2476,00' / '6.589.592,00'
      US  : '1,234.56' / '280.00'  / '20,933' (no decimals)
    The format is decided by the last separator: ',' followed by 1-2 digits = EU decimal comma.
    The Arabic decimal separator '٫' is treated as a comma; any other character is stripped.
-#}
{% macro parse_price(col) -%}
    CASE
        WHEN REGEXP_CONTAINS(REGEXP_REPLACE(REPLACE({{ col }}, '٫', ','), r'[^0-9.,]', ''), r',\d{1,2}$')
            THEN SAFE_CAST(
                REPLACE(REPLACE(REGEXP_REPLACE(REPLACE({{ col }}, '٫', ','), r'[^0-9.,]', ''), '.', ''), ',', '.')
                AS NUMERIC)
        ELSE SAFE_CAST(
                REPLACE(REGEXP_REPLACE(REPLACE({{ col }}, '٫', ','), r'[^0-9.,]', ''), ',', '')
                AS NUMERIC)
    END
{%- endmacro %}
