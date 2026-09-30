"""Checkpoint #10 / #11 — Crawl thông tin sản phẩm từ glamira.

CHẠY TRÊN MÁY LOCAL (Windows), KHÔNG chạy trên VM GCP: IP datacenter bị glamira trả 403.

    uv run python scripts/crawl_products.py --limit 100          # Checkpoint #10
    uv run python scripts/crawl_products.py                      # Checkpoint #11 (full)
    uv run python scripts/load_products_to_mongodb.py            # nạp kết quả vào MongoDB

- curl_cffi giả lập TLS fingerprint của browser thật (requests thường dễ bị chặn)
- URL: https://<host>/catalog/product/view/id/<product_id>  (Magento), random host
- Parse JSON-LD schema.org/Product, fallback og:title / breadcrumb
- Resume: đọc lại CSV, bỏ qua id đã OK hoặc 404 -> chạy lại là tự retry id lỗi
- Circuit breaker: 403 liên tục -> nghỉ 60s
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from curl_cffi import requests as cf

from common import OUTPUT_DIR, log, now_iso

IDS_FILE = OUTPUT_DIR / "product_ids.csv"
HOSTS_FILE = OUTPUT_DIR / "storefront_hosts.txt"
RESULTS_FILE = OUTPUT_DIR / "products_raw.csv"

URL_TEMPLATE = "https://{host}/catalog/product/view/id/{pid}"
# Ưu tiên store tiếng Anh để product_name/category cùng 1 ngôn ngữ (dashboard so sánh được).
# Sản phẩm không có ở store tiếng Anh (404) -> fallback sang store khác.
ENGLISH_HOSTS = ["www.glamira.com", "www.glamira.co.uk", "www.glamira.com.au", "www.glamira.ca",
                 "www.glamira.ie", "www.glamira.co.nz", "www.glamira.in", "www.glamira.sg"]
BROWSERS = ["chrome136", "chrome133a", "chrome131", "chrome124", "firefox144",
            "firefox135", "safari184", "safari180", "edge101"]
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
FIELDS = ["product_id", "success", "http_status", "error", "product_name", "sku", "price",
          "currency", "category", "image_url", "description", "source_url", "host", "crawled_at"]


# ---------------------------------------------------------------- parsing
def _find_products(node):
    if isinstance(node, list):
        for x in node:
            yield from _find_products(x)
    elif isinstance(node, dict):
        t = node.get("@type")
        if t == "Product" or (isinstance(t, list) and "Product" in t):
            yield node
        if "@graph" in node:
            yield from _find_products(node["@graph"])


def parse_product(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = dict.fromkeys(["product_name", "sku", "price", "currency", "category",
                         "image_url", "description"])
    breadcrumb: list[str] = []
    is_product = False

    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            payload = json.loads(tag.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        for item in (payload if isinstance(payload, list) else [payload]):
            if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                breadcrumb = [
                    (e.get("name") or (e.get("item") or {}).get("name") or "")
                    for e in item.get("itemListElement", []) if isinstance(e, dict)
                ]
        for p in _find_products(payload):
            is_product = True
            out["product_name"] = out["product_name"] or p.get("name")
            out["sku"] = out["sku"] or p.get("sku")
            out["description"] = out["description"] or p.get("description")
            out["category"] = out["category"] or p.get("category")
            img = p.get("image")
            out["image_url"] = out["image_url"] or (img[0] if isinstance(img, list) and img else img)
            offers = p.get("offers")
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                out["price"] = out["price"] or offers.get("price") or offers.get("lowPrice")
                out["currency"] = out["currency"] or offers.get("priceCurrency")

    if not out["price"]:
        m = (soup.find("meta", property="product:price:amount") or soup.find("meta", itemprop="price")
             or soup.find(attrs={"itemprop": "price"}))
        if m:
            out["price"] = m.get("content") or m.get_text(strip=True) or None
    if not out["currency"]:
        m = soup.find("meta", property="product:price:currency") or soup.find("meta", itemprop="priceCurrency")
        if m:
            out["currency"] = m.get("content")
    og_type = soup.find("meta", property="og:type")
    is_product = is_product or (og_type is not None and "product" in (og_type.get("content") or ""))
    if not out["product_name"]:
        og = soup.find("meta", property="og:title")
        title = soup.find("title")
        out["product_name"] = (og.get("content") if og else None) or (title.text.strip() if title else None)
    if not out["image_url"]:
        og = soup.find("meta", property="og:image")
        out["image_url"] = og.get("content") if og else None
    if not out["category"] and len(breadcrumb) >= 2:
        out["category"] = breadcrumb[-2]  # [..., category, product]
    if isinstance(out["category"], list):
        out["category"] = " > ".join(map(str, out["category"]))
    if out["description"]:
        out["description"] = " ".join(str(out["description"]).split())[:1000]
    out["_is_product"] = is_product
    return out


# ---------------------------------------------------------------- crawling
class Guard:
    """Đếm 403 liên tiếp, nghỉ khi bị chặn."""

    def __init__(self, threshold: int = 15, pause: int = 60):
        self.lock = threading.Lock()
        self.streak = 0
        self.threshold, self.pause = threshold, pause
        self.status = Counter()

    def record(self, status):
        with self.lock:
            self.status[str(status)] += 1
            self.streak = self.streak + 1 if status == 403 else 0
            hit = self.streak >= self.threshold
            if hit:
                self.streak = 0
        if hit:
            log.warning("Bị 403 liên tục -> nghỉ %ss", self.pause)
            time.sleep(self.pause)


def fetch(pid: str, hosts: tuple[list[str], list[str]], args, guard: Guard) -> dict:
    row = dict.fromkeys(FIELDS)
    row.update(product_id=pid, success=False)
    primary, fallback = hosts
    pool = primary or fallback
    for attempt in range(args.retries + 2):
        host = random.choice(pool)
        url = URL_TEMPLATE.format(host=host, pid=pid)
        row.update(host=host, source_url=url, crawled_at=now_iso())
        time.sleep(random.uniform(args.min_delay, args.max_delay))
        try:
            r = cf.get(url, impersonate=random.choice(BROWSERS), headers=HEADERS,
                       timeout=20, allow_redirects=True)
            row["http_status"] = r.status_code
            guard.record(r.status_code)
            if r.status_code == 200:
                data = parse_product(r.text)
                is_product = data.pop("_is_product")
                row.update(data, source_url=str(r.url), error="")
                row["success"] = bool(is_product and data["product_name"])
                if not row["success"]:
                    # 200 nhưng không phải trang sản phẩm (redirect về home/category)
                    row["error"] = "not_product_page"
                return row
            if r.status_code == 404:
                row["error"] = "not_found"
                if pool is primary and fallback:
                    pool = fallback  # không có ở store tiếng Anh -> thử store khác
                    continue
                return row
            row["error"] = f"http_{r.status_code}"
        except Exception as exc:  # noqa: BLE001 - log mọi lỗi, không crash
            row["error"] = f"{type(exc).__name__}: {exc}"[:200]
        time.sleep(2 * (attempt + 1))
    return row


def load_done() -> set[str]:
    if not RESULTS_FILE.exists():
        return set()
    with RESULTS_FILE.open(encoding="utf-8") as f:
        return {r["product_id"] for r in csv.DictReader(f)
                if r["success"] == "True" or r["error"] == "not_found"}


def crawl(args) -> None:
    with IDS_FILE.open(encoding="utf-8") as f:
        all_ids = [r["product_id"] for r in csv.DictReader(f)]
    observed = [h for h in HOSTS_FILE.read_text(encoding="utf-8").split() if h] or ["www.glamira.com"]
    english = [h for h in ENGLISH_HOSTS if h in observed] or ["www.glamira.com"]
    others = [h for h in observed if h not in english][: args.top_hosts]
    hosts = (english, others)

    done = load_done()
    todo = [p for p in all_ids if p not in done]
    if args.limit:
        todo = todo[: args.limit]
    log.info("Total %s | done %s | crawl %s | hosts %s", len(all_ids), len(done), len(todo), hosts)

    new_file = not RESULTS_FILE.exists()
    lock = threading.Lock()
    guard = Guard()
    ok = fail = 0
    t0 = time.perf_counter()

    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(fetch, pid, hosts, args, guard) for pid in todo]
            for i, fut in enumerate(as_completed(futures), 1):
                row = fut.result()
                with lock:
                    writer.writerow(row)
                    f.flush()
                ok += row["success"]
                fail += not row["success"]
                if i % 100 == 0 or i == len(todo):
                    rate = i / (time.perf_counter() - t0)
                    log.info("%s/%s | ok %s | fail %s | %.1f req/s | %s",
                             i, len(todo), ok, fail, rate, dict(guard.status))

    print("\n===== CRAWL SUMMARY =====")
    print(f"Crawled lần này : {len(todo):,} | OK {ok:,} | fail {fail:,}")
    print(f"HTTP status     : {dict(guard.status)}")
    print(f"Tổng đã xong    : {len(load_done()):,} / {len(all_ids):,}")
    print(f"Kết quả thô     : {RESULTS_FILE}")


# ---------------------------------------------------------------- to MongoDB
def to_mongo() -> None:
    """1 bản ghi active duy nhất / product_id (lấy lần crawl OK mới nhất)."""
    from pymongo import UpdateOne

    latest: dict[str, dict] = {}
    with RESULTS_FILE.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["success"] == "True":
                prev = latest.get(r["product_id"])
                if prev is None or r["crawled_at"] > prev["crawled_at"]:
                    latest[r["product_id"]] = r

    keep = ["product_id", "product_name", "sku", "price", "currency", "category",
            "image_url", "description", "source_url", "host", "crawled_at"]
    docs = [{k: (r[k] or None) for k in keep} for r in latest.values()]

    with CLEAN_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keep)
        w.writeheader()
        w.writerows(docs)

    col = db()["products"]
    col.create_index("product_id", unique=True)
    for i in range(0, len(docs), 1000):
        col.bulk_write([UpdateOne({"product_id": d["product_id"]}, {"$set": d}, upsert=True)
                        for d in docs[i:i + 1000]], ordered=False)

    with IDS_FILE.open(encoding="utf-8") as f:
        n_ids = sum(1 for _ in csv.DictReader(f))
    with_cat = sum(1 for d in docs if d["category"])
    print("\n===== CHECKPOINT #11 =====")
    print(f"Unique product_ids (extract) : {n_ids:,}")
    print(f"products trong MongoDB       : {col.count_documents({}):,}")
    print(f"Coverage                     : {len(docs) / max(n_ids, 1):.2%}")
    print(f"Có category                  : {with_cat:,} ({with_cat / max(len(docs), 1):.1%})")
    print(f"CSV sạch                     : {CLEAN_FILE}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="100 để test")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--min-delay", type=float, default=1.5)
    ap.add_argument("--max-delay", type=float, default=4.2)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--top-hosts", type=int, default=10)
    ap.add_argument("--to-mongo", action="store_true", help="chỉ upsert CSV -> MongoDB")
    args = ap.parse_args()
    to_mongo() if args.to_mongo else crawl(args)


if __name__ == "__main__":
    main()