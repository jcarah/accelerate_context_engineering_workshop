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
"""
Analyze Evaluation Results and Generate Reports (Step 3).

This script serves as the final step in the evaluation pipeline, focusing on
analysis, reporting, and data persistence.

Key functionalities:
1.  **Generate Q&A Log:** Creates a detailed Markdown file (`question_answer_log.md`)
    that compares the agent's response and generated SQL against the reference
    (golden) answers and SQL for each question. This is invaluable for manual
    review and debugging.
2.  **Generate AI-Powered Analysis:** Uses the Gemini model to generate a
    comprehensive analysis of the evaluation results. It produces a two-part
    report: a high-level summary for leadership and a detailed, actionable
    breakdown for developers.
3.  **Upload to BigQuery:** Optionally, uploads the final, enriched evaluation
    results CSV to a specified BigQuery table for long-term storage, trending,
    and advanced analytics.

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
from google.cloud import bigquery
from google.genai.types import HttpOptions

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_explorer_agent.config import get_settings
from evaluation.gemini_prompt_builder import GeminiAnalysisPrompter


class LogEntry(TypedDict):
    """A structured representation of a single question's evaluation results."""

    question_id: str
    complexity: str
    tier: str
    question: str
    reference_answer: str
    agent_answer: str
    reference_sql: str
    agent_sql: str
    deterministic_accuracy: str
    sql_exact_match: str
    end_to_end_success: str
    show_deterministic_metrics: bool
    agents_evaluated: List[str]


def upload_to_bigquery(
    dataframe: pd.DataFrame, project_id: str, dataset_id: str, table_id: str
) -> None:
    """Uploads a pandas DataFrame to a specified BigQuery table.

    Args:
        dataframe: The DataFrame to upload.
        project_id: The Google Cloud project ID.
        dataset_id: The BigQuery dataset ID.
        table_id: The BigQuery table ID.
    """
    print(
        f"\n--- Uploading Results to BigQuery table: {project_id}.{dataset_id}.{table_id} ---"
    )
    try:
        client = bigquery.Client(project=project_id)
        dataset_ref = client.dataset(dataset_id)
        client.create_dataset(dataset_ref, exists_ok=True)
        table_ref = dataset_ref.table(table_id)

        # Prepare a copy for BigQuery with all columns converted to strings.
        bq_df = dataframe.astype(str)

        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            autodetect=False,
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
            schema=[bigquery.SchemaField(col, "STRING") for col in bq_df.columns],
        )

        job = client.load_table_from_dataframe(bq_df, table_ref, job_config=job_config)
        job.result()
        print(f"Successfully loaded {job.output_rows} rows into BigQuery.")
    except Exception as e:
        print(f"Error saving to BigQuery: {e}")


def robust_json_loads(x: Any) -> Optional[Dict[str, Any]]:
    """Safely load JSON strings, handling various input types.

    Args:
        x: The input to parse, expected to be a JSON string.

    Returns:
        A dictionary if parsing is successful. Returns the original input if
        it's not a valid JSON string but might be some other value.
        Returns None if the input is not a string or is empty.
    """
    if not isinstance(x, str) or not x:
        return None
    try:
        return json.loads(x)
    except (json.JSONDecodeError, TypeError):
        return x  # Return original value if it's not JSON but something else.


