# Learning Analytics Studio

**Live dashboard → https://learning-analytics-studio.streamlit.app/**

A learning-analytics project that measures learner engagement and training-program
effectiveness end to end — from raw event data to a governed dashboard and a leakage-free
early-warning model — and does it the way a careful data scientist would: deterministic,
reproducible, honest about its own limits, and using AI only where it can be validated.

It is built on the **Open University Learning Analytics Dataset (OULAD)** — 32,593 learner
enrolments and a 10.6-million-row engagement clickstream — used here as a public proxy for
workplace / training-program learning analytics.

---

## The question it answers

*Who completes an online course, who disengages — and how early can you tell?*

Every part of the project is in service of that question: understanding the learners,
measuring what happens to them, finding the behavioural signal that predicts the outcome,
and turning that signal into something a program team could act on in time to help.

## What it shows

The dashboard is organised as a report with six sections:

- **Overview** — headline outcomes, the outcome mix, a learner-progression funnel, and a
  one-paragraph executive summary.
- **Students** — who the learners are: cohort size, composition across demographics, and how
  early they register.
- **Outcomes** — pass/withdrawal by course run, a pass-rate heatmap, equity gaps across
  cohorts, statistical outliers, and rule-based course risk tiers.
- **Engagement** — how learners interact over time, and the engagement→outcome relationship.
- **Content & effectiveness** — where attention goes, assessment-score distributions,
  submission timing, and how engagement translates into measured learning.
- **Early warning** — a model that flags at-risk learners from their first four weeks, with
  honest evaluation, a fairness audit, calibration, and an intervention trade-off tool.

## What the data says

- Outcomes overall: **47% pass · 31% withdrawal · 22% fail · 9% distinction**.
- **Engagement is a dose-response signal.** Across deciles of first-four-week activity, pass
  rate climbs from **7% to 75%** and mean assessment score from **69 to 80**. The
  relationship is monotonic — which is exactly why an early-warning model is feasible.
- **The cohort leaks early.** Of 32,593 registrations, ~29,900 start, ~25,800 submit an
  assessment, and **15,385 pass** — with the largest drop-off before the first assessment.
- **Timing is a cheap pre-course signal.** Learners who register late (or with no recorded
  date) withdraw far more often; early submitters (8+ days before a due date) outscore late
  submitters (**80.7** vs **75.0**).

## Design decisions (the nuances that matter)

- **Deterministic by default.** Every number comes from SQL and fixed transforms, so the same
  input always produces the same output. There is no randomness in the reported figures.
- **Governed metrics.** Each KPI is defined exactly once as a SQL view and documented in a
  metric glossary — a single source of truth, rather than numbers re-derived ad hoc per chart.
- **Data quality is a gate, not an afterthought.** Row counts, value domains, key uniqueness,
  referential integrity and missingness are checked on every build and reported as
  OK/WARN/FAIL.
- **The model is built to be trusted, not to look good.** It uses **only first-four-week
  features** (no post-outcome leakage), is evaluated on a **temporal split** (train on 2013
  course runs, test on 2014 — future cohorts, not shuffled rows), and is reported with
  **PR-AUC and recall at a chosen operating point** rather than a flattering accuracy number.
  It reaches **ROC-AUC 0.79 / PR-AUC 0.84**, and ~**75% precision at ~70% recall**.
- **Fairness and calibration are first-class.** Flag rate and recall are reported per group
  (gender, disability, age, deprivation), and predicted risk is checked against actual risk.
- **AI is a validated accelerator, never a source of truth.** An optional Gemini-written
  summary is given *only* the governed figures and told to re-express them; every number it
  produces is then **checked back against the warehouse**, and anything unverifiable is
  flagged. With no model configured it falls back to a deterministic template that is correct
  by construction — so the dashboard never depends on an LLM to be right.
- **Deploys without the raw data.** The 454 MB clickstream stays out of the repository; the
  app runs on a ~220 KB bundle of pre-computed aggregates, so the live demo is light and the
  sensitive raw data never ships.

## Honest limitations

- OULAD is 2013–2014 Open University data — a **proxy**, not any specific organisation's.
- Engagement is measured as platform clicks only; it says nothing about off-platform learning
  or content quality.
- The engagement→outcome relationship is **predictive, not causal** — engagement correlates
  with ability, motivation and available time. A flag is a prompt for support, not a judgement
  about a learner, and proving that intervention *causes* better outcomes would need a
  controlled study.

## What it demonstrates

End-to-end ownership of a learning-analytics problem: ETL and data-quality engineering,
reproducible SQL modelling and metric governance, clear and accessible data visualisation,
a leakage-free predictive model with honest evaluation and fairness, and disciplined,
validated use of AI — all framed around a decision a program team would actually make.

## Built with

Python · DuckDB · SQL · scikit-learn · Streamlit · Plotly · (optional) Gemini.
Data © The Open University — [OULAD](https://analyse.kmi.open.ac.uk/open_dataset), open dataset.
