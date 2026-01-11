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
Evaluate Agent Interactions using Vertex AI Evaluation.

This script takes the output from the `01_agent_interaction.py` script (a CSV file
of agent interactions) and runs evaluations on it based on a set of metric
definitions. It supports both LLM-based and deterministic metrics.

Key functionalities:
- Loads agent interaction data from a CSV file.
- Consolidates metric definitions from one or more JSON files, applying prefixes.
- Filters metrics based on user-provided criteria (e.g., by metric type or agent).
- Prepares the data for evaluation by normalizing nested JSON and mapping columns.
- Runs evaluations using the Vertex AI SDK's EvalTask in parallel for speed.
- Calculates deterministic metrics for objective, reproducible measurements.
- Aggregates results, generates a summary, and saves them to CSV and JSON files.

This script is designed to be modular and configurable, allowing for flexible
evaluation of different agents and scenarios.
"""

import argparse
import concurrent.futures
import json
import logging
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from dotenv import load_dotenv
from google.cloud import aiplatform
from vertexai import Client, types
from vertexai.preview.evaluation import PointwiseMetric
from google.genai import types as genai_types
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Automatically load environment variables from .env file
load_dotenv(override=True)

# Add project root to Python path to allow importing from other modules.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import deterministic metrics calculator and registry
from evaluation.scripts.deterministic_metrics import evaluate_deterministic_metrics, DETERMINISTIC_METRICS
# Import robust data mapper
from evaluation.utils.data_mapper import map_dataset_columns, robust_json_loads

# --- Configuration Management ---

class EvalConfig(BaseSettings):
    """
    Centralized configuration for the evaluation pipeline using Pydantic.
    Reads from environment variables and provides type safety.
    """
    model_config = SettingsConfigDict(
        env_prefix="EVAL_", 
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Managed Metric Names
    METRIC_TOOL_USE_QUALITY: str = "TOOL_USE_QUALITY"
    METRIC_GENERAL_QUALITY: str = "GENERAL_QUALITY"
    
    # Standard Dataset Column Names
    COL_PROMPT: str = "prompt"
    COL_RESPONSE: str = "response"
    COL_INTERMEDIATE_EVENTS: str = "intermediate_events"
    COL_TOOL_USAGE: str = "tool_usage"
    
    # Execution Settings
    GOOGLE_CLOUD_PROJECT: Optional[str] = Field(default=None, description="GCP Project ID")
    GOOGLE_CLOUD_LOCATION: str = Field(default="us-central1", description="GCP Region")
    MAX_RETRIES: int = Field(default=3, description="Max retries for LLM calls")
    RETRY_DELAY_SECONDS: int = Field(default=5, description="Base delay for retries")
    MAX_WORKERS: int = Field(default=4, description="Threads for parallel evaluation")
    
    # Data Mappings
    EXTRACTED_DATA_PREFIX: str = "extracted_data"
    REFERENCE_DATA_PREFIX: str = "reference_data"

# Initialize Config
CONFIG = EvalConfig()

# Setup Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agent_eval")


# --- Core Logic Functions ---

def parse_eval_result(result: Any, metric_name: str, metric_df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes result parsing across different Vertex AI SDK versions.
    Extracts scores and explanations into a flat DataFrame.
    """
    rows = []

    # Standard SDK / Legacy Path
    if hasattr(result, "metrics_table"):
        df = result.metrics_table
        df["original_index"] = metric_df.index
        return df

    # Preview SDK Path
    if hasattr(result, "eval_case_results"):
        found_key = metric_name
        if result.eval_case_results:
            first_case = result.eval_case_results[0]
            available_metrics = {}
            if hasattr(first_case, "metrics") and first_case.metrics:
                available_metrics = first_case.metrics
            elif (
                hasattr(first_case, "response_candidate_results")
                and first_case.response_candidate_results
            ):
                available_metrics = getattr(
                    first_case.response_candidate_results[0], "metric_results", {}
                )

            for k in [metric_name, metric_name.lower(), metric_name.upper()]:
                if k in available_metrics:
                    found_key = k
                    break
            else:
                if available_metrics:
                    found_key = list(available_metrics.keys())[0]

        for idx, case_result in enumerate(result.eval_case_results):
            original_idx = metric_df.index[idx]
            val = None

            if (
                hasattr(case_result, "response_candidate_results")
                and case_result.response_candidate_results
            ):
                val = getattr(
                    case_result.response_candidate_results[0], "metric_results", {}
                ).get(found_key)
            if val is None:
                val = getattr(case_result, "metrics", {}).get(found_key)

            rows.append(
                {
                    "original_index": original_idx,
                    f"{metric_name}/score": getattr(val, "score", None)
                    if val
                    else None,
                    f"{metric_name}/explanation": getattr(val, "explanation", None)
                    if val
                    else None,
                }
            )

    return pd.DataFrame(rows)


