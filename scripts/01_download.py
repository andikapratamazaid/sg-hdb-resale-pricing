"""Download the full HDB resale flat prices dataset from data.gov.sg.

Dataset: "Resale flat prices based on registration date from Jan-2017 onwards"
Dataset/resource id: d_8b84c4ee58e3cfc0ece0d773c8ca6abc

Primary path: api-open.data.gov.sg v1 initiate-download -> poll-download -> CSV.
Fallback path: page through the CKAN datastore_search endpoint (no API key).

Output: data/raw/hdb_resale_2017_onwards.csv
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

DATASET_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = RAW_DIR / "hdb_resale_2017_onwards.csv"
LOG = RAW_DIR / "download_log.json"


def download_via_open_api() -> str:
    """Return the signed CSV URL using the v1 initiate/poll download flow."""
    base = "https://api-open.data.gov.sg/v1/public/api/datasets"
    r = requests.get(f"{base}/{DATASET_ID}/initiate-download", timeout=60)
    r.raise_for_status()
    for attempt in range(60):
        time.sleep(5)
        p = requests.get(f"{base}/{DATASET_ID}/poll-download", timeout=60)
        p.raise_for_status()
        payload = p.json()
        data = payload.get("data", {})
        if data.get("status") == "DOWNLOAD_SUCCESS" and data.get("url"):
            return data["url"]
        if attempt % 6 == 0:
            print(f"  poll {attempt}: status={data.get('status')}")
    raise RuntimeError("poll-download did not reach DOWNLOAD_SUCCESS in time")


def download_via_ckan() -> pd.DataFrame:
    """Fallback: page through datastore_search in chunks of 10,000 rows."""
    url = "https://data.gov.sg/api/action/datastore_search"
    frames, offset, total = [], 0, None
    while total is None or offset < total:
        r = requests.get(
            url,
            params={"resource_id": DATASET_ID, "limit": 10000, "offset": offset},
            timeout=120,
        )
        r.raise_for_status()
        result = r.json()["result"]
        total = result["total"]
        records = result["records"]
        if not records:
            break
        frames.append(pd.DataFrame(records))
        offset += len(records)
        print(f"  CKAN: {offset:,}/{total:,} rows")
    df = pd.concat(frames, ignore_index=True)
    return df.drop(columns=[c for c in df.columns if c == "_id"], errors="ignore")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    method = None
    try:
        print("Trying api-open.data.gov.sg download flow...")
        csv_url = download_via_open_api()
        with requests.get(csv_url, stream=True, timeout=600) as resp:
            resp.raise_for_status()
            with open(OUT, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
        method = "api-open.data.gov.sg v1 initiate/poll-download"
    except Exception as exc:  # noqa: BLE001 - fall back to CKAN paging
        print(f"Open API flow failed ({exc}); falling back to CKAN paging.")
        df = download_via_ckan()
        df.to_csv(OUT, index=False)
        method = "CKAN datastore_search paging"

    df = pd.read_csv(OUT, usecols=["month"])
    log = {
        "dataset_id": DATASET_ID,
        "method": method,
        "rows": int(len(df)),
        "month_min": str(df["month"].min()),
        "month_max": str(df["month"].max()),
        "file": OUT.name,
        "bytes": OUT.stat().st_size,
    }
    LOG.write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
