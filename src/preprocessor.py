"""
Build and Error Log Preprocessor.

Performs ANSI code stripping, noise filtering, error cluster detection,
and attention-focused context windowing to compress large CI/CD logs
before LLM inference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Set


ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Typical noise patterns in CI/CD build logs
NOISE_LINE_PATTERNS = [
    re.compile(r"^\s*[\-\=\_]{10,}\s*$"),                          # Divider lines
    re.compile(r"^\s*(\[INFO\]\s+)?Downloading from\b", re.IGNORECASE), # Maven/Gradle dependency downloads
    re.compile(r"^\s*(\[INFO\]\s+)?Downloaded from\b", re.IGNORECASE),
    re.compile(r"^\s*Get:\d+\s+http", re.IGNORECASE),               # apt-get download progress
    re.compile(r"^\s*Fetch(ing)?\b", re.IGNORECASE),
    re.compile(r"^\s*(\[INFO\]\s+)?Progress\s*\(?\d+%\)?", re.IGNORECASE),
    re.compile(r"^\s*[\.]{5,}\s*$"),                                # Dots progress indicator
    re.compile(r"^\s*([0-9\.]+[kMG]b\/[0-9\.]+[kMG]b|\d+%\s*\|)"),   # Progress bars
]

# Patterns that indicate critical failure/error lines
ERROR_PATTERNS = [
    re.compile(r"\b(error|fatal|fail|failed|failure|panic|exception|fault)\b", re.IGNORECASE),
    re.compile(r"\b(AssertionError|NullPointerException|Segmentation fault|CrashLoopBackOff)\b"),
    re.compile(r"\berror\[E\d+\]:", re.IGNORECASE),                  # Rust errors
    re.compile(r"\bexit(ed)? with code\s+[1-9]\d*", re.IGNORECASE),  # Exit codes
    re.compile(r"\bTraceback \(most recent call last\):", re.IGNORECASE),
    re.compile(r"\bCompilation failure\b", re.IGNORECASE),
    re.compile(r"\bERESOLVE could not resolve\b", re.IGNORECASE),
    re.compile(r"\bfailed to solve:\b", re.IGNORECASE),
    re.compile(r"\bcannot find symbol\b", re.IGNORECASE),
]


@dataclass
class PreprocessingResult:
    """Result of log preprocessing and noise reduction."""
    raw_log: str
    filtered_log: str
    raw_line_count: int
    filtered_line_count: int
    raw_char_count: int
    filtered_char_count: int
    raw_token_estimate: int
    filtered_token_estimate: int
    compression_ratio_percent: float
    detected_error_lines: List[int] = field(default_factory=list)
    detected_keywords: List[str] = field(default_factory=list)


class LogPreprocessor:
    """Preprocesses raw logs to extract high-signal context for LLM ingestion."""

    def __init__(
        self,
        context_radius: int = 15,
        head_lines: int = 15,
        tail_lines: int = 25,
        max_output_tokens: int = 4000,
    ):
        """
        Args:
            context_radius: Lines of context before & after each error line to preserve.
            head_lines: Initial lines of log (environment, initial command) to keep.
            tail_lines: Final lines of log (summary, exit code) to keep.
            max_output_tokens: Approximate cap on tokens (~4 chars/token).
        """
        self.context_radius = context_radius
        self.head_lines = head_lines
        self.tail_lines = tail_lines
        self.max_output_tokens = max_output_tokens

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Removes terminal ANSI color codes and formatting escapes."""
        return ANSI_REGEX.sub("", text)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 characters per token)."""
        return max(1, len(text) // 4)

    def is_noise(self, line: str) -> bool:
        """Determines whether a line is purely noise/progress logging."""
        for pattern in NOISE_LINE_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def is_error_line(self, line: str) -> Tuple[bool, List[str]]:
        """Checks if line matches error/critical failure patterns."""
        matched_keywords = []
        for pattern in ERROR_PATTERNS:
            match = pattern.search(line)
            if match:
                matched_keywords.append(match.group(0))
        return (len(matched_keywords) > 0, matched_keywords)

    def process(self, raw_text: str) -> PreprocessingResult:
        """
        Processes raw log text and returns optimized representation.

        Algorithm:
        1. Strip ANSI escape sequences.
        2. Normalize linebreaks and index lines.
        3. Identify error lines & failure anchors.
        4. Select union of:
           - First `head_lines` (pipeline configuration & environment)
           - Context windows around all error lines (`+/- context_radius`)
           - Last `tail_lines` (final error exit summaries)
        5. Filter out high-frequency noise patterns inside selected lines.
        6. Collapse omitted gaps with explicit markers.
        """
        clean_text = self.strip_ansi(raw_text)
        lines = clean_text.splitlines()
        total_lines = len(lines)
        raw_char_count = len(raw_text)
        raw_token_est = self.estimate_tokens(raw_text)

        if total_lines == 0:
            return PreprocessingResult(
                raw_log=raw_text,
                filtered_log="",
                raw_line_count=0,
                filtered_line_count=0,
                raw_char_count=0,
                filtered_char_count=0,
                raw_token_estimate=0,
                filtered_token_estimate=0,
                compression_ratio_percent=0.0,
            )

        error_indices: List[int] = []
        collected_keywords: Set[str] = set()

        for idx, line in enumerate(lines):
            has_error, keywords = self.is_error_line(line)
            if has_error:
                error_indices.append(idx)
                collected_keywords.update(keywords)

        # Lines to preserve
        kept_indices: Set[int] = set()

        # Keep initial lines
        for i in range(min(self.head_lines, total_lines)):
            kept_indices.add(i)

        # Keep terminal lines
        for i in range(max(0, total_lines - self.tail_lines), total_lines):
            kept_indices.add(i)

        # If no explicit error matches found, preserve more head/tail
        if not error_indices:
            for i in range(min(total_lines, 100)):
                kept_indices.add(i)
        else:
            # Preserve context window around each error line
            for err_idx in error_indices:
                start = max(0, err_idx - self.context_radius)
                end = min(total_lines, err_idx + self.context_radius + 1)
                for i in range(start, end):
                    kept_indices.add(i)

        # Assemble filtered lines with gap markers
        sorted_indices = sorted(kept_indices)
        output_lines: List[str] = []
        last_idx = -1

        for idx in sorted_indices:
            line = lines[idx]
            # Strip noise unless this line was an explicit error match
            if idx not in error_indices and self.is_noise(line):
                continue

            if last_idx != -1 and idx > last_idx + 1:
                omitted_count = idx - last_idx - 1
                output_lines.append(f"\n[... {omitted_count} non-critical lines omitted for context brevity ...]\n")

            output_lines.append(line)
            last_idx = idx

        filtered_text = "\n".join(output_lines)
        filtered_char_count = len(filtered_text)
        filtered_token_est = self.estimate_tokens(filtered_text)

        compression_ratio = 0.0
        if raw_char_count > 0:
            compression_ratio = max(0.0, round((1.0 - (filtered_char_count / raw_char_count)) * 100, 2))

        return PreprocessingResult(
            raw_log=raw_text,
            filtered_log=filtered_text,
            raw_line_count=total_lines,
            filtered_line_count=len(output_lines),
            raw_char_count=raw_char_count,
            filtered_char_count=filtered_char_count,
            raw_token_estimate=raw_token_est,
            filtered_token_estimate=filtered_token_est,
            compression_ratio_percent=compression_ratio,
            detected_error_lines=error_indices,
            detected_keywords=sorted(collected_keywords),
        )
