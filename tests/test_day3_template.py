import unittest
from pathlib import Path


DAY3_TEMPLATE = Path(__file__).resolve().parents[1] / "app" / "templates" / "day3.html"


class TestDay3Template(unittest.TestCase):
    def test_day3_evaluation_snapshot_card_removed(self):
        content = DAY3_TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("Day 3 evaluation snapshot", content)

    def test_quick_action_buttons_use_run_quick_action(self):
        content = DAY3_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("onclick=\"runQuickAction('expense')\"", content)
        self.assertIn("onclick=\"runQuickAction('income')\"", content)
        self.assertIn("onclick=\"runQuickAction('transfer')\"", content)

    def test_run_quick_action_executes_save_flow(self):
        content = DAY3_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("async function runQuickAction(type)", content)
        self.assertIn("await saveQuickTransaction();", content)
        self.assertIn("window.runQuickAction = runQuickAction;", content)


if __name__ == "__main__":
    unittest.main()
