import sqlite3
import tempfile
import unittest
from collections import Counter
from contextlib import closing
from pathlib import Path

from growth.experiment import enrollment_weeks, planning_baseline, sample_per_arm
from growth.generate import CHANNELS, TEAM_SIZES, generate
from growth.metrics import activation_diagnostic, cohorts, funnel, segment, summary, workspace_outcomes
from growth.model import DATA, DAY, STAGES, WEEK, read_data, timestamp, week_start
from growth.warehouse import load, query


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.workspaces, cls.events = read_data()
        cls.cutoff = cls.manifest["cutoff_ts"]
        cls.rows = workspace_outcomes(cls.workspaces, cls.events, cls.cutoff)
        cls.connection = sqlite3.connect(":memory:")
        cls.addClassCleanup(cls.connection.close)
        load(cls.connection, cls.workspaces, cls.events, cls.cutoff)

    def test_snapshot_integrity(self):
        signup = {row["workspace_id"]: row["signup_ts"] for row in self.workspaces}
        self.assertEqual(len(signup), self.manifest["workspaces"])
        self.assertEqual(len(signup), len(self.workspaces))
        self.assertEqual(len(self.events), self.manifest["events"])
        self.assertEqual(len({event["event_id"] for event in self.events}), len(self.events))
        self.assertEqual({row["channel"] for row in self.workspaces}, set(CHANNELS))
        self.assertEqual({row["team_size"] for row in self.workspaces}, set(TEAM_SIZES))
        created = Counter()
        for event in self.events:
            when = event["event_ts"]
            self.assertLess(when, self.cutoff)
            self.assertGreaterEqual(when, signup[event["workspace_id"]])
            if event["event_name"] == "workspace_created":
                self.assertEqual(when, signup[event["workspace_id"]])
                created[event["workspace_id"]] += 1
            if event["event_name"] == "invoice_paid":
                self.assertGreater(event["amount_cents"], 0)
                self.assertEqual(event["actor_role"], "billing")
            else:
                self.assertIsNone(event["amount_cents"])
        self.assertEqual(created, Counter({key: 1 for key in signup}))

    def test_seed_regenerates_bundled_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory)
            generate(generated)
            self.assertEqual(read_data(generated), (self.manifest, self.workspaces, self.events))
            self.assertEqual((generated / "workspaces.csv").read_bytes(), (DATA / "workspaces.csv").read_bytes())

    def test_sql_matches_python_for_every_funnel_and_cohort_row(self):
        self.assertEqual(query(self.connection, "01_funnel.sql"), funnel(self.rows, self.cutoff))
        self.assertEqual(query(self.connection, "02_cohorts.sql"), cohorts(self.rows, self.cutoff))

    def test_sql_matches_python_for_all_segments_and_diagnostic_groups(self):
        expected = {("all", "All"): summary(self.rows, self.cutoff)}
        for dimension in ("channel", "team_size"):
            for row in segment(self.rows, self.cutoff, dimension):
                expected[dimension, row.pop("segment")] = row
        for row in query(self.connection, "03_segments.sql"):
            self.assertEqual(row, expected.pop((row.pop("dimension"), row.pop("segment"))))
        self.assertFalse(expected)
        expected = activation_diagnostic(self.rows, self.cutoff)
        for row in expected:
            self.assertLessEqual(row.pop("lower_95"), row["w4_rate"])
            self.assertGreaterEqual(row.pop("upper_95"), row["w4_rate"])
        self.assertEqual(query(self.connection, "04_activation_diagnostic.sql"), expected)

    def test_published_counts_and_experiment_input(self):
        values = summary(self.rows, self.cutoff)
        self.assertEqual(
            [values[key] for key in ("signups", "d7_eligible", "activated", "w4_eligible", "retained_w4",
                                     "d30_eligible", "paid_d30", "cash_d30_cents")],
            [4532, 4317, 1365, 3444, 918, 3602, 411, 1902900],
        )
        planning = planning_baseline(self.rows, self.cutoff)
        self.assertEqual((planning["eligible"], planning["activated"]), (985, 381))
        size = sample_per_arm(planning["baseline"], 0.05)
        self.assertEqual(size, 1520)
        self.assertEqual(enrollment_weeks(size, planning["per_week"]), 19)
        self.assertGreater(sample_per_arm(planning["baseline"], 0.03), size)
        self.assertEqual(sample_per_arm(0.5, 0.1), 388)


class BoundaryTests(unittest.TestCase):
    def test_order_retries_billing_and_age_windows(self):
        start = timestamp("2025-01-06")
        cutoff = start + 5 * WEEK
        workspaces = [
            {"workspace_id": key, "signup_ts": signup, "channel": "Organic", "team_size": "2–5"}
            for key, signup in (("A", start), ("B", start + 1), ("C", cutoff - 1))
        ]
        sequence = [
            ("A", start, STAGES[0]), ("A", start + 10, STAGES[2]),
            ("A", start + 20, STAGES[1]), ("A", start + 20, STAGES[2]),
            ("A", start + 25, STAGES[2]), ("A", start + WEEK, STAGES[3]),
            ("A", start + WEEK - 1, STAGES[3]), ("A", start + 4 * WEEK, "task_completed"),
            ("A", start + 4 * WEEK + 3, "task_completed"),
            ("A", start + 30 * DAY - 1, "invoice_paid"), ("A", start + 30 * DAY, "invoice_paid"),
            ("B", start + 1, STAGES[0]), ("B", start + 2, STAGES[1]),
            ("B", start + 3, STAGES[2]), ("B", start + WEEK + 1, STAGES[3]),
            ("C", cutoff - 1, STAGES[0]), ("C", cutoff, "task_completed"),
        ]
        events = [
            {"event_id": index, "workspace_id": key, "event_ts": when, "event_name": name,
             "actor_role": "billing" if name == "invoice_paid" else "owner",
             "amount_cents": 2900 if name == "invoice_paid" else None}
            for index, (key, when, name) in enumerate(reversed(sequence))
        ]
        rows = workspace_outcomes(workspaces, events, cutoff)
        self.assertEqual([row.funnel_depth for row in rows], [4, 3, 1])
        self.assertFalse(rows[-1].active_weeks)
        self.assertEqual(rows[0].active_weeks, frozenset((0, 1, 4)))
        metrics = summary(rows, cutoff)
        self.assertEqual((metrics["activated"], metrics["d7_eligible"]), (1, 2))
        self.assertEqual((metrics["retained_w4"], metrics["w4_eligible"]), (1, 1))
        self.assertEqual((metrics["cash_d30_cents"], metrics["d30_eligible"]), (2900, 2))
        cells = cohorts(rows, cutoff)
        self.assertIsNone(cells[3]["retention_rate"])
        self.assertEqual(cells[2]["retention_rate"], 0)
        self.assertEqual(week_start(start + WEEK - 1), start)
        with closing(sqlite3.connect(":memory:")) as connection:
            load(connection, workspaces, events, cutoff)
            self.assertEqual(query(connection, "01_funnel.sql"), funnel(rows, cutoff))
            self.assertEqual(query(connection, "02_cohorts.sql"), cells)

    def test_empty_selection_and_invalid_experiment_inputs(self):
        self.assertIsNone(summary([], 0)["w4_rate"])
        self.assertIsNone(funnel([], 0)[0]["step_rate"])
        self.assertIsNone(activation_diagnostic([], 0)[0]["lower_95"])
        with self.assertRaises(ValueError):
            sample_per_arm(0.98, 0.05)
        with self.assertRaises(ValueError):
            enrollment_weeks(100, 0)
