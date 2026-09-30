"""Cấu hình dùng chung. Đọc từ biến môi trường / file .env để chạy được cả local lẫn VM.

.env (xem .env.example):
    MONGO_URI=mongodb://user:pass@<VM_IP>:27017/?authSource=admin
    MONGO_DB=glamira_db
Tên cũ MONGODB_URI / MONGODB_DB vẫn được đọc nếu không có tên mới.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("MONGODB_DB", "glamira_db")
EVENTS_COLLECTION = os.getenv("EVENTS_COLLECTION", "summary")

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCHEMAS_DIR = ROOT / "schemas"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("glamira")


def db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10_000)
    return client[MONGO_DB]


def events():
    return db()[EVENTS_COLLECTION]


def schema_fields(table: str) -> list[str]:
    """Tên cột của raw.<table> theo schemas/<table>.json (nguồn sự thật duy nhất)."""
    return [f["name"] for f in json.loads((SCHEMAS_DIR / f"{table}.json").read_text())]


def to_str(value):
    """Ép mọi giá trị về STRING cho raw layer (schema-on-read, ép kiểu ở dbt)."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, ensure_ascii=False)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
