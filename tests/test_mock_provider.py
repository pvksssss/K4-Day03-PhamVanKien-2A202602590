from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from providers import MockOfflineProvider
from tools import TOOLS_SCHEMA


class MockProviderTests(unittest.TestCase):
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
