"""Download Redfin zip-code market tracker data and extract Miami, FL rows."""

from pathlib import Path

import pandas as pd
import requests

DATA_URL = (
    "https://redfin-public-data.s3.us-west-2.amazonaws.com/"
    "redfin_market_tracker/zip_code_market_tracker.tsv000.gz"
)
RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "zip_code_market_tracker.tsv000.gz"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "miami_zip_data.csv"

USECOLS = [
    "PERIOD_BEGIN",
    "PERIOD_END",
    "PERIOD_DURATION",
    "REGION_TYPE",
    "REGION",
    "STATE",
    "STATE_CODE",
    "PROPERTY_TYPE",
    "MEDIAN_SALE_PRICE",
    "MEDIAN_LIST_PRICE",
    "MEDIAN_PPSF",
    "MEDIAN_LIST_PPSF",
    "HOMES_SOLD",
    "PENDING_SALES",
    "NEW_LISTINGS",
    "INVENTORY",
    "MONTHS_OF_SUPPLY",
    "MEDIAN_DOM",
    "AVG_SALE_TO_LIST",
    "SOLD_ABOVE_LIST",
    "OFF_MARKET_IN_TWO_WEEKS",
    "PARENT_METRO_REGION",
    "LAST_UPDATED",
]

CHUNKSIZE = 200_000
DOWNLOAD_CHUNK_BYTES = 8 * 1024 * 1024


def download_raw_file() -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(DATA_URL, stream=True, timeout=60) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        last_reported_mb = 0
        with open(RAW_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_BYTES):
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded / 1e6 - last_reported_mb >= 50:
                    last_reported_mb = downloaded / 1e6
                    pct = f"{downloaded / total:.1%}" if total else "?"
                    print(f"downloaded {downloaded / 1e6:.0f} MB / {total / 1e6:.0f} MB ({pct})")


def fetch_miami_data() -> pd.DataFrame:
    reader = pd.read_csv(
        RAW_PATH,
        sep="\t",
        compression="gzip",
        usecols=USECOLS,
        chunksize=CHUNKSIZE,
        low_memory=False,
    )

    matches = []
    rows_scanned = 0
    for i, chunk in enumerate(reader, start=1):
        rows_scanned += len(chunk)
        mask = (chunk["STATE_CODE"] == "FL") & chunk["PARENT_METRO_REGION"].str.contains(
            "Miami", case=False, na=False
        )
        filtered = chunk[mask]
        if not filtered.empty:
            matches.append(filtered)
        print(f"chunk {i}: scanned {rows_scanned:,} rows, {len(filtered)} matched")

    if not matches:
        return pd.DataFrame(columns=USECOLS)
    return pd.concat(matches, ignore_index=True)


def main() -> None:
    if not RAW_PATH.exists():
        print(f"Downloading {DATA_URL} ...")
        download_raw_file()
    else:
        print(f"Using cached download at {RAW_PATH}")

    miami_df = fetch_miami_data()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    miami_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(miami_df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
