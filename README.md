# 🎓 Learning Analytics Studio

A reproducible learning-analytics pipeline and (soon) dashboard built on the **Open
University Learning Analytics Dataset (OULAD)** — 32,593 learner enrolments and a
**10.6M-row engagement clickstream**. A portfolio project inspired by a Learning
Analytics / Employee-Experience data-science role; **all data is the public OULAD**, used
here as a proxy for training-program analytics.

> Status: **Phase 3 complete** — SQL warehouse + data-quality + governed KPIs, a six-tab
> **Streamlit/Plotly dashboard**, and an **early-warning model** (predict at-risk from the
> first 4 weeks; temporal split; honest metrics + fairness; intervention what-if).
>
> **Dashboard tabs:** 📊 Overview (business framing, outcome-mix donut, learner funnel) ·
> 👥 Students (registrations, cohort composition, registration lead time) · 🎯 Outcomes
> (by-course, pass-rate heatmap, segment gaps, anomalies) · 📈 Engagement (by-outcome,
> timeline, dose-response) · 📚 Content & Effectiveness (content share, assessment-score
> distributions, submission-timing, engagement→score) · 🚨 Early-warning (the model).

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
- **Engagement is a dose-response signal** — across first-4-week engagement deciles, pass
  rate climbs **7% → 75%** and mean assessment score **69 → 80**; early submitters (8+ days
  before the due date) average **80.7** vs **75.0** for late ones.
- **The funnel leaks early** — 32,593 registered → 29,915 started → 29,228 engaged →
  25,843 assessed → **15,385 passed**; late/unknown registrants withdraw far more.
- **Early-warning model** (first 4 weeks → at-risk, 2013→2014 temporal split): **ROC-AUC 0.79,
  PR-AUC 0.84**; at a ~70% recall operating point, **75% precision**. See the
  [model card](docs/model_card.md).

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
  same output.
- **Governed metrics** — KPIs defined once in SQL, documented in the glossary.
- **Quality first** — DQ checks run on every build.
- **AI as a validated accelerator, never a source of truth** — see below.

## AI accelerator (optional, validated)

The Overview tab can generate a short executive summary with a language model. By design it
is an *accelerator*, not an oracle:

- The model is given **only the governed figures** already computed by the SQL, and is
  instructed to re-express them verbatim — it never produces a number of its own.
- Every figure in its output is then **checked back against the warehouse facts**
  (`analytics/narrative.py` → `validate_narrative`); anything unverifiable is flagged in
  the UI rather than shown as fact.
- With no model configured it falls back to a **deterministic template** that is correct by
  construction — so the dashboard never depends on an LLM to be right.

The model is **Gemini** (via its OpenAI-compatible endpoint) configured with `GOOGLE_API_KEY`
(+ optional `GEMINI_MODEL`). The same validate-then-trust pattern is how a free-text classifier
(e.g. survey verbatims) would be governed. The guardrail is unit-tested offline
(`tests/test_narrative.py`).

## Project structure

```
├── config.py                 # env-driven paths/params
├── etl/
│   ├── load_raw.py           # CSV -> DuckDB raw tables
│   ├── quality.py            # data-quality checks (OK/WARN/FAIL)
│   └── build_marts.py        # run the SQL files
├── sql/
│   ├── marts.sql             # analytical base tables
│   ├── metrics.sql           # governed KPI views
│   └── analytics.sql         # deep-dive KPI views (funnel, dose-response, assessments)
├── docs/
│   ├── data_dictionary.md
│   └── metric_glossary.md
├── scripts/build_warehouse.py
├── tests/
├── data/raw/                 # the 7 OULAD CSVs (gitignored)
└── requirements.txt
```

## Roadmap

- ✅ **Phase 2** — six-tab Streamlit + Plotly dashboard: overview (donut + funnel), student
  demographics & registration timing, outcomes (+ pass-rate heatmap), engagement
  (timeline + dose-response), content & assessment-effectiveness deep-dive, anomaly flags.
- ✅ **Phase 3** — early-warning deep-dive: predict withdrawal/fail from the first 4 weeks,
  with a temporal split, honest recall/PR-AUC, fairness check, and an intervention what-if.
- ✅ **Phase 4 (in progress)** — validated AI accelerator: LLM narrative constrained to
  governed figures with a fact-checking guardrail + deterministic fallback; deterministic
  course risk-tier classification. Next: packaged findings/deck, Tableau companion.