def extract_reference_answer(
    reference_bq_response: Optional[Union[str, list, dict]]
) -> str:
    """Extracts a human-readable answer from reference SQL execution results.

    Args:
        reference_bq_response: The raw response from a BigQuery query, which can
            be a JSON string, a list of dicts, or None.

    Returns:
        A formatted, human-readable string summarizing the query result.
    """
    if not reference_bq_response:
        return "No reference data available"

    try:
        data = (
            json.loads(reference_bq_response)
            if isinstance(reference_bq_response, str)
            else reference_bq_response
        )

        if not isinstance(data, list):
            return "No data returned or data is not in list format"

        if not data:
            return "Query returned no results"

        if len(data) == 1:
            row = data[0]
            if isinstance(row, dict):
                values = [f"{k}: {v}" for k, v in row.items()]
                return f"Result: {', '.join(values)}"
            return f"Result: {row}"

        # Multiple results - show first few
        formatted_rows = []
        for i, row in enumerate(data[:5]):  # Show first 5 rows
            if isinstance(row, dict):
                row_str = ", ".join(f"{k}: {v}" for k, v in list(row.items())[:3])
                if len(row) > 3:
                    row_str += "..."
                formatted_rows.append(f"Row {i+1}: {{{row_str}}}")
            else:
                formatted_rows.append(f"Row {i+1}: {row}")

        result = f"Results ({len(data)} total): " + "; ".join(formatted_rows)
        if len(data) > 5:
            result += f" ... and {len(data) - 5} more"
        return result

    except json.JSONDecodeError:
        return (
            f"Error: Could not decode JSON from reference data: {str(reference_bq_response)[:100]}..."
        )
    except Exception as e:
        return f"Error parsing reference data: {str(e)}"


def _process_log_row(row: pd.Series, index: int) -> Optional[LogEntry]:
    """Processes a single DataFrame row to extract structured log data."""
    try:
        user_inputs = row.get("user_inputs", [])
        question = (
            user_inputs[0]
            if isinstance(user_inputs, list) and user_inputs
            else str(user_inputs or "Unknown question")
        )

        metadata = row.get("question_metadata", {}) or {}
        question_id = row.get("question_id", f"row_{index}")
        complexity = metadata.get("complexity", "Unknown")
        tier = metadata.get("tier", "Unknown")

        reference_data = row.get("reference_data", {}) or {}
        reference_bq_response = reference_data.get(
            "sql_explorer:reference_bq_raw_response"
        )
        reference_answer = extract_reference_answer(reference_bq_response)
        reference_sql = reference_data.get(
            "sql_explorer:reference_sql", "No reference SQL available"
        )

        session_state = row.get("final_session_state", {})
        if isinstance(session_state, dict):
            state = session_state.get("state", {})
            agent_answer = state.get("nl_final_response_text", "No agent response")
            agent_sql = state.get("sql_explorer:generated_sql", "No SQL generated")
        else:
            agent_answer = "Session state not available"
            agent_sql = "Session state not available"

        agents_evaluated = row.get("agents_evaluated", [])
        agents_evaluated_list = (
            robust_json_loads(agents_evaluated)
            if isinstance(agents_evaluated, str)
            else agents_evaluated
            if isinstance(agents_evaluated, list)
            else []
        )
        show_deterministic_metrics = "sql_explorer" in agents_evaluated_list

        eval_results = (
            robust_json_loads(row["eval_results"])
            if "eval_results" in row and pd.notna(row["eval_results"])
            else {}
        )
        eval_results = eval_results or {}

        det_accuracy = eval_results.get("deterministic_accuracy", {})
        sql_match = eval_results.get("sql_result_exact_match", {})
        e2e_success = eval_results.get("end_to_end_success", {})

        return LogEntry(
            question_id=question_id,
            complexity=complexity,
            tier=tier,
            question=question,
            reference_answer=reference_answer,
            agent_answer=agent_answer,
            reference_sql=reference_sql,
            agent_sql=agent_sql,
            deterministic_accuracy=f"{det_accuracy.get('score', 'N/A')} - {str(det_accuracy.get('explanation', ''))[:100]}...",
            sql_exact_match=f"{sql_match.get('score', 'N/A')} - {str(sql_match.get('explanation', ''))[:100]}...",
            end_to_end_success=f"{e2e_success.get('score', 'N/A')} - {str(e2e_success.get('explanation', ''))[:100]}...",
            show_deterministic_metrics=show_deterministic_metrics,
            agents_evaluated=agents_evaluated_list,
        )
    except Exception as e:
        print(f"Error processing row {index}: {e}")
        return None


