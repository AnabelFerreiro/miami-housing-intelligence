"""Export a per-zip-code housing summary CSV for the Power BI dashboard."""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "housing.db"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "miami_housing_summary.csv"
SOURCE_TABLE = "zip_market_data"
LOG_TABLE = "insights_log"
MONTHS = 12
PROPERTY_TYPE = "All Residential"

RECENT_DATA_QUERY = f"""
WITH ranked AS (
    SELECT
        REGION,
        PERIOD_BEGIN,
        MEDIAN_SALE_PRICE,
        HOMES_SOLD,
        INVENTORY,
        ROW_NUMBER() OVER (PARTITION BY REGION ORDER BY PERIOD_BEGIN DESC) AS rn
    FROM {SOURCE_TABLE}
    WHERE PROPERTY_TYPE = ?
)
SELECT REGION, PERIOD_BEGIN, MEDIAN_SALE_PRICE, HOMES_SOLD, INVENTORY
FROM ranked
WHERE rn <= ?
ORDER BY REGION, PERIOD_BEGIN
"""

LATEST_INSIGHTS_QUERY = f"""
SELECT generated_at, insights
FROM {LOG_TABLE}
ORDER BY generated_at DESC
LIMIT 1
"""


def fetch_recent_data(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(RECENT_DATA_QUERY, conn, params=(PROPERTY_TYPE, MONTHS))


def build_zip_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for region, group in df.groupby("REGION"):
        group = group.sort_values("PERIOD_BEGIN")
        first_price = group["MEDIAN_SALE_PRICE"].iloc[0]
        latest = group.iloc[-1]
        pct_change = (
            (latest["MEDIAN_SALE_PRICE"] - first_price) / first_price * 100
            if first_price
            else None
        )
        rows.append(
            {
                "zip_code": region.replace("Zip Code: ", ""),
                "median_sale_price": latest["MEDIAN_SALE_PRICE"],
                "price_change_pct_12mo": round(pct_change, 1) if pct_change is not None else None,
                "homes_sold": latest["HOMES_SOLD"],
                "inventory": latest["INVENTORY"],
            }
        )
    return pd.DataFrame(rows).sort_values("zip_code")


def fetch_latest_insights(conn: sqlite3.Connection) -> tuple[str | None, str | None]:
    row = conn.execute(LATEST_INSIGHTS_QUERY).fetchone()
    if row is None:
        return None, None
    return row[0], row[1]


def main() -> None:
    if not DB_PATH.exists():
        sys.exit(f"Database not found at {DB_PATH}. Run scripts/load_db.py first.")

    with sqlite3.connect(DB_PATH) as conn:
        recent = fetch_recent_data(conn)
        if recent.empty:
            sys.exit(f"No rows found in {SOURCE_TABLE} for PROPERTY_TYPE='{PROPERTY_TYPE}'.")

        summary = build_zip_summary(recent)

        generated_at, insights = fetch_latest_insights(conn)
        summary["insights_generated_at"] = generated_at
        summary["latest_insights"] = insights

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_PATH, index=False)
    print(f"Exported {len(summary)} zip codes to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
