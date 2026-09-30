# Data Profiling — Glamira Raw Layer (BigQuery `raw`)

> Project 06 — Data Pipeline & Storage
> Nguồn query: [`sql/data_profiling.sql`](../sql/data_profiling.sql)
> Ngày chạy: 2026-09-30

---

## 1. Tổng quan pipeline & đối soát số lượng

```
MongoDB (VM) ──export_to_gcs.py──> GCS (JSONL.gz) ──Cloud Function──> BigQuery raw
```

| Bảng | MongoDB | GCS (manifest) | BigQuery | Số file | Khớp |
|---|---:|---:|---:|---:|:---:|
| `raw.events` | 41,432,473 | 41,432,473 | 41,432,473 | 166 | ✅ |
| `raw.ip_locations` | 3,239,628 | 3,239,628 | 3,239,628 | 13 | ✅ |
| `raw.products` | 19,511 | 19,511 | 19,511 | 1 | ✅ |

- Định dạng trung gian: JSON Lines nén gzip, 250,000 dòng/file.
- Cloud Function `gcs-to-bigquery` (gen2, trigger `object.finalized`) route theo prefix
  `staging/<table>/incoming/` → `raw.<table>`; `job_id` sinh từ `bucket/object#generation`
  nên event bị gửi lại không gây load trùng.
- Raw layer lưu **mọi cột dạng STRING**, `raw.events` giữ thêm `payload` = nguyên document gốc
  (schema-on-read). Ép kiểu thực hiện ở tầng transform (dbt — Project 07).

**Khoảng thời gian dữ liệu:** `2020-04-01 00:00:01 UTC` → `2020-06-04 10:21:32 UTC` (~65 ngày).

---

## 2. Data sources — bảng, cột, kiểu dữ liệu

### 2.1 `raw.events` — 41,432,473 dòng, 22 cột

| Cột | Kiểu raw | Kiểu gốc (MongoDB) | Kiểu đích đề xuất | Ghi chú |
|---|---|---|---|---|
| `event_id` | STRING | ObjectId | STRING | **Khóa chính** (từ `_id`) |
| `collection` | STRING | string | STRING | Loại event, 27 giá trị |
| `time_stamp` | STRING | number (unix giây) | TIMESTAMP | |
| `local_time` | STRING | string | DATETIME | Giờ địa phương của người dùng |
| `ip` | STRING | string | STRING | FK → `ip_locations.ip` |
| `user_agent` | STRING | string | STRING | |
| `resolution` | STRING | string | STRING | vd. `1920x1080` |
| `user_id_db` | STRING | string | INT64 | Rỗng = khách vãng lai |
| `device_id` | STRING | string | STRING | |
| `api_version` | STRING | string | — | Chỉ 1 giá trị → bỏ |
| `store_id` | STRING | string | INT64 | 86 store |
| `current_url` | STRING | string | STRING | |
| `referrer_url` | STRING | string | STRING | |
| `email_address` | STRING | string | STRING | PII |
| `product_id` | STRING | string | INT64 | FK → `products.product_id` |
| `viewing_product_id` | STRING | string | INT64 | FK → `products.product_id` |
| `order_id` | STRING | string | STRING | Chỉ có ở `checkout*` |
| `cat_id` | STRING | string | STRING | |
| `collect_id` | STRING | string | STRING | |
| `payload` | STRING | document | JSON | Toàn bộ document gốc |
| `_run_id`, `_exported_at` | STRING | — | — | Metadata pipeline |

### 2.2 `raw.ip_locations` — 3,239,628 dòng, 11 cột

`ip` (khóa chính), `country_code`, `country_name`, `region_name`, `city_name`,
`latitude`, `longitude`, `event_count`, `geo_status`, `_run_id`, `_exported_at`.
Nguồn: IP2Location LITE DB5, lookup trên **unique IP**.

### 2.3 `raw.products` — 19,511 dòng, 18 cột

`product_id` (khóa chính), `product_name`, `sku`, `price`, `currency`, `category`,
`image_url`, `description`, `source_url`, `host`, `crawled_at`, `success`, `http_status`,
`error`, `_loaded_at`, `_source_file`, `_run_id`, `_exported_at`.
Nguồn: crawl `https://<store>/catalog/product/view/id/<product_id>` (JSON-LD schema.org/Product).