def _format_log_entry_markdown(entry: LogEntry, entry_num: int) -> str:
    """Formats a single log entry into a markdown string."""
    agents = ", ".join(entry["agents_evaluated"])
    header = f"## {entry_num}. {entry['question_id']} ({entry['complexity']}, {entry['tier']}) - Agent: {agents}"

    if entry["show_deterministic_metrics"]:
        return f"""{header}

### Question:
{entry['question']}

### Reference Answer (Expected):
{entry['reference_answer']}

### Agent Answer (Actual):
{entry['agent_answer']}

### Reference SQL (Expected):
```sql
{entry['reference_sql']}
```

### Agent SQL (Generated):
```sql
{entry['agent_sql']}
```

### Metrics:
- **Deterministic Accuracy:** {entry['deterministic_accuracy']}
- **SQL Exact Match:** {entry['sql_exact_match']}
- **End-to-End Success:** {entry['end_to_end_success']}
"""
    else:
        return f"""{header}

### Question:
{entry['question']}

### Agent Answer (Actual):
{entry['agent_answer']}

### Metrics:
- **End-to-End Success:** {entry['end_to_end_success']}
"""


def generate_question_answer_log(results_file: Path, output_path: Path) -> bool:
    """Generates a detailed log comparing questions, reference answers, and agent answers."""
    print(f"\n--- Generating Question-Answer Log from {results_file} ---")
    try:
        df = pd.read_csv(results_file)
        print(f"Loaded {len(df)} evaluation results.")

        json_cols = [
            "final_session_state",
            "reference_data",
            "user_inputs",
            "question_metadata",
        ]
        for col in json_cols:
            if col in df.columns:
                df[col] = df[col].apply(robust_json_loads)

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

        output_path.write_text("---\n".join(markdown_content), encoding="utf-8")
        print(f"Question-answer log saved to {output_path}")
        return True

    except FileNotFoundError:
        print(f"Error: Results file not found at {results_file}")
        return False
    except Exception as e:
        print(f"Error generating question-answer log: {e}")
        return False


def analyze_evaluation_results(
    summary_path: Path,
    results_path: Path,
) -> tuple[Optional[dict], Optional[str]]:
    """Analyzes evaluation results and returns the content for the prompt."""
    try:
        summary_data = json.loads(summary_path.read_text())
        results_df = pd.read_csv(results_path)
    except FileNotFoundError as e:
        print(f"Error: Input file not found: {e}")
        return None, None

    average_metrics = summary_data.get("average_metrics", {})
    all_explanations = {metric: [] for metric in average_metrics}

    for _, row in results_df.iterrows():
        try:
            eval_results = json.loads(row["eval_results"])
            for metric, details in eval_results.items():
                if (
                    metric in all_explanations
                    and "explanation" in details
                    and "score" in details
                ):
                    all_explanations[metric].append(
                        {"score": details["score"], "explanation": details["explanation"]}
                    )
        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    output_lines = ["--- Evaluation Analysis ---\n"]
    for metric, values in average_metrics.items():
        mean_score = values if isinstance(values, (int, float)) else values.get("score", "N/A")
        output_lines.append(f"\n## Metric: `{metric}`\n")
        score_str = f"{mean_score:.2f}" if isinstance(mean_score, (int, float)) else str(mean_score)
        output_lines.append(f"**Average Score:** {score_str}\n")

        if explanations := all_explanations.get(metric):
            explanation_summary = "\n".join(
                f"- [Score: {exp['score']}] {exp['explanation']}" for exp in explanations
            )
            output_lines.append(f"**All Explanations:**\n{explanation_summary}\n")

    return summary_data, "".join(output_lines)


