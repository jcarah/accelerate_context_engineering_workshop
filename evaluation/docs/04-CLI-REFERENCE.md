# CLI Reference

Complete reference for all `agent-eval` commands.

## Getting Help

```bash
# See all commands
uv run agent-eval --help

# See options for a specific command
uv run agent-eval <command> --help
```

---

## Commands Overview

| Command | Purpose | Evaluation Path |
|---------|---------|-----------------|
| `convert` | Convert ADK simulator traces to JSONL | Path A (Simulation) |
| `create-dataset` | Convert ADK test files to Golden Dataset | Path B (Live API) |
| `interact` | Run interactions against live agent | Path B (Live API) |
| `evaluate` | Run metrics on processed interactions | Both paths |
| `analyze` | Generate reports and AI analysis | Both paths |

---

## `agent-eval convert`

Converts ADK simulator history (`.adk/eval_history/`) to the evaluation JSONL format.

### Usage

```bash
uv run agent-eval convert \
  --agent-dir ../your-agent/your_agent_module \
  --output-dir ../your-agent/eval/results
```

### Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--agent-dir` | Agent module directory containing `.adk/eval_history/` | Yes | - |
| `--output-dir` | Output directory for JSONL | No | `results/` |
| `--questions-file` | Golden dataset for merging reference data | No | - |

### Output

Creates `<output-dir>/<timestamp>/raw/processed_interaction_sim.jsonl`

### Error Handling