---

## 3. Profiling `raw.events`

### 3.1 Constraint

| Kiểm tra | Kết quả |
|---|---|
| `event_id` duy nhất | 41,432,473 / 41,432,473 — **0 trùng** ✅ |
| `collection`, `ip`, `store_id`, `time_stamp`, `device_id` NOT NULL | 0 NULL ✅ |

### 3.2 Phân bố loại event (27 loại)

| collection | Số event | % |
|---|---:|---:|
| view_listing_page | 11,259,694 | 27.18 |
| view_product_detail | 10,944,427 | 26.42 |
| select_product_option | 8,844,342 | 21.35 |
| select_product_option_quality | 2,231,825 | 5.39 |
| view_static_page | 1,451,565 | 3.50 |
| view_landing_page | 1,434,230 | 3.46 |
| product_detail_recommendation_visible | 1,302,362 | 3.14 |
| view_home_page | 1,053,420 | 2.54 |
| … (15 loại khác) | | |
| view_shopping_cart | 343,077 | 0.83 |
| add_to_cart_action | 187,901 | 0.45 |
| checkout | 88,540 | 0.21 |
| **checkout_success** | **26,079** | **0.06** |
| back_to_product_action | 561 | 0.00 |

Phễu chuyển đổi: 10.9M xem sản phẩm → 188K thêm giỏ → 88.5K checkout → **26K đơn thành công**.

### 3.3 NULL, chuỗi rỗng & distinct

| Cột | NULL | Chuỗi rỗng `''` | % thiếu | Distinct (≈) |
|---|---:|---:|---:|---:|
| `cat_id` | 41,432,215 | 0 | 100.00 | 37 |
| `order_id` | 41,317,854 | 88,540 | 99.94 | 26,069 |
| `viewing_product_id` | 39,443,421 | 0 | 95.20 | 16,995 |
| `email_address` | 397 | 39,443,524 | 95.20 | 31,379 |
| `user_id_db` | 0 | 39,440,191 | 95.19 | 30,956 |
| `collect_id` | 29,389,367 | 9,413,260 | 93.65 | 62 |
| `product_id` | 19,189,753 | 0 | 46.32 | 19,443 |
| `referrer_url` | 0 | 3,783,396 | 9.13 | 3,576,569 |
| `resolution` | 240 | 0 | 0.00 | 6,227 |
| `local_time` | 240 | 0 | 0.00 | 3,124,559 |
| `user_agent` | 0 | 3 | 0.00 | 207,533 |
| `store_id` | 0 | 0 | 0.00 | 86 |
| `api_version` | 0 | 0 | 0.00 | **1** |
| `ip` | 0 | 0 | 0.00 | 3,231,048 |
| `device_id` | 0 | 0 | 0.00 | 7,777,105 |
| `current_url` | 0 | 0 | 0.00 | 16,172,394 |

> `distinct` dùng `APPROX_COUNT_DISTINCT` (sai số ~1%). Số chính xác: `ip` = 3,239,628;
> `product_id` = 19,417; `event_id` = 41,432,473.

**Nhận xét**

- **Giá trị thiếu được biểu diễn không nhất quán**: có cột dùng `NULL`, có cột dùng chuỗi rỗng
  (`user_id_db`, `email_address`, `referrer_url`, `collect_id`) → chuẩn hóa `NULLIF(col, '')` ở staging.
- **~95% event là khách vãng lai** (`user_id_db`, `email_address` rỗng).
- `order_id` rỗng đúng **88,540** dòng = số event `checkout` → event `checkout` có key `order_id`
  nhưng chưa có giá trị; chỉ `checkout_success` có mã đơn.
- `order_id` distinct ≈ 26,069 < 26,079 event `checkout_success` → **có đơn bị ghi nhận trùng**,
  cần dedup khi xây fact bán hàng.
- `cat_id` có key trong các event listing nhưng giá trị gần như luôn NULL (chỉ 258 dòng có giá trị).
- `product_id` NULL 46% là **đúng nghiệp vụ**: chỉ event liên quan sản phẩm mới có.
- `api_version` hằng số → bỏ.

### 3.4 Tính nhất quán kiểu dữ liệu

