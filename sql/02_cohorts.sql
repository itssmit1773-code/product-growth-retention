WITH RECURSIVE ages(age_week) AS (
    VALUES (1) UNION ALL SELECT age_week + 1 FROM ages WHERE age_week < 8
), cells AS (
    SELECT w.cohort, a.age_week, COUNT(*) AS cohort_size,
           unixepoch(w.cohort) + (a.age_week + 2) * 604800 <= w.cutoff_ts AS mature,
           SUM(EXISTS (
               SELECT 1 FROM events e
               WHERE e.workspace_id = w.workspace_id
                 AND e.event_name IN ('task_completed', 'collaborative_action')
                 AND e.event_ts >= w.signup_ts + a.age_week * 604800
                 AND e.event_ts < MIN(w.cutoff_ts, w.signup_ts + (a.age_week + 1) * 604800)
           )) AS observed
    FROM workspace_outcomes w CROSS JOIN ages a
    GROUP BY w.cohort, a.age_week, w.cutoff_ts
)
SELECT cohort, age_week, cohort_size,
       CASE WHEN mature THEN cohort_size ELSE 0 END AS eligible,
       CASE WHEN mature THEN observed END AS retained,
       CASE WHEN mature THEN 1.0 * observed / cohort_size END AS retention_rate
FROM cells ORDER BY cohort, age_week;
