#!/usr/bin/env python3
"""
Quick demo script for LLM-Based Build/Error Log Summarization.
Runs through multiple build failure logs and displays diagnostics and benchmarks.
"""

import sys
from pathlib import Path
from src.summarizer import LogSummarizer
from src.benchmark import BenchmarkRunner


def main():
    print("=" * 80)
    print(" ⚡ LLM-BASED BUILD & ERROR LOG SUMMARIZER — QUICK DEMO")
    print("=" * 80)

    summarizer = LogSummarizer(provider="offline")
    sample_file = Path("data/sample_logs/docker_build_failure.log")

    print(f"\n[1] Analyzing sample build failure log: {sample_file.name}")
    with open(sample_file, "r") as f:
        log_content = f.read()

    result = summarizer.analyze(log_content)
    print(f" ▶ Category:        {result.error_category}")
    print(f" ▶ Failing Step:    {result.failing_step}")
    print(f" ▶ Root Cause:      {result.root_cause}")
    print(f" ▶ Compression:     {result.compression_ratio_percent}% noise filtered")
    print(f" ▶ Confidence:      {result.confidence_score * 100:.1f}%\n")
    print(" 🛠️ Suggested Fixes:")
    for i, fix in enumerate(result.suggested_fixes, 1):
        print(f"   {i}. {fix}")

    print("\n" + "=" * 80)
    print(" [2] Running Automated Benchmark Across All Sample Datasets")
    print("=" * 80)
    runner = BenchmarkRunner(provider="offline")
    benchmark_results = runner.run_all()
    print(runner.print_markdown_table(benchmark_results))

    print("\n" + "=" * 80)
    print(" ✅ Quick demo completed successfully!")
    print(" To start interactive web dashboard: python3 -m src.cli serve --port 8080")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

