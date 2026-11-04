"""
config.py
Environment-driven configuration for the Learning Analytics Studio (OULAD).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Where the 7 raw OULAD CSVs live (kept out of git). Override with OULAD_RAW.
RAW_DIR = os.getenv("OULAD_RAW", "data/raw")

# Built DuckDB warehouse (out of git).
DB_PATH = os.getenv("DB_PATH", "warehouse/oulad.duckdb")

# Early-warning window: clicks within the first N weeks of a course.
FIRST_WEEKS = int(os.getenv("FIRST_WEEKS", "4"))

# The 7 OULAD tables (file stem == raw table name).
RAW_TABLES = [
    "courses",
    "assessments",
    "vle",
    "studentInfo",
    "studentRegistration",
    "studentAssessment",
    "studentVle",
]
