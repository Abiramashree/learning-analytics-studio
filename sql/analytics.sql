-- analytics.sql — deeper governed KPI views for the Students, Engagement, and
-- Content & Effectiveness deep-dives. All deterministic aggregates over the marts.

-- Learner progression funnel: registered -> started -> engaged -> assessed -> passed.
CREATE OR REPLACE VIEW kpi_funnel AS
SELECT 1 AS ord, 'Registered' AS stage, count(*) AS learners FROM mart_student
UNION ALL
SELECT 2, 'Started (no early withdrawal)', count(*) FROM mart_student
       WHERE NOT (date_unregistration IS NOT NULL AND date_unregistration < 0)
UNION ALL
SELECT 3, 'Engaged (any activity)', count(*) FROM mart_student WHERE total_clicks > 0
UNION ALL
SELECT 4, 'Submitted an assessment', count(*) FROM mart_student WHERE n_assessments_submitted > 0
UNION ALL
SELECT 5, 'Passed', count(*) FROM mart_student WHERE passed;

-- Registration lead time: how early learners enrol, and whether it tracks success.
CREATE OR REPLACE VIEW kpi_registration_timing AS
SELECT ord, bucket,
       count(*)                      AS enrolments,
       round(avg(passed::INT), 4)    AS pass_rate,
       round(avg(withdrawn::INT), 4) AS withdrawal_rate
FROM (
    SELECT passed, withdrawn,
           CASE
             WHEN date_registration IS NULL        THEN 5
             WHEN date_registration <= -60         THEN 1
             WHEN date_registration <= -30         THEN 2
             WHEN date_registration <  0           THEN 3
             ELSE 4
           END AS ord,
           CASE
             WHEN date_registration IS NULL        THEN 'Unknown'
             WHEN date_registration <= -60         THEN '60+ days before'
             WHEN date_registration <= -30         THEN '30–59 days before'
             WHEN date_registration <  0           THEN '1–29 days before'
             ELSE 'On/after start'
           END AS bucket
    FROM mart_student
) t
GROUP BY ord, bucket
ORDER BY ord;

-- Engagement dose-response: decile of first-4-week clicks -> outcomes & score.
CREATE OR REPLACE VIEW kpi_engagement_dose AS
WITH d AS (
    SELECT passed, withdrawn, avg_score, clicks_first_4w,
           ntile(10) OVER (ORDER BY clicks_first_4w) AS decile
    FROM mart_student
)
SELECT decile,
       count(*)                       AS enrolments,
       min(clicks_first_4w)           AS min_clicks,
       max(clicks_first_4w)           AS max_clicks,
       round(avg(passed::INT), 4)     AS pass_rate,
       round(avg(withdrawn::INT), 4)  AS withdrawal_rate,
       round(avg(avg_score), 1)       AS avg_score
FROM d
GROUP BY decile
ORDER BY decile;

-- Assessment score distribution by assessment type (box-plot inputs).
CREATE OR REPLACE VIEW kpi_assessment_by_type AS
SELECT a.assessment_type,
       count(*)                                  AS n_submissions,
       round(avg(sa.score), 1)                   AS mean_score,
       quantile_cont(sa.score, 0.05)             AS p05,
       quantile_cont(sa.score, 0.25)             AS p25,
       quantile_cont(sa.score, 0.50)             AS p50,
       quantile_cont(sa.score, 0.75)             AS p75,
       quantile_cont(sa.score, 0.95)             AS p95
FROM studentAssessment sa
JOIN assessments a USING (id_assessment)
WHERE sa.score IS NOT NULL
GROUP BY a.assessment_type
ORDER BY n_submissions DESC;

-- Average assessment score per course (training effectiveness by presentation).
CREATE OR REPLACE VIEW kpi_assessment_by_course AS
SELECT a.code_module, a.code_presentation,
       count(*)                 AS n_submissions,
       round(avg(sa.score), 1)  AS avg_score
FROM studentAssessment sa
JOIN assessments a USING (id_assessment)
WHERE sa.score IS NOT NULL
GROUP BY 1, 2
ORDER BY avg_score DESC;

-- Submission timing: do learners submit before the due date, and does it pay off?
CREATE OR REPLACE VIEW kpi_submission_timing AS
SELECT ord, timing,
       count(*)                AS n_submissions,
       round(avg(sa.score), 1) AS avg_score
FROM (
    SELECT sa.score, a.date AS due, sa.date_submitted,
           CASE
             WHEN sa.date_submitted <  a.date - 7 THEN 1
             WHEN sa.date_submitted <  a.date     THEN 2
             WHEN sa.date_submitted =  a.date     THEN 3
             ELSE 4
           END AS ord,
           CASE
             WHEN sa.date_submitted <  a.date - 7 THEN 'Early (8+ days)'
             WHEN sa.date_submitted <  a.date     THEN 'Early (1–7 days)'
             WHEN sa.date_submitted =  a.date     THEN 'On the due date'
             ELSE 'Late'
           END AS timing
    FROM studentAssessment sa
    JOIN assessments a USING (id_assessment)
    WHERE sa.score IS NOT NULL AND a.date IS NOT NULL
) sa
GROUP BY ord, timing
ORDER BY ord;
