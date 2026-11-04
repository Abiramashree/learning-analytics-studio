# Metric glossary — Learning Analytics Studio

Governed KPI definitions (the "source of truth"). Each is a SQL view in
[`sql/metrics.sql`](../sql/metrics.sql) over `mart_student` / `mart_content`.
Grain is per learner enrolment (student × module × presentation) unless noted.

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
| **Pass rate by segment** | pass/withdrawal by demographic band | grouped `avg(passed)` | `kpi_pass_rate_by_segment` |

## Reference values (full OULAD, current build)
- Pass 47.2% · Withdrawal 31.2% · Fail 21.6% · Distinction 9.3%.
- First-4-week clicks by outcome: Distinction 427 · Pass 317 · Fail 176 · Withdrawn 131.

## Conventions
- **Early-warning window** = first 4 weeks (days 0–27), set by `FIRST_WEEKS`.
- Dates are days relative to course start; pre-start activity is tracked separately
  (`clicks_pre_start`).
- `imd_band` (deprivation) is ~3.4% null — reported, not imputed, in descriptive views.
