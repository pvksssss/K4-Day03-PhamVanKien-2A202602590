from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from providers import MockOfflineProvider
from tools import TOOLS_SCHEMA


class MockProviderTests(unittest.TestCase):
    def test_booking_request_without_time_or_advisor_asks_for_missing_details(self):
        response = MockOfflineProvider().generate_with_tools(
            "Đặt lịch tư vấn học vụ cho sinh viên SV2026001.",
            TOOLS_SCHEMA,
        )

        self.assertEqual(response.get("type"), "text")
        self.assertIn("thời gian", response.get("content", "").lower())
        self.assertIn("cố vấn", response.get("content", "").lower())
        self.assertNotIn("thành công", response.get("content", "").lower())

    def test_lookup_observation_without_booking_request_returns_final_text(self):
        observation = {
            "tool_name": "academic_query",
            "result": {
                "status": "SUCCESS",
                "student_id": "SV2026001",
                "data": {
                    "full_name": "Nguyễn Văn An",
                    "class": "AI-K4",
                    "gpa": 3.85,
                    "advisor": "PGS.TS Nguyễn Văn A",
                },
            },
        }

        response = MockOfflineProvider().generate_with_tools(
            "Hãy tra cứu thông tin học vụ của sinh viên SV2026001.",
            TOOLS_SCHEMA,
            context=[observation],
        )

        self.assertEqual(response.get("type"), "text")
        self.assertIn("Nguyễn Văn An", response.get("content", ""))

    def test_lookup_observation_leads_to_booking_with_returned_advisor(self):
        observation = {
            "tool_name": "academic_query",
            "result": {
                "status": "SUCCESS",
                "student_id": "SV2026001",
                "data": {"advisor": "PGS.TS Nguyễn Văn A"},
            },
        }

        response = MockOfflineProvider().generate_with_tools(
            "Tra cứu SV2026001 rồi đặt lịch tư vấn lúc 14:00 ngày 15/09/2026.",
            TOOLS_SCHEMA,
            context=[observation],
        )

        self.assertEqual(response.get("type"), "tool_call")
        self.assertEqual(response.get("tool_name"), "schedule_appointment")
        self.assertEqual(
            response.get("arguments", {}).get("advisor_name"),
            "PGS.TS Nguyễn Văn A",
        )
