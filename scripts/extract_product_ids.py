"""Checkpoint #9 — Lấy set unique product_id (+ 1 URL mẫu) và danh sách storefront host.

Group ngay trong MongoDB (aggregation) thay vì kéo 41M docs về Python.
Chạy trên VM cho nhanh:  uv run python scripts/extract_product_ids.py

Output:
    output/product_ids.csv        product_id, url, event_count
    output/storefront_hosts.txt   host glamira, sắp theo tần suất (dùng cho crawl)
"""
from __future__ import annotations

import csv
from collections import Counter
from time import perf_counter
from urllib.parse import urlparse

from common import OUTPUT_DIR, events, log

PID_COLLECTIONS = [
    "view_product_detail",
    "select_product_option",
    "select_product_option_quality",
    "add_to_cart_action",
    "product_detail_recommendation_visible",
    "product_detail_recommendation_noticed",
    "back_to_product_action",
    "view_all_recommend",
    "product_view_all_recommend_clicked",  # product_id = null -> dùng viewing_product_id
]


def as_string(expr):
    return {"$convert": {"input": expr, "to": "string", "onError": None, "onNull": None}}


PIPELINE_EVENTS = [
    {"$match": {"collection": {"$in": PID_COLLECTIONS}}},
    {"$project": {
        "pid": as_string({"$ifNull": ["$product_id", "$viewing_product_id"]}),
        "url": {"$cond": [
            {"$eq": ["$collection", "product_view_all_recommend_clicked"]},
            "$referrer_url",
            "$current_url",
        ]},
    }},
    {"$match": {"pid": {"$nin": [None, ""]}}},
    {"$group": {"_id": "$pid", "url": {"$max": "$url"}, "n": {"$sum": 1}}},
]

# Sản phẩm chỉ xuất hiện trong giỏ hàng lúc checkout (không có URL sản phẩm)
PIPELINE_CART = [
    {"$match": {"collection": "checkout_success"}},
    {"$unwind": "$cart_products"},
    {"$project": {"pid": as_string("$cart_products.product_id")}},
    {"$match": {"pid": {"$nin": [None, ""]}}},
    {"$group": {"_id": "$pid", "n": {"$sum": 1}}},
]


def main() -> None:
    col = events()
    products: dict[str, dict] = {}
    t0 = perf_counter()

    log.info("Aggregating product events ...")
    for row in col.aggregate(PIPELINE_EVENTS, allowDiskUse=True, batchSize=10_000):
        pid = row["_id"].strip()
        if pid:
            products[pid] = {"url": row.get("url"), "n": row["n"]}
    from_events = len(products)
    log.info("  %s unique product_id từ event sản phẩm", f"{from_events:,}")

    log.info("Aggregating checkout_success.cart_products ...")
    cart_only = 0
    for row in col.aggregate(PIPELINE_CART, allowDiskUse=True, batchSize=10_000):
        pid = row["_id"].strip()
        if not pid:
            continue
        if pid in products:
            products[pid]["n"] += row["n"]
        else:
            products[pid] = {"url": None, "n": row["n"]}
            cart_only += 1
    log.info("  +%s product_id chỉ có trong cart", f"{cart_only:,}")

    hosts = Counter()
    for info in products.values():
        url = info["url"]
        if url:
            host = urlparse(url).hostname or ""
            if "glamira" in host:
                hosts[host] += 1

    ids_file = OUTPUT_DIR / "product_ids.csv"
    with ids_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "url", "event_count"])
        for pid, info in sorted(products.items(), key=lambda kv: -kv[1]["n"]):
            w.writerow([pid, info["url"] or "", info["n"]])

    hosts_file = OUTPUT_DIR / "storefront_hosts.txt"
    hosts_file.write_text("\n".join(h for h, _ in hosts.most_common()), encoding="utf-8")

    print("\n===== CHECKPOINT #9 =====")
    print(f"Unique product_id : {len(products):,}")
    print(f"  có URL          : {sum(1 for p in products.values() if p['url']):,}")
    print(f"  chỉ trong cart  : {cart_only:,}")
    print(f"Storefront hosts  : {len(hosts):,}  (top 5: {[h for h, _ in hosts.most_common(5)]})")
    print(f"Output            : {ids_file}, {hosts_file}")
    print(f"Thời gian         : {perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
