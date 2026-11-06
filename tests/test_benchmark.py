"""
Unit tests for BenchmarkRunner.
"""

import unittest
from src.benchmark import BenchmarkRunner


class TestBenchmarkRunner(unittest.TestCase):
    def test_benchmark_runs_across_samples(self):
        runner = BenchmarkRunner(provider="offline")
        results = runner.run_all()
        self.assertGreaterEqual(len(results), 6)

        table = runner.print_markdown_table(results)
        self.assertIn("| Log Dataset |", table)
        self.assertIn("docker_build_failure.log", table)


if __name__ == "__main__":
    unittest.main()