def run_single_metric_evaluation(
    task_args: Tuple,
) -> Tuple[Optional[pd.DataFrame], str]:
    """Worker function for parallel evaluation."""
    eval_dataset, metric_obj, metric_df, metric_name, client = task_args

    for attempt in range(CONFIG.MAX_RETRIES):
        try:
            logger.info(f"Starting evaluation: {metric_name} (Attempt {attempt + 1})")
            result = client.evals.evaluate(dataset=eval_dataset, metrics=[metric_obj])
            parsed_df = parse_eval_result(result, metric_name, metric_df)
            logger.info(f"Finished evaluation: {metric_name}")
            return parsed_df, metric_name
        except Exception as e:
            logger.error(f"Failed '{metric_name}': {e}")
            if attempt < CONFIG.MAX_RETRIES - 1:
                time.sleep(CONFIG.RETRY_DELAY_SECONDS * (2**attempt))
            else:
                logger.critical(f"'{metric_name}' exhausted retries.")

    return None, metric_name


def load_and_consolidate_metrics(metric_files: List[str]) -> Dict[str, Any]:
    """Load and consolidate metric definitions from multiple JSON files."""
    consolidated = {}
    logger.info("--- Consolidating Metric Definitions ---")
    for file_path in metric_files:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                prefix = data.get("metric_prefix", "").lstrip("_")
                metrics = data.get("metrics", {})
                for name, definition in metrics.items():
                    full_name = f"{prefix}_{name}".lstrip("_")
                    consolidated[full_name] = definition
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            sys.exit(1)
    logger.info(f"Consolidated {len(consolidated)} metrics.")
    return consolidated


def parse_metric_filters(filter_strings: Optional[List[str]]) -> Dict[str, List[str]]:
    """Parse metric filter strings from command-line arguments."""
    filters = {}
    if not filter_strings:
        return filters
    for filter_string in filter_strings:
        if ":" not in filter_string:
            logger.warning(f"Invalid filter format '{filter_string}'.")
            continue
        key, values_str = filter_string.split(":", 1)
        values = [v.strip() for v in values_str.split(",")]
        if key in filters:
            filters[key].extend(values)
        else:
            filters[key] = values
    return filters


def filter_metrics_by_criteria(
    metric_definitions: Dict[str, Any], filters: Dict[str, List[str]]
) -> Dict[str, Any]:
    """Filter metric definitions based on specified criteria."""
    if not filters:
        return metric_definitions
    filtered = {}
    for name, info in metric_definitions.items():
        match = True
        for key, vals in filters.items():
            val_to_check = (
                info.get("metric_type", "llm")
                if key == "metric_type"
                else info.get("agents", ["data_explorer_agent"])
                if key == "agents"
                else name
                if key == "metrics"
                else info.get(key)
            )
            if val_to_check is None:
                match = False
                break
            check_list = (
                val_to_check if isinstance(val_to_check, list) else [str(val_to_check)]
            )
            if not any(str(v) in vals for v in check_list):
                match = False
                break
        if match:
            filtered[name] = info
    return filtered


