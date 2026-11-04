# Data dictionary — Learning Analytics Studio (OULAD)

Source: Open University Learning Analytics Dataset (OULAD), 32,593 learner enrolments
across 7 modules / 2013–2014 presentations. Dates are integer **days relative to course
start** (day 0); negative = before the course began. Empty strings load as NULL.

## Raw tables

### `courses` (22 rows)
| column | type | meaning |
|---|---|---|
| code_module | text | module code (AAA…GGG) |
| code_presentation | text | presentation (e.g. 2013J, 2014B) |
| module_presentation_length | int | length of the presentation in days |

### `studentInfo` (32,593) — grain: student × module × presentation
| column | meaning |
|---|---|
| id_student | learner id |
| gender, region, highest_education, imd_band, age_band, disability | demographics (imd_band = deprivation band; 3.4% null) |
| num_of_prev_attempts | prior attempts at the module |
| studied_credits | credits being studied |
| **final_result** | Pass / Fail / Withdrawn / Distinction (outcome) |

### `studentRegistration` (32,593)
date_registration (days before start, usually negative), date_unregistration (NULL unless withdrawn).

### `assessments` (206)
id_assessment, assessment_type (TMA / CMA / Exam), date (due), weight.

### `studentAssessment` (173,912)
id_assessment, id_student, date_submitted, is_banked, score (0–100).

### `vle` (6,364)
id_site, code_module, code_presentation, activity_type (content type), week_from/week_to.

### `studentVle` (10,655,280) — the clickstream
id_student × id_site × day → sum_click (interactions that day).

## Marts (built by `sql/marts.sql`)

### `mart_student` — grain: student × module × presentation (the analytical base)
Demographics + outcome flags (`passed`, `withdrawn`, `failed`) + registration +
engagement (`total_clicks`, `active_days`, `clicks_first_4w`, `clicks_pre_start`,
`active_days_first_4w`) + assessments (`n_assessments_submitted`, `avg_score`).

### `mart_engagement_weekly` — grain: student × relative week → clicks (timeline).

### `mart_content` — grain: activity type → interactions, total_clicks, distinct_students.
