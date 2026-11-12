"""Build workspace outcomes from raw events and aggregate eligible denominators."""

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt

from growth.model import DAY, WEEK, STAGES, USAGE, date_label, week_start


@dataclass(frozen=True)
class WorkspaceOutcome:
    workspace_id: str
    signup_ts: int
    channel: str
    team_size: str
    cohort_ts: int
    funnel_depth: int
    first_project_ts: int | None
    active_weeks: frozenset[int]
    paid_d30: bool
    cash_d30_cents: int


def workspace_outcomes(workspaces, events, cutoff):
    timelines = defaultdict(list)
    for event in events:
        if event["event_ts"] < cutoff:
            timelines[event["workspace_id"]].append(event)

    outcomes = []
    for workspace in workspaces:
        signup = workspace["signup_ts"]
        if signup >= cutoff:
            continue
        depth, previous = 0, signup - 1
        project = None
        active_weeks = set()
        cash = 0
        timeline = sorted(timelines[workspace["workspace_id"]], key=lambda event: event["event_ts"])
        for event in timeline:
            when, name = event["event_ts"], event["event_name"]
            age = when - signup
            if age < 0:
                continue
            if name == "project_created" and project is None:
                project = when
            if depth < len(STAGES) and name == STAGES[depth] and previous < when < signup + WEEK:
                depth += 1
                previous = when
            if name in USAGE:
                active_weeks.add(age // WEEK)
            if name == "invoice_paid" and age < 30 * DAY:
                cash += event["amount_cents"]
        outcomes.append(WorkspaceOutcome(
            workspace["workspace_id"], signup, workspace["channel"], workspace["team_size"],
            week_start(signup), depth, project, frozenset(active_weeks), cash > 0, cash,
        ))
    return outcomes


def rate(numerator, denominator):
    return numerator / denominator if denominator else None


def summary(rows, cutoff):
    d7 = [row for row in rows if row.signup_ts + WEEK <= cutoff]
    w4 = [row for row in rows if row.signup_ts + 5 * WEEK <= cutoff]
    d30 = [row for row in rows if row.signup_ts + 30 * DAY <= cutoff]
    activated = sum(row.funnel_depth == len(STAGES) for row in d7)
    retained = sum(4 in row.active_weeks for row in w4)
    paid = sum(row.paid_d30 for row in d30)
    cash = sum(row.cash_d30_cents for row in d30)
    return {
        "signups": len(rows),
        "d7_eligible": len(d7), "activated": activated, "activation_rate": rate(activated, len(d7)),
        "w4_eligible": len(w4), "retained_w4": retained, "w4_rate": rate(retained, len(w4)),
        "d30_eligible": len(d30), "paid_d30": paid, "paid_rate": rate(paid, len(d30)),
        "cash_d30_cents": cash, "cash_per_signup": rate(cash / 100, len(d30)),
    }


def funnel(rows, cutoff):
    eligible = [row for row in rows if row.signup_ts + WEEK <= cutoff]
    results = []
    previous = len(eligible)
    for depth, stage in enumerate(STAGES, start=1):
        reached = sum(row.funnel_depth >= depth for row in eligible)
        results.append({
            "stage": stage, "reached": reached, "eligible": len(eligible),
            "share": rate(reached, len(eligible)), "step_rate": rate(reached, previous),
            "lost": previous - reached,
        })
        previous = reached
    return results


def cohorts(rows, cutoff, max_age=8):
    groups = defaultdict(list)
    for row in rows:
        groups[row.cohort_ts].append(row)
    results = []
    for cohort, members in sorted(groups.items()):
        for age in range(1, max_age + 1):
            # Publish a cell only after the entire UTC signup week has matured.
            mature = cohort + (age + 2) * WEEK <= cutoff
            retained = sum(age in row.active_weeks for row in members) if mature else None
            results.append({
                "cohort": date_label(cohort), "age_week": age, "cohort_size": len(members),
                "eligible": len(members) if mature else 0,
                "retained": retained, "retention_rate": rate(retained, len(members)) if mature else None,
            })
    return results


def segment(rows, cutoff, dimension):
    if dimension not in {"channel", "team_size"}:
        raise ValueError("Segment by channel or team size")
    groups = defaultdict(list)
    for row in rows:
        groups[getattr(row, dimension)].append(row)
    return [{"segment": name, **summary(members, cutoff)} for name, members in sorted(groups.items())]


def wilson(successes, total, z=1.959963984540054):
    if not total:
        return None, None
    proportion = successes / total
    scale = 1 + z**2 / total
    center = (proportion + z**2 / (2 * total)) / scale
    radius = z * sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2)) / scale
    return max(0.0, center - radius), min(1.0, center + radius)


def activation_diagnostic(rows, cutoff):
    mature = [row for row in rows if row.signup_ts + 5 * WEEK <= cutoff]
    results = []
    for activated in (True, False):
        members = [row for row in mature if (row.funnel_depth == len(STAGES)) == activated]
        retained = sum(4 in row.active_weeks for row in members)
        lower, upper = wilson(retained, len(members))
        results.append({
            "group": "Activated by day 7" if activated else "Other workspaces",
            "eligible": len(members), "retained": retained, "w4_rate": rate(retained, len(members)),
            "lower_95": lower, "upper_95": upper,
        })
    return results
