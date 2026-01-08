# Evaluation Pipeline

This document provides a comprehensive guide to the evaluation pipeline, a three-step process designed to test, measure, and analyze the performance of the Data Explorer Agent.

## Overview

The pipeline is orchestrated by three core scripts:

1.  `01_agent_interaction.py`: Runs a set of questions against the agent and records the interactions.
2.  `02_agent_run_eval.py`: Calculates performance metrics based on the recorded interactions.
3.  `03_analyze_eval_results.py`: Generates a detailed, AI-powered analysis of the results.

These scripts are designed to be scalable and configurable, allowing for the easy addition of new questions and metrics without modifying the core logic.

## Running the Pipeline

The easiest way to run the full pipeline is by using the `Makefile`.

### Quickstart

To run a full evaluation using the default golden questions and all available metrics, simply run:

```bash
make eval-full
```

This command will:
1.  Run the agent with the questions defined in `evaluation/datasets/su_golden_questions.json` and `evaluation/datasets/harmful_language_questions_su.json`.
2.  Calculate all defined metrics.
3.  Generate a detailed analysis report.
4.  Save all results to a new timestamped folder inside `evaluation/results/`.
5.  Upload the results to BigQuery.

### Advanced Usage

For more granular control, you can use the `make eval` command and pass arguments to each step of the pipeline.

```bash
make eval ARGS_1="..." ARGS_2="..." ARGS_3="..."
```

- `ARGS_1`: Arguments for `01_agent_interaction.py`.
- `ARGS_2`: Arguments for `02_agent_run_eval.py`.
- `ARGS_3`: Arguments for `03_analyze_eval_results.py`.

**Example:** Run a quick evaluation on a small sample of questions, calculate only deterministic metrics, and skip the final AI analysis.

```bash
make eval \
  ARGS_1="--questions-file evaluation/datasets/su_golden_questions.json --num-questions 5" \
  ARGS_2="--metric-filter metric_type:deterministic" \
  ARGS_3="--skip-gemini-analysis"
```

---

## The Three-Step Pipeline in Detail

### Step 1: `01_agent_interaction.py`

This script orchestrates running a set of questions against the agent and processing the results.

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--user-id` | The user ID for the evaluation session. | `eval_user` |
| `--base-url` | The base URL of the agent service. | `https://genai.ops.dematic.dev` |
| `--questions-file` | One or more paths to JSON files with test questions. (Required) | N/A |
| `--num-questions` | Number of questions to sample from each file. -1 for all. | `-1` |
| `--results-dir` | Directory to save results. | `evaluation/results` |
| `--user` | Username of the person running the script. | Current user |
| `--filter` | Filter questions by metadata (e.g., 'complexity:level1'). | N/A |
| `--runs` | Number of times to run each question. | `1` |
| `--skip-interactions` | Skip running new interactions and only process an existing CSV. | `False` |

**Usage Example:**

Run the evaluation with both golden questions and harmful language questions, sampling 10 from each, and filter for `level1` complexity.

```bash
uv run python evaluation/01_agent_interaction.py \
  --questions-file evaluation/datasets/su_golden_questions.json evaluation/datasets/harmful_language_questions_su.json \
  --num-questions 10 \
  --filter "complexity:level1" \
  --results-dir evaluation/results_level1_test
```

### Step 2: `02_agent_run_eval.py`

This script calculates performance metrics based on the interactions recorded in Step 1.

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--interaction-results-file` | Path to the processed CSV from Step 1. | `evaluation/results/interaction_su_golden_questions.csv` |
| `--results-dir` | Directory to save evaluation results. | `evaluation/results` |
| `--metrics-files` | One or more paths to metric definition JSON files. | `evaluation/metrics/metric_definitions.json` |
| `--scheduled` | Flag to indicate a scheduled run. | `False` |
| `--test-description` | A brief description of the test. | "Evaluation run from 02_agent_run_eval.py." |
| `--metric-filter` | Filter which metrics to run (e.g., 'metric_type:llm'). | N/A |
| `--dataset-id` | The BigQuery dataset for storing results. | `data_explorer_eval` |

**Usage Example:**

Run only the `correctness` and `end_to_end_success` metrics on a specific interaction file.

```bash
uv run python evaluation/02_agent_run_eval.py \
  --interaction-results-file evaluation/results_level1_test/processed_interaction_consolidated.csv \
  --results-dir evaluation/results_level1_test \
  --metrics-files evaluation/metrics/metric_definitions.json evaluation/metrics/metric_definitions_harmful_language.json \
  --metric-filter "metrics:correctness,end_to_end_success"
