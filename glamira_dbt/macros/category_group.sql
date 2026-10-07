{#-
    Group the crawled breadcrumb category into a small set for dashboards.
    'Home' in several languages means the crawler took the first breadcrumb → Unknown.
    'earring' is checked before 'ring' because 'Earrings' contains 'ring'.
-#}
{% macro category_group(col) -%}
    CASE
        WHEN {{ col }} IS NULL
            OR LOWER(TRIM({{ col }})) IN ('home', 'startseite', 'acasă', 'hem', 'accueil', 'inicio', 'hjem', 'etusivu', 'startpagina')
            THEN 'Unknown'
        WHEN REGEXP_CONTAINS(LOWER({{ col }}), r'earring') THEN 'Earrings'
        WHEN REGEXP_CONTAINS(LOWER({{ col }}), r'ring') THEN 'Rings'
        WHEN REGEXP_CONTAINS(LOWER({{ col }}), r'necklace|pendant') THEN 'Necklaces'
        WHEN REGEXP_CONTAINS(LOWER({{ col }}), r'bracelet|bangle') THEN 'Bracelets'
        WHEN REGEXP_CONTAINS(LOWER({{ col }}), r'\bset\b') THEN 'Sets'
        ELSE 'Other'
    END
{%- endmacro %}
