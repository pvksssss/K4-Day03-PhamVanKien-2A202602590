import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import save_waterfall_trace


class TraceLoggingTests(unittest.TestCase):
    def test_save_waterfall_trace_writes_all_events_for_a_session(self):
        events = [
            {"step": 1, "query": "Câu hỏi đầu", "action_type": "FINAL_ANSWER"},
            {"step": 2, "query": "Câu hỏi tiếp", "action_type": "FINAL_ANSWER"},
        ]

        with TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "trace.json"
            save_waterfall_trace(events, trace_path=trace_path)
            saved_events = json.loads(trace_path.read_text(encoding="utf-8"))

        self.assertEqual(saved_events, events)
