"""
etl/quality.py
Data-quality checks across the raw OULAD tables. Each check returns a row with a
status (OK / WARN / FAIL) so issues are flagged proactively, as the role requires.
"""
from __future__ import annotations

from typing import Any, Dict, List

import duckdb


def _one(con, sql: str) -> Any:
    return con.execute(sql).fetchone()[0]


def run_checks(con: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, status: str, detail: str):
        checks.append({"check": name, "status": status, "detail": detail})

    # 1) Expected non-empty tables
    for t in ("studentInfo", "studentVle", "studentAssessment", "assessments", "vle", "courses", "studentRegistration"):
        n = _one(con, f"SELECT count(*) FROM {t}")
        add(f"rowcount:{t}", "OK" if n > 0 else "FAIL", f"{n:,} rows")

    # 2) final_result domain
    bad = _one(con, """
        SELECT count(*) FROM studentInfo
        WHERE final_result NOT IN ('Pass','Fail','Withdrawn','Distinction')
    """)
    add("domain:final_result", "OK" if bad == 0 else "FAIL", f"{bad} rows outside expected set")

    # 3) assessment score range (0-100, NULL allowed)
    oob = _one(con, "SELECT count(*) FROM studentAssessment WHERE score IS NOT NULL AND (score < 0 OR score > 100)")
    add("range:score", "OK" if oob == 0 else "WARN", f"{oob} scores outside 0-100")

    # 4) duplicate student keys in studentInfo (grain = student x module x presentation)
    dup = _one(con, """
        SELECT count(*) FROM (
            SELECT id_student, code_module, code_presentation, count(*) c
            FROM studentInfo GROUP BY 1,2,3 HAVING c > 1
        )
    """)
    add("pk:studentInfo", "OK" if dup == 0 else "FAIL", f"{dup} duplicate (student,module,presentation) keys")

    # 5) referential integrity: clickstream students exist in studentInfo
    orphan = _one(con, """
        SELECT count(*) FROM (
            SELECT DISTINCT v.id_student, v.code_module, v.code_presentation
            FROM studentVle v
            LEFT JOIN studentInfo s USING (id_student, code_module, code_presentation)
            WHERE s.id_student IS NULL
        )
    """)
    add("fk:studentVle->studentInfo", "OK" if orphan == 0 else "WARN", f"{orphan} click rows w/o matching student")

    # 6) referential integrity: assessments link
    orphan_a = _one(con, """
        SELECT count(*) FROM studentAssessment sa
        LEFT JOIN assessments a USING (id_assessment)
        WHERE a.id_assessment IS NULL
    """)
    add("fk:studentAssessment->assessments", "OK" if orphan_a == 0 else "WARN", f"{orphan_a} submissions w/o assessment")

    # 7) missingness on key analytical fields
    imd_null = _one(con, "SELECT round(100.0*sum(CASE WHEN imd_band IS NULL THEN 1 ELSE 0 END)/count(*),1) FROM studentInfo")
    add("missing:imd_band", "OK" if imd_null < 10 else "WARN", f"{imd_null}% null (deprivation band)")

    return checks


def to_markdown(checks: List[Dict[str, Any]]) -> str:
    lines = ["| check | status | detail |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['check']} | {c['status']} | {c['detail']} |")
    return "\n".join(lines)
