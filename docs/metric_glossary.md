# Metric glossary — Learning Analytics Studio

Governed KPI definitions (the "source of truth"). Each is a SQL view in
[`sql/metrics.sql`](../sql/metrics.sql) or [`sql/analytics.sql`](../sql/analytics.sql)
over `mart_student` / `mart_content`. Grain is per learner enrolment
(student × module × presentation) unless noted.

| Metric | Definition | Formula | View |
|---|---|---|---|
| **Pass rate** | share of enrolments passing | `avg(final_result IN ('Pass','Distinction'))` | `kpi_overall`, `kpi_outcomes_by_course` |
| **Withdrawal rate** | share that withdrew | `avg(final_result = 'Withdrawn')` | same |
| **Fail rate** | share that failed (not withdrawn) | `avg(final_result = 'Fail')` | same |
| **Distinction rate** | share achieving distinction | `avg(final_result = 'Distinction')` | `kpi_overall` |
| **Avg clicks (first 4 weeks)** | mean VLE clicks in days 0–27 — the early-engagement signal | `avg(clicks_first_4w)` | `kpi_engagement_by_outcome` |
| **Active days** | distinct days with ≥1 click | `avg(active_days)` | `kpi_engagement_by_outcome` |
| **Avg assessment score** | mean submitted score (0–100) | `avg(avg_score)` | `kpi_engagement_by_outcome` |
| **Content performance** | engagement share by content/activity type | `total_clicks / sum(total_clicks)` | `kpi_content_performance` |
| **Pass rate by segment** | pass/withdrawal by demographic band (gender, region, age, education, imd, disability) | grouped `avg(passed)` | `kpi_pass_rate_by_segment` |
| **Learner funnel** | counts at each stage: registered → started → engaged → assessed → passed | staged `count(*)` | `kpi_funnel` |
| **Registration lead time** | enrolments & pass rate by how early the learner registered | bucketed `date_registration` | `kpi_registration_timing` |
| **Engagement dose-response** | pass/withdrawal/score by decile of first-4-week clicks | `ntile(10)` over `clicks_first_4w` | `kpi_engagement_dose` |
| **Assessment score by type** | score distribution (p05–p95) per TMA/CMA/Exam | `quantile_cont(score, …)` | `kpi_assessment_by_type` |
| **Assessment score by course** | mean submitted score per module-presentation | `avg(score)` | `kpi_assessment_by_course` |
| **Submission timing** | submissions & avg score by lead/lag vs the due date | `date_submitted − assessment.date` | `kpi_submission_timing` |

## Reference values (full OULAD, current build)
- Pass 47.2% · Withdrawal 31.2% · Fail 21.6% · Distinction 9.3%.
- First-4-week clicks by outcome: Distinction 427 · Pass 317 · Fail 176 · Withdrawn 131.
- Engagement dose-response: pass rate climbs **7% → 75%** from the least- to most-active
  first-4-week decile; avg assessment score **69 → 80** across the same deciles.
- Funnel: 32,593 registered → 29,915 started → 29,228 engaged → 25,843 assessed → 15,385 passed.
- Early submitters (8+ days before due) average **80.7** vs **75.0** for late submissions.

## Conventions
- **Early-warning window** = first 4 weeks (days 0–27), set by `FIRST_WEEKS`.
- Dates are days relative to course start; pre-start activity is tracked separately
  (`clicks_pre_start`).
- `imd_band` (deprivation) is ~3.4% null — reported, not imputed, in descriptive views.
