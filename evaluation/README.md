# Evaluation Pipeline

This document provides a comprehensive guide to the evaluation pipeline, a multi-step process designed to test, measure, and analyze the performance of ADK agents.

## Overview

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

## Workflow: The Simulation Path

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


### Step 3: Deep Metrics Calculation (`02_agent_run_eval.py`)
Now that we have the `run_<timestamp>.csv`, we can apply advanced Python-based metrics (e.g., business logic validation, complex latency breakdown) that go beyond the basic ADK checks.

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

### Deterministic Metrics Explained

These metrics provide objective, reproducible measurements by analyzing execution traces.

*   **`token_usage`**: Calculates the **Estimated Cost in USD** for the session based on model-specific pricing (e.g., Gemini 1.5 Pro).
*   **`latency_metrics`**: Measures both **Total Session Duration** and **Average Turn Latency** in seconds, breaking down time spent in LLM calls vs tools.

---


## Customizing Metrics

The evaluation framework is designed for extensibility. `02_agent_run_eval.py` dynamically loads metrics from two sources, so you can add or modify them without changing the main script.

### 1. Deterministic Metrics (Python)
Logic-based metrics are defined in `evaluation/scripts/deterministic_metrics.py`.

*   **How it works:** The script maintains a `DETERMINISTIC_METRICS` registry mapping metric names to Python functions.
*   **To add a metric:**
    1.  Define a new function in `deterministic_metrics.py` (e.g., `def calculate_my_metric(...)`).
    2.  Add it to the `DETERMINISTIC_METRICS` dictionary at the bottom of the file.
    3.  `02_agent_run_eval.py` will automatically detect and run it if listed in your JSON config or if passed via CLI filters.

### 2. LLM-based Metrics (JSON)
AI-as-judge metrics are defined in JSON configuration files (e.g., `metrics/metric_definitions_customer_service.json`).

*   **How it works:** These files define the prompt templates and data mapping logic.
*   **To add a metric:** Simply add a new entry to the `metrics` object in your JSON file. The pipeline reads these files at runtime, so no code changes are needed.

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


## Example Evaluation Commands

### Retail Location Strategy Agent
```bash
uv run python 02_agent_run_eval.py \
  --interaction-results-file results/app/20260110_005102/processed_interaction_format_golden_data.csv \
  --metrics-files metrics/metric_definitions_retail_location.json \
  --input-label retail_run_2
```

### Customer Service Agent
```bash
uv run python 02_agent_run_eval.py \
  --interaction-results-file results/customer_service/20260110_002956/processed_interaction_format_golden_data.csv \
  --metrics-files metrics/metric_definitions_customer_service.json \
  --input-label customer_service_run_3
```

---


## Extending the Framework

### Creating New Evaluation Datasets
You can create raw datasets using the `adk eval` command. Use `convert_test_to_golden.py` to structure existing turn-based test data:

```bash
uv run python scripts/convert_test_to_golden.py \
  --input path/to/your/test_data.json \
  --output datasets/your_new_golden_data.json \
  --agent <agent_app_name> \
  --metadata "complexity:easy" \
  --prefix q_prefix
```

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
