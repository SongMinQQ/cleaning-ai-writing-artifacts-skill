import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "cleaning-ai-writing-artifacts" / "scripts" / "audit_unicode.py"
FIXTURE = ROOT / "ai-watermark-test.txt"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_unicode", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AuditTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_module()

    def test_reports_actionable_characters_with_positions(self):
        result = self.audit.audit_text("plain\nA\u200bB\u2060C")

        self.assertEqual("found", result["hidden_artifacts"])
        self.assertEqual("unknown", result["statistical_watermark"])
        self.assertEqual(
            [
                {
                    "index": 7,
                    "line": 2,
                    "column": 2,
                    "codepoint": "U+200B",
                    "name": "ZERO WIDTH SPACE",
                    "kind": "zero_width",
                    "classification": "suspicious",
                },
                {
                    "index": 9,
                    "line": 2,
                    "column": 4,
                    "codepoint": "U+2060",
                    "name": "WORD JOINER",
                    "kind": "word_joiner",
                    "classification": "suspicious",
                },
            ],
            [{key: finding[key] for key in (
                "index", "line", "column", "codepoint", "name", "kind", "classification"
            )} for finding in result["findings"]],
        )

    def test_preserves_leading_bom_as_informational(self):
        result = self.audit.audit_text("\ufeffordinary text")

        self.assertEqual("none", result["hidden_artifacts"])
        self.assertEqual("informational", result["findings"][0]["classification"])
        self.assertEqual("byte_order_mark", result["findings"][0]["kind"])

    def test_marks_mid_file_feff_as_suspicious(self):
        result = self.audit.audit_text("ordinary\ufefftext")

        self.assertEqual("found", result["hidden_artifacts"])
        self.assertEqual("suspicious", result["findings"][0]["classification"])

    def test_recognizes_semantic_emoji_zwj_and_arabic_zwnj(self):
        result = self.audit.audit_text("👩\u200d💻 می\u200cروم")

        self.assertEqual("none", result["hidden_artifacts"])
        self.assertEqual(
            ["likely_semantic", "likely_semantic"],
            [finding["classification"] for finding in result["findings"]],
        )

    def test_detects_bidi_controls(self):
        result = self.audit.audit_text("safe\u202etxt")

        self.assertEqual("found", result["hidden_artifacts"])
        self.assertEqual("bidi_control", result["findings"][0]["kind"])

    def test_repository_fixture_has_expected_ten_findings(self):
        result = self.audit.audit_file(FIXTURE)

        self.assertEqual("found", result["hidden_artifacts"])
        self.assertEqual(10, result["actionable_count"])
        self.assertEqual(
            {"U+200B": 3, "U+200C": 3, "U+2060": 3, "U+FEFF": 1},
            result["counts"],
        )


class AuditCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_json_output_and_finding_exit_code(self):
        completed = self.run_cli(FIXTURE, "--json")

        self.assertEqual(1, completed.returncode)
        payload = json.loads(completed.stdout)
        self.assertEqual(10, payload["actionable_count"])
        self.assertEqual("unknown", payload["statistical_watermark"])

    def test_clean_file_returns_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.txt"
            path.write_text("ordinary text", encoding="utf-8")

            completed = self.run_cli(path, "--json")

        self.assertEqual(0, completed.returncode)
        self.assertEqual("none", json.loads(completed.stdout)["hidden_artifacts"])

    def test_invalid_utf8_returns_usage_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.txt"
            path.write_bytes(b"\xff\xfe\x00")

            completed = self.run_cli(path)

        self.assertEqual(2, completed.returncode)
        self.assertIn("not valid UTF-8", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
