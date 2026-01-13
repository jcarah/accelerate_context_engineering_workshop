# Agent Evaluation Pipeline (`agent-eval`)

A production-grade evaluation framework for ADK agents. This CLI provides advanced metrics beyond ADK's built-in hallucination/safety checks, including tool usage accuracy, trajectory analysis, state management fidelity, and AI-powered root cause diagnosis.

## Overview

### Two Evaluation Paths

#### Path A: Simulation Path (Recommended for Development)
Uses the native ADK simulator to generate conversations from scenarios, then runs our extended metrics.

```
adk eval (native)  →  agent-eval convert  →  agent-eval evaluate  →  agent-eval analyze
      ↓                      ↓                    ↓                    ↓
.adk/eval_history/    results/<timestamp>/   (same folder)       (same folder)
                      └── raw/               └── eval_summary.json  └── question_answer_log.md
                          └── processed_*.csv   └── raw/              └── gemini_analysis.md
                                                    └── evaluation_*.csv
```

#### Path B: Live/Remote Path (For Deployed Agents)
Sends questions from a Golden Dataset to a running agent endpoint, then runs metrics.

```
agent-eval interact  →  agent-eval evaluate  →  agent-eval analyze
         ↓                    ↓                       ↓
results/<timestamp>/      (same folder)          (same folder)
└── raw/                  └── eval_summary.json  └── question_answer_log.md
    └── processed_*.csv       └── raw/               └── gemini_analysis.md
                                  └── evaluation_*.csv
```

---

## Quick Start: Simulation Path (Customer Service Agent)

### Prerequisites

```bash
# 1. Install the evaluation CLI
cd evaluation
uv sync

# 2. Set up Google Cloud authentication
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=your-project-id
```

---

### Step 1: Run the ADK Simulator

Generate agent interactions using the native ADK simulator. Simulation scenarios are defined in `eval/scenarios/`.

