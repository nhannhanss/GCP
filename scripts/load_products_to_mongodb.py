"""
Load output/products_raw.csv vào MongoDB collection `products`.
- 1 product_id = 1 document (ưu tiên bản crawl có name)
- Upsert theo product_id -> chạy lại nhiều lần không bị duplicate
- Validate count sau khi load

Chạy: uv run python load_products_to_mongodb.py [đường_dẫn_csv]
"""
import os
import sys
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, ReplaceOne

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")          # sửa lại cho khớp tên biến trong .env của bạn
DB_NAME = os.getenv("MONGO_DB", "glamira_db")
COLLECTION = "products"
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "output/products_raw.csv"
BATCH_SIZE = 1000


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"product_id": str})
    print(f"CSV rows            : {len(df):,}")
    print(f"Unique product_id   : {df['product_id'].nunique():,}")

    # Nếu 1 product_id xuất hiện nhiều lần -> giữ bản có name
    name_col = next((c for c in ("product_name", "name") if c in df.columns), None)
    if name_col:
        df["_has_name"] = df[name_col].notna()
        df = df.sort_values("_has_name", ascending=False).drop(columns="_has_name")
    df = df.drop_duplicates(subset="product_id", keep="first")

    # NaN -> None để Mongo lưu null thay vì NaN
    df = df.astype(object).where(pd.notna(df), None)
    print(f"Rows sau dedupe     : {len(df):,}")
    return df


def main():
    if not MONGO_URI:
        sys.exit("Thiếu MONGO_URI trong .env")

    df = load_csv(CSV_PATH)

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    coll = client[DB_NAME][COLLECTION]
    coll.create_index([("product_id", ASCENDING)], unique=True)

    loaded_at = datetime.now(timezone.utc)
    records = df.to_dict("records")
    upserted = modified = 0

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        ops = [
            ReplaceOne(
                {"product_id": r["product_id"]},
                {**r, "_loaded_at": loaded_at, "_source_file": os.path.basename(CSV_PATH)},
                upsert=True,
            )
            for r in batch
        ]
        res = coll.bulk_write(ops, ordered=False)
        upserted += res.upserted_count
        modified += res.modified_count
        print(f"  {min(i + BATCH_SIZE, len(records)):,}/{len(records):,}")

    # ---- Validation ----
    total = coll.count_documents({})
    dups = list(coll.aggregate([
        {"$group": {"_id": "$product_id", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gt": 1}}},
        {"$count": "dup"},
    ]))
    print("\n===== LOAD SUMMARY =====")
    print(f"Upserted mới        : {upserted:,}")
    print(f"Cập nhật            : {modified:,}")
    print(f"countDocuments()    : {total:,}")
    print(f"Duplicate product_id: {dups[0]['dup'] if dups else 0}")
    print(f"Khớp CSV            : {'OK' if total == len(df) else 'KHÔNG KHỚP'}")
    client.close()


if __name__ == "__main__":
    main()