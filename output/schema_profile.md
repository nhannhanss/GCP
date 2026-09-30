# Schema Profile (sample 20,000 docs / collection)

_Generated: 2026-09-30 07:40_


## summary

- Tổng documents: **41,432,473** | Sampled: 20,000
- Số event types trong sample: 26

| Field | Type(s) | % có field | % null/rỗng | Example | Event types |
|---|---|---|---|---|---|
| `_id` | OBJECTID | 100.0% | 0.0% | 5ec167989d843b370657a86f | tất cả |
| `api_version` | STRING | 100.0% | 0.0% | 1.0 | tất cả |
| `collection` | STRING | 100.0% | 0.0% | view_listing_page | tất cả |
| `current_url` | STRING | 100.0% | 0.0% | https://www.glamira.it/orecchini-con-dia | tất cả |
| `device_id` | STRING | 100.0% | 0.0% | a3e53d78-2fc8-44bf-92bb-1e4e26d91729 | tất cả |
| `email_address` | STRING | 100.0% | 95.2% | florian.beillon@sfr.fr | tất cả |
| `ip` | STRING | 100.0% | 0.0% | 5.88.29.169 | tất cả |
| `local_time` | STRING | 100.0% | 0.0% | 2020-05-17 6:34:28 | tất cả |
| `referrer_url` | STRING | 100.0% | 9.0% | https://www.glamira.it/orecchini-con-dia | tất cả |
| `resolution` | STRING | 100.0% | 0.0% | 393x851 | tất cả |
| `show_recommendation` | STRING, NULL | 100.0% | 19.0% | true | tất cả |
| `store_id` | STRING | 100.0% | 0.0% | 14 | tất cả |
| `time_stamp` | INTEGER | 100.0% | 0.0% | 1589733273 | tất cả |
| `user_agent` | STRING | 100.0% | 0.0% | Mozilla/5.0 (Linux; Android 9; Mi Note 1 | tất cả |
| `user_id_db` | STRING | 100.0% | 95.2% | 485793 | tất cả |
| `option` | ARRAY, OBJECT | 82.3% | 0.0% |  | add_to_cart_action, listing_page_recommendation_clicked, listing_page_recommendation_noticed, listing_page_recommendation_visible (+6) |
| `product_id` | STRING | 53.4% | 0.0% | 103499 | add_to_cart_action, back_to_product_action, select_product_option, select_product_option_quality (+2) |
| `option[].option_label` | STRING | 53.1% | 0.0% | alloy | add_to_cart_action, select_product_option, select_product_option_quality, view_product_detail |
| `option[].value_id` | STRING | 53.1% | 0.3% | 2214087 | add_to_cart_action, select_product_option, select_product_option_quality, view_product_detail |
| `option[].value_label` | STRING | 53.1% | 50.7% | yellow_white-585 | add_to_cart_action, select_product_option, select_product_option_quality, view_product_detail |
| `option[].option_id` | STRING | 52.7% | 0.3% | 262387 | add_to_cart_action, select_product_option, select_product_option_quality, view_product_detail |
| `option.alloy` | STRING | 29.0% | 76.9% | yellow-375 | listing_page_recommendation_clicked, listing_page_recommendation_noticed, listing_page_recommendation_visible, view_all_recommend (+2) |
| `option.diamond` | STRING | 28.9% | 70.4% | emerald-Swarovsky | listing_page_recommendation_clicked, listing_page_recommendation_noticed, listing_page_recommendation_visible, view_listing_page (+1) |
| `option.shapediamond` | STRING | 28.9% | 96.6% | 4400 | listing_page_recommendation_clicked, listing_page_recommendation_noticed, listing_page_recommendation_visible, view_listing_page (+1) |
| `cat_id` | NULL | 28.8% | 100.0% |  | listing_page_recommendation_clicked, listing_page_recommendation_noticed, listing_page_recommendation_visible, view_listing_page |
| `collect_id` | STRING | 28.8% | 79.0% | 5243 | listing_page_recommendation_clicked, listing_page_recommendation_noticed, listing_page_recommendation_visible, view_listing_page |
| `recommendation` | BOOLEAN | 26.4% | 0.0% | False | view_product_detail |
| `utm_medium` | BOOLEAN, STRING | 26.4% | 0.0% | False | view_product_detail |
| `utm_source` | BOOLEAN, STRING | 26.4% | 0.0% | False | view_product_detail |
| `option[].quality` | STRING | 5.2% | 0.0% | AAA | select_product_option_quality |
| `viewing_product_id` | STRING | 5.0% | 0.0% | 90744 | product_detail_recommendation_clicked, product_detail_recommendation_noticed, product_detail_recommendation_visible, product_view_all_recommend_clicked |
| `option[].quality_label` | STRING | 4.6% | 0.0% | AAA | select_product_option_quality |
| `cart_products` | ARRAY | 1.1% | 0.0% |  | checkout, checkout_success, view_shopping_cart |
| `cart_products[].option` | ARRAY, STRING | 0.9% | 4.9% |  | checkout, checkout_success, view_shopping_cart |
| `cart_products[].product_id` | INTEGER | 0.9% | 0.0% | 94970 | checkout, checkout_success, view_shopping_cart |
| `cart_products[].option[].option_id` | INTEGER | 0.9% | 0.0% | 143746 | checkout, checkout_success, view_shopping_cart |
| `cart_products[].option[].option_label` | STRING | 0.9% | 0.0% | alloy | checkout, checkout_success, view_shopping_cart |
| `cart_products[].option[].value_id` | INTEGER | 0.9% | 0.0% | 1073718 | checkout, checkout_success, view_shopping_cart |
| `cart_products[].option[].value_label` | STRING | 0.9% | 0.0% | Weißgold 750 | checkout, checkout_success, view_shopping_cart |
| `recommendation_product_id` | STRING, NULL | 0.7% | 7.6% | 99205 | landing_page_recommendation_clicked, listing_page_recommendation_clicked, product_detail_recommendation_clicked, product_view_all_recommend_clicked |
| `key_search` | NULL, STRING | 0.6% | 70.1% | GLAMIRARING BRIDAL RISE 0,5CRT | search_box_action |
| `recommendation_clicked_position` | INTEGER, NULL | 0.5% | 9.6% | 0 | listing_page_recommendation_clicked, product_detail_recommendation_clicked |
| `currency` | STRING | 0.4% | 0.0% | CHF | add_to_cart_action |
| `is_paypal` | NULL | 0.4% | 100.0% |  | add_to_cart_action |
| `price` | STRING | 0.4% | 0.0% | 296.00 | add_to_cart_action |
| `cart_products[].amount` | INTEGER | 0.3% | 0.0% | 1 | checkout, checkout_success |
| `order_id` | STRING, INTEGER, FLOAT | 0.3% | 75.0% | 1072033514 | checkout, checkout_success |
| `recommendation_product_position` | INTEGER, STRING | 0.1% | 40.7% | 8 | landing_page_recommendation_clicked, product_view_all_recommend_clicked |
| `option.Kollektion` | STRING | 0.1% | 18.8% | Twinset | view_all_recommend |
| `option.category id` | STRING | 0.1% | 0.0% | 757 | view_all_recommend |
| `option.finish` | STRING | 0.1% | 68.8% | polished | view_all_recommend |
| `option.kollektion_id` | STRING | 0.1% | 18.8% | 4090 | view_all_recommend |
| `option.pearlcolor` | STRING | 0.1% | 100.0% |  | view_all_recommend |
| `option.price` | STRING | 0.1% | 0.0% | 614.00 | view_all_recommend |
| `option.stone` | STRING | 0.1% | 0.0% | 6 | view_all_recommend |
| `cart_products[].currency` | STRING | 0.1% | 0.0% | CHF | checkout_success |
| `cart_products[].price` | STRING | 0.1% | 0.0% | 245.00 | checkout_success |

## ip_locations

- Tổng documents: **3,239,628** | Sampled: 20,000

| Field | Type(s) | % có field | % null/rỗng | Example |
|---|---|---|---|---|
| `_id` | OBJECTID | 100.0% | 0.0% | 6abc280a2779207afe3102ec |
| `city_name` | STRING | 100.0% | 0.0% | Mosonszentmiklos |
| `country_code` | STRING | 100.0% | 0.0% | HU |
| `country_name` | STRING | 100.0% | 0.0% | Hungary |
| `event_count` | INTEGER | 100.0% | 0.0% | 2 |
| `geo_status` | STRING | 100.0% | 0.0% | FOUND |
| `ip` | STRING | 100.0% | 0.0% | 84.2.63.253 |
| `latitude` | FLOAT | 100.0% | 0.0% | 47.727779 |
| `longitude` | FLOAT | 100.0% | 0.0% | 17.427839 |
| `region_name` | STRING | 100.0% | 0.0% | Gyor-Moson-Sopron |

## products

- Tổng documents: **19,511** | Sampled: 19,511

| Field | Type(s) | % có field | % null/rỗng | Example |
|---|---|---|---|---|
| `_id` | OBJECTID | 100.0% | 0.0% | 6abc5874cbf5d333f5705e8e |
| `_loaded_at` | TIMESTAMP | 100.0% | 0.0% | 2026-09-30 00:31:48.448000 |
| `_source_file` | STRING | 100.0% | 0.0% | products_raw.csv |
| `category` | STRING, NULL | 100.0% | 4.6% | Wedding Rings |
| `crawled_at` | STRING | 100.0% | 0.0% | 2026-09-29T22:32:48.445568+00:00 |
| `currency` | STRING, NULL | 100.0% | 4.6% | AUD |
| `description` | NULL | 100.0% | 100.0% |  |
| `error` | NULL, STRING | 100.0% | 95.4% | not_found |
| `host` | STRING | 100.0% | 0.0% | www.glamira.com.au |
| `http_status` | INTEGER | 100.0% | 0.0% | 200 |
| `image_url` | STRING, NULL | 100.0% | 4.6% | https://cdn-media.glamira.com/media/prod |
| `price` | FLOAT, NULL | 100.0% | 4.6% | 3491.0 |
| `product_id` | STRING | 100.0% | 0.0% | 92703 |
| `product_name` | STRING, NULL | 100.0% | 4.6% | Wedding Ring Classic Shield |
| `sku` | NULL | 100.0% | 100.0% |  |
| `source_url` | STRING | 100.0% | 0.0% | https://www.glamira.com.au/catalog/produ |
| `success` | BOOLEAN | 100.0% | 0.0% | True |
