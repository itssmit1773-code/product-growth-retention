# The teammate invite gap at TandemDesk

TandemDesk is a fictional SaaS product for coordinating team tasks. The growth team has one onboarding change to investigate. I built a workspace-level measurement workflow to locate the largest drop-off, check whether first-week collaboration lines up with later use, and estimate how long an experiment would take.

## Finding the drop-off

The analysis follows 4,532 workspaces through 46,002 simulated events. Of the 4,317 workspaces with a full seven-day window, 3,374 created a project and 1,919 then invited a teammate in the required order. **The invite step lost 1,455 project creators, or 43.1% of the workspaces that reached the previous step.** It was the largest loss in the funnel. The final collaborative action was completed by 1,365 workspaces, giving a day-7 activation rate of **31.6%**.

The event stream records invite submission. It provides no evidence about whether owners had teammates ready, saw the entry point, or received a delivery error. The observed loss is enough to put the invite step first in the investigation. Interviews and instrumented invite events would help narrow the cause.

## Checking what happens later

Among workspaces with 35 days of follow-up, **45.8%** of early activators returned in week 4 (501 / 1,095, Wilson 95% interval 42.8%–48.7%), compared with **17.8%** of the remaining workspaces (417 / 2,349, 16.3%–19.3%). Both groups used the same observation window. Latent intent and activity probabilities are built into the simulation. The 28.0-point gap is an association and should stay out of the forecast for an invite prompt.

Channel mix also matters when reading an aggregate. Paid-search workspaces activated at **26.5%** (407 / 1,534), compared with **39.4%** for referral workspaces (309 / 785). The simulation assigns different intent distributions to these channels. The gap shows why a growth team should inspect the signup mix before interpreting topline movement. It provides no basis for changing acquisition spend.

Overall, **26.7%** returned in week 4 (918 / 3,444) and **11.4%** paid within 30 days (411 / 3,602). Those day-30-eligible workspaces produced **$19,029** in simulated collections, or **$5.28 per eligible signup**. The three rates use different denominators because the required follow-up periods differ.

## Making the next decision

The proposed test adds an inline teammate invitation prompt immediately after the first project is created. The eligible historical baseline is **38.7%** (381 / 985), higher than the all-signup activation rate because eligibility requires creating a project within three days. A five-percentage-point detectable lift requires **1,520 workspaces per arm** under the stated power assumptions. At simulated traffic, this is **19 weeks of enrollment plus up to five weeks of follow-up**.

The next decision is whether actual traffic and the value of the change justify that commitment. Start by validating invite instrumentation, confirming real eligible traffic, and watching a few owners create their first project. If the opportunity holds, run a workspace-randomized test and check week-4 retention and invite delivery alongside activation. The experiment is a proposal. All measured results in this case come from simulated activity.

## What to show in an interview

Start with the gap after project creation. Explain why a signup from yesterday should stay out of a seven-day activation rate and why a workspace with five task completions counts once in retention. Then explain the difference between the observed 28-point retention gap and the five-point effect the proposed experiment is designed to detect. The two numbers answer different questions.

[Metric definitions](data-dictionary.md) · [Experiment protocol](experiment.md) · [Business requirements](business-requirements.md) · [Reproducible output](../results/summary.json)
