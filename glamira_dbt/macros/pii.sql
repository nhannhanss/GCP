{#-
    One-way SHA-256 hash for personal data (PII), with a salt so the hash cannot be
    reversed by hashing a list of known emails/IPs. Override the salt with the
    environment variable DBT_PII_SALT. NULL stays NULL.
-#}
{% macro pii_hash(col) -%}
    TO_HEX(SHA256(CONCAT('{{ env_var("DBT_PII_SALT", "glamira-p07") }}', CAST({{ col }} AS STRING))))
{%- endmacro %}
