# Data Dictionary — Glamira Analytics

> Database: MongoDB `glamira_db` (GCP VM)
> Nguồn schema: `scripts/profile_collections.py` (sample ngẫu nhiên 20.000 docs/collection), cập nhật 2026-09-30

## Tổng quan

| Collection | Documents | Mô tả | Nguồn |
|---|---|---|---|
| `summary` | 41.432.473 | Raw events tracking hành vi người dùng trên các website Glamira | Dữ liệu gốc (load từ file raw) |
| `ip_locations` | 3.239.628 | Vị trí địa lý của từng IP unique trong `summary` | `enrich_ip_locations.py` (IP2Location LITE) |
| `products` | 19.511 | Thông tin sản phẩm crawl từ website Glamira | `crawl_products.py` |

## Quan hệ giữa các collection

```
summary.ip ─────────────────────────────► ip_locations.ip          (N:1)

summary.product_id ─────────────┐
summary.viewing_product_id ─────┤
summary.recommendation_product_id ──────► products.product_id      (N:1)
summary.cart_products[].product_id ─┘   (⚠ INTEGER, cần cast sang STRING)
```

---

## Collection: `summary` (raw events)

Schema-on-read: mỗi event type (`collection`) có tập field khác nhau. Cột **Event types** cho biết field xuất hiện ở đâu; "tất cả" = mọi event.

### Field chung (mọi event)

| Field | Type | Nullable | Mô tả | Example |
|---|---|---|---|---|
| `_id` | OBJECTID | No | ID của document MongoDB | `5ec167989d843b370657a86f` |
| `collection` | STRING | No | Event type | `view_product_detail` |
| `time_stamp` | INTEGER | No | Thời điểm event, **Unix epoch (giây)** | `1589733273` |
| `local_time` | STRING | No | Giờ local phía client, format `YYYY-MM-DD H:MM:SS`, không có timezone | `2020-05-17 6:34:28` |
| `ip` | STRING | No | IP người dùng, khóa join với `ip_locations` | `5.88.29.169` |
| `device_id` | STRING | No | UUID của thiết bị/trình duyệt | `a3e53d78-2fc8-...` |
| `user_id_db` | STRING | Yes (rỗng 95,2%) | ID user đã đăng nhập, chuỗi rỗng nếu là khách | `485793` |
| `email_address` | STRING | Yes (rỗng 95,2%) | Email user đã đăng nhập ⚠ **PII** | — |
| `store_id` | STRING | No | ID store (mỗi store là 1 domain/quốc gia) | `14` |
| `current_url` | STRING | No | URL trang xảy ra event | `https://www.glamira.it/...` |
| `referrer_url` | STRING | Yes (rỗng 9%) | URL trang trước đó | `https://www.glamira.it/...` |
| `user_agent` | STRING | No | User-Agent trình duyệt | `Mozilla/5.0 (Linux; Android 9; ...)` |
| `resolution` | STRING | No | Độ phân giải màn hình `WxH` | `393x851` |
| `api_version` | STRING | No | Phiên bản tracking API | `1.0` |
| `show_recommendation` | STRING | Yes (19%) | Có hiện recommendation không, lưu dạng chuỗi `"true"`/`"false"` | `true` |

### Field sản phẩm

| Field | Type | Nullable | Mô tả | Event types |
|---|---|---|---|---|
| `product_id` | STRING | Yes | ID sản phẩm đang tương tác | add_to_cart_action, back_to_product_action, select_product_option, select_product_option_quality, view_product_detail, view_all_recommend |
| `viewing_product_id` | STRING | Yes | ID sản phẩm đang xem khi tương tác với recommendation (`product_id` = null ở các event này) | product_detail_recommendation_clicked/noticed/visible, product_view_all_recommend_clicked |
| `recommendation_product_id` | STRING | Yes | ID sản phẩm được recommend và được click | landing_page / listing_page / product_detail / product_view_all _recommend_clicked |
| `recommendation_product_position` | INTEGER, STRING | Yes | Vị trí sản phẩm trong khối recommendation ⚠ lẫn kiểu | landing_page_recommendation_clicked, product_view_all_recommend_clicked |
| `recommendation_clicked_position` | INTEGER | Yes | Vị trí được click | listing_page_recommendation_clicked, product_detail_recommendation_clicked |
| `recommendation` | BOOLEAN | No | Người dùng vào trang sản phẩm từ recommendation hay không | view_product_detail |
| `price` | STRING | No | Giá sản phẩm khi thêm vào giỏ ⚠ lưu dạng chuỗi | add_to_cart_action |
| `currency` | STRING | No | Đơn vị tiền tệ của `price` | add_to_cart_action |

### Field `option` — **đa hình (2 cấu trúc khác nhau)**

