"""
analytics/data_access.py
Return the small aggregate DataFrames the dashboard needs.

Prefers the full DuckDB warehouse (local dev); falls back to committed serving parquet
files (for deployment, where the 454MB raw clickstream isn't available).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

import config

SERVING_DIR = Path(__file__).resolve().parent.parent / "data" / "serving"

# name -> SQL against the warehouse (KPI views from sql/metrics.sql + two extras).
QUERIES: Dict[str, str] = {
    "overall": "SELECT * FROM kpi_overall",
    "outcomes_by_course": "SELECT * FROM kpi_outcomes_by_course",
    "engagement_by_outcome": "SELECT * FROM kpi_engagement_by_outcome",
    "content": "SELECT * FROM kpi_content_performance",
    "segment": "SELECT * FROM kpi_pass_rate_by_segment",
    # Average clicks per enrolled student per relative week, by outcome (timeline).
    "timeline": """
        WITH n AS (SELECT final_result, count(*) AS n FROM mart_student GROUP BY 1)
        SELECT s.final_result,
               w.rel_week,
               round(sum(w.clicks) * 1.0 / n.n, 1) AS avg_clicks
        FROM mart_engagement_weekly w
        JOIN mart_student s USING (id_student, code_module, code_presentation)
        JOIN n ON n.final_result = s.final_result
        WHERE w.rel_week BETWEEN 0 AND 39
        GROUP BY s.final_result, w.rel_week, n.n
        ORDER BY s.final_result, w.rel_week
    """,
}


def _from_warehouse() -> Dict[str, pd.DataFrame]:
    import duckdb

    con = duckdb.connect(config.DB_PATH, read_only=True)
    try:
        return {name: con.execute(sql).fetchdf() for name, sql in QUERIES.items()}
    finally:
        con.close()


def _from_serving() -> Dict[str, pd.DataFrame]:
    return {name: pd.read_parquet(SERVING_DIR / f"{name}.parquet") for name in QUERIES}


def get_frames() -> Dict[str, pd.DataFrame]:
    """Load dashboard frames from the warehouse if present, else serving parquet."""
    if Path(config.DB_PATH).exists():
        frames = _from_warehouse()
    elif SERVING_DIR.exists() and any(SERVING_DIR.glob("*.parquet")):
        frames = _from_serving()
    else:
        raise FileNotFoundError(
            "No warehouse or serving data. Run `python scripts/build_warehouse.py` "
            "(local) or `python scripts/export_serving.py` to create serving files."
        )
    frames["anomalies"] = detect_course_anomalies(frames["outcomes_by_course"])
    return frames


def detect_course_anomalies(outcomes: pd.DataFrame, z_threshold: float = 1.5) -> pd.DataFrame:
    """Deterministic flag: courses whose withdrawal rate is an outlier (|z| >= threshold)."""
    df = outcomes.copy()
    mu, sd = df["withdrawal_rate"].mean(), df["withdrawal_rate"].std(ddof=0)
    df["z"] = 0.0 if sd == 0 else ((df["withdrawal_rate"] - mu) / sd).round(2)
    df["flag"] = df["z"].abs() >= z_threshold
    df["direction"] = df["z"].apply(lambda z: "high withdrawal" if z > 0 else "low withdrawal")
    return df.sort_values("z", ascending=False)
