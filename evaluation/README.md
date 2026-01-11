# Agent Evaluation Pipeline

This document provides a comprehensive guide to the evaluation pipeline, a multi-step process designed to test, measure, and analyze the performance of ADK agents.

## 🚀 Overview

This pipeline automates the end-to-end evaluation process:
1.  **Interaction:** Runs a dataset of questions against your agent API (concurrently).
2.  **Evaluation:** Grades the interactions using both **Deterministic** logic (cost, latency) and **LLM-as-a-Judge** metrics (correctness, tool usage).
3.  **Analysis:** Generates a human-readable Q&A log and an AI-powered Root Cause Analysis report.

We support two primary workflows for generating evaluation data:

### 1. The Simulation Path (Recommended)
**"Write Scenarios, Generate Conversations."**
*   **Best for:** Development, regression testing, and creating high-quality multi-turn datasets without manual effort.
*   **How it works:** You define high-level *Conversation Scenarios* (your "wishlist" of user behaviors). The ADK User Simulator plays these out against your agent locally.
*   **Advantage:** No need to manually script every turn or deploy the agent to a remote URL.

### 2. The Live/Remote Path
**"Run Questions against a URL."**
*   **Best for:** End-to-end testing of deployed environments (Staging/Prod) or running legacy fixed-question datasets.
*   **How it works:** You run `01_agent_interaction.py` to send a list of static questions to a running agent service (e.g., Cloud Run).

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

## Workflow 1: The Simulation Path (Recommended)

### Step 0: Blueprinting & Scenarios
Before running anything, we define *what* we want to test. We analyze the agent's code to create "Conversation Scenarios."

*   **Input:** `conversation_scenarios.json`
*   **Concept:** Instead of writing "User: Hi, Agent: Hello", you write "User wants to buy Petunias but needs a discount." The Simulator handles the dialogue.

(See "Case Study: Blueprinting" below for details)

### Step 1: User Simulation & ADK Evaluation (CLI)
Execute the scenarios using the ADK CLI. This runs the agent locally and performs initial safety checks.

**Prerequisites:**
1. `cd customer-service` (or your agent directory)
2. `gcloud auth application-default login`

**Commands:**
1.  **Create Eval Set:** `uv run adk eval_set create customer_service eval_set_with_scenarios`
2.  **Add Scenarios:**
    ```bash
    uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
      --scenarios_file customer_service/conversation_scenarios.json \
      --session_input_file customer_service/session_input.json
    ```
3.  **Run Simulation:**
    ```bash
    uv run adk eval customer_service \
      --config_file_path customer_service/eval_config.json \
      eval_set_with_scenarios \
      --print_detailed_results
    ```

**Output:** Trace files generated in `.adk/eval_history`.

---

### Step 2: Process Simulation Data (The Bridge)
This step bridges the gap between the ADK Eval's raw history logs and our evaluation pipeline (ADK Eval with User Simulation currently only supports 2 evaluation metrics: hallucination & safety). It converts the simulation traces into a structured, analyzable dataset.

**Usage:**
```bash
cd evaluation && uv run python scripts/convert_adk_history_to_dataset.py \
  --agent-dir customer-service/customer_service
```

**Output:** `customer-service/eval/eval_data/interactions/run_<timestamp>.csv`

#### Dataset Reference (`run_<timestamp>.csv`)

This CSV is the "Golden Record" for analysis.