**a) ARRAY of objects**, gặp ở add_to_cart_action, select_product_option, select_product_option_quality, view_product_detail:

| Field | Type | Nullable | Mô tả | Example |
|---|---|---|---|---|
| `option[].option_label` | STRING | No | Tên thuộc tính | `alloy` |
| `option[].option_id` | STRING | Yes | ID thuộc tính | `262387` |
| `option[].value_label` | STRING | Yes (rỗng ~51%) | Giá trị đã chọn | `yellow_white-585` |
| `option[].value_id` | STRING | Yes | ID giá trị | `2214087` |
| `option[].quality` | STRING | Yes | Chất lượng đá (chỉ có ở select_product_option_quality) | `AAA` |
| `option[].quality_label` | STRING | Yes | Nhãn chất lượng | `AAA` |

**b) OBJECT (key = tên thuộc tính)**, gặp ở listing_page_recommendation_*, view_listing_page, view_all_recommend:

| Field | Type | Nullable | Mô tả |
|---|---|---|---|
| `option.alloy` | STRING | Yes (~77%) | Chất liệu kim loại, ví dụ `yellow-375` |
| `option.diamond` | STRING | Yes (~70%) | Loại đá |
| `option.shapediamond` | STRING | Yes (~97%) | Hình dáng đá |
| `option.category id` | STRING | No | ⚠ Key có dấu cách (chỉ ở view_all_recommend) |
| `option.Kollektion`, `option.kollektion_id` | STRING | Yes | Bộ sưu tập (tên key tiếng Đức) |
| `option.finish`, `option.stone`, `option.price`, `option.pearlcolor` | STRING | Yes | Các thuộc tính khác của view_all_recommend |

### Field giỏ hàng / đơn hàng

| Field | Type | Nullable | Mô tả | Event types |
|---|---|---|---|---|
| `cart_products` | ARRAY | No | Danh sách sản phẩm trong giỏ | checkout, checkout_success, view_shopping_cart |
| `cart_products[].product_id` | **INTEGER** | No | ID sản phẩm ⚠ khác kiểu với `products.product_id` (STRING) | checkout, checkout_success, view_shopping_cart |
| `cart_products[].amount` | INTEGER | No | Số lượng | checkout, checkout_success |
| `cart_products[].price` | STRING | No | Đơn giá ⚠ lưu dạng chuỗi | checkout_success |
| `cart_products[].currency` | STRING | No | Đơn vị tiền tệ | checkout_success |
| `cart_products[].option` | ARRAY, STRING | Yes | Option đã chọn, chuỗi rỗng khi không có option ⚠ lẫn kiểu | checkout, checkout_success, view_shopping_cart |
| `order_id` | STRING, INTEGER, FLOAT | Yes | Mã đơn hàng ⚠ lẫn 3 kiểu | checkout, checkout_success |

> **Doanh thu:** không có field `order_amount`. Doanh thu của một đơn được tính bằng `Σ cart_products[].price × amount` trên event `checkout_success`, sau đó quy đổi tiền tệ theo `cart_products[].currency`.

### Field khác

| Field | Type | Nullable | Mô tả | Event types |
|---|---|---|---|---|
| `collect_id` | STRING | Yes (~79%) | ID collection sản phẩm trên trang listing | view_listing_page, listing_page_recommendation_* |
| `cat_id` | NULL | Luôn null | Không có dữ liệu → bỏ | view_listing_page, listing_page_recommendation_* |
| `key_search` | STRING | Yes (~70%) | Từ khóa tìm kiếm | search_box_action |
| `utm_source`, `utm_medium` | BOOLEAN, STRING | No | Nguồn marketing, bằng `false` khi không có UTM ⚠ lẫn kiểu | view_product_detail |
| `is_paypal` | NULL | Luôn null | Không có dữ liệu → bỏ | add_to_cart_action |

---

## Collection: `ip_locations`

1 document = 1 IP unique trong `summary`. Tra cứu bằng IP2Location LITE.

| Field | Type | Nullable | Mô tả | Example |
|---|---|---|---|---|
| `_id` | OBJECTID | No | ID của document MongoDB | — |
| `ip` | STRING | No | IP address, **unique**, khóa join | `84.2.63.253` |
| `country_code` | STRING | No | Mã quốc gia ISO 3166-1 alpha-2 | `HU` |
| `country_name` | STRING | No | Tên quốc gia | `Hungary` |
| `region_name` | STRING | No | Vùng/tỉnh | `Gyor-Moson-Sopron` |
| `city_name` | STRING | No | Thành phố | `Mosonszentmiklos` |
| `latitude` | FLOAT | No | Vĩ độ | `47.727779` |
| `longitude` | FLOAT | No | Kinh độ | `17.427839` |
| `geo_status` | STRING | No | Trạng thái tra cứu, `FOUND` = tra được | `FOUND` |
| `event_count` | INTEGER | No | Số event trong `summary` có IP này | `2` |

