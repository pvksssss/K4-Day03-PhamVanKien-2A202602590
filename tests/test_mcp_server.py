from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_server import MCPAcademicServer
from tools import TOOLS_SCHEMA


class MCPServerTests(unittest.TestCase):
    def test_schedule_schema_requires_all_booking_arguments(self):
        tool = next(item for item in TOOLS_SCHEMA if item["name"] == "schedule_appointment")

        self.assertEqual(
            set(tool["parameters"]["required"]),
            {"student_id", "datetime_str", "advisor_name"},
        )
        self.assertEqual(
            set(tool["parameters"]["properties"]),
            {"student_id", "datetime_str", "advisor_name"},
        )

    def test_call_tool_returns_decoded_jsonrpc_result(self):
        result = MCPAcademicServer().call_tool(
            "academic_query", {"student_id": "SV2026001"}
        )

        self.assertEqual(result.get("jsonrpc"), "2.0")
        self.assertEqual(result.get("server"), "vinuni-academic-mcp-server")
        self.assertEqual(result.get("tool"), "academic_query")
        self.assertEqual(result.get("result", {}).get("status"), "SUCCESS")
        self.assertEqual(
            result.get("result", {}).get("data", {}).get("full_name"),
            "Nguyễn Văn An",
        )

    def test_booking_with_missing_fields_returns_validation_error(self):
        result = MCPAcademicServer().call_tool(
            "schedule_appointment", {"student_id": "SV2026001"}
        )

        self.assertEqual(result.get("result", {}).get("status"), "VALIDATION_ERROR")
        self.assertEqual(
            set(result.get("result", {}).get("missing_fields", [])),
            {"datetime_str", "advisor_name"},
        )

    def test_exam_schedule_query_returns_time_and_room(self):
        result = MCPAcademicServer().call_tool(
            "exam_schedule_query", {"student_id": "SV2026001"}
        )

        self.assertEqual(result.get("result", {}).get("status"), "SUCCESS")
        first_exam = result.get("result", {}).get("data", [])[0]
        self.assertEqual(first_exam["course_code"], "AI201")
        self.assertEqual(first_exam["room"], "C304")
        self.assertIn("2026", first_exam["datetime"])

    def test_class_schedule_query_filters_by_weekday(self):
        result = MCPAcademicServer().call_tool(
            "class_schedule_query", {"student_id": "SV2026001", "weekday": "Thứ Hai"}
        )

        self.assertEqual(result.get("result", {}).get("status"), "SUCCESS")
        first_class = result.get("result", {}).get("data", [])[0]
        self.assertEqual(first_class["course_code"], "AI201")
        self.assertEqual(first_class["room"], "D201")
        self.assertEqual(first_class["weekday"], "Thứ Hai")
