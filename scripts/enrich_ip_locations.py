"""Checkpoint #8 — IP geolocation bằng IP2Location LITE DB5.

Chỉ lookup trên UNIQUE IP (group trong MongoDB), không lookup từng event.
Tải file BIN (miễn phí, cần đăng ký): https://lite.ip2location.com
  -> IP2LOCATION-LITE-DB5.IPV6.BIN  (bản IPV6 chứa cả IPv4)

Chạy trên VM:
    export IP2LOCATION_BIN=data/IP2LOCATION-LITE-DB5.IPV6.BIN
    uv run python scripts/enrich_ip_locations.py

Output: collection `ip_locations` + output/ip_locations.csv
"""
from __future__ import annotations

import csv
import os
from ipaddress import ip_address
from time import perf_counter

import IP2Location

from common import OUTPUT_DIR, db, events, log

BIN_PATH = os.getenv("IP2LOCATION_BIN", "data/IP2LOCATION-LITE-DB5.IPV6.BIN")
BATCH = 10_000
FIELDS = ["ip", "country_code", "country_name", "region_name", "city_name",
          "latitude", "longitude", "event_count", "geo_status"]

EMPTY = {"", "-", None}


def lookup(reader: IP2Location.IP2Location, raw_ip: str) -> dict:
    row = {"ip": raw_ip, "country_code": None, "country_name": None, "region_name": None,
           "city_name": None, "latitude": None, "longitude": None}
    try:
        parsed = ip_address(raw_ip.strip())
    except ValueError:
        return {**row, "geo_status": "INVALID"}
    if not parsed.is_global:
        return {**row, "geo_status": "NON_GLOBAL"}  # private / loopback / reserved

    rec = reader.get_all(str(parsed))
    if rec is None or rec.country_short in EMPTY or "INVALID" in str(rec.country_short):
        return {**row, "geo_status": "NOT_FOUND"}

    return {
        **row,
        "country_code": rec.country_short,
        "country_name": rec.country_long,
        "region_name": None if rec.region in EMPTY else rec.region,
        "city_name": None if rec.city in EMPTY else rec.city,
        "latitude": float(rec.latitude) if rec.latitude not in EMPTY else None,
        "longitude": float(rec.longitude) if rec.longitude not in EMPTY else None,
        "geo_status": "FOUND",
    }


def main() -> None:
    t0 = perf_counter()
    reader = IP2Location.IP2Location(BIN_PATH, "SHARED_MEMORY")
    target = db()["ip_locations"]
    target.drop()  # idempotent: chạy lại không bị trùng

    total_events = events().estimated_document_count()
    pipeline = [
        {"$match": {"ip": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$ip", "n": {"$sum": 1}}},
    ]

    csv_path = OUTPUT_DIR / "ip_locations.csv"
    status_ips: dict[str, int] = {}
    status_events: dict[str, int] = {}
    batch: list[dict] = []
    n_ips = 0

    log.info("Grouping unique IPs (có thể mất vài phút) ...")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for g in events().aggregate(pipeline, allowDiskUse=True, batchSize=BATCH):
            doc = lookup(reader, str(g["_id"]))
            doc["event_count"] = g["n"]
            s = doc["geo_status"]
            status_ips[s] = status_ips.get(s, 0) + 1
            status_events[s] = status_events.get(s, 0) + g["n"]

            writer.writerow(doc)
            batch.append(doc)
            n_ips += 1
            if len(batch) >= BATCH:
                target.insert_many(batch, ordered=False)
                batch.clear()
                log.info("  %s IPs processed", f"{n_ips:,}")

        if batch:
            target.insert_many(batch, ordered=False)

    target.create_index("ip", unique=True)
    target.create_index("country_code")

    events_with_ip = sum(status_events.values())
    found_ev = status_events.get("FOUND", 0)
    print("\n===== CHECKPOINT #8 =====")
    print(f"Unique IPs              : {n_ips:,}")
    for s, c in sorted(status_ips.items(), key=lambda kv: -kv[1]):
        print(f"  {s:<12}: {c:>10,} IPs | {status_events[s]:>12,} events")
    print(f"Events có IP            : {events_with_ip:,} / {total_events:,}")
    print(f"Coverage (theo IP)      : {status_ips.get('FOUND', 0) / max(n_ips, 1):.2%}")
    print(f"Coverage (theo event)   : {found_ev / max(total_events, 1):.2%}   <- cần >= 80%")
    print(f"db.ip_locations.count   : {target.count_documents({}):,}")
    print(f"CSV backup              : {csv_path}")
    print(f"Thời gian               : {perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
