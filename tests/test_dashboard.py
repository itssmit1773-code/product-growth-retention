import unittest

from streamlit.testing.v1 import AppTest

from growth.model import ROOT


class DashboardTests(unittest.TestCase):
    def test_default_and_acquisition_filter(self):
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual([metric.value for metric in app.metric], ["4,532", "31.6%", "26.7%", "11.4%"])
        self.assertEqual(len(app.get("download_button")), 1)
        app.multiselect(key="channels").set_value(["Paid search"]).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual([metric.value for metric in app.metric[:2]], ["1,607", "26.5%"])

    def test_navigation_and_latest_cohort(self):
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.radio(key="page").set_value("Retention").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.subheader[0].value, "Return usage by signup week")
        self.assertEqual(len(app.get("vega_lite_chart")), 1)
        app.slider(key="age_limit").set_value(4).run(timeout=30)
        self.assertFalse(app.exception)
        app.radio(key="page").set_value("Segments").run(timeout=30)
        self.assertFalse(app.exception)
        app.radio[1].set_value("Team size").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn("<td>16+</td>", app.get("html")[0].proto.body)
        app.radio(key="page").set_value("Onboarding").run(timeout=30)
        app.select_slider(key="weeks").set_value(("2025-06-30", "2025-06-30")).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[1].value, "—")
        self.assertIn("complete seven-day window", app.info[0].value)
        app.radio(key="page").set_value("Experiment").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual([metric.value for metric in app.metric], ["38.7%", "1,520", "19 weeks"])
        app.slider(key="traffic").set_value(50).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, "38 weeks")