**a) Giá trị ép kiểu được không** (toàn bộ 41.4M dòng)

| Kiểm tra | Số dòng lỗi |
|---|---:|
| `time_stamp` không phải số nguyên | 0 |
| `store_id` không phải số nguyên | 0 |
| `product_id` không phải số nguyên | 0 |
| `user_id_db` không phải số nguyên (khác rỗng) | 0 |
| `ip` không hợp lệ | **6** (1 IP, khớp `geo_status = INVALID`) |
| `email_address` sai định dạng | 0 |

**b) Kiểu gốc trong MongoDB** (đọc từ `payload`, mẫu 5%)

| Field | Kiểu JSON | Số dòng (mẫu) |
|---|---|---:|
| `time_stamp` | number | 1,998,417 |
| `store_id` | string | 1,998,417 |
| `user_id_db` | string | 1,998,417 |
| `product_id` | string | 1,074,348 |
| `cart_products` | array | 21,947 |
| **`option`** | **array** | **1,072,699 (65%)** |
| **`option`** | **object** | **581,976 (35%)** |

- ID dạng số (`store_id`, `product_id`, `user_id_db`) được lưu là **string** trong nguồn nhưng
  nội dung 100% là số → ép sang INT64 an toàn.
- **`option` đa hình** (lúc object, lúc array of object) → đây là lý do raw layer không ép schema
  cứng; staging cần chuẩn hóa về array: `IF(JSON_TYPE(option)='object', [option], option)`.

### 3.5 Schema theo từng loại event (mẫu 5%)

Mỗi loại event có tập field riêng. Field **chỉ nằm trong `payload`** (chưa tách cột), cần trích ở dbt:

| Field | Có ở event |
|---|---|
| `cart_products` (array) | `view_shopping_cart`, `checkout`, `checkout_success` |
| `price`, `currency`, `is_paypal` | `add_to_cart_action` |
| `option` | `view_product_detail`, `select_product_option*`, `view_listing_page`, `listing_page_recommendation_*`, `view_all_recommend`, `view_sorting_relevance`, `add_to_cart_action` |
| `recommendation_product_id` | `*_recommendation_clicked`, `product_view_all_recommend_clicked`, `sorting_relevance_click_action` |
| `recommendation_product_position` / `recommendation_clicked_position` | các event click recommendation |
| `key_search` | `search_box_action` |
| `utm_source`, `utm_medium`, `recommendation` | `view_product_detail` |
| `show_recommendation` | hầu hết event |

---

## 4. Profiling `raw.ip_locations`

| Kiểm tra | Kết quả |
|---|---|
| `ip` duy nhất | 3,239,628 / 3,239,628 ✅ |
| `latitude`, `longitude` ép FLOAT64 | 0 lỗi ✅ |
| `event_count` ép INT64 | 0 lỗi ✅ |
| Tổng `event_count` | 41,432,473 = tổng event ✅ |

| `geo_status` | Số IP | Số event | % event |
|---|---:|---:|---:|
| FOUND | 3,238,974 | 41,422,924 | **99.98** |
| NOT_FOUND | 347 | 3,440 | 0.01 |
| NON_GLOBAL (private/reserved) | 306 | 6,103 | 0.01 |
| INVALID | 1 | 6 | 0.00 |

| Cột | NULL | % | Distinct (≈) |
|---|---:|---:|---:|
| `country_code`, `country_name`, `latitude`, `longitude` | 654 | 0.02 | 225 quốc gia |
| `region_name` | 883 | 0.03 | 2,572 |
| `city_name` | 883 | 0.03 | 44,557 |

229 IP xác định được quốc gia nhưng không có vùng/thành phố.

**Top quốc gia theo số event:** United States 5.10M · Germany 5.08M · United Kingdom 2.77M ·
Sweden 2.23M · France 2.18M · Italy 1.65M · Spain 1.47M · Romania 1.25M · Australia 1.24M ·
Netherlands 1.18M.

---

## 5. Profiling `raw.products`

| Kiểm tra | Kết quả |
|---|---|
| `product_id` duy nhất | 19,511 / 19,511 ✅ |
| `product_id` ép INT64 | 0 lỗi ✅ |
| `price` ép FLOAT64 | 0 lỗi ✅ |
| `crawled_at` ép TIMESTAMP | 0 lỗi ✅ |

