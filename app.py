"""Streamlit dashboard for the TandemDesk product growth case."""

import csv
import io
from html import escape
from pathlib import Path

import altair as alt
import streamlit as st

from growth.experiment import enrollment_weeks, planning_baseline, sample_per_arm
from growth.metrics import activation_diagnostic, cohorts, funnel, segment, summary, workspace_outcomes
from growth.model import DATA, STAGES, date_label

st.set_page_config(page_title="TandemDesk | Growth & retention", layout="wide")

GREEN = "#16644e"
INK = "#182c26"
NAMES = dict(zip(STAGES, ("Workspace created", "Project created", "Teammate invited", "Collaborative action")))


@st.cache_data(show_spinner=False)
def load_snapshot(directory, file_signature):
    from growth.model import read_data

    metadata, workspaces, events = read_data(directory)
    return metadata, workspace_outcomes(workspaces, events, metadata["cutoff_ts"])


def percent(value):
    return "—" if value is None else f"{value:.1%}"


def metric(container, title, records, numerator, denominator, rate_key):
    container.metric(title, percent(records[rate_key]),
                     help=f'{records[numerator]:,} of {records[denominator]:,} eligible workspaces')


def download(label, filename, rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    st.download_button(label, buffer.getvalue(), filename, "text/csv")


def chart_view(chart):
    # Keep the small, aggregated datasets inline with their Vega-Lite layers.
    spec = chart.configure_view(stroke=None).to_dict()
    datasets = spec.pop("datasets", {})
    shared_data = spec.pop("data", None)
    for layer in spec["layer"]:
        data = layer.get("data", shared_data)
        layer["data"] = {"values": datasets[data["name"]]} if "name" in data else data
    st.vega_lite_chart(spec=spec, width="stretch")


def table(rows, columns):
    header = "".join(f'<th scope="col">{escape(label)}</th>' for _, label, _ in columns)
    body = []
    for row in rows:
        cells = "".join(f"<td>{escape(formatter(row[key]))}</td>" for key, _, formatter in columns)
        body.append(f"<tr>{cells}</tr>")
    st.html(
        '<style>.growth-table {overflow-x:auto;margin:.3rem 0 .8rem}'
        '.growth-table table {border-collapse:collapse;width:100%;font-size:.89rem}'
        '.growth-table th,.growth-table td {padding:.65rem .8rem;text-align:right;white-space:nowrap;'
        'border-bottom:1px solid #dce5df}.growth-table th {background:#eef3ef}'
        '.growth-table tr > :first-child {text-align:left}</style>'
        '<div class="growth-table" role="region" aria-label="Metric detail" tabindex="0">'
        f'<table><thead><tr>{header}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )


def integer(value):
    return f"{value:,}"


def dollars(value):
    return "—" if value is None else f"${value:,.2f}"


def onboarding(rows, cutoff):
    records = funnel(rows, cutoff)
    if not records[0]["eligible"]:
        st.info("No workspace in this selection has a complete seven-day window.")
        return
    for record in records:
        record["step"] = NAMES[record["stage"]]
    data = alt.InlineData(values=records)
    st.subheader("Seven-day onboarding funnel")
    st.caption("Each step must occur in order. Bars show the share of eligible signups that reached each step.")
    chart = alt.Chart(data).encode(
        x=alt.X("share:Q", title="Share of eligible signups", scale=alt.Scale(domain=[0, 1.12]),
                axis=alt.Axis(format=".0%", values=[0, .25, .5, .75, 1], grid=True)),
        y=alt.Y("step:N", title=None, sort=list(NAMES.values()), axis=alt.Axis(labelLimit=185)),
    )
    bars = chart.mark_bar(size=28, cornerRadiusEnd=4).encode(
        color=alt.condition(alt.datum.stage == "teammate_invited", alt.value("#b35c33"), alt.value(GREEN)),
        tooltip=[
            alt.Tooltip("step:N", title="Step"), alt.Tooltip("reached:Q", title="Reached", format=","),
            alt.Tooltip("share:Q", title="Of eligible signups", format=".1%"),
            alt.Tooltip("step_rate:Q", title="Of previous step", format=".1%"),
            alt.Tooltip("lost:Q", title="Lost at step", format=","),
        ],
    )
    labels = chart.mark_text(align="left", dx=7, color=INK, fontWeight=600).encode(
        text=alt.Text("share:Q", format=".1%")
    )
    chart_view((bars + labels).properties(height=218))
    furthest_loss = max(records, key=lambda record: record["lost"])
    if furthest_loss["lost"]:
        st.write(f'**Largest drop-off:** {furthest_loss["lost"]:,} workspaces before '
                 f'{furthest_loss["step"].lower()}, from the previous funnel step.')
    with st.expander("Funnel counts and step conversion"):
        table(records, [
            ("step", "Step", str), ("reached", "Reached", integer), ("eligible", "Eligible signups", integer),
            ("share", "Of signups", percent), ("step_rate", "Of previous step", percent),
            ("lost", "Lost at step", integer),
        ])
    download("Download funnel data", "funnel.csv", records)


def retention(rows, cutoff):
    st.subheader("Return usage by signup week")
    st.caption("A workspace returns when it completes a task or records a collaborative action during the age week. "
               "Gray cells are still maturing for the full signup cohort.")
    age_limit = st.slider("Weeks since signup", min_value=4, max_value=8, value=8, key="age_limit")
    records = cohorts(rows, cutoff, age_limit)
    for row in records:
        row["cell"] = percent(row["retention_rate"])
        row["observed"] = (
            f'{row["retained"]:,} / {row["eligible"]:,}' if row["eligible"] else "Still maturing"
        )
    data = alt.InlineData(values=records)
    base = alt.Chart(data).encode(
        x=alt.X("age_week:O", title="Age week", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("cohort:O", title="Signup week (UTC)", axis=alt.Axis(labelLimit=110)),
    )
    tiles = base.mark_rect(stroke="#fafbf9", strokeWidth=2, cornerRadius=3).encode(
        color=alt.condition(
            "isValid(datum.retention_rate)",
            alt.Color("retention_rate:Q", title="Retention", scale=alt.Scale(
                domain=[0, 1], range=["#ebf5ee", "#14654f"]), legend=None),
            alt.value("#e5e9e6"),
        ),
        tooltip=[alt.Tooltip("cohort:N", title="Signup week"),
                 alt.Tooltip("age_week:O", title="Age week"),
                 alt.Tooltip("observed:N", title="Returned / eligible"),
                 alt.Tooltip("cell:N", title="Retention")],
    )
    labels = base.mark_text(fontSize=11).encode(
        text="cell:N", color=alt.condition("datum.retention_rate >= 0.62", alt.value("white"), alt.value(INK)),
    )
    cohort_count = len({row["cohort"] for row in records})
    chart_view((tiles + labels).properties(height=max(170, 25 * cohort_count)))
    st.subheader("Week 4 retention by early activation")
    st.caption("The groups have the same 35-day observation requirement. Intervals are 95% Wilson intervals. "
               "This comparison is observational.")
    table(activation_diagnostic(rows, cutoff), [
        ("group", "Group", str), ("eligible", "Eligible", integer), ("retained", "Returned", integer),
        ("w4_rate", "Week 4 retention", percent), ("lower_95", "Lower 95%", percent),
        ("upper_95", "Upper 95%", percent),
    ])
    download("Download cohort data", "cohorts.csv", records)


def segments(rows, cutoff):
    st.subheader("Activation, retention and paid conversion")
    dimension = st.radio("Compare by", ("Acquisition channel", "Team size"), horizontal=True)
    records = segment(rows, cutoff, "channel" if dimension == "Acquisition channel" else "team_size")
    measures = {"activation_rate": "Day 7 activation", "w4_rate": "Week 4 retention", "paid_rate": "Day 30 paid"}
    chart_rows = [
        {"segment": record["segment"], "measure": label, "rate": record[key]}
        for record in records for key, label in measures.items() if record[key] is not None
    ]
    if chart_rows:
        chart = alt.Chart(alt.InlineData(values=chart_rows)).mark_bar(cornerRadiusEnd=3).encode(
            x=alt.X("rate:Q", title="Share of eligible workspaces", axis=alt.Axis(format="%"),
                    scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("segment:N", title=None, sort=[row["segment"] for row in records]),
            yOffset="measure:N",
            color=alt.Color("measure:N", title=None, scale=alt.Scale(
                domain=["Day 7 activation", "Week 4 retention", "Day 30 paid"],
                range=[GREEN, "#b35c33", "#52758b"]), legend=alt.Legend(orient="top")),
            tooltip=[alt.Tooltip("segment:N", title=dimension), alt.Tooltip("measure:N", title="Metric"),
                     alt.Tooltip("rate:Q", title="Rate", format=".1%")],
        )
        chart_view(alt.layer(chart).properties(height=max(160, 64 * len(records))))
    else:
        st.info("The selected workspaces are still maturing for these measures.")
    st.caption("Each rate uses its own eligible population. Cash is collected USD per day-30 eligible signup.")
    table(records, [
        ("segment", dimension, str), ("signups", "Signups", integer),
        ("activation_rate", "Day 7 activation", percent), ("d7_eligible", "Day 7 eligible", integer),
        ("w4_rate", "Week 4 retention", percent), ("w4_eligible", "Week 4 eligible", integer),
        ("paid_rate", "Day 30 paid", percent), ("d30_eligible", "Day 30 eligible", integer),
        ("cash_per_signup", "Cash per signup", dollars),
    ])
    download("Download segment data", "segments.csv", records)


def experiment(all_rows, cutoff):
    st.subheader("Test a teammate invitation prompt")
    st.write("Randomize a workspace when its owner creates the first project in the first three days. "
             "Compare the existing experience with an inline prompt that opens the existing invite flow.")
    st.caption("This calculator uses the six most recent complete day-7 signup cohorts across all channels and sizes. "
               "Dashboard filters leave the planning population fixed.")
    planning = planning_baseline(all_rows, cutoff)
    baseline = planning["baseline"]
    lift = st.slider("Minimum detectable lift (percentage points)", 3, 12, 5, key="mde") / 100
    traffic_share = st.slider("Share of eligible traffic enrolled (%)", 25, 100, 100, step=5, key="traffic") / 100
    per_arm = sample_per_arm(baseline, lift)
    weeks = enrollment_weeks(per_arm, planning["per_week"] * traffic_share)
    cols = st.columns(3)
    cols[0].metric("Baseline activation", percent(baseline))
    cols[1].metric("Workspaces per arm", f"{per_arm:,}")
    cols[2].metric("Enrollment", f"{weeks} weeks")
    st.caption(f'{planning["activated"]:,} activated / {planning["eligible"]:,} eligible historically. '
               "Equal allocation, two-sided 5% significance, 80% power. "
               "Allow five additional weeks for week-4 follow-up after enrollment ends.")
    with st.expander("Protocol and decision rules"):
        protocol = Path(__file__).parent / "docs" / "experiment.md"
        st.markdown(protocol.read_text(encoding="utf-8"))


def main():
    files = ("manifest.json", "workspaces.csv", "events.csv.gz")
    try:
        signature = tuple((DATA / name).stat().st_mtime_ns for name in files)
    except FileNotFoundError:
        st.error("The bundled data is missing. Run python -m growth.generate from the project folder.")
        st.stop()
    metadata, all_rows = load_snapshot(DATA, signature)
    cutoff = metadata["cutoff_ts"]

    st.sidebar.header("Workspace filters")
    channels = sorted({row.channel for row in all_rows})
    sizes = sorted({row.team_size for row in all_rows})
    weeks = sorted({date_label(row.cohort_ts) for row in all_rows})
    selected_channels = st.sidebar.multiselect("Acquisition channel", channels, placeholder="All channels", key="channels")
    selected_sizes = st.sidebar.multiselect("Team size", sizes, placeholder="All team sizes", key="sizes")
    first_week, last_week = st.sidebar.select_slider("Signup week (UTC)", options=weeks, value=(weeks[0], weeks[-1]),
                                                     key="weeks")
    st.sidebar.divider()
    st.sidebar.caption(f'Fictional SaaS · seed {metadata["seed"]} · events before '
                       f'{metadata["observation_end_exclusive_utc"]} UTC')
    rows = [
        row for row in all_rows
        if (not selected_channels or row.channel in selected_channels)
        and (not selected_sizes or row.team_size in selected_sizes)
        and first_week <= date_label(row.cohort_ts) <= last_week
    ]
    st.title("Product growth & retention")
    st.caption("TandemDesk · synthetic workspace analytics")
    page = st.radio("Analysis view", ("Onboarding", "Retention", "Segments", "Experiment"),
                    horizontal=True, label_visibility="collapsed", key="page")
    if page == "Experiment":
        experiment(all_rows, cutoff)
        return
    if not rows:
        st.info("No workspaces match these filters. Expand the signup weeks or clear a filter.")
        return
    records = summary(rows, cutoff)
    cols = st.columns(4)
    cols[0].metric("Workspace signups", f'{records["signups"]:,}')
    metric(cols[1], "Day 7 activation", records, "activated", "d7_eligible", "activation_rate")
    metric(cols[2], "Week 4 retention", records, "retained_w4", "w4_eligible", "w4_rate")
    metric(cols[3], "Day 30 paid", records, "paid_d30", "d30_eligible", "paid_rate")
    st.caption("Each rate uses workspaces with a complete observation window. Hover over a metric’s info icon for its count.")
    st.divider()
    {"Onboarding": onboarding, "Retention": retention, "Segments": segments}[page](rows, cutoff)


main()
