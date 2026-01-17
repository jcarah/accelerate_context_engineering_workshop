# Getting Started with Agent Evaluation

This guide walks you through setting up and running your first agent evaluation.

## Prerequisites

### 1. Install the Evaluation CLI

```bash
cd evaluation
uv sync
```

### 2. Set Up Google Cloud Authentication

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### 3. Verify Installation

```bash
uv run agent-eval --help
```

You should see the available commands: `convert`, `create-dataset`, `interact`, `evaluate`, `analyze`.

---

## Choose Your Evaluation Path

The framework supports two ways to generate agent interactions for evaluation:

| Path | Best For | Input |
|------|----------|-------|
| **Path A: Simulation** | Development, rapid iteration | Scenario files (conversation plans) |
| **Path B: Live API** | Testing deployed agents | Golden Dataset (expected answers) |

> **Learn More:** See [02-EVALUATION-PATHS.md](02-EVALUATION-PATHS.md) for detailed comparison.

---

## Quick Start: Path A (Simulation)

Use this path during development to quickly test agent behavior.

### Step 1: Run ADK Simulator

```bash
cd your-agent

# Clear previous history
rm -rf your_agent_module/.adk/eval_history/*

# Run simulation
uv run adk eval your_agent_module \
  --config_file_path eval/scenarios/eval_config.json \
  eval_set_with_scenarios
```

### Step 2: Convert Traces

```bash
cd ../evaluation

uv run agent-eval convert \
  --agent-dir ../your-agent/your_agent_module \
  --output-dir ../your-agent/eval/results
```

### Step 3: Run Evaluation

```bash
uv run agent-eval evaluate \
  --interaction-file ../your-agent/eval/results/<timestamp>/raw/processed_interaction_sim.jsonl \
  --metrics-files ../your-agent/eval/metrics/metric_definitions.json \
  --results-dir ../your-agent/eval/results/<timestamp>
```

### Step 4: Analyze Results

```bash
uv run agent-eval analyze \
  --results-dir ../your-agent/eval/results/<timestamp> \
  --agent-dir ../your-agent
```

---

## Quick Start: Path B (Live API)

Use this path to test a running agent with expected answers.

### Step 1: Convert Test File to Golden Dataset

```bash
uv run agent-eval create-dataset \
  --input ../your-agent/eval/eval_data/test.json \
  --output ../your-agent/eval/datasets/golden_dataset.json \
  --agent-name your_agent
```

### Step 2: Start Your Agent

```bash
# In another terminal
cd your-agent
make playground  # or your preferred method
```

### Step 3: Run Interactions

```bash
uv run agent-eval interact \
  --app-name your_agent \
  --questions-file ../your-agent/eval/datasets/golden_dataset.json \
  --base-url http://localhost:8080 \
  --results-dir ../your-agent/eval/results
```

### Step 4: Evaluate and Analyze

Same as Path A Steps 3-4.

---

## Agent Directory Structure

Each agent should have an `eval/` folder with this structure:

```
your-agent/
├── your_agent_module/           # Agent code
│   └── .adk/eval_history/       # ADK simulator output (auto-generated)
└── eval/
    ├── scenarios/               # Path A: Simulation files
    │   ├── conversation_scenarios.json
    │   ├── eval_config.json
    │   └── eval_set_with_scenarios.evalset.json
    ├── eval_data/               # Path B: Source test files
    │   └── test.json
    ├── datasets/                # Path B: Converted golden datasets
    │   └── golden_dataset.json
    ├── metrics/                 # Metric definitions
    │   └── metric_definitions.json
    └── results/                 # Evaluation output
        └── <timestamp>/
            ├── eval_summary.json
            └── raw/
```

---

## Next Steps

- [02-EVALUATION-PATHS.md](02-EVALUATION-PATHS.md) - Understand scenarios vs golden datasets
- [03-METRICS-GUIDE.md](03-METRICS-GUIDE.md) - Define custom evaluation metrics
- [04-CLI-REFERENCE.md](04-CLI-REFERENCE.md) - Full command reference
- [05-OUTPUT-FILES.md](05-OUTPUT-FILES.md) - Understanding output files
