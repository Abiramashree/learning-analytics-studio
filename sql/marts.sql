-- marts.sql — analytical base tables built from the raw OULAD tables.
-- Dates are relative to course start (day 0); negative = before the course began.
-- "First 4 weeks" = days 0..27 (early-warning window).

-- Grain: one row per learner enrolment (student x module x presentation).
CREATE OR REPLACE TABLE mart_student AS
WITH vle_agg AS (
    SELECT id_student, code_module, code_presentation,
           sum(sum_click)                                              AS total_clicks,
           count(DISTINCT date)                                        AS active_days,
           sum(CASE WHEN date BETWEEN 0 AND 27 THEN sum_click ELSE 0 END) AS clicks_first_4w,
           sum(CASE WHEN date < 0 THEN sum_click ELSE 0 END)           AS clicks_pre_start,
           count(DISTINCT CASE WHEN date BETWEEN 0 AND 27 THEN date END) AS active_days_first_4w
    FROM studentVle
    GROUP BY 1, 2, 3
),
asmt AS (
    SELECT sa.id_student, a.code_module, a.code_presentation,
           count(*)                                        AS n_assessments_submitted,
           avg(sa.score)                                   AS avg_score,
           min(a.date) FILTER (WHERE sa.score IS NOT NULL) AS first_assessment_date
    FROM studentAssessment sa
    JOIN assessments a USING (id_assessment)
    GROUP BY 1, 2, 3
)
SELECT s.id_student, s.code_module, s.code_presentation,
       s.gender, s.region, s.highest_education, s.imd_band, s.age_band,
       s.num_of_prev_attempts, s.studied_credits, s.disability,
       s.final_result,
       (s.final_result IN ('Pass', 'Distinction')) AS passed,
       (s.final_result = 'Withdrawn')              AS withdrawn,
       (s.final_result = 'Fail')                   AS failed,
       r.date_registration, r.date_unregistration,
       c.module_presentation_length,
       COALESCE(v.total_clicks, 0)          AS total_clicks,
       COALESCE(v.active_days, 0)           AS active_days,
       COALESCE(v.clicks_first_4w, 0)       AS clicks_first_4w,
       COALESCE(v.clicks_pre_start, 0)      AS clicks_pre_start,
       COALESCE(v.active_days_first_4w, 0)  AS active_days_first_4w,
       COALESCE(am.n_assessments_submitted, 0) AS n_assessments_submitted,
       am.avg_score
FROM studentInfo s
LEFT JOIN studentRegistration r USING (id_student, code_module, code_presentation)
LEFT JOIN courses c            USING (code_module, code_presentation)
LEFT JOIN vle_agg v            USING (id_student, code_module, code_presentation)
LEFT JOIN asmt am              USING (id_student, code_module, code_presentation);

-- Grain: learner x relative week -> clicks (engagement timeline).
CREATE OR REPLACE TABLE mart_engagement_weekly AS
SELECT code_module, code_presentation, id_student,
       CAST(floor(date / 7.0) AS INTEGER) AS rel_week,
       sum(sum_click)                     AS clicks
FROM studentVle
GROUP BY 1, 2, 3, 4;

-- Grain: content activity type -> engagement (content performance).
CREATE OR REPLACE TABLE mart_content AS
SELECT vl.activity_type,
       count(*)                   AS interactions,
       sum(v.sum_click)           AS total_clicks,
       count(DISTINCT v.id_student) AS distinct_students
FROM studentVle v
JOIN vle vl USING (id_site, code_module, code_presentation)
GROUP BY 1
ORDER BY total_clicks DESC;