| Column | Description | Detailed Example | Source/Logic |
| :--- | :--- | :--- | :--- |
| **`eval_id`** | Unique ID for the specific test case. | `68e57b06` | ADK Eval History |
| **`session_id`** | Unique ID for the conversation session. | `___eval___session___700c...` | `session_details.id` |
| **`agent_name`** | Internal name of the agent. | `customer_service` | `session_details.app_name` |
| **`score.hallucinations_v1`** | **Quality Metric:** Pass/Fail score (0-1) for hallucination. | `1.0` (Pass) | Extracted from `eval_metric_results` in ADK history. |
| **`score.safety_v1`** | **Quality Metric:** Pass/Fail score (0-1) for safety. | `0.0` (Fail) | Extracted from `eval_metric_results`. |
| **`metric.duration_sec`** | **Perf Metric:** Total wall-clock time of the session. | `18.47` | `last_event.timestamp - first_event.timestamp` |
| **`metric.total_tokens`** | **Cost Metric:** Total tokens consumed (Prompt + Completion). | `17045` | Sum of `usage_metadata.total_token_count` across all turns. |
| **`metric.cache_hit_rate`** | **Optimization:** Efficiency of Context Caching. | `0.41` (41%) | `cached_tokens / (input_tokens + epsilon)` |
| **`metric.turn_count`** | **Behavior:** Length of conversation. | `3` | Count of user messages. |
| **`metric.tool_calls`** | **Behavior:** Number of tools invoked. | `5` | Count of `functionCall` events. |
| **`metric.tool_errors`** | **Reliability:** Number of failed tool calls. | `0` | Count of `functionResponse` where `status='error'`. |
| **`metric.unique_tools`** | **Behavior:** Which tools were actually used. | `["generate_qr_code", "search"]` | Set of unique tool names used. |
| **`final_response`** | The final answer given to the user. | "I have scheduled your appointment..." | Text from the last model turn. |
| **`system_instructions`** | **Context:** The system prompt used. | "You are Project Pro..." | Extracted from `app_details`. |
| **`custom_extract`** | **Deep Analysis Log:** Rich list of turns. | `[{"turn":1, "role":"user", "tokens":{...}, "tool_calls":[...]}]` | Custom parsing containing tokens, models, timestamps, and tool I/O per turn. |
| **`session_state`** | **Full Fidelity:** Complete session object. | `{"state": {...}, "events": [...]}` | JSON dump of the entire `session_details` object. |
| **`session_trace`** | **Synthetic Trace:** OTEL-compatible spans. | `[{"name": "call_llm", "start_time": ...}]` | Synthetic span tree constructed from events for compatibility with trace analyzers. |

---

## Workflow 2: The Live/Remote Path

### 🔄 Workflow & Key Files

| Step | Script | Description |
| :--- | :--- | :--- |
| **1** | `01_agent_interaction.py` | **Data Collection.** Orchestrates `scripts/run_interactions.py` to hit your agent's API in parallel (`asyncio`). Enriches raw logs with traces and state variables via `scripts/process_interactions.py`. |
| **2** | `02_agent_run_eval.py` | **Scoring.** Runs the evaluation suite. Uses `ThreadPoolExecutor` to run Vertex AI evaluations in parallel. Manages configuration via `Pydantic`. |
| **3** | `03_analyze_eval_results.py` | **Insight Generation.** Produces `question_answer_log.md` (readable transcript) and uses Gemini to write `gemini_analysis.md` (technical diagnosis). |

### ⚙️ Configuration

The pipeline uses a **layered configuration** strategy (CLI > Env Vars > Defaults).

#### Environment Variables (`.env`)
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

#### CLI Arguments
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

## Deep Metrics Calculation (`02_agent_run_eval.py`)

Now that we have the `run_<timestamp>.csv` (from Simulation) or `processed_interaction.csv` (from Live/Remote), we can apply advanced Python-based metrics (e.g., business logic validation, complex latency breakdown) that go beyond the basic ADK checks.

**Usage:**

```bash
uv run python 02_agent_run_eval.py \
  --interaction-results-file <path_to_step2_csv> \
  --metrics-files <path_to_metrics.json> \
  [--input-label <run_label>] \
  [--test-description <description>] \
  [--metric-filter key:value]
```

### Arguments

| Argument | Description | Default |
|---|---|---|
| `--interaction-results-file` | Path to the CSV file generated by Step 2. **(Required)** | N/A |
| `--metrics-files` | One or more paths to JSON files containing metric definitions. **(Required)** | N/A |
| `--results-dir` | Directory to save evaluation results. | Parent of input file. |
| `--input-label` | A short label for the run (e.g., `baseline`, `exp_v2`). | `manual` |
| `--test-description` | A detailed description of the test scenario. | Standard description. |
| `--metric-filter` | Filter metrics (e.g., `metric_type:llm` or `agents:customer_service`). | Run all metrics. |

---

# Metrics Reference

## 1. Deterministic Metrics
Calculated directly from execution traces without using an LLM.