> **📚 Learn More:** See the [ADK User Simulation Documentation](https://google.github.io/adk-docs/evaluate/user-sim/) for details on scenario format and configuration.

```bash
cd customer-service

# IMPORTANT: Clear previous eval history before each baseline run
rm -rf customer_service/.adk/eval_history/*

# Run the ADK evaluation (scenarios are in eval/scenarios/)
uv run adk eval customer_service \
  --config_file_path eval/scenarios/eval_config.json \
  eval_set_with_scenarios \
  --print_detailed_results
```

**Output:** Trace files in `customer_service/.adk/eval_history/`

**Simulation Files:**
```
eval/scenarios/
├── conversation_scenarios.json    # Multi-turn conversation plans
├── eval_config.json               # Evaluation criteria (hallucination, safety)
├── eval_set_with_scenarios.evalset.json  # Eval set definition
└── session_input.json             # Initial session state
```

> **Why Clear `.adk/eval_history/`?**
>
> The ADK simulator accumulates traces from ALL evaluation runs in this folder.
> The `convert` command processes ALL files in this directory. If you don't clear it
> before running a new evaluation, your results will include stale data from previous
> runs, corrupting your baseline comparison.

---

### Step 2: Convert ADK Traces

Convert the ADK simulator output to our evaluation format.

```bash
cd ../evaluation

uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results
```

**Output:** Creates `eval/results/<timestamp>/raw/processed_interaction_sim.csv`

---

### Step 3: Run Evaluation Metrics

Apply deterministic metrics (latency, cost) and LLM-as-Judge metrics (correctness, tool usage).

```bash
# Use the timestamp folder from Step 2
RUN_DIR=../customer-service/eval/results/<timestamp>

uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.csv \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline \
  --test-description "Customer Service Agent Baseline"
```

**Output:** Adds to the same folder:
```
<timestamp>/
├── eval_summary.json              # NEW: Aggregated metrics
└── raw/
    ├── processed_interaction_sim.csv  # From Step 2
    └── evaluation_results_*.csv       # NEW: Full results
```

---

### Step 4: Analyze Results

Generate human-readable reports and AI-powered root cause analysis.

```bash
# Use the same timestamp folder
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service
```

**Output:** Adds analysis reports to the same folder:
```
<timestamp>/
├── eval_summary.json              # From Step 3
├── question_answer_log.md         # NEW: Detailed Q&A with all metrics
├── gemini_analysis.md             # NEW: AI root cause analysis
└── raw/
    ├── processed_interaction_sim.csv
    ├── evaluation_results_*.csv
    └── gemini_prompt.txt          # NEW: Debug prompt sent to Gemini
```

---

## Quick Start: Live/Remote Path

For evaluating a deployed agent or running against localhost.

### Step 1: Prepare a Golden Dataset

If you have ADK test data (like `full_conversation.test.json`), convert it:

```bash
uv run agent-eval create-dataset \
  --input ../customer-service/eval/eval_data/full_conversation.test.json \
  --output ../customer-service/eval/datasets/golden_dataset.json \
  --agent-name customer_service
```

Or use an existing Golden Dataset (JSON with `user_inputs` and `reference_data`).

### Step 2: Run Interactions

```bash
# Start your agent first (e.g., make playground in another terminal)

uv run agent-eval interact \
  --app-name customer_service \
  --questions-file ../customer-service/eval/datasets/golden_dataset.json \
  --base-url http://localhost:8080 \
  --results-dir ../customer-service/eval/results
```

**Output:** Creates `eval/results/<timestamp>/raw/processed_interaction_customer_service.csv`

The CLI prints the next command to run. Example:
```
Run folder: ../customer-service/eval/results/20260112_143022

To evaluate, run:
agent-eval evaluate --interaction-file .../raw/processed_interaction_customer_service.csv --metrics-files <metrics.json> --results-dir .../20260112_143022
```

### Step 3-4: Evaluate and Analyze

Same as Simulation Path Steps 3-4 - pass the timestamp folder as `--results-dir`.

---

## CLI Reference

### Getting Help

Use `--help` to see all available options for any command:

```bash
# See all commands
uv run agent-eval --help

# See options for a specific command
uv run agent-eval interact --help
uv run agent-eval evaluate --help
uv run agent-eval analyze --help
uv run agent-eval convert --help
uv run agent-eval create-dataset --help
```

### `agent-eval convert`

Converts ADK simulator history (`.adk/eval_history/`) to evaluation format.

| Argument | Description | Required |
|----------|-------------|----------|
| `--agent-dir` | Agent module directory containing `.adk/eval_history/` | Yes |
| `--output-dir` | Output directory for CSV | No (default: results/) |
| `--questions-file` | Golden dataset for merging reference data | No |

### `agent-eval create-dataset`

Converts ADK test files to Golden Dataset format (for use with `interact` command).

| Argument | Description | Required |
|----------|-------------|----------|
| `--input` | Path to ADK test JSON (list of turns) | Yes |
| `--output` | Path for output Golden Dataset | Yes |
| `--agent-name` | Agent name | Yes |
| `--metadata key:value` | Add metadata tags | No |

### `agent-eval interact`

Runs interactions against a live agent endpoint.

| Argument | Description | Required |
|----------|-------------|----------|
| `--app-name` | Agent application name | Yes |
| `--questions-file` | Golden Dataset JSON | Yes |
| `--base-url` | Agent API URL | No (default: localhost:8080) |
| `--results-dir` | Output directory | No |

### `agent-eval evaluate`

Runs evaluation metrics on processed interactions.

| Argument | Description | Required |
|----------|-------------|----------|
| `--interaction-file` | Path to processed_interaction CSV | Yes |
| `--metrics-files` | Metric definition JSON files | Yes |
| `--results-dir` | Output directory | Yes |
| `--input-label` | Run label (e.g., baseline, v2) | No |
| `--test-description` | Description for this run | No |

### `agent-eval analyze`

Generates analysis reports from evaluation results.

| Argument | Description | Required |
|----------|-------------|----------|
| `--results-dir` | Directory containing eval results | Yes |
| `--agent-dir` | Agent source (adds context to AI analysis) | No |
| `--model` | Gemini model (default: gemini-2.5-pro) | No |
| `--skip-gemini` | Skip AI analysis (Q&A log only) | No |

---

## Output Folder Structure

Each evaluation run creates a single timestamped folder. All commands add to this folder:

```
eval/results/
├── 20260112_143022/                          # Baseline run
│   ├── eval_summary.json                     # Aggregated metrics (from evaluate)
│   ├── question_answer_log.md                # Q&A transcript (from analyze)
│   ├── gemini_analysis.md                    # AI root cause analysis (from analyze)
│   └── raw/
│       ├── processed_interaction_*.csv       # Interaction data (from interact/convert)
│       ├── evaluation_results_*.csv          # Full eval results (from evaluate)
│       └── gemini_prompt.txt                 # Debug: prompt for AI analysis
│
└── 20260112_160045/                          # After optimization
    └── ...
```

---

## Metrics Reference

### Deterministic Metrics

| Metric | Description |
|--------|-------------|
| `latency_metrics` | Total duration, avg turn latency, time to first response |
| `cache_efficiency` | KV-cache hit rate, cached vs fresh tokens |
| `thinking_metrics` | Reasoning ratio (thinking / output tokens) |
| `tool_utilization` | Total and unique tool calls |
| `tool_success_rate` | Successful calls / total calls |
| `context_saturation` | Max tokens in any single turn |
| `agent_handoffs` | Control transfers between agents |

### LLM-as-Judge Metrics

| Metric | Scale | Description |
|--------|-------|-------------|
| `trajectory_accuracy` | 0-5 | Did agent follow expected task sequence? |
| `response_correctness` | 0-5 | Is final answer accurate and relevant? |
| `tool_usage_accuracy` | 0-5 | Correct tools with correct arguments? |
| `state_management_fidelity` | 0-5 | Correct entity extraction and storage? |

---

## Troubleshooting

### "No .adk/eval_history found"
- Run `adk eval` first (native ADK command)
- Check path: history is in `[agent_module]/.adk/eval_history/`

### Stale data in evaluations
- **Always clear `.adk/eval_history/` before each new baseline**
- `rm -rf [agent_module]/.adk/eval_history/*`

### "No evaluation results found" in analyze
- Run `agent-eval evaluate` first
- Analyzer looks for `eval_summary.json`

---

## Additional Documentation

- [DATASETS_GUIDE.md](DATASETS_GUIDE.md) - Golden dataset schema
- [METRICS_GUIDE.md](METRICS_GUIDE.md) - Metric definition schema
- [OUTPUTS.md](OUTPUTS.md) - Output file reference
