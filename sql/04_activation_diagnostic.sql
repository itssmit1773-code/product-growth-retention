WITH groups(activated) AS (VALUES (1), (0)),
counts AS (
    SELECT g.activated, COUNT(w.workspace_id) AS eligible,
           COALESCE(SUM(w.retained_w4), 0) AS retained
    FROM groups g LEFT JOIN workspace_outcomes w
      ON (w.funnel_depth = 4) = g.activated
      AND w.signup_ts + 3024000 <= w.cutoff_ts
    GROUP BY g.activated
)
SELECT CASE WHEN activated THEN 'Activated by day 7' ELSE 'Other workspaces' END AS "group",
       eligible, retained, 1.0 * retained / eligible AS w4_rate
FROM counts ORDER BY activated DESC;
