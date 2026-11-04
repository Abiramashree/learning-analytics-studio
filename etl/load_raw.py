"""
etl/load_raw.py
Load the 7 raw OULAD CSVs into DuckDB raw tables (empty strings -> NULL).
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

import config


def load_raw(con: duckdb.DuckDBPyConnection, raw_dir: str = config.RAW_DIR) -> dict[str, int]:
    """Create one DuckDB table per CSV (named after the file). Returns row counts."""
    counts: dict[str, int] = {}
    for name in config.RAW_TABLES:
        path = Path(raw_dir) / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Put the 7 OULAD CSVs in {raw_dir}/.")
        con.execute(
            f"CREATE OR REPLACE TABLE {name} AS "
            f"SELECT * FROM read_csv_auto(?, header=true, nullstr='', sample_size=-1)",
            [str(path)],
        )
        counts[name] = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
    return counts


def main() -> None:
    os.makedirs(Path(config.DB_PATH).parent, exist_ok=True)
    con = duckdb.connect(config.DB_PATH)
    try:
        for name, n in load_raw(con).items():
            print(f"  loaded {name}: {n:,} rows")
    finally:
        con.close()


if __name__ == "__main__":
    main()
