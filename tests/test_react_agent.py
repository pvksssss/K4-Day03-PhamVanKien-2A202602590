from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import run_react_agent
from mcp_server import MCPAcademicServer
from providers import MockOfflineProvider


class ReActAgentTests(unittest.TestCase):
    def test_class_schedule_request_uses_class_tool_then_returns_schedule(self):
        trace = run_react_agent(
            "Tra cứu lịch học thứ Hai của sinh viên SV2026001.",
            MockOfflineProvider(),
            MCPAcademicServer(),
        )

        self.assertEqual(trace[0]["tool_name"], "class_schedule_query")
        self.assertEqual(trace[-1]["action_type"], "FINAL_ANSWER")
        self.assertIn("AI201", trace[-1]["output"])
        self.assertIn("D201", trace[-1]["output"])

    def test_exam_schedule_request_uses_exam_tool_then_returns_schedule(self):
        trace = run_react_agent(
            "Tra cứu lịch thi của sinh viên SV2026001.",
            MockOfflineProvider(),
            MCPAcademicServer(),
        )

        self.assertEqual(trace[0]["tool_name"], "exam_schedule_query")
        self.assertEqual(trace[-1]["action_type"], "FINAL_ANSWER")
        self.assertIn("AI201", trace[-1]["output"])
        self.assertIn("C304", trace[-1]["output"])

    def test_multi_step_request_runs_lookup_then_booking_then_final_answer(self):
        trace = run_react_agent(
            "Hãy tra cứu SV2026001 rồi đặt lịch tư vấn lúc 14:00 ngày 15/09/2026.",
            MockOfflineProvider(),
            MCPAcademicServer(),
        )

        self.assertEqual(
            [event["action_type"] for event in trace],
            ["TOOL_EXECUTION", "TOOL_EXECUTION", "FINAL_ANSWER"],
        )
        self.assertEqual(
            [event["tool_name"] for event in trace[:2]],
            ["academic_query", "schedule_appointment"],
        )
        self.assertEqual(
            trace[1]["arguments"]["advisor_name"],
            "PGS.TS Nguyễn Văn A",
        )
