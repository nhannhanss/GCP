"""
Project 06 - Step 1: Export MongoDB collections -> GCS (JSONL.gz, chia part)

Usage (trên VM):
    uv run python export_to_gcs.py summary ip_locations products

- Đọc theo _id range (không dùng skip) -> RAM thấp, resume được khi bị ngắt
- Mỗi part = PART_SIZE docs -> ghi /tmp -> upload GCS -> xoá file local
- Trạng thái lưu ở export_state.json -> chạy lại lệnh sẽ tiếp tục từ chỗ dừng
"""
import gzip
import json
import logging
import os
import re
import sys
import time
from datetime import datetime

from bson import Decimal128, ObjectId, json_util
from google.cloud import storage
from pymongo import MongoClient

# ---------- Config (override bằng biến môi trường) ----------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "glamira")
GCS_BUCKET = os.getenv("GCS_BUCKET", "glamira-raw-data-asia")  # sửa tên bucket của bạn
GCS_PREFIX = os.getenv("GCS_PREFIX", "raw")
PART_SIZE = int(os.getenv("PART_SIZE", "1000000"))  # 1M docs/part ~ 100-200MB gz
TMP_DIR = os.getenv("TMP_DIR", "/tmp/glamira_export")
STATE_FILE = "export_state.json"

os.makedirs(TMP_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("export_to_gcs.log"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("export")

_INVALID_KEY = re.compile(r"[^A-Za-z0-9_]")


def clean_key(k: str) -> str:
    """BigQuery column name: chỉ chữ/số/_, không bắt đầu bằng số."""
    k = _INVALID_KEY.sub("_", str(k))
    return f"_{k}" if k and k[0].isdigit() else k


def to_json_safe(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, Decimal128):
        return str(v.to_decimal())
    if isinstance(v, dict):
        return {clean_key(k): to_json_safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [to_json_safe(x) for x in v]
    return v


# ---------- State (resume) ----------
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json_util.loads(f.read())
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        f.write(json_util.dumps(state, indent=2))


def upload_with_retry(bucket, local_path: str, blob_name: str, retries: int = 3):
    for attempt in range(1, retries + 1):
        try:
            bucket.blob(blob_name).upload_from_filename(local_path, timeout=900)
            return
        except Exception as e:
            log.warning(f"Upload lỗi (lần {attempt}/{retries}) {blob_name}: {e}")
            if attempt == retries:
                raise
            time.sleep(10 * attempt)


# ---------- Export 1 collection ----------
def export_collection(db, bucket, coll_name: str, state: dict):
    coll = db[coll_name]
    total = coll.estimated_document_count()
    st = state.setdefault(coll_name, {"last_id": None, "part": 0, "exported": 0, "done": False})

    if st["done"]:
        log.info(f"[{coll_name}] đã export xong trước đó ({st['exported']:,} docs) -> bỏ qua")
        return

    log.info(f"[{coll_name}] bắt đầu | tổng ~{total:,} docs | resume từ part {st['part']}")
    t0 = time.time()

    while True:
        query = {"_id": {"$gt": st["last_id"]}} if st["last_id"] is not None else {}
        cursor = coll.find(query).sort("_id", 1).limit(PART_SIZE).batch_size(10_000)

        fname = f"{coll_name}-part-{st['part']:05d}.jsonl.gz"
        local_path = os.path.join(TMP_DIR, fname)
        n, last_id = 0, None

        with gzip.open(local_path, "wt", encoding="utf-8") as f:
            for doc in cursor:
                f.write(json.dumps(to_json_safe(doc), ensure_ascii=False) + "\n")
                last_id = doc["_id"]
                n += 1

        if n == 0:
            os.remove(local_path)
            break

        blob_name = f"{GCS_PREFIX}/{coll_name}/{fname}"
        upload_with_retry(bucket, local_path, blob_name)
        size_mb = os.path.getsize(local_path) / 1024 / 1024
        os.remove(local_path)

        st["last_id"] = last_id
        st["part"] += 1
        st["exported"] += n
        save_state(state)

        pct = st["exported"] / total * 100 if total else 100
        log.info(
            f"[{coll_name}] part {st['part'] - 1:05d}: {n:,} docs, {size_mb:.1f}MB "
            f"-> gs://{GCS_BUCKET}/{blob_name} | {st['exported']:,}/{total:,} ({pct:.1f}%)"
        )

        if n < PART_SIZE:
            break

    # Validation: số docs export phải khớp count trong MongoDB
    actual = coll.count_documents({})
    st["done"] = True
    save_state(state)
    status = "OK" if actual == st["exported"] else "MISMATCH"
    log.info(
        f"[{coll_name}] XONG trong {(time.time() - t0) / 60:.1f} phút | "
        f"exported={st['exported']:,} | mongo={actual:,} | {status}"
    )


def main():
    collections = sys.argv[1:] or ["summary", "ip_locations", "products"]
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    bucket = storage.Client().bucket(GCS_BUCKET)
    state = load_state()

    for name in collections:
        if name not in db.list_collection_names():
            log.error(f"Collection '{name}' không tồn tại trong DB '{MONGO_DB}' -> bỏ qua")
            continue
        try:
            export_collection(db, bucket, name, state)
        except Exception:
            log.exception(f"[{name}] lỗi - chạy lại lệnh để resume")
            raise

    client.close()


if __name__ == "__main__":
    main()