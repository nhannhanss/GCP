"""Cloud Function (gen2) — GCS object finalized -> BigQuery load job.

Route theo prefix:
    staging/events/incoming/...        -> raw.events
    staging/ip_locations/incoming/...  -> raw.ip_locations
    staging/products/incoming/...      -> raw.products

job_id deterministic từ bucket/object#generation: Eventarc gửi lại cùng 1 event
thì dùng lại job cũ, không load trùng.
"""
from __future__ import annotations

import hashlib
import os

import functions_framework
from cloudevents.http import CloudEvent
from google.api_core.exceptions import Conflict
from google.cloud import bigquery

BQ_DATASET = os.getenv("BQ_DATASET", "raw")
BQ_LOCATION = os.getenv("BQ_LOCATION", "asia-southeast1")
ROUTES = {
    "staging/events/incoming/": "events",
    "staging/ip_locations/incoming/": "ip_locations",
    "staging/products/incoming/": "products",
}

client = bigquery.Client()


def job_id_for(bucket: str, name: str, generation: str) -> str:
    digest = hashlib.sha256(f"{bucket}/{name}#{generation}".encode()).hexdigest()[:32]
    return f"gcs_load_{digest}"


@functions_framework.cloud_event
def load_gcs_to_bigquery(cloud_event: CloudEvent) -> str:
    data = cloud_event.data
    bucket, name = data["bucket"], data["name"]
    generation = str(data.get("generation", ""))

    table = next((t for p, t in ROUTES.items() if name.startswith(p)), None)
    if table is None or not name.endswith(".jsonl.gz"):
        print(f"ignored: gs://{bucket}/{name}")
        return "ignored"

    uri = f"gs://{bucket}/{name}"
    destination = f"{client.project}.{BQ_DATASET}.{table}"
    job_id = job_id_for(bucket, name, generation)
    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        ignore_unknown_values=False,
        max_bad_records=0,
    )

    print(f"loading {uri} -> {destination} job_id={job_id}")
    try:
        job = client.load_table_from_uri(uri, destination, job_id=job_id,
                                         location=BQ_LOCATION, job_config=config)
    except Conflict:
        print(f"job already exists (redelivery): {job_id}")
        job = client.get_job(job_id, location=BQ_LOCATION)

    job.result()  # raise nếu load lỗi -> log lỗi trong Cloud Logging
    print(f"done {uri} output_rows={job.output_rows}")
    return "ok"