**Kết quả crawl**

| success | http_status | Số SP | % |
|---|---|---:|---:|
| True | 200 | 18,609 | 95.38 |
| False | 404 (sản phẩm đã gỡ) | 902 | 4.62 |

Không có request bị chặn (403) hay timeout.

| Cột | NULL | % | Distinct (≈) |
|---|---:|---:|---:|
| `sku`, `description` | 19,511 | **100.00** | 0 |
| `product_name`, `price`, `currency`, `category`, `image_url` | 902 | 4.62 | — |
| `category` | | | 59 |
| `currency` | | | 13 |
| `host` | 0 | 0.00 | 18 |

**Vấn đề chất lượng**

1. **`category = 'Home'` — 4,557 dòng (23%)**: trang chỉ có breadcrumb `Home > <sản phẩm>`,
   parser lấy nhầm `Home`. → Suy category từ `product_name` ở staging.
2. **Category không chuẩn hóa**: `Rings`, `Wedding Rings`, `Men’s Wedding Rings`,
   `Women’s Wedding Rings`, `Engagement Rings`, `PEARL's Rings`, `Knuckle Rings`… (59 giá trị)
   → map về ~10 nhóm cha (Rings, Necklaces, Earrings, Bracelets, …).
3. **`currency` do store quyết định** (1 host ↔ 1 tiền tệ); store được chọn ngẫu nhiên trong
   8 store tiếng Anh → 13 loại tiền. **`price` chỉ mang tính tham khảo**, không dùng để tính
   doanh thu; doanh thu lấy từ `cart_products` của `checkout_success`.
4. `sku`, `description` luôn rỗng (JSON-LD của Glamira không có) → bỏ.

---

## 6. Relationships

```
raw.events.ip                          ──N:1──> raw.ip_locations.ip
raw.events.product_id                  ──N:1──> raw.products.product_id
raw.events.viewing_product_id          ──N:1──> raw.products.product_id
payload.cart_products[].product_id     ──N:1──> raw.products.product_id
payload.recommendation_product_id      ──N:1──> raw.products.product_id
raw.events.store_id                    ──N:1──> (store — chưa có bảng, 86 giá trị)
raw.events.user_id_db                  ──N:1──> (customer — chưa có bảng)
```

| Quan hệ | Kết quả |
|---|---|
| `events.ip` → `ip_locations.ip` | 41,432,473 / 41,432,473 khớp (100%); có vị trí: **99.98%** |
| `events.product_id` → `products.product_id` | 19,417 / 19,417 distinct ID khớp (**100%**) |
| `products` ngoài `events.product_id` | 94 ID chỉ xuất hiện trong `cart_products` |

So sánh với repo tham khảo (19,558 ID): lệch 47 ID (0.24%) do chưa gom `cart_products` của
`view_shopping_cart`/`checkout` và `recommendation_product_id`.

---

## 7. Đề xuất cho tầng transform (Project 07 — dbt)

| # | Việc | Áp dụng |
|---|---|---|
| 1 | `NULLIF(col, '')` cho mọi cột chuỗi | `user_id_db`, `email_address`, `referrer_url`, `collect_id`, `order_id` |
| 2 | Ép kiểu | `time_stamp` → TIMESTAMP; `store_id`, `product_id`, `user_id_db` → INT64; `latitude/longitude` → FLOAT64 |
| 3 | Chuẩn hóa `option` về array | `IF(JSON_TYPE(option)='object', [option], option)` |
| 4 | `UNNEST(cart_products)` → 1 dòng / sản phẩm / đơn | fact bán hàng từ `checkout_success` |
| 5 | Dedup đơn trùng | `checkout_success` theo `order_id` (+ `store_id`) |
| 6 | Sửa `category = 'Home'`, map category về nhóm cha | `products` |
| 7 | Không cộng tiền khác loại | doanh thu luôn đi kèm `currency` |
| 8 | Bỏ cột vô dụng | `api_version`, `sku`, `description` |
| 9 | Unknown member thay vì bỏ dòng | IP không định vị được, sản phẩm 404 |
| 10 | Bảo vệ PII | `email_address`, `ip`, `user_id_db`, `device_id` |
