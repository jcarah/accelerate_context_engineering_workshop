"""
Summary builder for deterministic evaluation metrics.

This script reads processed interaction CSVs, runs the deterministic metrics suite,
and prints (and optionally writes) per-dataset summaries that highlight the new
composite `deterministic_accuracy` metric alongside the component metrics.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from evaluation.scripts.deterministic_metrics import evaluate_deterministic_metrics

DATASET_CONFIGS = {
    "su": {
        "interaction": "processed_interaction_su_golden_questions.csv",
        "interaction_fallback": "interaction_su_golden_questions.csv",
        "llm": "eval_result_su_golden_bank.csv",
        "llm_fallback": "eval_result_golden_bank.csv",
    },
    "tti": {
        "interaction": "processed_interaction_tti_golden_questions.csv",
        "interaction_fallback": "interaction_tti_golden_questions.csv",
        "llm": "eval_result_tti_golden_bank.csv",
        "llm_fallback": "eval_result_golden_bank.csv",
    },
}

MAX_FAILURES_TO_DISPLAY = 10

METRIC_THRESHOLDS = {
    "end_to_end_success": 1.0,
    "deterministic_accuracy": 1.0,
    "sql_execution_success": 1.0,
    "sql_generation_success": 1.0,
    "rag_retrieval_success": 1.0,
    "nl_sql_output_groundedness": 0.8,
    "sql_result_exact_match": 1.0,
}

METRIC_DEFINITIONS = {
    "nl_sql_output_groundedness": {"accuracy_threshold": 0.8}
}


def safe_json_load(value: Any) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """Handle NaN/null strings when loading JSON from DataFrame cells."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in {"nan", "null"}:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def load_llm_scores(llm_eval_file: str) -> Dict[str, Any]:
    """Parse the LLM evaluation CSV into a map of question_id -> scores JSON."""
    if not llm_eval_file or not os.path.exists(llm_eval_file):
        return {}

    llm_df = pd.read_csv(llm_eval_file)
    scores: Dict[str, Any] = {}
    for _, row in llm_df.iterrows():
        try:
            payload = json.loads(row.iloc[-1])
            question_id = row.get("question_id")
            if question_id:
                scores[question_id] = payload
        except (json.JSONDecodeError, IndexError):
            continue
    return scores


def find_data_file(base_dir: str, primary_name: str, fallback_name: Optional[str] = None) -> str:
    """Return the primary path if it exists, otherwise use the fallback if provided."""
    primary_path = os.path.join(base_dir, primary_name)
    if os.path.exists(primary_path):
        return primary_path
    if fallback_name:
        fallback_path = os.path.join(base_dir, fallback_name)
        if os.path.exists(fallback_path):
            return fallback_path
    return primary_path


def is_metric_pass(metric_name: str, score: float) -> bool:
    threshold = METRIC_THRESHOLDS.get(metric_name, 1.0)
    try:
        return float(score) >= threshold
    except (TypeError, ValueError):
        return False


def write_summary(output_dir: str, dataset_name: str, content: str) -> None:
    if not output_dir:
        return
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    summary_path = Path(output_dir) / f"deterministic_metrics_summary_{dataset_name.lower()}.md"
    with open(summary_path, "w") as out_file:
        out_file.write(content)
    print(f"\nSummary written to {summary_path}")


