"""
Unit tests for LogSummarizer & Diagnostic Outputs.
"""

import unittest
from pathlib import Path
from src.summarizer import LogSummarizer


class TestLogSummarizer(unittest.TestCase):
    def setUp(self):
        self.summarizer = LogSummarizer(provider="offline")
        self.sample_dir = Path(__file__).parent.parent / "data" / "sample_logs"

    def test_docker_summarize(self):
        log_path = self.sample_dir / "docker_build_failure.log"
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()

        result = self.summarizer.analyze(content)
        self.assertEqual(result.error_category, "DEPENDENCY_RESOLUTION")
        self.assertIn("pg_config", result.root_cause)
        self.assertTrue(len(result.suggested_fixes) >= 1)
        self.assertIn("psycopg2-binary", result.code_patch)

    def test_python_pytest_summarize(self):
        log_path = self.sample_dir / "python_pytest_failure.log"
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()

        result = self.summarizer.analyze(content)
        self.assertEqual(result.error_category, "TEST_FAILURE")
        self.assertIn("test_user_email_verification", result.failing_step)
        self.assertTrue(result.confidence_score >= 0.9)

    def test_markdown_export(self):
        log_path = self.sample_dir / "rust_cargo_borrow.log"
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()

        result = self.summarizer.analyze(content)
        md = result.to_markdown()
        self.assertIn("### 🔍 Build Failure Diagnostic Report", md)
        self.assertIn("COMPILATION_ERROR", md)
        self.assertIn("orders", md)


if __name__ == "__main__":
    unittest.main()

