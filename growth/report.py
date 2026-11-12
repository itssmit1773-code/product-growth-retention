"""Export repeatable results from both the Python and SQL implementations."""

import argparse
import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from growth.experiment import enrollment_weeks, planning_baseline, sample_per_arm
from growth.metrics import activation_diagnostic, cohorts, funnel, segment, summary, workspace_outcomes
from growth.model import read_data
from growth.warehouse import load, query


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(destination):
    metadata, workspaces, events = read_data()
    cutoff = metadata["cutoff_ts"]
    rows = workspace_outcomes(workspaces, events, cutoff)
    destination.mkdir(parents=True, exist_ok=True)
    metrics = {
        "source": metadata,
        "overall": summary(rows, cutoff),
        "experiment_baseline": planning_baseline(rows, cutoff),
    }
    planning = metrics["experiment_baseline"]
    planning["mde"] = 0.05
    planning["per_arm"] = sample_per_arm(planning["baseline"], planning["mde"])
    planning["enrollment_weeks"] = enrollment_weeks(planning["per_arm"], planning["per_week"])
    (destination / "summary.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    tables = {
        "01_funnel": funnel(rows, cutoff),
        "02_cohorts": cohorts(rows, cutoff),
        "03_segments": [
            {"dimension": dimension, **record}
            for dimension in ("channel", "team_size") for record in segment(rows, cutoff, dimension)
        ] + [{"dimension": "all", "segment": "All", **summary(rows, cutoff)}],
        "04_activation_diagnostic": activation_diagnostic(rows, cutoff),
    }
    with closing(sqlite3.connect(":memory:")) as connection:
        load(connection, workspaces, events, cutoff)
        for name, records in tables.items():
            write_csv(destination / f"python_{name}.csv", records)
            write_csv(destination / f"sql_{name}.csv", query(connection, f"{name}.sql"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    main(args.output)
