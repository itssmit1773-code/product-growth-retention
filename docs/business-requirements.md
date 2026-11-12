# Business requirements

**Decision owner** · Growth product manager  
**Reviewers** · Product analytics, onboarding engineering and messaging operations  
**Decision** · Choose which onboarding step to investigate and determine whether a teammate invitation experiment is feasible.

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| BR-01 | Quantify onboarding friction at workspace level | Show ordered day-7 step counts, overall and conditional conversion, and count lost at each step. Use the same eligible population across all steps. |
| BR-02 | Compare repeat usage across signup weeks | Show weeks 1–8 since signup, label the qualifying events, and leave immature cells blank. Show week-4 retention by day-7 activation with eligible counts. |
| BR-03 | Find differences across acquisition channels and team sizes | Support channel, team size and signup-week filters. Show activation, retention, day-30 paid conversion and cash per signup with aligned denominators. |
| BR-04 | Make the evidence reviewable | Bundle the source and generator, document the metric rules, export filtered tables, and reconcile Python and SQLite results. |
| BR-05 | Decide whether a prompt test is feasible | Document assignment, measurement, instrumentation, guardrails and decision rules. Show sensitivity to effect size and traffic allocation. |
| BR-06 | Enable a local review without paid services | Run from a clean Python 3.12 environment with published dependencies and the bundled dataset. Include a start guide and automated checks. |

**Scope** · Initial workspace onboarding, repeat product activity, first-30-day cash collections and experiment planning. Production telemetry integration, prompt implementation, live assignment and experiment execution are separate delivery work.

**Handoff** · The growth PM owns the product decision. Analytics validates eligible traffic and baseline metrics. Engineering checks assignment, event delivery and identity joins. Messaging owns delivery-quality thresholds and the incident response for invite traffic.
