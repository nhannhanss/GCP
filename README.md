# Glamira Pipeline — Project 05

Pipeline thu thập và làm giàu dữ liệu hành vi người dùng của Glamira (trang trang sức), phục vụ dashboard **Geographic Performance** và **Product Analysis**.

- **Operational DB:** MongoDB trên GCP Compute Engine VM
- **Enrichment:** IP → vị trí địa lý (IP2Location LITE), product_id → thông tin sản phẩm (crawl website Glamira)

## Kết quả

| Collection | Documents | Ghi chú |
|---|---|---|
| `summary` | 41.432.473 | Raw events, row count khớp file nguồn |
| `ip_locations` | 3.239.628 IP unique | Coverage ~100% <!-- TODO: điền con số chính xác --> |
| `products` | 19.511 product_id unique | 18.511 crawl thành công (95,4%), 900 trả 404 (sản phẩm đã gỡ) |

Chi tiết schema và các vấn đề data quality: [`data_dictionary.md`](data_dictionary.md)

## Cấu trúc thư mục

```
glamira-pipeline/
├── scripts/
│   ├── common.py                    # Hàm dùng chung (kết nối MongoDB, logging...)
│   ├── enrich_ip_locations.py       # IP -> country/region/city
│   ├── extract_product_ids.py       # Lấy (product_id, url) unique từ summary
│   ├── crawl_products.py            # Crawl thông tin sản phẩm
│   ├── load_products_to_mongodb.py  # Upsert products_raw.csv -> collection products
│   ├── profile_collections.py       # Profile schema -> output/schema_profile.md
│   └── export_to_gcs.py             # (Project 06) MongoDB -> GCS
├── functions/gcs_to_bigquery/       # (Project 06) Cloud Function trigger
├── schemas/                         # Schema BigQuery
├── output/                          # File sinh ra (không commit)
├── data_quality_report.md
├── scope_confirmation.md
├── data_dictionary.md
└── pyproject.toml
```

## Setup

**Yêu cầu:** Python 3.10+, [uv](https://docs.astral.sh/uv/), MongoDB VM đang chạy và firewall mở port 27017 cho IP máy local.

```powershell
git clone https://github.com/nhannhanss/glamira-pipeline.git
cd glamira-pipeline
uv sync
```

Tạo file `.env` ở thư mục gốc (xem `.env.example`):

```env
MONGO_URI=mongodb://<user>:<password>@<VM_EXTERNAL_IP>:27017/?authSource=admin
MONGO_DB=glamira_db
```

Tải IP2Location LITE DB5 (file `.BIN`) từ [lite.ip2location.com](https://lite.ip2location.com) <!-- TODO: ghi đường dẫn đặt file / tên biến trong .env nếu có -->.

## Thứ tự chạy

| # | Lệnh | Output |
|---|---|---|
| 1 | Load raw data vào `summary` <!-- TODO: lệnh/script đã dùng --> | Collection `summary` |
| 2 | `uv run python scripts/enrich_ip_locations.py` | Collection `ip_locations` + CSV backup |
| 3 | `uv run python scripts/extract_product_ids.py` | `output/product_ids.csv` |
| 4 | `uv run python scripts/crawl_products.py --workers 8` | `output/products_raw.csv` |
| 5 | `uv run python scripts/load_products_to_mongodb.py` | Collection `products` |
| 6 | `uv run python scripts/profile_collections.py` | `output/schema_profile.md` |

Crawler có rate limit, retry và resume từ điểm dừng: chạy lại lệnh 4 sẽ bỏ qua các product đã crawl.

## Lưu ý

- **Stop VM** trên GCP Console sau khi chạy xong để tránh tốn credit.
- Không commit `.env`, credentials JSON, file `.BIN` và thư mục `output/`.