---

## Collection: `products`

1 document = 1 `product_id` unique (upsert theo `product_id`, có unique index).

| Field | Type | Nullable | Mô tả | Example |
|---|---|---|---|---|
| `_id` | OBJECTID | No | ID của document MongoDB | — |
| `product_id` | STRING | No | ID sản phẩm, **unique**, khóa join | `92703` |
| `product_name` | STRING | Yes (4,6%) | Tên sản phẩm | `Wedding Ring Classic Shield` |
| `category` | STRING | Yes (4,6%) | Danh mục sản phẩm | `Wedding Rings` |
| `price` | FLOAT | Yes (4,6%) | Giá trên trang tại thời điểm crawl, theo tiền tệ của `host` | `3491.0` |
| `currency` | STRING | Yes (4,6%) | Đơn vị tiền tệ của `price` | `AUD` |
| `image_url` | STRING | Yes (4,6%) | Ảnh sản phẩm | `https://cdn-media.glamira.com/...` |
| `description` | NULL | Luôn null | Chưa parse được → bỏ | — |
| `sku` | NULL | Luôn null | Chưa parse được → bỏ | — |
| `host` | STRING | No | Domain đã crawl | `www.glamira.com.au` |
| `source_url` | STRING | No | URL đã request | `https://www.glamira.com.au/catalog/...` |
| `http_status` | INTEGER | No | HTTP status: `200` hoặc `404` | `200` |
| `success` | BOOLEAN | No | Crawl thành công hay không | `true` |
| `error` | STRING | Yes (95,4% null) | Lý do lỗi, `not_found` khi 404 | `not_found` |
| `crawled_at` | STRING | No | Thời điểm crawl, ISO 8601 UTC | `2026-09-29T22:32:48+00:00` |
| `_loaded_at` | TIMESTAMP | No | Thời điểm load vào MongoDB | `2026-09-30 00:31:48` |
| `_source_file` | STRING | No | File nguồn | `products_raw.csv` |

---

## Known Data Quality Issues

| # | Vấn đề | Ảnh hưởng | Xử lý đề xuất (Project 06/07) |
|---|---|---|---|
| 1 | 900 / 19.511 product (**4,6%**) trả HTTP 404, tức sản phẩm đã bị gỡ khỏi website | Không có name/category → doanh thu của những product này rơi vào nhóm "Unknown" | Giữ record với `success=false`; trên dashboard gán category `Unknown` |
| 2 | Kiểu `product_id` không đồng nhất: STRING ở `summary`/`products`, INTEGER ở `cart_products[]` | Join sai hoặc mất dòng | Cast toàn bộ sang STRING ở raw layer |
| 3 | `order_id` lẫn STRING / INTEGER / FLOAT | FLOAT có thể mất chữ số, sai khi dedupe đơn | Cast sang STRING (không qua float) |
| 4 | `price`, `cart_products[].price` lưu dạng STRING | Không tính toán trực tiếp được | `SAFE_CAST(... AS NUMERIC)` |
| 5 | Nhiều tiền tệ (CHF, AUD, EUR, ...) | Không cộng doanh thu trực tiếp được | Quy đổi FX sang 1 đơn vị (Project 07) |
| 6 | `products.price` là giá tại host đã crawl, không phải giá lúc bán | Không dùng để tính doanh thu | Doanh thu lấy từ `cart_products[].price` |
| 7 | `option` có 2 cấu trúc (ARRAY / OBJECT); `cart_products[].option` lẫn ARRAY/STRING; key `category id` có dấu cách | Lỗi schema khi load BigQuery | Load raw dưới dạng JSON/STRING, parse ở tầng transform |
| 8 | `utm_source`/`utm_medium` lẫn BOOLEAN/STRING; `recommendation_product_position` lẫn INTEGER/STRING | Lỗi auto-detect schema | Khai báo schema STRING |
| 9 | `time_stamp` là Unix epoch (INTEGER); `local_time` không có timezone, giờ không có số 0 đầu | Phải convert trước khi phân tích theo thời gian | Dùng `TIMESTAMP_SECONDS(time_stamp)`, bỏ `local_time` |
| 10 | `cat_id`, `is_paypal`, `products.description`, `products.sku` luôn null | Không có giá trị | Loại bỏ ở tầng analytical |
| 11 | `email_address` là dữ liệu cá nhân (PII) | Rủi ro bảo mật | Hash hoặc loại bỏ trước khi đưa lên BigQuery |
| 12 | 95,2% event không có `user_id_db` (khách chưa đăng nhập) | Không phân tích được theo user | Dùng `device_id` làm định danh |

<!-- Bổ sung thêm findings từ data_quality_report.md (duplicate, future dates, negative revenue...) -->
