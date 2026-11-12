"""Load the CSV extract into SQLite for independent metric calculations."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from growth.model import EVENT_FIELDS, ROOT, WORKSPACE_FIELDS, read_data

SQL = ROOT / "sql"


def load(connection, workspaces, events, cutoff):
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript("""
        CREATE TABLE workspaces (
            workspace_id TEXT PRIMARY KEY, signup_ts INTEGER NOT NULL,
            channel TEXT NOT NULL, team_size TEXT NOT NULL
        );
        CREATE TABLE events (
            event_id INTEGER PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces,
            event_ts INTEGER NOT NULL, event_name TEXT NOT NULL, actor_role TEXT NOT NULL,
            amount_cents INTEGER,
            CHECK ((event_name = 'invoice_paid' AND amount_cents IS NOT NULL AND amount_cents > 0)
                OR (event_name <> 'invoice_paid' AND amount_cents IS NULL))
        );
        CREATE TABLE observation (cutoff_ts INTEGER NOT NULL);
        CREATE INDEX event_lookup ON events(workspace_id, event_name, event_ts);
    """)
    with connection:
        connection.execute("INSERT INTO observation VALUES (?)", (cutoff,))
        connection.executemany(
            "INSERT INTO workspaces VALUES (?, ?, ?, ?)",
            (tuple(row[key] for key in WORKSPACE_FIELDS) for row in workspaces),
        )
        connection.executemany(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
            (tuple(row[key] for key in EVENT_FIELDS) for row in events),
        )
        connection.execute((SQL / "00_workspace_outcomes.sql").read_text(encoding="utf-8"))


def query(connection, filename):
    statement = (SQL / filename).read_text(encoding="utf-8")
    return [dict(row) for row in connection.execute(statement)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Path for a new SQLite file")
    args = parser.parse_args()
    if args.database.exists():
        parser.error("Choose a new path. The loader preserves existing files.")
    metadata, workspaces, events = read_data()
    with closing(sqlite3.connect(args.database)) as connection:
        load(connection, workspaces, events, metadata["cutoff_ts"])
    print(f"Built {args.database} from {len(workspaces):,} workspaces and {len(events):,} events.")
