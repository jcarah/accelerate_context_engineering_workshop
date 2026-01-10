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
""".
Analyze Evaluation Results and Generate Reports (Step 3).

This script serves as the final step in the evaluation pipeline, focusing on
analysis, reporting, and data persistence.

Key functionalities:
1.  **Generate Q&A Log:** Creates a detailed Markdown file (`question_answer_log.md`)
    that compares the agent's response and state against the reference data.
2.  **Generate AI-Powered Analysis:** Uses the Gemini model to generate a
    comprehensive root-cause analysis of the evaluation results.
3.  **Upload to GCS (Placeholder):** Uploads summary artifacts to Google Cloud Storage.

This script consumes the outputs of `02_agent_run_eval.py` (`eval_summary.json`
and the `evaluation_results_*.csv`) to perform its analysis.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

import pandas as pd
from google import genai
from google.genai.types import HttpOptions

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.gemini_prompt_builder import GeminiAnalysisPrompter


class LogEntry(TypedDict):
    """A structured representation of a single question's evaluation results."""
    question_id: str
    metadata: Dict[str, Any]
    user_question: str
    reference_data: Dict[str, Any]
    extracted_data: Dict[str, Any]
    metrics: Dict[str, Dict[str, Any]]
    agents_evaluated: List[str]


def upload_to_gcs(results_dir: Path, bucket_name: str, destination_prefix: str) -> None:
    """
    Placeholder for uploading evaluation artifacts to Google Cloud Storage.
    
    Args:
        results_dir: The local directory containing results.
        bucket_name: The GCS bucket name.
        destination_prefix: The prefix path in the bucket.
    """
    print(f"\n--- [PLACEHOLDER] Uploading Results to GCS: gs://{bucket_name}/{destination_prefix} ---")
    # TODO: Implement GCS upload logic using google-cloud-storage
    pass


def robust_json_loads(x: Any) -> Optional[Dict[str, Any]]:
    """Safely load JSON strings, handling various input types."""
    if x is None: return None
    if isinstance(x, (dict, list)): return x
    if not isinstance(x, str) or not x: return None
    try:
        return json.loads(x)
    except (json.JSONDecodeError, TypeError):
        return x


def _process_log_row(row: pd.Series, index: int) -> Optional[LogEntry]:
    """Processes a single DataFrame row to extract structured log data for Markdown reporting."""
    try:
        user_inputs = robust_json_loads(row.get("user_inputs", []))
        question = (
            user_inputs[0]
            if isinstance(user_inputs, list) and user_inputs
            else str(user_inputs or "Unknown question")
        )

        metadata = robust_json_loads(row.get("question_metadata", {})) or {}
        question_id = row.get("question_id", f"row_{index}")

        reference_data = robust_json_loads(row.get("reference_data", {})) or {}
        extracted_data = robust_json_loads(row.get("extracted_data", {})) or {}

        agents_evaluated = robust_json_loads(row.get("agents_evaluated", []))
        agents_list = agents_evaluated if isinstance(agents_evaluated, list) else [agents_evaluated]

        eval_results = robust_json_loads(row.get("eval_results", "{{}}")) or {}

        return LogEntry(
            question_id=question_id,
            metadata=metadata,
            user_question=question,
            reference_data=reference_data,
            extracted_data=extracted_data,
            metrics=eval_results,
            agents_evaluated=agents_list,
        )
    except Exception as e:
        print(f"Error processing row {index}: {e}")
        return None


def _format_log_entry_markdown(entry: LogEntry, entry_num: int) -> str:
    """Formats a single log entry into a markdown string."""
    agents = ", ".join(entry["agents_evaluated"])
    metadata_str = ", ".join([f"{k}: {v}" for k, v in entry["metadata"].items()])
    
    header = f"## {entry_num}. {entry['question_id']}\n**Metadata:** {metadata_str}\n**Agents:** {agents}"

    # Extract dynamic metric summary
    metrics_md = ""
    for m_name, m_val in entry["metrics"].items():
        if isinstance(m_val, dict):
            score = m_val.get("score", "N/A")
            expl = m_val.get("explanation", "")
            metrics_md += f"- **{m_name}:** {score} - {expl[:200]}...\n"
        else:
            metrics_md += f"- **{m_name}:** {m_val}\n"

    # Reference Data Section
    ref_md = json.dumps(entry["reference_data"], indent=2)
    # Extracted Data Section
    ext_md = json.dumps(entry["extracted_data"], indent=2)

    return f"""{header}

### Question:
{entry['user_question']}

### Reference Data (Expected):
```json
{ref_md}
```

### Extracted Agent Data (Actual):
```json
{ext_md}
```

### Metrics:
{metrics_md}
"""


def generate_question_answer_log(results_file: Path, output_path: Path) -> bool:
    """Generates a detailed log comparing questions, reference data, and agent output."""
    print(f"\n--- Generating Question-Answer Log from {results_file} ---")
    try:
        df = pd.read_csv(results_file)
        print(f"Loaded {len(df)} evaluation results.")

        log_entries = [
            entry
            for index, row in df.iterrows()
            if (entry := _process_log_row(row, index)) is not None
        ]

        header = f"# Question-Answer Analysis Log\n\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**Total Questions:** {len(log_entries)}\n"
        markdown_content = [header]
        markdown_content.extend(
            _format_log_entry_markdown(entry, i)
            for i, entry in enumerate(log_entries, 1)
        )

        output_path.write_text("---".join(markdown_content), encoding="utf-8")
        print(f"Question-answer log saved to {output_path}")
        return True

    except Exception as e:
        print(f"Error generating question-answer log: {e}")
        return False


