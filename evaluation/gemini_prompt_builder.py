# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Builds the prompt for the Gemini analysis report."""

from __future__ import annotations

import json
from typing import Any, Dict


class GeminiAnalysisPrompter:
    """Constructs a detailed prompt for the Gemini analysis report."""

    BASE_TEMPLATE = """
You are an expert AI evaluation analyst. Your task is to produce a deep technical diagnosis of an AI agent's performance. You MUST base your analysis exclusively on the context provided below.

**CRITICAL INSTRUCTIONS:**
1.  **Focus on Diagnosis, Not Recommendations:** Your primary goal is to explain *why* the metrics are what they are. Do not provide a future-looking action plan or make recommendations about business decisions. Stick to a root cause analysis of the current state.
2.  **Synthesize, Don't Summarize:** Do not simply repeat the scores. Your value is in synthesizing insights by connecting the metric scores, the metric definitions, the source code, and the raw explanations.
3.  **Reference Your Sources:** When you make a claim or analyze a metric, you MUST reference the specific source file (e.g., `metric_definitions.json`, `deterministic_metrics.py`, `agent.py`).
4.  **Analyze Calculation Methods:** For each metric you discuss, you MUST explain how its calculation method (deterministic vs. LLM-judged) influences its interpretation.
5.  **CRITICAL: Diagnose the Evaluation Itself:** Your analysis is not limited to the agent's code. You MUST also diagnose potential flaws in the evaluation setup. If a metric score seems incorrect or misleading, investigate the interaction between the question's metadata, the agent's expected behavior, and the metric's calculation logic.

---

**Technical Performance Diagnosis**

*   **Objective:** Provide a detailed root cause analysis of the agent's performance by linking metric scores to the agent's underlying source code, prompts, and execution logic. This includes identifying when low scores are caused by flaws in the evaluation methodology itself.

*   **Structure:**
    1.  **Overall Performance Summary:** Briefly state the agent's key strengths and weaknesses, supported by 2-3 primary metrics. Highlight any metrics that may be misleading due to evaluation flaws.
    2.  **Deep Dive Diagnosis:** For each major finding, present a detailed hypothesis.
        *   **Finding:** State the observation.
        *   **Supporting Metrics:** List the specific metrics and scores that support this finding.
        *   **Root Cause Hypothesis:** Provide a detailed, evidence-based hypothesis connecting the metric, the source code, and the evaluation data.

---

**Context for Your Analysis**

You are provided with the following context files to perform your diagnosis. Use them to connect the agent's behavior (the metrics) to its underlying implementation (the code).

**1. Overall Performance Data:**
*   **Evaluation Summary:** High-level average scores for all metrics. Use this to identify the most significant areas of success and failure.
{summary_section}

*   **Detailed Explanations:** Raw, detailed explanations from the LLM judge for each metric on a per-question basis. Use this to find patterns in *why* a metric scored high or low.
{explanations_section}

**2. Metric Calculation & Definitions:**
*   **Metric Definitions:** The rubrics and descriptions for each metric. You MUST use these files to understand what each metric is actually measuring and whether it is `llm` judged or `deterministic`.
{metric_definitions_section}

*   **Deterministic Logic:** The Python code that calculates the deterministic metrics. Refer to this file to understand the precise logic behind scores for metrics like `token_usage` or `latency_metrics`.
{deterministic_logic_section}

**3. Agent Implementation Details:**
*   **Agent Source Code:** The source code for the agent being evaluated. This is your primary source for forming hypotheses about *why* the agent behaves a certain way.
{source_code_section}

**4. Evaluation Questions:**
*   **Questions Evaluated:** The full set of questions used in the evaluation. This can provide context if certain types of questions are causing specific failures.
{questions_section}

---
Format your entire response as a single Markdown document.
"""

    def __init__(
        self,
        summary_data: Dict[str, Any],
        analysis_content: str,
        context_files: Dict[str, str],
        question_file_path: str,
        consolidated_metrics_path: str,
    ):
        self.summary_data = summary_data
        self.analysis_content = analysis_content
        self.context_files = context_files
        self.question_file_path = question_file_path
        self.consolidated_metrics_path = consolidated_metrics_path

    def _format_context_section(self, title: str, content: str, lang: str = "") -> str:
        return f"**{title}**\n```{lang}\n{content}\n```"

    def _format_code_section(self, file_path: str, lang: str = "python") -> str:
        content = self.context_files.get(
            file_path, f"Error: File '{file_path}' not found."
        )
        return self._format_context_section(f"File: `{file_path}`", content, lang)

    def build_prompt(self) -> str:
        """Builds the final prompt string with all context included."""
        summary_section = self._format_context_section(
            "Evaluation Summary", json.dumps(self.summary_data, indent=2), "json"
        )

        explanations_section = (
            f"**Detailed Explanations per Metric:**\n{self.analysis_content}"
        )

        metric_definitions_section = self._format_code_section(
            self.consolidated_metrics_path, "json"
        )

        deterministic_logic_section = self._format_code_section(
            "evaluation/scripts/deterministic_metrics.py"
        )

        # Dynamically include all .py files except deterministic_metrics.py
        source_code_parts = []
        for file_path in self.context_files:
            if (
                file_path.endswith(".py")
                and "deterministic_metrics.py" not in file_path
            ):
                source_code_parts.append(self._format_code_section(file_path))

        source_code_section = (
            "\n".join(source_code_parts)
            if source_code_parts
            else "No agent source code provided."
        )

        questions_section = self._format_context_section(
            "Questions Evaluated",
            self.context_files.get(
                self.question_file_path, "Questions file not found."
            ),
            "json",
        )

        return self.BASE_TEMPLATE.format(
            summary_section=summary_section,
            explanations_section=explanations_section,
            metric_definitions_section=metric_definitions_section,
            deterministic_logic_section=deterministic_logic_section,
            source_code_section=source_code_section,
            questions_section=questions_section,
        )
