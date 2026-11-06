"""
Unit tests for LogPreprocessor.
"""

import unittest
from src.preprocessor import LogPreprocessor


class TestLogPreprocessor(unittest.TestCase):
    def setUp(self):
        self.preprocessor = LogPreprocessor(context_radius=2, head_lines=2, tail_lines=2)

    def test_strip_ansi(self):
        colored = "\x1b[31mERROR:\x1b[0m Something failed \x1b[1;32mhere\x1b[m"
        cleaned = self.preprocessor.strip_ansi(colored)
        self.assertEqual(cleaned, "ERROR: Something failed here")

    def test_empty_log(self):
        res = self.preprocessor.process("")
        self.assertEqual(res.raw_line_count, 0)
        self.assertEqual(res.filtered_line_count, 0)
        self.assertEqual(res.compression_ratio_percent, 0.0)

    def test_compression_on_repetitive_noise(self):
        lines = [
            "CI Job initialized",
            "Environment Linux x86_64",
        ]
        # Add 100 downloading noise lines
        for i in range(100):
            lines.append(f"[INFO] Downloading from central: https://repo.maven/pkg_{i}.jar")
        # Add error
        lines.append("ERROR: Failed to resolve symbol 'PaymentMethod'")
        lines.append("Exit code 1")

        raw_log = "\n".join(lines)
        res = self.preprocessor.process(raw_log)

        self.assertGreater(res.compression_ratio_percent, 50.0)
        self.assertIn("ERROR: Failed to resolve symbol 'PaymentMethod'", res.filtered_log)
        self.assertIn("non-critical lines omitted", res.filtered_log)

    def test_error_detection(self):
        log = "Line 1\nLine 2\nTraceback (most recent call last):\nAssertionError: expected 200 got 500\nDone"
        res = self.preprocessor.process(log)
        self.assertTrue(len(res.detected_error_lines) > 0)


if __name__ == "__main__":
    unittest.main()