def analyze_evaluation_results(
    summary_path: Path,
    results_path: Path,
) -> tuple[Optional[dict], Optional[str]]:
    """Analyzes evaluation results and returns the content for the Gemini prompt."""
    try:
        summary_data = json.loads(summary_path.read_text())
        results_df = pd.read_csv(results_path)
    except FileNotFoundError as e:
        print(f"Error: Input file not found: {e}")
        return None, None

    # Use 'average_metrics' from summary_data (includes flattened sub-metrics)
    average_metrics = summary_data.get("overall_summary", {}).get("average_metrics", {})
    all_explanations = {metric: [] for metric in average_metrics}

    for _, row in results_df.iterrows():
        try:
            eval_results = json.loads(row["eval_results"])
            for metric, details in eval_results.items():
                if (
                    metric in all_explanations
                    and isinstance(details, dict)
                    and "explanation" in details
                    and "score" in details
                ):
                    all_explanations[metric].append(
                        {"score": details["score"], "explanation": details["explanation"]}
                    )
        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    output_lines = ["--- Evaluation Analysis ---\n"]
    for metric, mean_score in average_metrics.items():
        output_lines.append(f"\n## Metric: `{metric}`\n")
        score_str = f"{mean_score:.4f}" if isinstance(mean_score, (int, float)) else str(mean_score)
        output_lines.append(f"**Average Score:** {score_str}\n")

        if explanations := all_explanations.get(metric):
            # Show first 10 explanations as a sample to avoid prompt bloating
            explanation_summary = "\n".join(
                f"- [Score: {exp['score']}] {exp['explanation']}" for exp in explanations[:10]
            )
            output_lines.append(f"**Sample Explanations:**\n{explanation_summary}\n")

    return summary_data, "".join(output_lines)


def generate_gemini_analysis(
    summary_data: dict,
    analysis_content: str,
    results_dir: Path,
    output_path: Path,
) -> None:
    """Generates a detailed technical diagnosis using Gemini."""
    # Find relevant context files dynamically
    consolidated_metrics_file = results_dir / "temp_consolidated_metrics.json"
    question_file = results_dir / "temp_consolidated_questions.json"
    
    context_files = {
        str(consolidated_metrics_file),
        "evaluation/scripts/deterministic_metrics.py",
        # Add core agent logic for context
        "customer-service/customer_service/agent.py",
        "retail-ai-location-strategy/app/agent.py",
        str(question_file),
    }
    
    context_content = {}
    for file_path in context_files:
        try:
            context_content[file_path] = Path(file_path).read_text()
        except FileNotFoundError:
            print(f"Warning: Context file not found at '{file_path}'")
            context_content[file_path] = ""

    prompter = GeminiAnalysisPrompter(
        summary_data=summary_data,
        analysis_content=analysis_content,
        context_files=context_content,
        question_file_path=str(question_file),
        consolidated_metrics_path=str(consolidated_metrics_file),
    )
    prompt = prompter.build_prompt()

    # Save prompt for debugging
    (output_path.parent / "gemini_prompt.txt").write_text(prompt, encoding="utf-8")

    print("\n--- Calling Vertex AI to generate root-cause analysis ---")
    try:
        client = genai.Client(http_options=HttpOptions(api_version="v1"))
        # Using gemini-2.0-flash for faster/cheaper analysis
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)

        analysis_text = response.text
        output_path.write_text(analysis_text, encoding="utf-8")
        print(f"Analysis report saved to {output_path}")

    except Exception as e:
        print(f"An error occurred while calling the Vertex AI API: {e}")


def main():
    """Main function to orchestrate the analysis and reporting."""
    parser = argparse.ArgumentParser(
        description="Analyze evaluation results and generate reports.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Directory containing the evaluation results files.",
    )
    parser.add_argument(
        "--skip-gemini",
        action="store_true",
        help="Skip the AI-powered analysis generation.",
    )
    parser.add_argument(
        "--gcs-bucket",
        type=str,
        help="If provided, upload summary artifacts to this GCS bucket.",
    )
    args = parser.parse_args()

    summary_file = args.results_dir / "eval_summary.json"
    try:
        results_file = next(args.results_dir.glob("evaluation_results_*.csv"))
    except StopIteration:
        print(f"Error: No 'evaluation_results_*.csv' file in '{args.results_dir}'")
        sys.exit(1)

    if not summary_file.exists():
        print(f"Error: summary file not found in '{args.results_dir}'")
        sys.exit(1)

    # 1. Generate Q&A Log
    qa_log_path = args.results_dir / "question_answer_log.md"
    generate_question_answer_log(results_file, qa_log_path)

    # 2. Generate Gemini Analysis
    if not args.skip_gemini:
        summary, analysis_content = analyze_evaluation_results(summary_file, results_file)
        if summary and analysis_content:
            analysis_path = args.results_dir / "gemini_analysis.md"
            generate_gemini_analysis(summary, analysis_content, args.results_dir, analysis_path)

    # 3. GCS Upload (Placeholder)
    if args.gcs_bucket:
        upload_to_gcs(args.results_dir, args.gcs_bucket, f"evaluations/{datetime.now().strftime('%Y%m%d')}")

if __name__ == "__main__":
    main()
