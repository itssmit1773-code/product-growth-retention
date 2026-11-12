# Teammate invitation prompt

**Status** · Proposed experiment. All planning inputs are synthetic.

## Hypothesis and experience

An invite prompt at the end of first-project creation may help an owner bring a teammate into the workspace while they are setting up work. The control keeps the existing project confirmation and invite entry point. The treatment adds a dismissible inline prompt with one action that opens the existing invite flow. No automatic emails or changes to recipient permissions.

## Eligibility, assignment and instrumentation

Enroll new workspaces immediately after the owner creates their first project within 72 hours of signup, before displaying the confirmation. Exclude internal and test workspaces using pre-assignment flags. Assign workspaces 1:1 with a persisted, server-side assignment keyed by workspace ID. Analyze all assigned eligible workspaces in their original arm, including workspaces where the prompt fails to render. Record eligibility time, assignment and variant, prompt render and dismissal, and invite submission with workspace ID, experiment ID and UTC event time. Join outcomes by workspace ID and deduplicate events by event ID.

Repeated owners or shared teammates can expose a person to both arms. Before launch, audit cross-workspace membership in real logs. If overlap is material, use owner-level assignment or clustering and redo the power analysis. The synthetic extract omits person IDs.

## Outcomes and decision

| Role | Measure | Decision use |
| --- | --- | --- |
| Primary | Day 7 activation per assigned workspace, with the same ordered funnel and deadline as the dashboard | Report treatment minus control in percentage points and a two-sided 95% score interval for the difference. Use a two-proportion test at 5%. |
| Diagnostic | Day 7 invite completion per assigned workspace | Check whether the prompt changes the intended behavior. Treat it as descriptive. |
| Retention guardrail | Week 4 return usage per assigned workspace | Require the lower 95% confidence limit on treatment minus control to exceed −5 percentage points. |
| Operational guardrail | Invite delivery failure per assigned workspace | Have Messaging define an acceptable margin from production telemetry before enrollment. Pause for incidents under the existing incident process. |
| Secondary | Day 30 paid conversion and cash per signup per assigned workspace | Report descriptively after maturation. |

Before launch, run a short A/A or shadow assignment to validate exposure logging, identity joins and daily volumes. Check sample-ratio mismatch against 50/50 using a chi-square test at p < 0.001 and investigate before interpreting results. Freeze definitions, sample size and exclusions. Review data quality and incidents during enrollment. Make the efficacy decision after the target is reached and 35 days have elapsed since the last signup in the experiment. A positive primary result with an estimated improvement of at least 5 points and passing guardrails supports rollout. If the primary result is positive but below 5 points, use the observed interval and implementation cost to decide whether a follow-up is worthwhile. An inconclusive or failed guardrail calls for further investigation before rollout.

## Feasibility

Among 985 eligible workspaces in the six signup weeks from May 19 through June 29, 2025, 381 activated by day 7 (38.7%). With a 5-point minimum detectable effect, two-sided 5% significance, 80% power and equal allocation, the normal approximation gives **1,520 workspaces per arm**. At about 164 eligible workspaces a week, allow **19 enrollment weeks plus up to 5 weeks of follow-up**. At 50% traffic, enrollment rises to 38 weeks. Traffic stability, independent workspaces and clean assignment are planning assumptions. Power targets the primary significance test at the specified alternative. The rollout rule also includes a practical threshold and guardrails, so its probability of passing differs from 80%.

Validate real eligible volume, baseline and business value before committing to a test of this length. A short instrumentation check can establish feasibility while Product validates the prompt with owners. Recalculate sample size and guardrail precision using real baselines before launch.

The calculator uses the usual equal-allocation normal approximation. For baseline p₀, treatment p₁, pooled midpoint p̄ and lift δ, the per-arm target is the ceiling of [z(1−α/2)√(2p̄(1−p̄)) + z(power)√(p₀(1−p₀)+p₁(1−p₁))]² / δ².
