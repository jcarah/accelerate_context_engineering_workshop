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
Run and Process Agent Interactions for Evaluation (Step 1).

This script orchestrates the first phase of the evaluation pipeline. It has two main responsibilities:
1.  **Run Interactions:** It executes the `run_interactions.py` script, which takes a
    JSON file of questions, runs them against a specified agent endpoint, and
    records the raw interactions (e.g., user prompts, agent responses, session IDs)
    into a CSV file.
2.  **Process Interactions:** It then executes the `process_interactions.py` script,
    which enriches the raw interaction data by fetching detailed trace and session
    state information from the application's backend database.

This script also supports consolidating multiple question datasets into a single
run, allowing for representative sampling from each dataset.

The final output is a processed CSV file ready to be used by the next step in
the pipeline, `02_agent_run_eval.py`.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def load_and_consolidate_questions(
    question_files: List[Path], num_questions: int
) -> List[Dict[str, Any]]:
    """
    Load and consolidate questions from multiple JSON files using stratified sampling.

    If `num_questions` is specified, it takes a representative sample from each
    file, ensuring that different agent evaluation types are proportionally
    represented.

    Args:
        question_files: A list of paths to the JSON question files.
        num_questions: The number of questions to sample from each file.
                       If -1, all questions are taken.

    Returns:
        A consolidated list of question objects.
    """
    print("--- Loading and Consolidating Questions ---")
    consolidated_questions = []
    for file_path in question_files:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                questions = data.get("golden_questions") or data.get("questions", [])
                print(f"Loaded {len(questions)} questions from '{file_path}'.")

                if 0 < num_questions < len(questions):
                    print(f"  -> Performing stratified sampling for {num_questions} questions.")
                    df = pd.DataFrame(questions)
                    # Create a hashable group key from the list of agents evaluated.
                    df["agent_group"] = df["agents_evaluated"].apply(lambda x: tuple(sorted(x)))

                    # Calculate how many questions to sample from each agent group.
                    group_counts = df["agent_group"].value_counts()
                    proportions = group_counts / len(df)
                    samples_per_group = (proportions * num_questions).round().astype(int)

                    # Adjust for rounding errors to ensure the total sample size is correct.
                    diff = num_questions - samples_per_group.sum()
                    if diff != 0:
                        largest_group = samples_per_group.idxmax()
                        samples_per_group[largest_group] += diff
                    
                    # Perform the sampling from each group.
                    sampled_df = df.groupby("agent_group", group_keys=False).apply(
                        lambda g: g.sample(n=min(len(g), int(samples_per_group[g.name])), random_state=42),
                        include_groups=False
                    )
                    
                    sampled_questions = sampled_df.to_dict("records")
                    consolidated_questions.extend(sampled_questions)
                    print(f"  -> Sampled {len(sampled_questions)} questions to maintain agent representation.")

                else:
                    # If num_questions is -1 or >= total questions, take all.
                    consolidated_questions.extend(questions)

        except FileNotFoundError:
            print(f"Error: Questions file not found: {file_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Could not parse JSON from file: {file_path}")
            sys.exit(1)

    print(f"Total consolidated questions to run: {len(consolidated_questions)}")
    return consolidated_questions


def main():
    """Main function to orchestrate the interaction and processing scripts."""
    parser = argparse.ArgumentParser(
        description="Run and process interactions for the Data Explorer Agent.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="eval_user",
        help="The user ID to associate with the evaluation session.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="https://genai.ops.dematic.dev",
        help="The base URL of the agent service.",
    )
    parser.add_argument(
        "--questions-file",
        type=Path,
        nargs="+",
        required=True,
        help="One or more paths to the JSON files with test questions.",
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=-1,
        help="Number of questions to run from each file. -1 for all.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("evaluation/results"),
        help="Directory to save interaction and processing results.",
    )
    parser.add_argument(
        "--user",
        type=str,
        default=os.environ.get("USER") or os.environ.get("GITLAB_USER_LOGIN") or "ci-runner",
        help="The username of the person running the script, for tracking.",
    )
    parser.add_argument(
        "--filter",
        action="append",
        dest="metadata_filters",
        help="Filter questions by metadata (e.g., 'complexity:level1'). Can be used multiple times.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of times to run the evaluation for each question.",
    )
    parser.add_argument(
        "--skip-interactions",
        action="store_true",
        help="Skip running new interactions and only process an existing CSV file.",
    )
    args = parser.parse_args()

    args.results_dir.mkdir(parents=True, exist_ok=True)

    # --- Consolidate questions and prepare for interaction ---
    consolidated_questions = load_and_consolidate_questions(
        args.questions_file, args.num_questions
    )

    # Gracefully exit if no questions are found to avoid running empty interactions.
    if not consolidated_questions:
        print("\nNo questions found to run after consolidation and filtering. Exiting.")
        sys.exit(0)
    
    # Save consolidated questions to a temporary file to pass to the next script.
    temp_questions_path = args.results_dir / "temp_consolidated_questions.json"
    with open(temp_questions_path, "w") as f:
        json.dump({"questions": consolidated_questions}, f, indent=4)
    print(f"Consolidated questions saved to '{temp_questions_path}'")

    # Define output CSV path
    interaction_csv_path = args.results_dir / "interaction_consolidated.csv"

    # --- Step 1: Run Interactions ---
    if not args.skip_interactions:
        run_interactions_cmd = [
            sys.executable,
            "evaluation/scripts/run_interactions.py",
            "--user_id", args.user_id,
            "--base_url", args.base_url,
            "--questions_file", str(temp_questions_path),
            "--num_questions", "-1",  # Use -1 as we've already sampled
            "--results_dir", str(args.results_dir),
            "--user", args.user,
            "--runs", str(args.runs),
            "--output-csv", str(interaction_csv_path),
        ]
        if args.metadata_filters:
            for f in args.metadata_filters:
                run_interactions_cmd.extend(["--filter", f])

        print("\n--- Running Interactions ---")
        print(f"Command: {' '.join(run_interactions_cmd)}")
        try:
            subprocess.run(run_interactions_cmd, check=True, text=True)
            print("Interaction script completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error running interaction script: {e}")
            sys.exit(1)

    # --- Step 2: Process Interactions ---
    if not interaction_csv_path.exists():
        print(f"Error: Interaction CSV file not found at '{interaction_csv_path}'. Cannot run processing.")
        sys.exit(1)

    process_interactions_cmd = [
        sys.executable,
        "evaluation/scripts/process_interactions.py",
        "--input-csv", str(interaction_csv_path),
        "--results_dir", str(args.results_dir),
    ]
    print("\n--- Processing Interactions ---")
    print(f"Command: {' '.join(process_interactions_cmd)}")
    try:
        subprocess.run(process_interactions_cmd, check=True, text=True)
        print("Processing script completed successfully.")
        print(f"\nFinal processed data saved in '{args.results_dir}'")
    except subprocess.CalledProcessError as e:
        print(f"Error running processing script: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
