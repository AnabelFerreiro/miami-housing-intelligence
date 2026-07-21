"""Generate natural language insights on Miami zip-level housing trends using a local Ollama model."""

import sqlite3
from datetime import datetime, timezone

import ollama
import pandas as pd

DB_PATH = "db/housing.db"
SOURCE_TABLE = "zip_market_data"
LOG_TABLE = "insights_log"
MODEL = "llama3.1:8b"
MONTHS = 12
PROPERTY_TYPE = "All Residential"

QUERY = f"""
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


def fetch_recent_data(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(QUERY, conn, params=(PROPERTY_TYPE, MONTHS))


def summarize_by_zip(df: pd.DataFrame) -> pd.DataFrame:
    summaries = []
    for region, group in df.groupby("REGION"):
        group = group.sort_values("PERIOD_BEGIN")
        start_price = group["MEDIAN_SALE_PRICE"].iloc[0]
        end_price = group["MEDIAN_SALE_PRICE"].iloc[-1]
        pct_change = (
            (end_price - start_price) / start_price * 100 if start_price else None
        )
        summaries.append(
            {
                "zip": region.replace("Zip Code: ", ""),
                "months": len(group),
                "start_price": round(start_price, 0),
                "end_price": round(end_price, 0),
                "pct_change": round(pct_change, 1) if pct_change is not None else None,
                "avg_homes_sold": round(group["HOMES_SOLD"].mean(), 1),
                "avg_inventory": round(group["INVENTORY"].mean(), 1),
            }
        )
    return pd.DataFrame(summaries).sort_values("pct_change", ascending=False)


def build_prompt(summary: pd.DataFrame) -> str:
    table = summary.to_csv(index=False)
    return (
        "You are a real estate market analyst. Below is a summary of the trailing "
        f"{MONTHS} months of housing data for {len(summary)} zip codes in the Miami, FL "
        "metro area (property type: all residential). Each row shows the median sale "
        "price at the start and end of the period, percent change, and average monthly "
        "homes sold and inventory.\n\n"
        f"{table}\n"
        "Based on this data, give 3-4 concise, natural language insights about pricing "
        "trends across these Miami metro zip codes. Call out specific zip codes where "
        "relevant. Do not include a preamble or disclaimer, just the insights."
    )


def generate_insights(prompt: str) -> str:
    response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


def save_insights(conn: sqlite3.Connection, insights: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {LOG_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT NOT NULL,
            model TEXT NOT NULL,
            insights TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"INSERT INTO {LOG_TABLE} (generated_at, model, insights) VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), MODEL, insights),
    )
    conn.commit()


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        recent = fetch_recent_data(conn)
        summary = summarize_by_zip(recent)
        prompt = build_prompt(summary)

        print(f"Querying {MODEL} for insights on {len(summary)} zip codes...")
        insights = generate_insights(prompt)

        print("\n" + insights + "\n")

        save_insights(conn, insights)
        print(f"Saved insights to {LOG_TABLE} in {DB_PATH}")


if __name__ == "__main__":
    main()
