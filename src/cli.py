"""
Command-Line Interface (CLI) for LLM-Based Build/Error Log Summarizer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.summarizer import LogSummarizer
from src.benchmark import BenchmarkRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="logsum",
        description="LLM-Based Build and Error Log Summarizer & Diagnostic Tool",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: summarize
    sum_parser = subparsers.add_parser("summarize", help="Analyze and summarize a build/error log")
    sum_parser.add_argument("logfile", type=str, help="Path to raw build log file")
    sum_parser.add_argument(
        "--provider",
        choices=["offline", "gemini", "openai", "ollama"],
        default="offline",
        help="LLM provider (default: offline)",
    )
    sum_parser.add_argument("--api-key", type=str, default=None, help="LLM API key (or use env var)")
    sum_parser.add_argument("--model", type=str, default=None, help="Specific model name")
    sum_parser.add_argument(
        "--format",
        choices=["pretty", "markdown", "json"],
        default="pretty",
        help="Output format (default: pretty)",
    )

    # Command: benchmark
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmark suite across curated logs")
    bench_parser.add_argument(
        "--provider",
        choices=["offline", "gemini", "openai", "ollama"],
        default="offline",
        help="LLM provider for benchmark",
    )

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Launch interactive Web Dashboard")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")

    return parser.parse_args()


def print_pretty_summary(res):
    BORDER = "=" * 70
    DIV = "-" * 70
    print("\n" + BORDER)
    print(" 🛠️  BUILD / ERROR LOG DIAGNOSTIC SUMMARY")
    print(BORDER)
    print(f" ▶ Category:        {res.error_category}")
    print(f" ▶ Failing Step:    {res.failing_step}")
    print(f" ▶ Confidence:      {res.confidence_score * 100:.1f}%")
    print(f" ▶ Noise Reduction: {res.compression_ratio_percent}% ({res.raw_tokens} -> {res.filtered_tokens} tokens)")
    print(f" ▶ Latency:         {res.total_latency_ms:.1f}ms (Engine: {res.provider})")
    print(DIV)
    print(f" 🎯 Root Cause:\n   {res.root_cause}")
    print(DIV)
    print(f" 📦 Affected Components:")
    for comp in res.affected_components:
        print(f"   • {comp}")
    print(DIV)
    print(f" 💡 Suggested Fixes:")
    for i, fix in enumerate(res.suggested_fixes, 1):
        print(f"   {i}. {fix}")
    if res.code_patch:
        print(DIV)
        print(" 💻 Suggested Code / Patch Snippet:")
        for line in res.code_patch.splitlines():
            print(f"   │ {line}")
    print(BORDER + "\n")


def main() -> int:
    args = parse_args()

    if not args.command:
        # Default help
        print("LLM-Based Build and Error Log Summarizer")
        print("Run 'python -m src.cli --help' for options.")
        print("Example: python -m src.cli summarize data/sample_logs/docker_build_failure.log")
        return 0

    if args.command == "summarize":
        path = Path(args.logfile)
        if not path.is_file():
            print(f"Error: Log file not found: {args.logfile}", file=sys.stderr)
            return 1

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        summarizer = LogSummarizer(
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
        )
        res = summarizer.analyze(raw_text)

        if args.format == "json":
            print(json.dumps(res.to_dict(), indent=2))
        elif args.format == "markdown":
            print(res.to_markdown())
        else:
            print_pretty_summary(res)
        return 0

    elif args.command == "benchmark":
        runner = BenchmarkRunner(provider=args.provider)
        results = runner.run_all()
        print(runner.print_markdown_table(results))
        return 0

    elif args.command == "serve":
        from src.web.server import start_server
        start_server(host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