If the converter detects missing `session_details` in the ADK history, it will display an error message explaining that the `app_name` in your evalset file likely doesn't match the agent's folder name. See [Troubleshooting](01-GETTING-STARTED.md#troubleshooting) for details.

### Example

```bash
# Convert customer-service agent traces
uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results

# With reference data from golden dataset
uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results \
  --questions-file ../customer-service/eval/datasets/golden.json
```

---

## `agent-eval create-dataset`

Converts ADK test files (list of turns) to Golden Dataset format for use with the `interact` command.

### Usage

```bash
uv run agent-eval create-dataset \
  --input path/to/test.json \
  --output path/to/golden_dataset.json \
  --agent-name my_agent
```

### Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--input` | Path to ADK test JSON (list of turns) | Yes | - |
| `--output` | Path for output Golden Dataset | Yes | - |
| `--agent-name` | Agent name to include in metadata | Yes | - |
| `--metadata` | Add metadata tags (format: `key:value`) | No | - |

### Input Format (ADK Test)

```json
[
  {"query": "hi", "expected_tool_use": [], "reference": "Hello!"},
  {"query": "help me", "expected_tool_use": [...], "reference": "..."}
]
```

### Output Format (Golden Dataset)

```json
{
  "questions": [
    {
      "question_id": "abc123",
      "user_inputs": ["hi"],
      "reference_data": {"expected_response": "Hello!", "expected_tool_use": []}
    }
  ],
  "metadata": {"agent_name": "my_agent", "created_at": "..."}
}
```

### Example

```bash
uv run agent-eval create-dataset \
  --input ../customer-service/eval/eval_data/full_conversation.test.json \
  --output ../customer-service/eval/datasets/golden_dataset.json \
  --agent-name customer_service \
  --metadata environment:staging \
  --metadata version:1.0
```

---

## `agent-eval interact`

Runs interactions against a live agent endpoint and captures traces.

### Usage

```bash
uv run agent-eval interact \
  --app-name my_agent \
  --questions-file path/to/golden_dataset.json \
  --base-url http://localhost:8080 \
  --results-dir path/to/results
```

### Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--app-name` | Agent application name | Yes | - |
| `--questions-file` | Golden Dataset JSON file | Yes | - |
| `--base-url` | Agent API URL | No | `http://localhost:8080` |
| `--results-dir` | Output directory | No | `results/` |
| `--user-id` | User ID for session | No | `test_user` |
| `--runs` | Number of runs per question | No | `1` |

### Output

Creates `<results-dir>/<timestamp>/raw/processed_interaction_<app_name>.jsonl`

The CLI prints the next command to run:
```
Run folder: ../your-agent/eval/results/20260114_143022

To evaluate, run:
agent-eval evaluate --interaction-file .../raw/processed_interaction_my_agent.jsonl ...
```

### Example

```bash
# Start agent first (in another terminal)
cd your-agent && make playground

# Run interactions
uv run agent-eval interact \
  --app-name customer_service \
  --questions-file ../customer-service/eval/datasets/golden_dataset.json \
  --base-url http://localhost:8080 \
  --results-dir ../customer-service/eval/results \
  --runs 2
```

---

## `agent-eval evaluate`

Runs evaluation metrics on processed interaction data.

### Usage

```bash
uv run agent-eval evaluate \
  --interaction-file path/to/processed_interaction.jsonl \
  --metrics-files path/to/metric_definitions.json \
  --results-dir path/to/results/<timestamp>
```

### Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--interaction-file` | Path to processed_interaction JSONL | Yes | - |
| `--metrics-files` | Metric definition JSON file(s) | Yes | - |
| `--results-dir` | Output directory (use same timestamp folder) | Yes | - |
| `--input-label` | Run label (e.g., `baseline`, `v2`) | No | - |
| `--test-description` | Description for this evaluation run | No | - |

### Output

Adds to the results folder:
```
<timestamp>/
├── eval_summary.json              # Aggregated metrics
└── raw/
    └── evaluation_results_*.csv   # Full results with scores
```

### Example

```bash
RUN_DIR=../customer-service/eval/results/20260114_143022

uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_customer_service.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline \
  --test-description "Customer Service Agent Baseline v1.0"
```

---

## `agent-eval analyze`

Generates human-readable reports and AI-powered root cause analysis.

### Usage

```bash
uv run agent-eval analyze \
  --results-dir path/to/results/<timestamp> \
  --agent-dir path/to/agent
```

### Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--results-dir` | Directory containing eval results | Yes | - |
| `--agent-dir` | Agent source directory (adds context to AI analysis) | No | - |
| `--strategy-file` | Path to a markdown file defining the optimization strategy/framework | No | - |
| `--model` | Gemini model for AI analysis | No | `gemini-2.5-pro` |
| `--skip-gemini` | Skip AI analysis (generate Q&A log only) | No | `false` |

### Output

Adds to the results folder:
```
<timestamp>/
├── question_answer_log.md   # Detailed Q&A transcript with scores
├── gemini_analysis.md       # AI-powered root cause analysis
└── raw/
    └── gemini_prompt.txt    # Debug: prompt sent to Gemini
```

### Example

```bash
RUN_DIR=../customer-service/eval/results/20260114_143022

# Full analysis with Gemini
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service

# Quick Q&A log only (no AI analysis)
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --skip-gemini
```

---

## Complete Workflow Examples

### Path A: Simulation (Development)

```bash
# 1. Run ADK simulator
cd customer-service
rm -rf customer_service/.adk/eval_history/*
uv run adk eval customer_service \
  --config_file_path eval/scenarios/eval_config.json \
  eval_set_with_scenarios

# 2. Convert traces
cd ../evaluation
uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results

# 3. Evaluate (use timestamp from step 2)
RUN_DIR=../customer-service/eval/results/20260114_143022
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline

# 4. Analyze
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service
```

### Path B: Live API (Deployed Agent)

```bash
cd evaluation

# 1. Create golden dataset (one-time)
uv run agent-eval create-dataset \
  --input ../customer-service/eval/eval_data/test.json \
  --output ../customer-service/eval/datasets/golden.json \
  --agent-name customer_service

# 2. Run interactions (agent must be running)
uv run agent-eval interact \
  --app-name customer_service \
  --questions-file ../customer-service/eval/datasets/golden.json \
  --base-url http://localhost:8080 \
  --results-dir ../customer-service/eval/results

# 3. Evaluate (use timestamp from step 2)
RUN_DIR=../customer-service/eval/results/20260114_150000
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_customer_service.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR

# 4. Analyze
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service
```

---

## Troubleshooting

### "No .adk/eval_history found"
- Run `adk eval` first (native ADK command)
- Check path: history is in `[agent_module]/.adk/eval_history/`

### Stale data in evaluations
- Always clear `.adk/eval_history/` before each new baseline
- `rm -rf [agent_module]/.adk/eval_history/*`

### "No evaluation results found" in analyze
- Run `agent-eval evaluate` first
- Analyzer looks for `eval_summary.json`

### Connection refused in interact
- Ensure agent is running on the specified `--base-url`
- Check firewall/network settings

---

## Related Documentation

- [01-GETTING-STARTED.md](01-GETTING-STARTED.md) - Quick start guide
- [02-EVALUATION-PATHS.md](02-EVALUATION-PATHS.md) - Understanding the two paths
- [03-METRICS-GUIDE.md](03-METRICS-GUIDE.md) - Defining metrics
- [05-OUTPUT-FILES.md](05-OUTPUT-FILES.md) - Understanding output files