| Metric | Description | Calculation Logic |
| :--- | :--- | :--- |
| **`token_usage`** | Cost & Volume | Sums prompt, completion, and cached tokens from `usage_metadata`. Calculates estimated cost using model-specific pricing (e.g., Gemini 1.5 Pro). |
| **`latency_metrics`** | Speed | **Total:** Sum of all agent invocation durations (excludes user think time). **Avg Turn:** Mean duration of agent invocations. **LLM/Tool:** Sum of individual span durations. |
| **`cache_efficiency`** | Optimization | `Cache Hit Rate = Cached Tokens / (Cached + Fresh Prompt Tokens)`. Measures how effectively the Context Cache is being used. |
| **`thinking_metrics`** | Cognitive Effort | `Reasoning Ratio = Thinking Tokens / Total Output Tokens`. Measures the proportion of output spent on internal reasoning (for Thinking models). |
| **`tool_utilization`** | Tool Usage | Counts total and unique tool calls. Provides a breakdown of which tools were called how often. |
| **`tool_success_rate`** | Reliability | `Successful Calls / Total Calls`. Parses tool output JSON to check for `status: "error"` or error messages. |
| **`grounding_utilization`** | Factuality Proxy | Counts the number of Google Search grounding chunks (citations) present in the LLM response metadata. |
| **`context_saturation`** | Capacity Planning | Tracks the **Maximum Total Tokens** used in any single turn. Helps identify if the session is nearing the model's context window limit. |
| **`agent_handoffs`** | Orchestration | Counts the number of times control transferred between agents (`invoke_agent` spans). Validates multi-agent architecture. |
| **`output_density`** | Conciseness | `Average Output Tokens per LLM Call`. A proxy for the "Reduce" pillar; lower values (for non-generative tasks) often indicate better instruction following. |
| **`sandbox_usage`** | Offloading | Counts calls to file system tools (`save_artifact`, `read_file`, etc.). Deterministically verifies if state is being offloaded to disk. |

## 2. LLM Metrics (Customer Service)
Evaluated by Gemini 1.5 Pro using the rubric in `metrics/metric_definitions_customer_service.json`.

*   **`trajectory_accuracy` (0-5):** Did the agent follow the expected sequence of sub-tasks? Compares actual agent order vs. reference trajectory.
*   **`response_correctness` (0-5):** Is the final answer relevant, accurate, and consistent with tool outputs?
*   **`tool_usage_accuracy` (0-5):** Did the agent pick the right tools and use the correct arguments (e.g., correct `customer_id`)?
*   **`state_management_fidelity` (0-5):** Did the agent correctly extract entities from the conversation and update its internal session state variables?

## 3. LLM Metrics (Retail Location Strategy)
Evaluated by Gemini 1.5 Pro using the rubric in `metrics/metric_definitions_retail_location.json`.

*   **`state_variable_fidelity` (0-5):** Checks if complex artifacts (Market Research, Gap Analysis) were correctly stored in the session state.
*   **`market_research_depth` (0-5):** Evaluates the quality of the gathered data. Does it cover demographics and specific competitors? Is it synthesized well?
*   **`strategic_recommendation_quality` (0-5):** Assesses the business logic. Is the recommendation evidence-based? Are risks acknowledged? Are next steps actionable?
*   **`tool_usage_effectiveness` (0-5):** Did the agent perform a comprehensive search (coverage)? Did it successfully generate the final HTML/Infographic artifacts?

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

Alternatively, convert a test file:

```bash
uv run python scripts/convert_test_to_golden.py \
  --input path/to/your/test_data.json \
  --output datasets/your_new_golden_data.json \
  --agent <agent_app_name> \
  --metadata "complexity:easy" \
  --prefix q_prefix
```

### 2. Define Metrics
Create a new file in `metrics/metric_definitions_travel_booker.json`.
*   **Dataset Mapping:** Map your agent's specific state variables (e.g., `extracted_data:booking_details`) to the metric's input variables.
*   **Rubric:** Define the criteria for `llm` metrics (e.g., "Did the agent capture the correct travel dates?").
*   **Guide:** See **[METRICS_GUIDE.md](METRICS_GUIDE.md)** for schema details and templates.

### 3. Run the Pipeline
Execute the standard workflow (Live or Simulation) pointing to your new files.

---


## Maintenance Note (TODO)

The file `02_agent_run_eval.py` currently operates with an older structure and version of the Vertex AI evaluation service. A migration is needed to align with the latest best practices.

**Required Actions:**

1.  **Migrate to Client:** Transition from `EvalTask` to the new `client` method for evaluation.
    *   Reference: [Define your evaluation metrics | Generative AI on Vertex AI | Google Cloud Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview#define_metrics)
    *   Alternatively, evaluate if `EvalTask` should be retained but updated to match: [Evaluate Gen AI agents | Generative AI on Vertex AI | Google Cloud Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluate-gen-ai-agents)

2.  **Refactor Metrics Calculation:**
    *   Consider using **Autoraters** for more robust evaluation.
    *   Update `deterministic_metrics.py` to potentially use custom function metrics.
    *   Validate that Custom metrics definitions remain compatible.
    *   Explore using **Agentic Pre-written metrics** and **Adaptive rubrics**.

3.  **Explain Metric Mapping:**
    *   Document the "WHY" behind `metric.json` and its mapping logic.
    *   Reference: [Details for managed rubric-based metrics | Generative AI on Vertex AI | Google Cloud Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-rubrics)