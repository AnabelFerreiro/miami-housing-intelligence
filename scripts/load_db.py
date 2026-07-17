"""Load the processed Miami zip market data into a SQLite database."""

import sqlite3
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "miami_zip_data.csv"
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "housing.db"
TABLE_NAME = "zip_market_data"


def main() -> None:
    df = pd.read_csv(CSV_PATH)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

    print(f"Loaded {len(df):,} rows into {DB_PATH} ({TABLE_NAME})")
    print(f"Date range: {df['PERIOD_BEGIN'].min()} to {df['PERIOD_BEGIN'].max()}")


if __name__ == "__main__":
    main()
