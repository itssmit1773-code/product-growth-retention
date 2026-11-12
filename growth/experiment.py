"""Planning calculations for a future two-arm workspace-randomized experiment."""

from math import ceil, sqrt
from statistics import NormalDist

from growth.model import DAY, STAGES, WEEK


def planning_baseline(rows, cutoff):
    # Use six complete, D7-observable signup cohorts for a recent traffic estimate.
    anchor = cutoff - WEEK
    population = [row for row in rows if anchor - 6 * WEEK <= row.cohort_ts < anchor]
    eligible = [
        row for row in population
        if row.first_project_ts is not None and row.first_project_ts < row.signup_ts + 3 * DAY
    ]
    activated = sum(row.funnel_depth == len(STAGES) for row in eligible)
    return {
        "eligible": len(eligible),
        "activated": activated,
        "baseline": activated / len(eligible) if eligible else None,
        "per_week": len(eligible) / 6,
    }


def sample_per_arm(baseline, mde, alpha=0.05, power=0.80):
    treatment = baseline + mde
    if not (0 < baseline < treatment < 1 and 0 < alpha < 1 and 0.5 < power < 1):
        raise ValueError("Enter valid proportions, positive lift, and power above 50%.")
    pooled = (baseline + treatment) / 2
    normal = NormalDist()
    null_term = normal.inv_cdf(1 - alpha / 2) * sqrt(2 * pooled * (1 - pooled))
    alternative_term = normal.inv_cdf(power) * sqrt(
        baseline * (1 - baseline) + treatment * (1 - treatment)
    )
    return ceil(((null_term + alternative_term) / mde) ** 2)


def enrollment_weeks(per_arm, eligible_per_week):
    if per_arm <= 0 or eligible_per_week <= 0:
        raise ValueError("Sample size and weekly traffic must be positive.")
    return ceil(2 * per_arm / eligible_per_week)
