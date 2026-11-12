-- SQLite. Input tables and cutoff are loaded by growth/warehouse.py.
-- Find the earliest valid timestamp at each step so retries can qualify.
CREATE VIEW workspace_outcomes AS
WITH started AS (
    SELECT w.*,
           date(w.signup_ts, 'unixepoch', '-6 days', 'weekday 1') AS cohort,
           c.cutoff_ts,
           (SELECT MIN(e.event_ts) FROM events e
            WHERE e.workspace_id = w.workspace_id AND e.event_name = 'workspace_created'
              AND e.event_ts >= w.signup_ts AND e.event_ts < MIN(c.cutoff_ts, w.signup_ts + 604800)
           ) AS created_ts,
           (SELECT MIN(e.event_ts) FROM events e
            WHERE e.workspace_id = w.workspace_id AND e.event_name = 'project_created'
              AND e.event_ts >= w.signup_ts AND e.event_ts < c.cutoff_ts
           ) AS first_project_ts
    FROM workspaces w CROSS JOIN observation c
    WHERE w.signup_ts < c.cutoff_ts
),
projects AS (
    SELECT s.*, (
        SELECT MIN(e.event_ts) FROM events e
        WHERE e.workspace_id = s.workspace_id AND e.event_name = 'project_created'
          AND e.event_ts > s.created_ts AND e.event_ts < MIN(s.cutoff_ts, s.signup_ts + 604800)
    ) AS project_ts FROM started s
),
invites AS (
    SELECT p.*, (
        SELECT MIN(e.event_ts) FROM events e
        WHERE e.workspace_id = p.workspace_id AND e.event_name = 'teammate_invited'
          AND e.event_ts > p.project_ts AND e.event_ts < MIN(p.cutoff_ts, p.signup_ts + 604800)
    ) AS invite_ts FROM projects p
)
SELECT i.*,
       CASE WHEN EXISTS (
           SELECT 1 FROM events e
           WHERE e.workspace_id = i.workspace_id AND e.event_name = 'collaborative_action'
             AND e.event_ts > i.invite_ts AND e.event_ts < MIN(i.cutoff_ts, i.signup_ts + 604800)
       ) THEN 4
       WHEN i.invite_ts IS NOT NULL THEN 3
       WHEN i.project_ts IS NOT NULL THEN 2
       WHEN i.created_ts IS NOT NULL THEN 1 ELSE 0 END AS funnel_depth,
       EXISTS (
           SELECT 1 FROM events e
           WHERE e.workspace_id = i.workspace_id
             AND e.event_name IN ('task_completed', 'collaborative_action')
             AND e.event_ts >= i.signup_ts + 2419200
             AND e.event_ts < MIN(i.cutoff_ts, i.signup_ts + 3024000)
       ) AS retained_w4,
       COALESCE((
           SELECT SUM(e.amount_cents) FROM events e
           WHERE e.workspace_id = i.workspace_id AND e.event_name = 'invoice_paid'
             AND e.event_ts >= i.signup_ts AND e.event_ts < MIN(i.cutoff_ts, i.signup_ts + 2592000)
       ), 0) AS cash_d30_cents
FROM invites i;
