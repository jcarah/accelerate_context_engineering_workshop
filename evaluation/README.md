# Agent Evaluation Pipeline

A professional, scalable, and agent-agnostic framework for evaluating AI agents on Google Cloud.

## 🚀 Overview

This pipeline automates the end-to-end evaluation process:
1.  **Interaction:** Runs a dataset of questions against your agent API (concurrently).
2.  **Evaluation:** Grades the interactions using both **Deterministic** logic (cost, latency) and **LLM-as-a-Judge** metrics (correctness, tool usage).
3.  **Analysis:** Generates a human-readable Q&A log and an AI-powered Root Cause Analysis report.

### ✨ Key Features
*   **Parallel Execution:** Runs LLM metrics concurrently, significantly reducing evaluation time.
*   **Robust Multi-Turn Support:** Automatically flattens conversation history to ensure compatibility with Vertex AI SDK metrics.
*   **Hybrid Metrics:** Supports both Google-managed rubrics (Safety, Quality) and fully custom business logic rubrics.
*   **Retry Logic:** Built-in exponential backoff for resilient API interactions.

---

## 📂 Project Structure

| Directory | Purpose |
| :--- | :--- |
| **`datasets/`** | Contains the **Golden Datasets** (JSON) defining questions and expected answers. This is your input source. |
| **`metrics/`** | Contains the **Rubrics** (JSON) for LLM-based grading. Defines what "Success" looks like for your agent. |
| **`scripts/`** | Contains the core logic for metrics and interactions. `deterministic_metrics.py` lives here. |
| **`tests/`** | Unit tests for the *evaluation framework itself* (not the agents). Ensures the pipeline is reliable. |
| **`results/`** | The output directory. See [OUTPUTS.md](OUTPUTS.md) for a detailed breakdown of every generated file. |

---

## 🔄 Workflow & Key Files

| Step | Script | Description |
| :--- | :--- | :--- |
| **1** | `01_agent_interaction.py` | **Data Collection.** Orchestrates `scripts/run_interactions.py` to hit your agent's API in parallel (`asyncio`). Enriches raw logs with traces and state variables via `scripts/process_interactions.py`. |
| **2** | `02_agent_run_eval.py` | **Scoring.** Runs the evaluation suite. Uses `ThreadPoolExecutor` to run Vertex AI evaluations in parallel. Manages configuration via `Pydantic`. |
| **3** | `03_analyze_eval_results.py` | **Insight Generation.** Produces `question_answer_log.md` (readable transcript) and uses Gemini to write `gemini_analysis.md` (technical diagnosis). |

---

## ⚙️ Configuration

The pipeline uses a **layered configuration** strategy (CLI > Env Vars > Defaults).

### Environment Variables (`.env`)
Define these in `evaluation/.env` for infrastructure settings:

```ini
# Required
EVAL_GOOGLE_CLOUD_PROJECT=your-project-id
EVAL_GOOGLE_CLOUD_LOCATION=us-central1

# Performance Tuning
EVAL_MAX_WORKERS=4          # Number of parallel evaluation threads
EVAL_MAX_RETRIES=3          # Retries for failed LLM calls
EVAL_RETRY_DELAY_SECONDS=5  # Base delay for exponential backoff
```

### CLI Arguments
Used for run-specific inputs.

**Step 1: Interaction**
```bash
uv run python 01_agent_interaction.py \
  --app-name customer_service \
  --base-url http://localhost:8080 \
  --questions-file datasets/your_data.json
```

**Step 2: Evaluation**
```bash
uv run python 02_agent_run_eval.py \
  --interaction-results-file results/.../processed_interaction.csv \
  --metrics-files metrics/metric_definitions_customer_service.json
```

**Step 3: Analysis**
```bash
uv run python 03_analyze_eval_results.py \
  --results-dir results/customer_service/2026...
```

---

## 📊 Outputs & Artifacts

All results are saved in `evaluation/results/<app_name>/<timestamp>/`.

| File | Description |
| :--- | :--- |
| `processed_interaction_*.csv` | **Raw Data.** The inputs, agent responses, traces, and state variables used for grading. |
| `evaluation_results_*.csv` | **Graded Data.** The processed interactions enriched with metric scores and explanations. |
| `eval_summary.json` | **Aggregated Stats.** Mean scores, costs, latencies, and per-question breakdowns. |
| `question_answer_log.md` | **Transcript.** A readable Markdown log of every Q&A pair, reference data, and extracted state. |
| `gemini_analysis.md` | **Diagnosis.** An AI-generated report identifying root causes of failures and performance trends. |

For a complete data dictionary, see **[OUTPUTS.md](OUTPUTS.md)**.

---

## 🛠️ Developer Guide: Adding a New Agent

To evaluate a new agent (e.g., "Travel Booker"), follow these steps:

### 1. Create a Golden Dataset
Create a new file in `datasets/travel_booker_golden.json`.
*   **Format:** List of questions with expected outputs (`reference_data`).
*   **Key Fields:** `user_inputs`, `reference_tool_interactions`, `metadata`.
*   **Guide:** See **[DATASETS_GUIDE.md](DATASETS_GUIDE.md)** for the full schema and examples.

### 2. Define Metrics
Create a new file in `metrics/metric_definitions_travel_booker.json`.
*   **Dataset Mapping:** Map your agent's specific state variables (e.g., `extracted_data:booking_details`) to the metric's input variables.
*   **Rubric:** Define the criteria for `llm` metrics (e.g., "Did the agent capture the correct travel dates?").
*   **Guide:** See **[METRICS_GUIDE.md](METRICS_GUIDE.md)** for schema details and templates.

### 3. Run the Pipeline
Execute the standard 3-step workflow, pointing to your new files:
1.  `01_agent_interaction.py ... --questions-file datasets/travel_booker_golden.json`
2.  `02_agent_run_eval.py ... --metrics-files metrics/metric_definitions_travel_booker.json`
