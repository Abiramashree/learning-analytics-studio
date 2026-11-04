"""
Offline tests for the ETL SQL handling — no data download required.
(Full warehouse build is validated by running scripts/build_warehouse.py on the CSVs.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.build_marts import _strip_line_comments  # noqa: E402

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def test_strip_line_comments_handles_semicolons_in_comments():
    sql = "-- a comment; with a semicolon\nSELECT 1;"
    out = _strip_line_comments(sql)
    assert "comment" not in out
    assert "SELECT 1;" in out


def _count_statements(path: Path) -> int:
    sql = _strip_line_comments(path.read_text(encoding="utf-8"))
    return len([s for s in sql.split(";") if s.strip()])


def test_marts_sql_has_three_statements():
    assert _count_statements(SQL_DIR / "marts.sql") == 3


def test_metrics_sql_has_five_views():
    assert _count_statements(SQL_DIR / "metrics.sql") == 5
