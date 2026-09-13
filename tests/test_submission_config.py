import json
from pathlib import Path
import unittest


class SubmissionConfigTests(unittest.TestCase):
    def test_submission_cases_are_complete_and_include_edge_case(self):
        path = Path(__file__).resolve().parents[1] / "config" / "test_cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(len(cases), 5)
        self.assertTrue(all(not case["question"].startswith("TODO") for case in cases))
        self.assertIn("SV9999999", cases[4]["question"])
        self.assertEqual(cases[3]["type"], "multi_step_reasoning")
