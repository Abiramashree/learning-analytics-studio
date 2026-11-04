# Model card — early-warning (at-risk) classifier

## Purpose
Flag learners likely to **withdraw or fail** using only information available in the
**first 4 weeks** of a course, so support can be targeted early. Decision-support, not
automated action.

## Data
- Open University Learning Analytics Dataset (OULAD), learner-enrolment grain.
- **Temporal split:** train on 2013 presentations, test on 2014 presentations — the model
  is evaluated on future cohorts, not shuffled rows (realistic, leakage-free).

## Target
`at_risk = final_result in {Withdrawn, Fail}`.

## Features (first-4-weeks only — no leakage)
- Enrolment-time: `code_module`, `gender`, `region`, `highest_education`, `imd_band`,
  `age_band`, `disability`, `num_of_prev_attempts`, `studied_credits`,
  `date_registration`, `module_presentation_length`.
- Early engagement: `clicks_first_4w`, `active_days_first_4w`, `clicks_pre_start`.
- **Deliberately excluded** (would leak the outcome): total clicks, average assessment
  score, assessments submitted, unregistration date, final result.

## Model
Random Forest (300 trees, `class_weight="balanced"`, fixed seed = 42) in a scikit-learn
pipeline (one-hot categoricals, median-imputed numerics). Deterministic.

## Performance (2014 test cohort)
- ROC-AUC **0.79**, PR-AUC **0.84** (test base rate ~54%), Brier **0.18**.
- Operating point chosen for ~70% recall: **recall 0.70, precision 0.75** at threshold ≈ 0.49.
- Top drivers: first-4-week clicks and active days, region, pre-start clicks, deprivation band.

## Fairness
Flag rate and recall are reported per group (`gender`, `disability`, `age_band`,
`imd_band`) in the dashboard. Review disparities before any deployment; `imd_band` has
~3.4% missing values (reported, not imputed in descriptive views).

## Limitations
- OULAD is 2013–2014 Open University data — a proxy, not the target organisation's.
- Engagement is VLE clicks only; no content quality or off-platform learning.
- A flag is a prompt for support, **not** a judgement about a learner; precision < 1 means
  some flagged learners would have passed anyway.

## Reproducibility
`python scripts/train_model.py` rebuilds all artifacts deterministically from the warehouse.
