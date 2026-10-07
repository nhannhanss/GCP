# glamira_dbt – Project 07: Data Transformation & Dashboard

Biến tầng raw trên BigQuery (Project 06) thành **star schema** bằng dbt, rồi dựng dashboard bán hàng trên Data Studio (Looker Studio).

```
raw (Project 06)  ──►  staging (view)  ──►  core (table: fact + 6 dim)  ──►  mart (table)  ──►  Data Studio
events                  stg_checkout_orders     fact_sales_order_detail          mart_sales
ip_locations            stg_order_lines         dim_date / dim_store / dim_geo
products                stg_products            dim_product / dim_device
                        stg_ip_locations        dim_customer
seeds: store_currency, exchange_rates
```

- **Dashboard:** [https://datastudio.google.com/reporting/6331ba7a-07ed-4c65-affd-636b5199ec7d]
- **ERD:** `docs/glamira_erd.png` (file draw.io: `docs/glamira_erd.drawio`)

## 1. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Đơn hàng thành công (sau khử trùng, bỏ đơn test) | 25.962 |
| Dòng sản phẩm (grain của fact) | 34.916 |
| Khách hàng | 24.017 |
| Doanh thu (quy đổi USD, tỷ giá TB 2020) | ≈ 20,8 triệu USD |
| Data tests | tất cả PASS, 2 WARN (1 dòng giá không parse được) |

## 2. Data model

**Grain:** 1 dòng `fact_sales_order_detail` = 1 sản phẩm trong giỏ của 1 đơn `checkout_success`, khóa `(order_id, line_number)`.

| Bảng | Trả lời | Natural key | Ghi chú |
|---|---|---|---|
| `fact_sales_order_detail` | Bao nhiêu? | `order_id` + `line_number` | `order_qty`, `unit_price_local`, `line_amount_local`, `line_amount_usd`; partition theo tháng `order_time`, cluster `store_key, product_key` |
| `dim_date` | When | `full_date` | `date_key` = YYYYMMDD |
| `dim_customer` | Who | `customer_id_hash` | Registered = `user_id_db`, Guest = `device_id`, chỉ lưu hash |
| `dim_product` | What | `product_id` | `category_group_name` gộp ~30 category thành 7 nhóm |
| `dim_geo` | Where | country + region + city | Mức thành phố, không lưu IP |
| `dim_store` | Where / How | `store_id` | 1 domain có thể có nhiều store_id (bản ngôn ngữ) |
| `dim_device` | How | device_type + resolution + is_bot | Tách từ `user_agent` |

- Surrogate key: `FARM_FINGERPRINT(natural_key)` (INT64). Dim và fact dùng **chung macro** sinh natural key nên key luôn khớp.
- Mỗi dim có dòng **Unknown** (`key = -1`, `is_unknown = TRUE`) → fact không bao giờ mất dòng khi join.

## 3. Quy tắc làm sạch (staging)

| Vấn đề trong raw | Xử lý |
|---|---|
| Mọi cột là STRING; `cart_products` nằm trong JSON `payload` | Ép kiểu; `UNNEST(JSON_QUERY_ARRAY(payload, '$.cart_products'))` |
| Giá 2 định dạng: `1.234,56` (EU) và `1,234.56` (US) | Macro `parse_price`: dấu phẩy + 1–2 chữ số cuối = EU |
| Ký hiệu tiền mơ hồ (`$` = USD/ARS/HKD) hoặc rỗng | Lấy tiền tệ theo **domain** (seed `store_currency`) |
| Đơn test từ `stage.*`, `dev*.glamira.de`, `glamira.local` | Loại theo domain |
| 48 `order_id` bị ghi 2 lần | Giữ event sớm nhất |
| Category "Home / Startseite / Acasă / Hem" (crawler lấy nhầm breadcrumb) | Nhóm `Unknown` |
| `order_id` có đuôi `.0`, chuỗi rỗng thay NULL | `REGEXP_REPLACE`, macro `clean_string` |

## 4. PII

| Trường | Xử lý |
|---|---|
| `email_address` | `email_hash` (SHA-256 có salt) |
| `ip` | `ip_hash`; fact join `ip_locations` bằng hash, `dim_geo` chỉ có quốc gia/thành phố |
| `user_id_db`, `device_id` | Gộp thành `customer_id_hash` + cờ `is_registered` |

Từ `staging` trở đi không còn cột PII gốc (đã kiểm tra bằng `INFORMATION_SCHEMA.COLUMNS`). Salt đặt bằng biến môi trường `DBT_PII_SALT` (có giá trị mặc định).

## 5. Data tests

- `unique` + `not_null` cho mọi khóa chính, `unique_combination_of_columns(order_id, line_number)`.
- `relationships` cho 6 khóa ngoại của fact.
- `accepted_values` cho `category_group_name`, `device_type`, `customer_type`, `geo_level`.
- `accepted_range`: `order_qty >= 1`, giá và doanh thu `>= 0`.
- Singular tests: mọi domain có tiền tệ; fact giữ đủ số dòng của staging; tổng doanh thu mart = fact.

## 6. Tối ưu

- `staging` là **view** (không tốn lưu trữ), `core` và `mart` là **table**.
- Fact partition theo tháng `order_time` + cluster `store_key, product_key`; mart partition theo tháng `order_date` + cluster `country_name, category_group_name` → dashboard lọc theo ngày/quốc gia chỉ quét phần cần thiết.
- `mart_sales` join sẵn mọi dim → Data Studio không phải blend, mỗi biểu đồ là 1 query trên 1 bảng.

## 7. Cách chạy

```powershell
uv sync
gcloud auth application-default login
cd glamira_dbt
uv run dbt deps
uv run dbt seed
uv run dbt build          # chạy model + test
uv run dbt docs generate
uv run dbt docs serve     # xem tài liệu và lineage graph
```

`profiles.yml` dùng `method: oauth` (organization chặn tạo key cho service account).

## 8. Hạn chế đã biết

- `exchange_rates.csv` là tỷ giá trung bình năm 2020, **xấp xỉ** – dùng để so sánh, không dùng cho kế toán.
- Khoảng 19% dòng đơn hàng không có thông tin sản phẩm (crawl lỗi/không crawl) và ~25% sản phẩm crawl có category "Home" → nhóm `Unknown`.
- Ngày tính theo **UTC** (`time_stamp`), không theo giờ địa phương của từng store.
- Khách vãng lai định danh bằng `device_id` → 1 người dùng nhiều thiết bị bị tính nhiều khách.

## 9. Khắc phục sự cố GCP đã gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `iam.disableServiceAccountKeyCreation` | Organization tự bật "Secure by Default" | Dùng OAuth (`gcloud auth application-default login`) |
| `IAM setPolicy failed ... not belong to a permitted customer` khi tạo dataset | Policy `iam.allowedPolicyMemberDomains` chặn tài khoản Gmail | Ghi đè policy ở cấp project bằng `gcloud org-policies set-policy` với `allowAll: true` |