```

### Step 3: `03_analyze_eval_results.py`

This script generates a detailed, AI-powered analysis of the evaluation results.

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--results-dir` | Directory containing the results from Step 2. (Required) | N/A |
| `--table-id` | The BigQuery table ID to upload results to. | `eval_results` |
| `--bq` | If set, upload the final results to BigQuery. | `False` |
| `--dataset-id` | The BigQuery dataset to use. | `danielazamora_tests_eval` |
| `--skip-gemini-analysis` | Skip the AI-powered analysis generation. | `False` |

**Usage Example:**

Generate a full analysis and upload the results to a specific BigQuery table.

```bash
uv run python evaluation/03_analyze_eval_results.py \
  --results-dir evaluation/results_level1_test \
  --bq \
  --table-id my_test_run_results
```

---

## Extending the Evaluation Framework

The pipeline is designed to be easily extended without code changes.

### Adding New Questions

1.  **Location:** Add new JSON files to the `evaluation/datasets/` directory.
2.  **Schema:** The file must contain a top-level key `questions` which is a list of question objects. Each object must conform to the schema defined in `schemas/eval_dataset_schema.json`.
3.  **Key Fields:**
    *   `id`: A unique identifier for the question.
    *   `user_inputs`: A list containing the question prompt.
    *   `agents_evaluated`: A list of agent names that this question is designed to test (e.g., `["sql_explorer", "visualization"]`).
    *   `metadata`: Contains keys like `tier` ('positive' or 'negative') and `complexity`.
    *   `reference_data`: Contains the ground truth, such as the `reference_sql`.

### Adding New Metrics

1.  **Location:** Add new JSON files to the `evaluation/metrics/` directory.
2.  **Structure:** The file can contain a `metric_prefix` (e.g., "safety") and a dictionary of `metrics`.
3.  **Metric Definition:** Each metric must include:
    *   `metric_type`: Either `llm` (for AI-judged metrics) or `deterministic`.
    *   `template`: The prompt template for the LLM judge.
    *   `dataset_mapping`: This is the crucial part that connects the metric to the data. It maps placeholders in the `template` to columns in the interaction CSV.

---

## BigQuery Results Table

When the `--bq` flag is used, the final results are appended to a BigQuery table for historical analysis and visualization.

**Table Schema:**

The schema of the BigQuery table mirrors the columns of the final CSV file (`evaluation_results_consolidated.csv`). All columns are of type `STRING` to ensure maximum flexibility.

| Column Name | Description |
|---|---|
| `status` | A JSON string indicating the success or failure of the interaction script for this row. |
| `run_id` | A unique identifier for the specific run of a question. |
| `question_id` | The unique ID of the question from the dataset. |
| `agents_evaluated` | A JSON string listing the agents intended to be evaluated for this question. |
| `user_inputs` | A JSON string of the user's prompt(s). |
| `question_metadata` | A JSON string containing metadata about the question (e.g., tier, complexity). |
| `interaction_datetime` | Timestamp of when the interaction was run. |
| `session_id` | The session ID from the agent interaction. |
| `base_url` | The base URL of the agent service that was tested. |
| `ADK_USER_ID` | The user ID passed to the agent service. |
| `USER` | The user who ran the evaluation script. |
| `reference_data` | A JSON string containing the ground truth data for the question. |
| `missing_information` | A JSON string indicating if any information was missing for this run (e.g., session trace). |
| `latency_data` | A JSON string of the raw trace spans, used for performance analysis. |
| `trace_summary` | A JSON string providing a summary of the execution trace. |
| `session_trace` | A JSON string of the full, detailed session trace. |
| `final_session_state` | A JSON string of the agent's complete final session state. |
| `extracted_data` | A JSON string containing key-value pairs extracted from the `final_session_state` for easier access during evaluation. |
| `evaluation_datetime` | Timestamp of when the evaluation metrics were calculated. |
| `run_type` | The type of run, either 'manual' or 'scheduled'. |
| `experiment_id` | A unique ID for the entire evaluation experiment (grouping multiple runs). |
| `eval_results` | A JSON string containing the scores and explanations for all calculated metrics for this run. |