"""
scripts/build_warehouse.py
One command to build the DuckDB warehouse: load raw OULAD -> run data-quality checks
-> build marts & KPI views. Prints the DQ report and headline KPIs.

    OULAD_RAW=/path/to/csvs python scripts/build_warehouse.py
"""
import os
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from etl.build_marts import build_marts  # noqa: E402
from etl.load_raw import load_raw  # noqa: E402
from etl.quality import run_checks, to_markdown  # noqa: E402


def main() -> None:
    os.makedirs(Path(config.DB_PATH).parent, exist_ok=True)
    con = duckdb.connect(config.DB_PATH)
    try:
        print("1) Loading raw OULAD CSVs…")
        for name, n in load_raw(con, config.RAW_DIR).items():
            print(f"   {name}: {n:,}")

        print("\n2) Data-quality checks:")
        checks = run_checks(con)
        print(to_markdown(checks))
        fails = [c for c in checks if c["status"] == "FAIL"]
        print(f"   -> {len(fails)} FAIL, "
              f"{len([c for c in checks if c['status'] == 'WARN'])} WARN")

        print("\n3) Building marts & KPI views…")
        build_marts(con)

        print("\n4) Headline KPIs")
        print("   overall:", con.execute("SELECT * FROM kpi_overall").fetchdf().to_dict("records")[0])
        print("   engagement by outcome:")
        print(con.execute("SELECT * FROM kpi_engagement_by_outcome").fetchdf().to_string(index=False))
        print("   top content types:")
        print(con.execute("SELECT activity_type, total_clicks, pct_of_clicks "
                          "FROM kpi_content_performance LIMIT 6").fetchdf().to_string(index=False))
    finally:
        con.close()
    print(f"\nWarehouse built -> {config.DB_PATH}")


if __name__ == "__main__":
    main()