def run_and_summarize(
    interaction_file: str,
    llm_eval_file: str,
    dataset_name: str,
    output_dir: Optional[str] = None,
) -> None:
    if not os.path.exists(interaction_file):
        print(f"\n{'='*80}")
        print(
            f"SKIPPING {dataset_name.upper()}: Interaction file not found at {interaction_file}"
        )
        print(f"{'='*80}")
        return

    interactions = pd.read_csv(interaction_file)
    llm_scores = load_llm_scores(llm_eval_file)

    metric_counts = defaultdict(lambda: {"pass": 0, "total": 0})
    det_tier_counts = defaultdict(lambda: {"pass": 0, "total": 0})
    det_level_counts = defaultdict(lambda: {"pass": 0, "total": 0})
    deterministic_failures: List[str] = []

    print(f"\n{'='*80}")
    print(f"RUNNING COMBINED EVALUATION FOR: {dataset_name.upper()}")
    print(f"Loaded {len(interactions)} interactions from {interaction_file}")
    print(f"{'='*80}")

    for idx, row in interactions.iterrows():
        question_id = row.get("question_id", f"row_{idx}")
        metadata = safe_json_load(row.get("question_metadata")) or {}
        tier = metadata.get("tier", "unknown")
        complexity = metadata.get("complexity", "unknown")
        session_state = safe_json_load(row.get("final_session_state"))
        session_trace = safe_json_load(row.get("session_trace"))
        agents_evaluated = safe_json_load(row.get("agents_evaluated")) or []
        reference_data = safe_json_load(row.get("reference_data")) or {}

        if not session_state:
            print(f"  > Missing session state for {question_id}, skipping metric evaluation.")
            continue

        session_trace = session_trace or []

        det_results = evaluate_deterministic_metrics(
            session_state=session_state,
            session_trace=session_trace,
            agents_evaluated=agents_evaluated,
            question_metadata=metadata,
            reference_data=reference_data,
            metric_definitions=METRIC_DEFINITIONS,
        )

        for metric_name in METRIC_THRESHOLDS:
            result = det_results.get(metric_name)
            if not result:
                continue
            metric_counts[metric_name]["total"] += 1
            passed = is_metric_pass(metric_name, result["score"])
            if passed:
                metric_counts[metric_name]["pass"] += 1
            if metric_name == "deterministic_accuracy":
                det_tier_counts[tier]["total"] += 1
                det_level_counts[complexity]["total"] += 1
                if passed:
                    det_tier_counts[tier]["pass"] += 1
                    det_level_counts[complexity]["pass"] += 1
                else:
                    deterministic_failures.append(question_id)

        if det_results.get("end_to_end_success", {}).get("score", 0.0) < 1.0:
            print(f"   > Execution failed for question {question_id}")

    summary_lines = [
        f"## Deterministic Metrics Summary — {dataset_name.upper()}",
        f"*Interactions processed*: {len(interactions)}",
        f"*LLM correctness data*: {'available' if llm_scores else 'missing'}",
        "",
        "### Metric pass rates",
    ]

    for metric_name in metric_counts:
        counts = metric_counts[metric_name]
        total = counts["total"]
        if total == 0:
            continue
        pass_rate = (counts["pass"] / total) * 100
        summary_lines.append(
            f"- **{metric_name}**: {pass_rate:.2f}% pass ({counts['pass']}/{total})"
        )

    if det_tier_counts:
        summary_lines.append("\n### Deterministic accuracy by tier")
        for tier, counts in sorted(det_tier_counts.items()):
            total = counts["total"]
            pass_rate = (counts["pass"] / total) * 100 if total else 0
            summary_lines.append(
                f"- Tier '{tier}': {pass_rate:.2f}% pass ({counts['pass']}/{total})"
            )

    if det_level_counts:
        summary_lines.append("\n### Deterministic accuracy by complexity level")
        for level, counts in sorted(det_level_counts.items()):
            total = counts["total"]
            pass_rate = (counts["pass"] / total) * 100 if total else 0
            summary_lines.append(
                f"- Level '{level}': {pass_rate:.2f}% pass ({counts['pass']}/{total})"
            )

    if deterministic_failures:
        summary_lines.append(
            f"\n### Deterministic accuracy failed for {len(deterministic_failures)} questions"
        )
        summary_lines.extend(
            f"- {qid}" for qid in deterministic_failures[:MAX_FAILURES_TO_DISPLAY]
        )
        if len(deterministic_failures) > MAX_FAILURES_TO_DISPLAY:
            summary_lines.append(
                f"- ...and {len(deterministic_failures) - MAX_FAILURES_TO_DISPLAY} more"
            )

    if llm_scores:
        correctness = defaultdict(lambda: {"correct": 0, "incorrect": 0})
        for idx, row in interactions.iterrows():
            question_id = row.get("question_id")
            tier = (
                safe_json_load(row.get("question_metadata")) or {}
            ).get("tier", "unknown")
            if question_id in llm_scores:
                bq_sim_score = llm_scores[question_id].get(
                    "bq_response_similarity", {}
                ).get("score", 0.0)
                bucket = "correct" if bq_sim_score >= 0.8 else "incorrect"
                correctness[tier][bucket] += 1

        if correctness:
            summary_lines.append("\n### LLM-judged correctness by tier")
            for tier, counts in sorted(correctness.items()):
                total = counts["correct"] + counts["incorrect"]
                if total == 0:
                    continue
                rate = (counts["correct"] / total) * 100
                summary_lines.append(
                    f"- Tier '{tier}': {rate:.2f}% correct ({counts['correct']}/{total})"
                )

    summary_text = "\n".join(summary_lines) + "\n"
    print(summary_text)
    write_summary(output_dir, dataset_name, summary_text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize deterministic metrics for processed evaluation runs."
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="evaluation/results_local",
        help="Directory containing interaction/LLM CSV files.",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["su"],
        help="List of dataset keys (su, tti) to summarize.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/analysis_reports",
        help="Directory where markdown summaries will be written.",
    )
    args = parser.parse_args()

    for dataset in args.datasets:
        config = DATASET_CONFIGS.get(dataset.lower())
        if not config:
            print(f"Unknown dataset '{dataset}'. Known datasets: {list(DATASET_CONFIGS)}")
            continue

        interaction_path = find_data_file(
            args.results_dir, config["interaction"], config.get("interaction_fallback")
        )
        llm_path = find_data_file(args.results_dir, config["llm"], config.get("llm_fallback"))

        run_and_summarize(interaction_path, llm_path, dataset.upper(), args.output_dir)


if __name__ == "__main__":
    main()

