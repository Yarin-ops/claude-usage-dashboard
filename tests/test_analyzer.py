"""Run with: python3 -m unittest discover -s tests"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyzer  # noqa: E402

TS = "2026-10-01T10:00:00.000Z"


def line(msg_id, model, content, output=10, cache_read=0, session="s1", ts=TS, cwd=None):
    return json.dumps({
        "type": "assistant", "timestamp": ts, "sessionId": session, "cwd": cwd,
        "message": {
            "id": msg_id, "model": model, "content": content,
            "usage": {"input_tokens": 100, "output_tokens": output,
                      "cache_read_input_tokens": cache_read},
        },
    })


def tool(block_id, name):
    return {"type": "tool_use", "id": block_id, "name": name}


class AnalyzerTest(unittest.TestCase):
    def summarize(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, lines in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return analyzer.build_summary(root)

    def test_counts_tools_from_every_line_of_a_streamed_message(self):
        data = self.summarize({"-proj/a.jsonl": [
            line("m1", "claude-opus-5-5", [tool("t1", "Read")]),
            line("m1", "claude-opus-5-5", [tool("t2", "Bash")]),
            line("m1", "claude-opus-5-5", [tool("t2", "Bash")]),
        ]})
        self.assertEqual(data["totals"]["messages"], 1)
        self.assertEqual({t["name"]: t["count"] for t in data["by_tool"]}, {"Read": 1, "Bash": 1})

    def test_uses_the_complete_usage_of_a_streamed_message(self):
        data = self.summarize({"-proj/a.jsonl": [
            line("m1", "claude-opus-5-5", [], output=5),
            line("m1", "claude-opus-5-5", [], output=500),
        ]})
        self.assertEqual(data["totals"]["output_tokens"], 500)

    def test_counts_a_message_once_across_files(self):
        data = self.summarize({
            "-proj/a.jsonl": [line("m1", "claude-opus-5-5", [])],
            "-proj/b.jsonl": [line("m1", "claude-opus-5-5", [])],
        })
        self.assertEqual(data["totals"]["messages"], 1)

    def test_subagent_logs_belong_to_their_project(self):
        data = self.summarize({
            "-proj/a.jsonl": [line("m1", "claude-opus-5-5", [])],
            "-proj/a/subagents/x.jsonl": [line("m2", "claude-opus-5-5", [])],
        })
        self.assertEqual([p["folder"] for p in data["by_project"]], ["-proj"])
        self.assertEqual(data["by_month"][0]["active_projects"], 1)

    def test_project_label_comes_from_the_real_path(self):
        data = self.summarize({"-tmp-----/a.jsonl": [
            line("m1", "claude-opus-5-5", [], cwd="/tmp/עיצוב"),
            line("m2", "claude-opus-5-5", [], cwd="/tmp/עיצוב/site"),
        ]})
        self.assertEqual(data["by_project"][0]["label"], "/tmp/עיצוב")

    def test_fable_is_its_own_model(self):
        data = self.summarize({"-proj/a.jsonl": [line("m1", "claude-fable-5-1", [])]})
        self.assertEqual(data["by_model"][0]["model"], "fable")

    def test_skips_synthetic_messages(self):
        data = self.summarize({"-proj/a.jsonl": [line("m1", "<synthetic>", [])]})
        self.assertEqual(data["totals"]["messages"], 0)

    def test_rates_match_the_most_specific_model(self):
        self.assertEqual(analyzer.rates_for("claude-opus-5-5")["input"], 4.00)
        self.assertEqual(analyzer.rates_for("claude-opus-5")["input"], 5.00)
        self.assertEqual(analyzer.rates_for("claude-haiku-4-5-20251001")["input"], 1.00)
        self.assertEqual(analyzer.rates_for("us.anthropic.claude-sonnet-4-6")["input"], 3.00)
        self.assertEqual(analyzer.rates_for("claude-opus-9-9")["input"], 4.00)

    def test_cost_uses_the_listed_cache_read_price(self):
        cost = analyzer.cost_for_entry("claude-fable-5-1", {"cache_read_input_tokens": 1_000_000})
        self.assertAlmostEqual(cost["cost"], 0.25)

    def test_haiku_55_price_depends_on_prompt_length(self):
        short = analyzer.cost_for_entry("claude-haiku-5-5", {"input_tokens": 100_000})
        long = analyzer.cost_for_entry("claude-haiku-5-5", {"input_tokens": 100_001})
        self.assertAlmostEqual(short["cost"], 0.01)
        self.assertAlmostEqual(long["cost"], 0.0500005)


if __name__ == "__main__":
    unittest.main()
