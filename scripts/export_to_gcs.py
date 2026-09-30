"""Project 06 — Export MongoDB -> GCS (JSONL.gz, chunk) để Cloud Function load vào BigQuery.

Chạy TRÊN VM (cạnh MongoDB, nhanh hơn nhiều so với kéo về local):
    uv run python scripts/export_to_gcs.py --source events       --bucket <BUCKET>
    uv run python scripts/export_to_gcs.py --source ip_locations --bucket <BUCKET>
    uv run python scripts/export_to_gcs.py --source products     --bucket <BUCKET>

File đích: gs://<BUCKET>/staging/<source>/incoming/<run_id>/part-00000.jsonl.gz
-> Cloud Function thấy file mới -> load vào raw.<source>.

- Raw layer: events giữ vài cột chính dạng STRING + `payload` = nguyên document (JSON string).
  Lý do: `option` lúc là object lúc là array, kiểu dữ liệu không nhất quán -> ép schema cứng là
  load fail. Ép kiểu để ở dbt staging (schema-on-read).
- ip_locations / products: chỉ xuất đúng các cột trong schemas/<source>.json. Field thừa trong Mongo
  (vd. products._loaded_at) sẽ bị bỏ, vì Cloud Function load với ignore_unknown_values=False.
- Resume: manifest lưu last _id của mỗi chunk đã upload. Chết giữa chừng -> chạy lại cùng --run-id.
  Upload dùng if_generation_match=0: file đã có trên GCS thì không ghi đè (tránh Cloud Function load trùng).
"""
from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime, timezone
from time import perf_counter

from bson import json_util
from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage

from common import EVENTS_COLLECTION, OUTPUT_DIR, db, log, now_iso, schema_fields, to_str

EVENT_FIELDS = [
    "collection", "time_stamp", "local_time", "ip", "user_agent", "resolution",
    "user_id_db", "device_id", "api_version", "store_id", "current_url", "referrer_url",
    "email_address", "product_id", "viewing_product_id", "order_id", "cat_id", "collect_id",
]
SOURCES = {  # source -> mongo collection
    "events": None,  # dùng EVENTS_COLLECTION
    "ip_locations": "ip_locations",
    "products": "products",
}


def transform(source: str, doc: dict, run_id: str, exported_at: str, fields: list[str]) -> dict:
    if source == "events":
        row = {"event_id": str(doc["_id"])}
        row.update({f: to_str(doc.get(f)) for f in EVENT_FIELDS})
        row["payload"] = json.dumps(doc, default=str, ensure_ascii=False)
    else:
        row = {k: to_str(doc.get(k)) for k in fields}
    row["_run_id"] = run_id
    row["_exported_at"] = exported_at
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES, required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    ap.add_argument("--chunk-size", type=int, default=250_000)
    ap.add_argument("--max-chunks", type=int, default=None, help="test: --max-chunks 1")
    args = ap.parse_args()

    col = db()[SOURCES[args.source] or EVENTS_COLLECTION]
    bucket = storage.Client().bucket(args.bucket)
    prefix = f"staging/{args.source}/incoming/{args.run_id}"
    fields = [f for f in schema_fields(args.source) if not f.startswith("_")]

    manifest_path = OUTPUT_DIR / f"export_{args.source}_{args.run_id}.json"
    manifest = (json.loads(manifest_path.read_text()) if manifest_path.exists()
                else {"run_id": args.run_id, "source": args.source, "chunks": []})
    chunk_no = len(manifest["chunks"])
    # last_id lưu bằng json_util để giữ đúng kiểu (ObjectId) khi resume
    last_id = json_util.loads(manifest["chunks"][-1]["last_id"]) if manifest["chunks"] else None
    rows_done = sum(c["rows"] for c in manifest["chunks"])
    if chunk_no:
        log.info("Resume từ chunk %s (%s rows đã xong)", chunk_no, f"{rows_done:,}")

    source_count = col.estimated_document_count()
    log.info("Export %s: %s docs -> gs://%s/%s/", args.source, f"{source_count:,}", args.bucket, prefix)

    t0 = perf_counter()
    exported_at = now_iso()
    work = OUTPUT_DIR / "export_tmp"
    work.mkdir(exist_ok=True)

    while args.max_chunks is None or len(manifest["chunks"]) < args.max_chunks:
        query = {"_id": {"$gt": last_id}} if last_id is not None else {}
        cursor = col.find(query).sort("_id", 1).limit(args.chunk_size).batch_size(10_000)

        local = work / f"part-{chunk_no:05d}.jsonl.gz"
        n = 0
        with gzip.open(local, "wt", encoding="utf-8", compresslevel=5) as f:
            for doc in cursor:
                f.write(json.dumps(transform(args.source, doc, args.run_id, exported_at, fields),
                                   ensure_ascii=False))
                f.write("\n")
                last_id = doc["_id"]
                n += 1
        if n == 0:
            local.unlink(missing_ok=True)
            break

        blob = bucket.blob(f"{prefix}/{local.name}")
        try:
            blob.upload_from_filename(str(local), content_type="application/gzip", timeout=600,
                                      if_generation_match=0)
        except PreconditionFailed:
            # đã upload ở lần chạy trước nhưng chết trước khi ghi manifest -> giữ file cũ
            log.warning("%s đã tồn tại trên GCS, bỏ qua upload", blob.name)
        local.unlink()

        rows_done += n
        manifest["chunks"].append({"file": blob.name, "rows": n, "last_id": json_util.dumps(last_id)})
        manifest_path.write_text(json.dumps(manifest, indent=2))
        chunk_no += 1
        rate = rows_done / (perf_counter() - t0)
        log.info("chunk %05d | %s rows | tổng %s/%s | %.0f rows/s",
                 chunk_no - 1, f"{n:,}", f"{rows_done:,}", f"{source_count:,}", rate)

    manifest["total_rows"] = rows_done
    manifest_path.write_text(json.dumps(manifest, indent=2))
    exact = col.count_documents({})
    print("\n===== EXPORT SUMMARY =====")
    print(f"Source             : {args.source}")
    print(f"Mongo count        : {exact:,}")
    print(f"Exported rows      : {rows_done:,}   {'MATCH' if rows_done == exact else 'CHƯA KHỚP'}")
    print(f"Files              : {len(manifest['chunks'])} -> gs://{args.bucket}/{prefix}/")
    print(f"Manifest           : {manifest_path}")


if __name__ == "__main__":
    main()
