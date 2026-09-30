"""
Profile schema của các collection MongoDB -> output/schema_profile.md
Dùng làm nguyên liệu để viết data_dictionary.md.

Chạy: uv run python scripts/profile_collections.py [sample_size]
      (mặc định sample 20.000 document / collection)
"""
import os
import sys
from collections import defaultdict
from datetime import datetime

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
db = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=10000)[
    os.getenv("MONGO_DB", "glamira_db")
]
SAMPLE = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
COLLECTIONS = ["summary", "ip_locations", "products"]
EVENT_FIELD = "collection"  # field chứa event type trong summary
OUT = "output/schema_profile.md"


def type_name(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "BOOLEAN"
    if isinstance(v, int):
        return "INTEGER"
    if isinstance(v, float):
        return "FLOAT"
    if isinstance(v, str):
        return "STRING"
    if isinstance(v, datetime):
        return "TIMESTAMP"
    if isinstance(v, ObjectId):
        return "OBJECTID"
    if isinstance(v, list):
        return "ARRAY"
    if isinstance(v, dict):
        return "OBJECT"
    return type(v).__name__.upper()


def is_empty(v):
    return v is None or (isinstance(v, str) and v.strip() in ("", "-"))


def new_stat():
    return {"present": 0, "empty": 0, "types": defaultdict(int), "example": None, "events": set()}


def walk(doc, prefix, stats, event):
    for k, v in doc.items():
        key = f"{prefix}{k}"
        s = stats[key]
        s["present"] += 1
        s["types"][type_name(v)] += 1
        if event is not None:
            s["events"].add(event)
        if is_empty(v):
            s["empty"] += 1
        elif s["example"] is None and not isinstance(v, (dict, list)):
            s["example"] = str(v)[:40].replace("|", "\\|").replace("\n", " ")
        if isinstance(v, dict):
            walk(v, key + ".", stats, event)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            walk(v[0], key + "[].", stats, event)


def profile(name):
    coll = db[name]
    total = coll.estimated_document_count()
    stats = defaultdict(new_stat)
    all_events, n = set(), 0
    for doc in coll.aggregate([{"$sample": {"size": SAMPLE}}], allowDiskUse=True):
        n += 1
        event = doc.get(EVENT_FIELD) if name == "summary" else None
        if event is not None:
            all_events.add(event)
        walk(doc, "", stats, event)
    print(f"{name}: sampled {n:,} / {total:,}")
    return total, n, stats, all_events


def events_label(events, all_events):
    if not all_events:
        return ""
    if events == all_events:
        return "tất cả"
    ev = sorted(events)
    return ", ".join(ev[:4]) + (f" (+{len(ev) - 4})" if len(ev) > 4 else "")


def main():
    lines = [f"# Schema Profile (sample {SAMPLE:,} docs / collection)\n",
             f"_Generated: {datetime.now():%Y-%m-%d %H:%M}_\n"]
    for name in COLLECTIONS:
        total, n, stats, all_events = profile(name)
        show_ev = name == "summary"
        lines.append(f"\n## {name}\n")
        lines.append(f"- Tổng documents: **{total:,}** | Sampled: {n:,}")
        if show_ev:
            lines.append(f"- Số event types trong sample: {len(all_events)}")
        lines.append("")
        header = "| Field | Type(s) | % có field | % null/rỗng | Example |"
        sep = "|---|---|---|---|---|"
        if show_ev:
            header += " Event types |"
            sep += "---|"
        lines += [header, sep]
        for key in sorted(stats, key=lambda k: (-stats[k]["present"], k)):
            s = stats[key]
            types = ", ".join(t for t, _ in sorted(s["types"].items(), key=lambda x: -x[1]))
            row = (f"| `{key}` | {types} | {s['present'] / n * 100:.1f}% | "
                   f"{s['empty'] / s['present'] * 100:.1f}% | {s['example'] or ''} |")
            if show_ev:
                row += f" {events_label(s['events'], all_events)} |"
            lines.append(row)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nĐã ghi: {OUT}")


if __name__ == "__main__":
    main()