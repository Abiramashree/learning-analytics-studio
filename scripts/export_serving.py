"""
scripts/export_serving.py
Export the small dashboard aggregates to parquet so the app can run WITHOUT the 454MB
raw clickstream (e.g. on a deployed host). Run after build_warehouse.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.data_access import SERVING_DIR, _from_warehouse  # noqa: E402


def main() -> None:
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in _from_warehouse().items():
        df.to_parquet(SERVING_DIR / f"{name}.parquet", index=False)
        print(f"  wrote {name}.parquet ({len(df)} rows)")
    print(f"Serving data -> {SERVING_DIR}")


if __name__ == "__main__":
    main()
