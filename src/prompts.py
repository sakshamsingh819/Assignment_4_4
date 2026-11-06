"""
Prompt templates, JSON schemas, and few-shot examples for LLM log summarization.
"""

from __future__ import annotations

import json
from typing import Any, Dict


# Structured JSON Schema expected from the LLM
SUMMARY_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "error_category": {
            "type": "string",
            "enum": [
                "COMPILATION_ERROR",
                "DEPENDENCY_RESOLUTION",
                "TEST_FAILURE",
                "ENVIRONMENT_CONFIG",
                "RUNTIME_CRASH",
                "SYNTAX_ERROR",
                "TIMEOUT_ERROR",
                "PERMISSION_ERROR",
                "UNKNOWN_FAILURE"
            ],
            "description": "High-level classification of build failure"
        },
        "failing_step": {
            "type": "string",
            "description": "Specific command, task, job, or test that failed (e.g. 'RUN pip install' or 'tests/test_users.py::test_email')"
        },
        "root_cause": {
            "type": "string",
            "description": "Direct technical reason for the failure (1-2 sentences)"
        },
        "affected_components": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific files, libraries, or service components involved"
        },
        "executive_summary": {
            "type": "string",
            "description": "Concise summary suitable for a PR comment or alert notification"
        },
        "suggested_fixes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Ordered, actionable steps to resolve the issue"
        },
        "code_patch": {
            "type": "string",
            "description": "Ready-to-use code, Dockerfile instruction, shell command, or configuration snippet"
        },
        "confidence_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence level in this root cause diagnosis"
        }
    },
    "required": [
        "error_category",
        "failing_step",
        "root_cause",
        "affected_components",
        "executive_summary",
        "suggested_fixes",
        "confidence_score"
    ]
}


SYSTEM_PROMPT = """You are an expert Senior Site Reliability and DevOps Engineer specializing in CI/CD pipeline diagnostics and build error root-cause analysis.

Your task is to analyze raw/filtered build and error logs, diagnose the exact failure point, and produce a structured, actionable technical diagnosis.

CRITICAL INSTRUCTIONS:
1. Grounding: Rely strictly on facts present in the provided log. Do NOT fabricate file paths, missing dependencies, or test names that are not referenced.
2. Root Cause vs Symptom: Distinguish the underlying root cause from cascading symptoms. (e.g., if a build fails with exit code 1 because 'pg_config is not found', the root cause is the missing PostgreSQL development headers, not the exit status code).
3. Actionability: Provide concrete, copy-pasteable solutions in `suggested_fixes` and `code_patch`.
4. Format: Respond ONLY with valid, RFC-8259 compliant JSON matching the provided schema. Do not include markdown code block backticks (like ```json), no prose before or after.
"""


FEW_SHOT_LOG_EXAMPLE = """
#7 [4/5] RUN pip install --no-cache-dir -r requirements.txt
#7 1.201 Collecting psycopg2>=2.9.9 (from -r requirements.txt (line 3))
#7 1.582   Error: pg_config executable not found.
#7 1.582   pg_config is required to build psycopg2 from source.
#7 ERROR: process "/bin/sh -c pip install --no-cache-dir -r requirements.txt" did not complete successfully: exit code: 1
"""

FEW_SHOT_SUMMARY_EXAMPLE = {
    "error_category": "DEPENDENCY_RESOLUTION",
    "failing_step": "Docker RUN pip install --no-cache-dir -r requirements.txt",
    "root_cause": "The build attempted to compile 'psycopg2' from source on a slim Debian base image without 'libpq-dev' and compilation tools installed, failing because 'pg_config' was missing.",
    "affected_components": [
        "requirements.txt",
        "Dockerfile",
        "psycopg2"
    ],
    "executive_summary": "Docker image build failed at step [4/5] during Python package installation: psycopg2 requires PostgreSQL C development headers (pg_config) to compile from source.",
    "suggested_fixes": [
        "Option A (Recommended): Switch from 'psycopg2' to precompiled wheel 'psycopg2-binary' in requirements.txt.",
        "Option B: Install OS dependencies before pip in Dockerfile: apt-get update && apt-get install -y libpq-dev gcc."
    ],
    "code_patch": "# In Dockerfile:\nRUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*\n\n# Or in requirements.txt replace:\n# psycopg2>=2.9.9\n# with:\n# psycopg2-binary>=2.9.9",
    "confidence_score": 0.98
}


def build_analysis_prompt(filtered_log: str) -> str:
    """Constructs user prompt containing log context and format guidance."""
    return f"""Please analyze the following build/error log and return a JSON summary according to the required schema:

=== LOG START ===
{filtered_log}
=== LOG END ===

Return ONLY valid JSON.
"""

