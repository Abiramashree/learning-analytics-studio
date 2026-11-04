-- metrics.sql — documented KPI views over the marts. These are the governed,
-- reusable definitions behind the dashboards (the "source of truth").

-- Overall outcome rates across all enrolments.
CREATE OR REPLACE VIEW kpi_overall AS
SELECT count(*)                                   AS enrolments,
       round(avg(passed::INT), 4)                 AS pass_rate,
       round(avg(withdrawn::INT), 4)              AS withdrawal_rate,
       round(avg(failed::INT), 4)                 AS fail_rate,
       round(avg((final_result = 'Distinction')::INT), 4) AS distinction_rate
FROM mart_student;

-- Outcome rates per course (module x presentation).
CREATE OR REPLACE VIEW kpi_outcomes_by_course AS
SELECT code_module, code_presentation,
       count(*)                      AS enrolments,
       round(avg(passed::INT), 4)    AS pass_rate,
       round(avg(withdrawn::INT), 4) AS withdrawal_rate,
       round(avg(failed::INT), 4)    AS fail_rate
FROM mart_student
GROUP BY 1, 2
ORDER BY enrolments DESC;

-- Engagement by outcome: the core "does engagement track success?" signal.
CREATE OR REPLACE VIEW kpi_engagement_by_outcome AS
SELECT final_result,
       count(*)                          AS enrolments,
       round(avg(total_clicks), 1)       AS avg_total_clicks,
       round(avg(clicks_first_4w), 1)    AS avg_clicks_first_4w,
       round(avg(active_days), 1)        AS avg_active_days,
       round(avg(avg_score), 1)          AS avg_assessment_score
FROM mart_student
GROUP BY 1
ORDER BY avg_clicks_first_4w DESC;

-- Pass rate by learner segment (reusable; swap the dimension in the WHERE/GROUP).
CREATE OR REPLACE VIEW kpi_pass_rate_by_segment AS
SELECT 'age_band' AS dimension, age_band AS value,
       count(*) AS enrolments, round(avg(passed::INT), 4) AS pass_rate,
       round(avg(withdrawn::INT), 4) AS withdrawal_rate
FROM mart_student GROUP BY age_band
UNION ALL
SELECT 'imd_band', imd_band, count(*), round(avg(passed::INT), 4), round(avg(withdrawn::INT), 4)
FROM mart_student GROUP BY imd_band
UNION ALL
SELECT 'highest_education', highest_education, count(*), round(avg(passed::INT), 4), round(avg(withdrawn::INT), 4)
FROM mart_student GROUP BY highest_education
UNION ALL
SELECT 'disability', disability, count(*), round(avg(passed::INT), 4), round(avg(withdrawn::INT), 4)
FROM mart_student GROUP BY disability
UNION ALL
SELECT 'gender', gender, count(*), round(avg(passed::INT), 4), round(avg(withdrawn::INT), 4)
FROM mart_student GROUP BY gender
UNION ALL
SELECT 'region', region, count(*), round(avg(passed::INT), 4), round(avg(withdrawn::INT), 4)
FROM mart_student GROUP BY region;

-- Content performance by activity type (share of total engagement).
CREATE OR REPLACE VIEW kpi_content_performance AS
SELECT activity_type, interactions, total_clicks, distinct_students,
       round(100.0 * total_clicks / sum(total_clicks) OVER (), 1) AS pct_of_clicks
FROM mart_content
ORDER BY total_clicks DESC;
