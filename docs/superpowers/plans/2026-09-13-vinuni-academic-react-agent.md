# VinUni Academic ReAct Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the VinUni academic ReAct Agent with two MCP tools, iterative observations, executable test cases, and evidence documentation.

**Architecture:** Keep the existing CLI and in-process MCP server. Tool execution is wrapped in JSON-RPC, while `app.py` carries an observation history into provider calls so the provider can decide whether to call another tool or return a final answer.

**Tech Stack:** Python 3.10-3.12, standard-library `unittest`, `python-dotenv`, optional Google GenAI/OpenAI SDKs.

**Spec:** `docs/superpowers/specs/2026-09-13-vinuni-academic-react-agent-design.md`

## Global Constraints

- Keep the `src/app.py --all` and `src/app.py --interactive` command interfaces.
- Keep the two existing tool names: `academic_query` and `schedule_appointment`.
- Use UTF-8 for Vietnamese source, configuration, documentation, and generated trace output.
- Do not require an API key for automated verification; Mock mode must cover every test case.
- Do not add a web service, database, or new runtime dependency.

---

### Task 1: Tool Schema and MCP JSON-RPC Response

**Files:**
- Modify: `src/tools.py`
- Modify: `src/mcp_server.py`
- Create: `tests/test_mcp_server.py`

**Interfaces:**
- Consumes: `dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str`
- Produces: `MCPAcademicServer.call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mcp_server import MCPAcademicServer
from tools import TOOLS_SCHEMA

class MCPServerTests(unittest.TestCase):
    def test_schedule_schema_requires_booking_arguments(self):
        tool = next(item for item in TOOLS_SCHEMA if item["name"] == "schedule_appointment")
        self.assertEqual(set(tool["parameters"]["required"]), {"student_id", "datetime_str", "advisor_name"})
        self.assertEqual(set(tool["parameters"]["properties"]), {"student_id", "datetime_str", "advisor_name"})

    def test_call_tool_wraps_decoded_result_in_jsonrpc(self):
        result = MCPAcademicServer().call_tool("academic_query", {"student_id": "SV2026001"})
        self.assertEqual(result["jsonrpc"], "2.0")
        self.assertEqual(result["tool"], "academic_query")
        self.assertEqual(result["result"]["status"], "SUCCESS")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_mcp_server -v`

Expected: a schema assertion failure and an empty response failure.

- [ ] **Step 3: Implement the schema and response wrapper**

```python
# src/tools.py
"properties": {
    "student_id": {"type": "string", "description": "Mã sinh viên cần đặt lịch."},
    "datetime_str": {"type": "string", "description": "Thời gian hẹn, ví dụ '14:00 15/09/2026'."},
    "advisor_name": {"type": "string", "description": "Tên cố vấn học tập."},
},
"required": ["student_id", "datetime_str", "advisor_name"],

# src/mcp_server.py
content = json.loads(dispatch_tool_call(tool_name, arguments))
return {"jsonrpc": "2.0", "server": self.server_name, "tool": tool_name, "result": content}
```

- [ ] **Step 4: Run the focused tests and MCP CLI check**

Run: `python -m unittest tests.test_mcp_server -v`

Expected: both tests PASS.

Run: `python src/mcp_server.py`

Expected: two published tools and a non-empty JSON-RPC response for `academic_query`.

- [ ] **Step 5: Commit**

```bash
git add src/tools.py src/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: complete academic MCP tool contracts"
```

### Task 2: Context-Aware Provider Decisions

**Files:**
- Modify: `src/providers.py`
- Create: `tests/test_mock_provider.py`

**Interfaces:**
- Consumes: `generate_with_tools(prompt, tools_schema, system_prompt="", context=None)`
- Produces: provider dictionaries with `type` equal to `text` or `tool_call`, and tool calls containing `tool_name` and `arguments`.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from providers import MockOfflineProvider
from tools import TOOLS_SCHEMA

class MockProviderTests(unittest.TestCase):
    def test_booking_request_calls_schedule_tool(self):
        response = MockOfflineProvider().generate_with_tools(
            "Đặt lịch tư vấn cho SV2026001 vào 14:00 ngày 15/09/2026", TOOLS_SCHEMA
        )
        self.assertEqual(response["tool_name"], "schedule_appointment")

    def test_observation_after_lookup_causes_booking_with_returned_advisor(self):
        context = [{"tool_name": "academic_query", "result": {"status": "SUCCESS", "student_id": "SV2026001", "data": {"advisor": "PGS.TS Nguyễn Văn A"}}}]
        response = MockOfflineProvider().generate_with_tools(
            "Tra cứu SV2026001 rồi đặt lịch vào 14:00 ngày 15/09/2026", TOOLS_SCHEMA, context=context
        )
        self.assertEqual(response["tool_name"], "schedule_appointment")
        self.assertEqual(response["arguments"]["advisor_name"], "PGS.TS Nguyễn Văn A")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_mock_provider -v`

Expected: `TypeError` because `context` is not yet accepted.

- [ ] **Step 3: Add optional context to all provider implementations**

```python
def generate_with_tools(self, prompt, tools_schema, system_prompt="", context=None):
    context = context or []
