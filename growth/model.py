"""Dataset location and shared units for the workspace-level analysis."""

import csv
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DAY = 86_400
WEEK = 7 * DAY
STAGES = ("workspace_created", "project_created", "teammate_invited", "collaborative_action")
USAGE = ("task_completed", "collaborative_action")
WORKSPACE_FIELDS = ("workspace_id", "signup_ts", "channel", "team_size")
EVENT_FIELDS = ("event_id", "workspace_id", "event_ts", "event_name", "actor_role", "amount_cents")


def timestamp(iso_date):
    return int(datetime.fromisoformat(iso_date).replace(tzinfo=timezone.utc).timestamp())


def date_label(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d")


def week_start(epoch):
    utc_day = epoch // DAY
    return (utc_day - (utc_day + 3) % 7) * DAY


def read_data(directory=DATA):
    metadata = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with (directory / "workspaces.csv").open(newline="", encoding="utf-8") as stream:
        workspaces = list(csv.DictReader(stream))
    for row in workspaces:
        row["signup_ts"] = int(row["signup_ts"])
    with gzip.open(directory / "events.csv.gz", "rt", newline="", encoding="utf-8") as stream:
        events = list(csv.DictReader(stream))
    for row in events:
        row["event_ts"] = int(row["event_ts"])
        row["amount_cents"] = int(row["amount_cents"]) if row["amount_cents"] else None
    return metadata, workspaces, events