def generate_gemini_analysis(
    summary_data: dict,
    analysis_content: str,
    context_content: dict,
    question_file_path: str,
    output_path: Path,
    consolidated_metrics_path: str,
) -> None:
    """Generates a detailed analysis using the Gemini 2.5 Pro model."""
    settings = get_settings()
    os.environ["GOOGLE_CLOUD_PROJECT"] = settings.GOOGLE_CLOUD_PROJECT
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

    model_id = "gemini-2.5-pro"
    prompter = GeminiAnalysisPrompter(
        summary_data,
        analysis_content,
        context_content,
        question_file_path,
        consolidated_metrics_path,
    )
    prompt = prompter.build_prompt()

    # Save the generated prompt for debugging and transparency
    prompt_output_path = output_path.parent / "gemini_prompt.txt"
    prompt_output_path.write_text(prompt, encoding="utf-8")
    print(f"Saved Gemini prompt to {prompt_output_path}")

    print("\n--- Calling Vertex AI to generate analysis ---")
    try:
        client = genai.Client(http_options=HttpOptions(api_version="v1"))
        response = client.models.generate_content(model=model_id, contents=prompt)

        print("\n--- Gemini 2.5 Pro Analysis ---")
        analysis_text = response.text
        print(analysis_text)

        output_path.write_text(analysis_text, encoding="utf-8")
        print(f"Analysis report saved to {output_path}")

    except Exception as e:
        print(f"An error occurred while calling the Vertex AI API: {e}")


def main():
    """Main function to orchestrate the analysis and reporting."""
    parser = argparse.ArgumentParser(
        description="Analyze evaluation results, generate reports, and upload to BigQuery.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Directory containing the evaluation results files.",
    )
    parser.add_argument(
        "--table-id",
        type=str,
        default="eval_results",
        help="The BigQuery table ID to upload results to.",
    )
    parser.add_argument(
        "--bq", action="store_true", help="If set, upload results to BigQuery."
    )
    parser.add_argument(
        "--dataset-id",
        type=str,
        default="danielazamora_tests_eval",
        help="The BigQuery dataset ID for evaluation results.",
    )
    parser.add_argument(
        "--skip-gemini-analysis",
        action="store_true",
        help="Skip the AI-powered analysis generation.",
    )
    args = parser.parse_args()

    summary_file = args.results_dir / "eval_summary.json"
    question_file = args.results_dir / "temp_consolidated_questions.json"
    try:
        results_file = next(args.results_dir.glob("evaluation_results_*.csv"))
    except StopIteration:
        print(f"Error: No 'evaluation_results_*.csv' file in '{args.results_dir}'")
        sys.exit(1)

    if not all([summary_file.exists(), results_file.exists(), question_file.exists()]):
        print(f"Error: Required input files not found in '{args.results_dir}'")
        sys.exit(1)

    results_df = pd.read_csv(results_file)
    qa_log_path = args.results_dir / "question_answer_log.md"
    generate_question_answer_log(results_file, qa_log_path)

    if not args.skip_gemini_analysis:
        summary, analysis = analyze_evaluation_results(summary_file, results_file)
        if summary and analysis:
            consolidated_metrics_file = args.results_dir / "temp_consolidated_metrics.json"
            context_files = {
                str(consolidated_metrics_file),
                "evaluation/scripts/deterministic_metrics.py",
                "data_explorer_agent/agent.py",
                "data_explorer_agent/prompts.py",
                "data_explorer_agent/sub_agents/sql_explorer/agent.py",
                "data_explorer_agent/sub_agents/sql_explorer/prompts.py",
                "data_explorer_agent/sub_agents/sql_explorer/sql_executor.py",
                "data_explorer_agent/sub_agents/visualization/agent.py",
                "data_explorer_agent/sub_agents/visualization/prompts.py",
                "data_explorer_agent/callbacks.py",
                "data_explorer_agent/tools.py",
                "evaluation/examples/example_trace.json",
                str(question_file),
            }
            context_content = {}
            for file_path in context_files:
                try:
                    context_content[file_path] = Path(file_path).read_text()
                except FileNotFoundError:
                    print(f"Warning: Context file not found at '{file_path}'")
                    context_content[file_path] = ""

            analysis_path = args.results_dir / "gemini_analysis.md"
            generate_gemini_analysis(
                summary,
                analysis,
                context_content,
                str(question_file),
                analysis_path,
                str(consolidated_metrics_file),
            )

    if args.bq:
        settings = get_settings()
        upload_to_bigquery(
            results_df,
            settings.GOOGLE_CLOUD_PROJECT,
            args.dataset_id,
            args.table_id,
        )

if __name__ == "__main__":
    main()