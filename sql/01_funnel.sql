WITH steps(depth, stage) AS (
    VALUES (1, 'workspace_created'), (2, 'project_created'),
           (3, 'teammate_invited'), (4, 'collaborative_action')
), counts AS (
    SELECT steps.depth, steps.stage, COUNT(w.workspace_id) AS eligible,
           COUNT(CASE WHEN w.funnel_depth >= steps.depth THEN 1 END) AS reached
    FROM steps
    LEFT JOIN workspace_outcomes w ON w.signup_ts + 604800 <= w.cutoff_ts
    GROUP BY steps.depth, steps.stage
), denominators AS (
    SELECT *, LAG(reached, 1, eligible) OVER (ORDER BY depth) AS previous FROM counts
)
SELECT stage, reached, eligible, 1.0 * reached / eligible AS share,
       1.0 * reached / previous AS step_rate, previous - reached AS lost
FROM denominators ORDER BY depth;
