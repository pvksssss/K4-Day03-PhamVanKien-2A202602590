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
