"""
Main Log Summarization Orchestration Engine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from src.preprocessor import LogPreprocessor, PreprocessingResult
from src.llm_client import BaseLLMClient, get_llm_client


@dataclass
class SummarizationResult:
    """Complete summary and diagnostic output."""
    error_category: str
    failing_step: str
    root_cause: str
    affected_components: list[str]
    executive_summary: str
    suggested_fixes: list[str]
    code_patch: Optional[str]
    confidence_score: float

    # Metadata & Metrics
    provider: str
    model: str
    raw_tokens: int
    filtered_tokens: int
    compression_ratio_percent: float
    raw_lines: int
    filtered_lines: int
    preprocessing_latency_ms: float
    inference_latency_ms: float
    total_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        """Renders GitHub PR-ready Markdown comment."""
        fixes_md = "\n".join(f"{i+1}. {fix}" for i, fix in enumerate(self.suggested_fixes))
        components_md = ", ".join(f"`{c}`" for c in self.affected_components) or "None specified"
        patch_md = f"```\n{self.code_patch}\n```" if self.code_patch else "_No automated code patch provided._"

        return f"""### 🔍 Build Failure Diagnostic Report

> **Category**: `{self.error_category}` &nbsp;|&nbsp; **Confidence**: `{self.confidence_score * 100:.1f}%` &nbsp;|&nbsp; **Noise Reduction**: `{self.compression_ratio_percent}%`

#### 📌 Executive Summary
{self.executive_summary}

#### 💥 Failing Step
`{self.failing_step}`

#### 🎯 Root Cause
{self.root_cause}

#### 📦 Affected Components
{components_md}

#### 🛠️ Recommended Actions
{fixes_md}

#### 💻 Suggested Code / Fix Patch
{patch_md}

---
*Analyzed by LLM-Based Log Summarizer ({self.provider} / {self.model}) in {self.total_latency_ms:.1f}ms*
"""


class LogSummarizer:
    """High-level facade orchestrating log filtering, LLM inference, and validation."""

    def __init__(
        self,
        provider: str = "offline",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        preprocessor: Optional[LogPreprocessor] = None,
    ):
        self.provider = provider
        self.model = model or ("offline-rules" if provider == "offline" else provider)
        self.client: BaseLLMClient = get_llm_client(provider, api_key, model)
        self.preprocessor = preprocessor or LogPreprocessor()

    def analyze(self, raw_log_text: str) -> SummarizationResult:
        """Performs end-to-end preprocessing, model inference, and metric collection."""
        start_time = time.perf_counter()

        # Step 1: Preprocessing & Context Extraction
        t0 = time.perf_counter()
        prep_res: PreprocessingResult = self.preprocessor.process(raw_log_text)
        t1 = time.perf_counter()
        prep_latency = (t1 - t0) * 1000.0

        # Step 2: LLM Inference
        t2 = time.perf_counter()
        diag = self.client.summarize(prep_res.filtered_log)
        t3 = time.perf_counter()
        inf_latency = (t3 - t2) * 1000.0

        total_latency = (time.perf_counter() - start_time) * 1000.0

        return SummarizationResult(
            error_category=diag.get("error_category", "UNKNOWN_FAILURE"),
            failing_step=diag.get("failing_step", "Unknown execution step"),
            root_cause=diag.get("root_cause", "No specific root cause identified"),
            affected_components=diag.get("affected_components", []),
            executive_summary=diag.get("executive_summary", ""),
            suggested_fixes=diag.get("suggested_fixes", []),
            code_patch=diag.get("code_patch"),
            confidence_score=float(diag.get("confidence_score", 0.8)),
            provider=self.provider,
            model=self.model,
            raw_tokens=prep_res.raw_token_estimate,
            filtered_tokens=prep_res.filtered_token_estimate,
            compression_ratio_percent=prep_res.compression_ratio_percent,
            raw_lines=prep_res.raw_line_count,
            filtered_lines=prep_res.filtered_line_count,
            preprocessing_latency_ms=round(prep_latency, 2),
            inference_latency_ms=round(inf_latency, 2),
            total_latency_ms=round(total_latency, 2),
        )

