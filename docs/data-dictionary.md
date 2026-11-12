# Data dictionary and metric definitions

TandemDesk is a fictional team task-management SaaS. The bundled extract contains signups from **January 6 through July 6, 2025 UTC**. The observation cutoff is **July 7, 2025 at 00:00 UTC**, exclusive. No customer records, personal identifiers or production data were used. `data/manifest.json` records the seed, date bounds and row counts.

## Tables

| File and grain | Field | Definition |
| --- | --- | --- |
| `workspaces.csv` · one row per workspace | `workspace_id` | Synthetic string key, unique in this table |
| | `signup_ts` | Workspace creation time in Unix seconds UTC |
| | `channel` | Synthetic first-touch channel at signup. Organic, Paid search, Referral or Partner |
| | `team_size` | Size band at signup. 2–5, 6–15 or 16+ people |
| `events.csv.gz` · one row per event | `event_id` | Unique synthetic integer key. Used for deduplication |
| | `workspace_id` | Foreign key to workspaces |
| | `event_ts` | Occurrence time in Unix seconds UTC |
| | `event_name` | Event from the taxonomy below |
| | `actor_role` | Owner, teammate or billing, stored in lowercase |
| | `amount_cents` | Positive integer USD cents for a paid invoice. Blank for other events |

| Event | Meaning |
| --- | --- |
| `workspace_created` | Owner registers the workspace |
| `project_created` | Owner creates the initial project |
| `teammate_invited` | Owner submits a teammate invite. Delivery and acceptance are outside the extract |
| `collaborative_action` | A teammate performs an action on shared work. In this simulation it is the first such action |
| `task_completed` | Owner or teammate completes a task. A workspace may log several in one week |
| `invoice_paid` | Simulated successful payment from the billing service |

## Metric rules

All metrics count distinct **workspaces** unless the metric is a sum of cash. Use half-open windows measured from the precise signup timestamp. A workspace is eligible when the entire window ends at or before the cutoff.

| Metric | Numerator | Denominator |
| --- | --- | --- |
| Workspace signups | Workspaces created in the selected signup cohorts | Count |
| Day 7 activation | Workspace created → project created → teammate invited → collaborative action, each later than the previous event, within age `[0, 7 days)` | Workspaces with 7 days of follow-up |
| Funnel step rate | Workspaces reaching this step | Workspaces reaching the previous step, or eligible signups for the first step |
| Week 4 retention | At least one task completion or collaborative action during age `[28, 35 days)` | Workspaces with 35 days of follow-up |
| Signup-cohort retention | At least one qualifying event during age `[7w, 7(w+1) days)` | All members of the selected Monday UTC signup week, after the final possible signup in that week matures |
| Day 30 paid conversion | At least one invoice paid in age `[0, 30 days)` | Workspaces with 30 days of follow-up |
| Day 30 cash per signup | Sum of first-30-day paid invoice cents divided by 100 | Workspaces with 30 days of follow-up |

A later retry can satisfy a missing funnel step. Same-second timestamps cannot establish order. Qualifying retention events are counted once per workspace and age week, and return usage need not be continuous across weeks. For the KPI and segments, eligibility is assessed workspace by workspace. The heatmap waits for the entire signup week, so its eligible population can be smaller. An immature cell is blank. An observed cell with no return usage is 0%. Segment rates are recomputed from their counts. Paid invoices measure collections for the initial window. Refunds, credits, failed payments, costs and subscription balances are outside the extract, so cash per signup supports an early monetization comparison only.

## How the data is simulated

Run `python -m growth.generate` with Python 3.12. The default seed is 1729. Read `growth/generate.py` for the complete probabilities and event timing rules.

1. Generate 26 Monday-based signup weeks with growing volume and random weekly variation. The channel mix shifts toward paid search midway through the period. Team size is sampled at signup.
2. Assign unobserved intent. Referral and larger workspaces have higher probabilities of high intent. Intent changes the odds of project creation, inviting and collaboration. Timing can push otherwise successful steps beyond day 7.
3. Simulate repeat task completion with declining activity as workspaces age. Both intent and early collaboration affect that activity. The activation–retention association is partly built into the simulation.
4. Simulate an initial paid invoice at a team-size-specific USD price, with possible renewal invoices 30 days apart. Stop recording events at the cutoff.

The event stream models a narrow happy path plus drop-off. It has no personal identities, invite deliverability logs, acquisition costs, feature releases, late-arriving records or actual experiment assignment. Use it to inspect measurement and decision logic. Live impact and causal effects would require real instrumentation and an experiment.