def save_metrics_summary(
    df: pd.DataFrame,
    results_dir: Path,
    experiment_id: str,
    run_type: str,
    test_description: str,
) -> None:
    """Calculate and save a summary of metrics and latency."""
    logger.info("--- Generating Metrics Summary ---")
    grouped = df.groupby("question_id")
    all_question_summaries = []
    per_metric_scores = defaultdict(list)

    for question_id, group in grouped:
        group["eval_results"] = group["eval_results"].apply(robust_json_loads)
        det_metrics, llm_metrics = {}, {}
        for result_dict in group["eval_results"].dropna():
            if not isinstance(result_dict, dict):
                continue
            for metric, val in result_dict.items():
                if not isinstance(val, dict):
                    continue
                is_det = metric in DETERMINISTIC_METRICS or any(
                    metric.endswith(f"_{k}") for k in DETERMINISTIC_METRICS
                )
                if "score" in val and val["score"] is not None:
                    try:
                        s = float(val["score"])
                        if not math.isnan(s):
                            per_metric_scores[metric].append(s)
                            if "details" in val and isinstance(val["details"], dict):
                                for k, v in val["details"].items():
                                    if isinstance(v, (int, float)) and not isinstance(
                                        v, bool
                                    ):
                                        per_metric_scores[f"{metric}.{k}"].append(v)
                    except (ValueError, TypeError):
                        pass
                if is_det:
                    det_metrics[metric] = val.get("details") or val.get("score")
                else:
                    llm_metrics[metric] = {
                        k: val[k] for k in ["score", "explanation"] if k in val
                    }
        metadata = robust_json_loads(group.iloc[0].get("question_metadata", "{}")) or {}
        summary = {
            "question_id": question_id,
            "runs": len(group),
            "deterministic_metrics": det_metrics,
            "llm_metrics": llm_metrics,
        }
        summary.update(metadata)
        all_question_summaries.append(summary)

    det_summary, llm_summary = {}, {}
    for metric, scores in per_metric_scores.items():
        if not scores:
            continue
        avg = sum(scores) / len(scores)
        if any(metric.startswith(f"{k}.") for k in DETERMINISTIC_METRICS):
            det_summary[metric] = avg
        elif metric in DETERMINISTIC_METRICS:
            continue
        else:
            llm_summary[metric] = avg

    output = {
        "experiment_id": experiment_id,
        "run_type": run_type,
        "test_description": test_description,
        "interaction_datetime": datetime.now().isoformat(),
        "overall_summary": {
            "deterministic_metrics": det_summary,
            "llm_based_metrics": llm_summary,
        },
        "per_question_summary": all_question_summaries,
    }
    with open(results_dir / "eval_summary.json", "w") as f:
        json.dump(output, f, indent=4)
    logger.info(f"Metrics summary saved to {results_dir / 'eval_summary.json'}")