```

In `MockOfflineProvider`, detect a successful `academic_query` observation before generic prompt matching and return `schedule_appointment` with the `advisor` from `context[-1]["result"]["data"]`. In Gemini and OpenAI providers, append a UTF-8 JSON serialization of `context` to the user content before calling the native SDK. Preserve the existing fallback to Mock mode.

- [ ] **Step 4: Run the focused tests**

Run: `python -m unittest tests.test_mock_provider -v`

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/providers.py tests/test_mock_provider.py
git commit -m "feat: carry MCP observations into provider decisions"
```

### Task 3: Iterative ReAct Loop and Trace Ordering

**Files:**
- Modify: `src/app.py`
- Create: `tests/test_react_agent.py`

**Interfaces:**
- Consumes: `run_react_agent(user_query: str, provider, mcp_server: MCPAcademicServer) -> list`
- Produces: ordered trace events with `action_type` values `TOOL_EXECUTION` and `FINAL_ANSWER`.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from app import run_react_agent
from mcp_server import MCPAcademicServer
from providers import MockOfflineProvider

class ReActAgentTests(unittest.TestCase):
    def test_multi_step_request_runs_lookup_then_booking_then_final_answer(self):
        trace = run_react_agent(
            "Hãy tra cứu SV2026001 rồi đặt lịch tư vấn lúc 14:00 ngày 15/09/2026.",
            MockOfflineProvider(), MCPAcademicServer(),
        )
        self.assertEqual([event["action_type"] for event in trace], ["TOOL_EXECUTION", "TOOL_EXECUTION", "FINAL_ANSWER"])
        self.assertEqual([event["tool_name"] for event in trace[:2]], ["academic_query", "schedule_appointment"])

    def test_unknown_student_ends_without_booking(self):
        trace = run_react_agent("Tra cứu thông tin SV9999999", MockOfflineProvider(), MCPAcademicServer())
        self.assertEqual(trace[0]["observation"]["status"], "NOT_FOUND")
        self.assertEqual(trace[-1]["action_type"], "FINAL_ANSWER")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_react_agent -v`

Expected: the multi-step trace has only one tool execution, and the unknown-student branch is not deterministically recognized by Mock mode.

- [ ] **Step 3: Implement iterative observation handling**

```python
observations = []
while step < MAX_ITERATIONS:
    llm_response = provider.generate_with_tools(
        user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT, context=observations
    )
    if llm_response.get("type") == "text":
        # append FINAL_ANSWER and break
    elif llm_response.get("type") == "tool_call":
        mcp_result = mcp_server.call_tool(tool_name, arguments)
        obs_data = mcp_result["result"]
        observations.append({"tool_name": tool_name, "arguments": arguments, "result": obs_data})
        # append TOOL_EXECUTION and continue
```

After a `NOT_FOUND`, use the next provider decision to generate a final response, not another tool call. Add Mock intent recognition for `SV9999999`, and return a final text response after a successful appointment observation.

- [ ] **Step 4: Run the focused tests**

Run: `python -m unittest tests.test_react_agent -v`

Expected: both tests PASS with trace order lookup, booking, final answer for the multi-step query.

- [ ] **Step 5: Commit**

```bash
git add src/app.py src/providers.py tests/test_react_agent.py
git commit -m "feat: support iterative academic ReAct workflows"
```

### Task 4: Submission Test Cases and Report Metadata

**Files:**
- Create: `config/test_cases.json`
- Modify: `docs/trace_eval.md`
- Test: `tests/test_submission_config.py`

**Interfaces:**
- Consumes: the existing `load_test_cases() -> list`.
- Produces: five non-placeholder JSON test cases and a report identifying the selected topic and 16/20 Agentic Fit score.

- [ ] **Step 1: Write the failing configuration test**

```python
import json
from pathlib import Path
import unittest

class SubmissionConfigTests(unittest.TestCase):
    def test_submission_cases_are_complete(self):
        path = Path(__file__).resolve().parents[1] / "config" / "test_cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 5)
        self.assertTrue(all(not case["question"].startswith("TODO") for case in cases))
        self.assertIn("SV9999999", cases[4]["question"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_submission_config -v`

Expected: `FileNotFoundError` because `config/test_cases.json` does not yet exist.

- [ ] **Step 3: Add five concrete academic-assistant cases and report selection**

Create `config/test_cases.json` with the existing TC01 and TC02 questions, an appointment request for TC03, a lookup-then-appointment request for TC04, and `Tra cứu thông tin học vụ của sinh viên SV9999999.` for TC05. In `docs/trace_eval.md`, replace the topic placeholder with `Trợ lý Học vụ & Tra cứu Lịch thi VinUni`, write the four scores `4`, `5`, `4`, and `3`, and state total `16 / 20`. Leave API-key and post-execution result fields truthful and unmarked.

- [ ] **Step 4: Run the configuration test and full offline suite**

Run: `python -m unittest tests.test_submission_config -v`

Expected: PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

Run: `python src/app.py --all`

Expected: five test cases execute in Mock mode, with a non-empty `docs/trace_waterfall.json` that contains tool observations.

- [ ] **Step 5: Commit**

```bash
git add config/test_cases.json docs/trace_eval.md tests/test_submission_config.py
git commit -m "docs: add VinUni academic agent submission evidence"
```
