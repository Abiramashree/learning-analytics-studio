# 🎓 Learning Analytics Studio

A reproducible learning-analytics pipeline and (soon) dashboard built on the **Open
University Learning Analytics Dataset (OULAD)** — 32,593 learner enrolments and a
**10.6M-row engagement clickstream**. A portfolio project inspired by a Learning
Analytics / Employee-Experience data-science role; **all data is the public OULAD**, used
here as a proxy for training-program analytics.

> Status: **Phase 2 complete** — SQL warehouse + data-quality + governed KPIs, and a
> **Streamlit/Plotly dashboard** (outcomes, engagement, content, cohorts, anomaly flags).
> Early-warning model + packaged findings are next.

## What it does today

- **ETL** (`etl/`) loads the 7 raw OULAD CSVs into a **DuckDB** warehouse.
- **Data-quality checks** (`etl/quality.py`) validate row counts, value domains, key
  uniqueness, referential integrity, and missingness — flagging issues with OK/WARN/FAIL.
- **SQL marts** (`sql/marts.sql`) build a clean learner-level base table plus engagement
  and content marts; **KPI views** (`sql/metrics.sql`) define the governed metrics.
- **Docs** (`docs/`): a data dictionary and a metric glossary (the "source of truth").

## Headline findings (full OULAD)

- Outcomes: **47.2% pass · 31.2% withdrawal · 21.6% fail · 9.3% distinction**.
- **Early engagement tracks success** — mean clicks in the first 4 weeks:
  Distinction **427** → Pass **317** → Fail **176** → Withdrawn **131**.
- Engagement is concentrated in course content (28%), forums (20%), and quizzes (18%).

## Quick start

1. Download OULAD (free) from <https://analyse.kmi.open.ac.uk/open_dataset> and put the 7
   CSVs in `data/raw/` (kept out of git).
2. Build the warehouse:

```bash
pip install -r requirements.txt
python scripts/build_warehouse.py        # load -> quality checks -> marts/KPIs
```

Point at CSVs elsewhere with `OULAD_RAW=/path/to/csvs python scripts/build_warehouse.py`.

3. Run the dashboard:

```bash
python scripts/export_serving.py   # small aggregates for fast/portable serving
streamlit run app.py
```

The dashboard reads the warehouse locally, or the committed `data/serving/*.parquet`
when deployed — so it runs **without** the 454 MB raw clickstream. Deploy on Railway
(included `Dockerfile` + `railway.json`) or Streamlit Community Cloud (point it at `app.py`).

## Design principles

- **Deterministic & reproducible** — everything is SQL + fixed transforms; same input →
  same output. (A later, optional LLM layer only *summarizes* validated results.)
- **Governed metrics** — KPIs defined once in SQL, documented in the glossary.
- **Quality first** — DQ checks run on every build.

## Project structure

```
├── config.py                 # env-driven paths/params
├── etl/
│   ├── load_raw.py           # CSV -> DuckDB raw tables
│   ├── quality.py            # data-quality checks (OK/WARN/FAIL)
│   └── build_marts.py        # run the SQL files
├── sql/
│   ├── marts.sql             # analytical base tables
│   └── metrics.sql           # governed KPI views
├── docs/
│   ├── data_dictionary.md
│   └── metric_glossary.md
├── scripts/build_warehouse.py
├── tests/
├── data/raw/                 # the 7 OULAD CSVs (gitignored)
└── requirements.txt
```

## Roadmap

- ✅ **Phase 2** — Streamlit + Plotly dashboard: outcomes, engagement timeline, content
  performance, cohort drilldowns, anomaly flags.
- **Phase 3** — early-warning deep-dive: predict withdrawal/fail from the first 4 weeks,
  with a temporal split, honest recall/PR-AUC, and a fairness check.
- **Phase 4** — intervention what-if + packaged findings (annotated visuals / deck);
  optional validated LLM narrative layer; Tableau companion spec.
