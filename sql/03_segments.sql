WITH dimensions AS (
    SELECT 'channel' AS dimension, channel AS segment, * FROM workspace_outcomes
    UNION ALL
    SELECT 'team_size', team_size, * FROM workspace_outcomes
    UNION ALL
    SELECT 'all', 'All', * FROM workspace_outcomes
), counts AS (
    SELECT dimension, segment, COUNT(*) AS signups,
           SUM(signup_ts + 604800 <= cutoff_ts) AS d7_eligible,
           SUM(signup_ts + 604800 <= cutoff_ts AND funnel_depth = 4) AS activated,
           SUM(signup_ts + 3024000 <= cutoff_ts) AS w4_eligible,
           SUM(signup_ts + 3024000 <= cutoff_ts AND retained_w4) AS retained_w4,
           SUM(signup_ts + 2592000 <= cutoff_ts) AS d30_eligible,
           SUM(signup_ts + 2592000 <= cutoff_ts AND cash_d30_cents > 0) AS paid_d30,
           SUM(CASE WHEN signup_ts + 2592000 <= cutoff_ts THEN cash_d30_cents ELSE 0 END) AS cash_d30_cents
    FROM dimensions GROUP BY dimension, segment
)
SELECT *, 1.0 * activated / d7_eligible AS activation_rate,
       1.0 * retained_w4 / w4_eligible AS w4_rate,
       1.0 * paid_d30 / d30_eligible AS paid_rate,
       cash_d30_cents / 100.0 / d30_eligible AS cash_per_signup
FROM counts ORDER BY dimension, segment;
