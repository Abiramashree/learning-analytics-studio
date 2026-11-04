"""
etl/build_marts.py
Execute the SQL files that build the analytical marts and KPI views.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _strip_line_comments(sql: str) -> str:
    """Drop `-- ...` comments (which may contain semicolons) before splitting."""
    out = []
    for line in sql.splitlines():
        i = line.find("--")
        out.append(line if i == -1 else line[:i])
    return "\n".join(out)


def _run_sql_file(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    """Execute every statement in a .sql file. Returns the count executed."""
    sql = _strip_line_comments(path.read_text(encoding="utf-8"))
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        con.execute(stmt)
    return len(statements)


def build_marts(con: duckdb.DuckDBPyConnection) -> None:
    for fname in ("marts.sql", "metrics.sql", "analytics.sql"):
        n = _run_sql_file(con, SQL_DIR / fname)
        print(f"  ran {fname}: {n} statements")
