"""Generate the fictional TandemDesk event export using a fixed seed."""

import argparse
import csv
import gzip
import io
import json
import random
from pathlib import Path

from growth.model import DATA, DAY, WEEK, EVENT_FIELDS, WORKSPACE_FIELDS, date_label, timestamp

START = timestamp("2025-01-06")
CUTOFF = timestamp("2025-07-07")
SEED = 1729
CHANNELS = ("Organic", "Paid search", "Referral", "Partner")
TEAM_SIZES = ("2–5", "6–15", "16+")
PRICES_CENTS = (2900, 5900, 11900)


def simulate(seed=SEED):
    rng = random.Random(seed)
    workspaces, events = [], []

    def log(workspace_id, when, name, role="owner", amount=None):
        if when < CUTOFF:
            events.append((len(events) + 1, workspace_id, when, name, role, amount))

    for week in range(26):
        weekly_signups = 125 + 4 * week + rng.randint(-14, 14)
        for _ in range(weekly_signups):
            workspace_id = f"TD-{len(workspaces) + 1:05d}"
            signup = START + week * WEEK + rng.randrange(WEEK)
            weights = (42, 27, 22, 9) if week < 13 else (35, 39, 17, 9)
            channel = rng.choices(CHANNELS, weights)[0]
            size_index = rng.choices(range(3), (63, 28, 9))[0]
            intent_probability = dict(zip(CHANNELS, (0.53, 0.37, 0.69, 0.64)))[channel]
            high_intent = rng.random() < intent_probability + 0.07 * size_index
            workspaces.append((workspace_id, signup, channel, TEAM_SIZES[size_index]))
            log(workspace_id, signup, "workspace_created")

            project = invite = collaboration = None
            if rng.random() < (0.91 if high_intent else 0.63):
                project = signup + rng.randint(300, 3 * DAY)
                log(workspace_id, project, "project_created")
                if rng.random() < (0.68 if high_intent else 0.32) + 0.06 * size_index:
                    invite = project + rng.randint(120, 4 * DAY)
                    log(workspace_id, invite, "teammate_invited")
                    if rng.random() < (0.86 if high_intent else 0.61):
                        collaboration = invite + rng.randint(300, 3 * DAY)
                        log(workspace_id, collaboration, "collaborative_action", "teammate")
            if project is None:
                continue

            engaged = collaboration is not None and collaboration < signup + WEEK
            # Common causes influence both activation and repeat usage.
            activity = 0.24 + 0.27 * high_intent + 0.18 * engaged + 0.03 * size_index
            for age in range(26):
                if signup + age * WEEK >= CUTOFF:
                    break
                if rng.random() < activity * (0.90 ** age):
                    for _ in range(rng.randint(1, 5)):
                        when = max(project, signup + age * WEEK) + rng.randrange(4 * DAY)
                        role = "teammate" if collaboration and when >= collaboration and rng.random() < 0.45 else "owner"
                        log(workspace_id, when, "task_completed", role)

            if rng.random() < 0.04 + 0.10 * high_intent + 0.26 * engaged:
                invoice = signup + rng.randint(9 * DAY, 39 * DAY)
                log(workspace_id, invoice, "invoice_paid", "billing", PRICES_CENTS[size_index])
                while rng.random() < 0.63 + 0.13 * high_intent:
                    invoice += 30 * DAY
                    if invoice >= CUTOFF:
                        break
                    log(workspace_id, invoice, "invoice_paid", "billing", PRICES_CENTS[size_index])

    return workspaces, sorted(events, key=lambda row: (row[2], row[0]))


def generate(directory=DATA, seed=SEED):
    workspaces, events = simulate(seed)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "workspaces.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(WORKSPACE_FIELDS)
        writer.writerows(workspaces)
    with (directory / "events.csv.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(EVENT_FIELDS)
                writer.writerows(events)
    manifest = {
        "product": "TandemDesk",
        "synthetic": True,
        "seed": seed,
        "signup_start_utc": date_label(START),
        "observation_end_exclusive_utc": date_label(CUTOFF),
        "cutoff_ts": CUTOFF,
        "workspaces": len(workspaces),
        "events": len(events),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    print(json.dumps(generate(args.output, args.seed), indent=2))
