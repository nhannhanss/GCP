{{
    config(
        partition_by = {'field': 'order_date', 'data_type': 'date', 'granularity': 'month'},
        cluster_by = ['country_name', 'category_group_name']
    )
}}

-- Flat table for Looker Studio: 1 row = 1 order line with every dimension attribute already joined.
-- Grain is the same as fact_sales_order_detail, so SUM / COUNT_DISTINCT work directly in the dashboard.

SELECT
    -- keys
    f.sales_order_detail_key
    ,f.order_id
    ,f.line_number

    -- When
    ,d.full_date                                AS order_date
    ,d.year_month
    ,d.year
    ,d.quarter_name
    ,d.month_number
    ,d.month_name
    ,d.week_of_year
    ,d.day_of_week
    ,d.day_name
    ,d.is_weekend
    ,EXTRACT(HOUR FROM f.order_time)            AS order_hour_utc

    -- Where
    ,g.country_code
    ,g.country_name
    ,g.region_name
    ,g.city_name
    ,s.store_id
    ,s.store_domain
    ,s.market_country_code

    -- What
    ,p.product_id
    ,p.product_name
    ,p.category_name
    ,p.category_group_name

    -- Who / How
    ,c.customer_key
    ,c.customer_type
    ,v.device_type
    ,v.is_bot

    -- measures
    ,f.order_qty
    ,f.unit_price_local
    ,f.line_amount_local
    ,f.currency_code
    ,f.line_amount_usd
FROM {{ ref('fact_sales_order_detail') }} AS f
LEFT JOIN {{ ref('dim_date') }} AS d
    ON f.date_key = d.date_key
LEFT JOIN {{ ref('dim_geo') }} AS g
    ON f.geo_key = g.geo_key
LEFT JOIN {{ ref('dim_store') }} AS s
    ON f.store_key = s.store_key
LEFT JOIN {{ ref('dim_product') }} AS p
    ON f.product_key = p.product_key
LEFT JOIN {{ ref('dim_customer') }} AS c
    ON f.customer_key = c.customer_key
LEFT JOIN {{ ref('dim_device') }} AS v
    ON f.device_key = v.device_key