def main():
    parser = argparse.ArgumentParser(
        description="Parallelized Agent Evaluation Pipeline."
    )
    parser.add_argument("--interaction-results-file", type=Path, required=True)
    parser.add_argument("--metrics-files", type=str, nargs="+", required=True)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--input-label", type=str, default="manual")
    parser.add_argument(
        "--test-description", type=str, default="Automated evaluation run."
    )
    parser.add_argument("--metric-filter", action="append", dest="metric_filters")
    args = parser.parse_args()

    # --- Initialization ---
    project_id = CONFIG.GOOGLE_CLOUD_PROJECT or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT not set.")
        sys.exit(1)

    aiplatform.init(project=project_id, location=CONFIG.GOOGLE_CLOUD_LOCATION)
    client = Client(project=project_id, location=CONFIG.GOOGLE_CLOUD_LOCATION)

    # --- Data Loading & Preparation ---
    interaction_results = pd.read_csv(
        args.interaction_results_file, dtype={"question_id": str}
    )
    results_dir = args.results_dir or args.interaction_results_file.parent
    results_dir.mkdir(parents=True, exist_ok=True)
    metric_definitions = load_and_consolidate_metrics(args.metrics_files)
    if args.metric_filters:
        filters = parse_metric_filters(args.metric_filters)
        metric_definitions = filter_metrics_by_criteria(metric_definitions, filters)

    original_df = interaction_results.copy()
    for col in [
        "extracted_data",
        "reference_data",
        "latency_data",
        "agents_evaluated",
        "user_inputs",
        "session_trace",
        "final_session_state",
    ]:
        if col in interaction_results.columns:
            interaction_results[col] = interaction_results[col].apply(robust_json_loads)

    dfs = [interaction_results]
    for prefix in [CONFIG.EXTRACTED_DATA_PREFIX, CONFIG.REFERENCE_DATA_PREFIX]:
        if prefix in interaction_results.columns:
            dfs.append(
                pd.json_normalize(interaction_results[prefix]).add_prefix(f"{prefix}.")
            )
    interaction_results = pd.concat(dfs, axis=1)

    # --- Evaluation Phase ---
    base_run_id = f"eval-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    all_llm_results, det_results_map = [], defaultdict(dict)

    logger.info("--- Phase 1: Deterministic Metrics ---")
    for index, row in interaction_results.iterrows():
        try:
            if not row.get("final_session_state"):
                continue
            res = evaluate_deterministic_metrics(
                session_state=robust_json_loads(row["final_session_state"]),
                session_trace=robust_json_loads(row.get("session_trace")) or [],
                agents_evaluated=robust_json_loads(row.get("agents_evaluated", "[]"))
                or [],
                reference_data=robust_json_loads(row.get("reference_data")) or {},
                question_metadata=robust_json_loads(row.get("question_metadata", "{}"))
                or {},
                metrics_to_run=list(DETERMINISTIC_METRICS.keys()),
                latency_data=robust_json_loads(row.get("latency_data")) or [],
            )
            det_results_map[index].update(res)
        except Exception as e:
            logger.error(f"Row {index} deterministic error: {e}")

    logger.info("--- Phase 2: Parallel LLM Evaluation ---")
    metrics_by_agent = defaultdict(list)
    for name, info in metric_definitions.items():
        for agent in info.get("agents", ["data_explorer_agent"]):
            metrics_by_agent[agent].append((name, info))

    for agent, metrics in metrics_by_agent.items():
        mask = (
            interaction_results["agents_evaluated"].apply(
                lambda x: agent in (x if isinstance(x, list) else [x]) if x else False
            )
            if agent != "data_explorer_agent"
            else [True] * len(interaction_results)
        )
        agent_df = interaction_results[mask].copy()
        if agent_df.empty:
            continue

        eval_tasks = []
        for metric_name, info in metrics:
            if info.get("metric_type") == "deterministic":
                continue
            
            # --- Robust Data Mapping Logic (Extracted) ---
            eval_dataset = map_dataset_columns(
                agent_df, 
                original_df, 
                info.get("dataset_mapping", {}), 
                metric_name, 
                CONFIG.METRIC_TOOL_USE_QUALITY,
                is_managed_metric=info.get("is_managed", False)
            )

            if eval_dataset.empty or len(eval_dataset.columns) == 0:
                logger.warning(f"Empty dataset for {metric_name}. Skipping.")
                continue


            if info.get("is_managed"):
                m_name = info.get("managed_metric_name", "").upper()
                metric_obj = getattr(
                    types.RubricMetric, m_name, None
                ) or PointwiseMetric(
                    metric=metric_name, metric_prompt_template=info.get("template", "")
                )
            else:
                metric_obj = types.LLMMetric(
                    name=metric_name,
                    prompt_template=types.MetricPromptBuilder(
                        instruction=info.get("instruction", ""),
                        criteria=info.get("criteria", {}),
                        rating_scores=info.get("rating_scores", {}),
                    ),
                )

            eval_tasks.append((eval_dataset, metric_obj, agent_df, metric_name, client))

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=CONFIG.MAX_WORKERS
        ) as executor:
            future_to_metric = {
                executor.submit(run_single_metric_evaluation, t): t[3]
                for t in eval_tasks
            }
            for future in concurrent.futures.as_completed(future_to_metric):
                res, m_name = future.result()
                if res is not None:
                    all_llm_results.append((res, m_name))

    final_df = original_df.copy()
    eval_results_data = [{} for _ in range(len(final_df))]
    for index, results in det_results_map.items():
        if index < len(eval_results_data):
            eval_results_data[index].update(results)
    for result_df, metric_name in all_llm_results:
        for _, row in result_df.iterrows():
            idx = int(row["original_index"])
            if idx < len(eval_results_data):
                eval_results_data[idx][metric_name] = {
                    "score": row[f"{metric_name}/score"],
                    "explanation": row[f"{metric_name}/explanation"],
                }

    final_df["eval_results"] = [json.dumps(r) if r else None for r in eval_results_data]
    out_path = (
        results_dir
        / f"evaluation_results_{args.interaction_results_file.stem.replace('processed_interaction_', '')}.csv"
    )
    final_df.to_csv(out_path, index=False)
    logger.info(f"Pipeline complete. Results: {out_path}")
    save_metrics_summary(
        final_df, results_dir, base_run_id, args.input_label, args.test_description
    )


if __name__ == "__main__":
    main()
