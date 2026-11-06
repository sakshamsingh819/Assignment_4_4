"""
Benchmark and Evaluation Suite.

Evaluates the log summarization system across multiple build logs,
measuring noise reduction ratio, latency, and diagnostic fidelity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any

from src.summarizer import LogSummarizer, SummarizationResult


SAMPLE_LOGS_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_logs"


class BenchmarkRunner:
    """Runs automated diagnostic benchmarks on curated build logs."""

    def __init__(self, provider: str = "offline", api_key: str | None = None):
        self.summarizer = LogSummarizer(provider=provider, api_key=api_key)

    def run_all(self, logs_dir: Path | None = None) -> List[Dict[str, Any]]:
        target_dir = logs_dir or SAMPLE_LOGS_DIR
        results: List[Dict[str, Any]] = []

        log_files = sorted(target_dir.glob("*.log"))
        if not log_files:
            print(f"No log files found in {target_dir}")
            return results

        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            summary: SummarizationResult = self.summarizer.analyze(content)
            results.append({
                "file_name": log_file.name,
                "error_category": summary.error_category,
                "raw_lines": summary.raw_lines,
                "filtered_lines": summary.filtered_lines,
                "raw_tokens": summary.raw_tokens,
                "filtered_tokens": summary.filtered_tokens,
                "compression_ratio": f"{summary.compression_ratio_percent}%",
                "total_latency_ms": f"{summary.total_latency_ms}ms",
                "root_cause": summary.root_cause,
                "failing_step": summary.failing_step,
            })

        return results

    def print_markdown_table(self, results: List[Dict[str, Any]]) -> str:
        headers = [
            "Log Dataset",
            "Category",
            "Raw L",
            "Filt L",
            "Tokens (Raw -> Filt)",
            "Compression",
            "Latency",
        ]
        divider = ["| " + " | ".join(["---"] * len(headers)) + " |"]
        header_row = "| " + " | ".join(headers) + " |"
        rows = []
        for r in results:
            rows.append(
                f"| `{r['file_name']}` | `{r['error_category']}` | {r['raw_lines']} | {r['filtered_lines']} | {r['raw_tokens']} -> {r['filtered_tokens']} | **{r['compression_ratio']}** | {r['total_latency_ms']} |"
            )

        table_str = "\n".join([header_row] + divider + rows)
        return table_str


if __name__ == "__main__":
    runner = BenchmarkRunner(provider="offline")
    benchmark_results = runner.run_all()
    print("\n" + "=" * 80)
    print(" LLM BUILD LOG SUMMARIZATION BENCHMARK REPORT ")
    print("=" * 80 + "\n")
    print(runner.print_markdown_table(benchmark_results))
    print("\nDetailed Root Causes:\n")
    for r in benchmark_results:
        print(f"▶ {r['file_name']}:")
        print(f"   Step:  {r['failing_step']}")
        print(f"   Cause: {r['root_cause']}\n")

