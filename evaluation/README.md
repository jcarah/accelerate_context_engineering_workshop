# Agent Evaluation Pipeline (`agent-eval`)

A production-grade evaluation framework for ADK agents. This CLI provides advanced metrics beyond ADK's built-in checks, including tool usage accuracy, trajectory analysis, state management fidelity, and AI-powered root cause diagnosis.

## Two Evaluation Paths

```
PATH A: SIMULATION (Development)
================================
eval/scenarios/ ──> adk eval ──> agent-eval convert ──> agent-eval evaluate ──> agent-eval analyze
                         │                                       │
                  .adk/eval_history/                    eval_summary.json
                                                        gemini_analysis.md

PATH B: LIVE API (Deployed Agents)
==================================
eval/eval_data/ ──> agent-eval create-dataset ──> agent-eval interact ──> agent-eval evaluate ──> agent-eval analyze
                              │                            │                        │
                     golden_dataset.json           processed_*.csv          eval_summary.json
```

| Path | Best For | Input Format |
|------|----------|--------------|
| **Path A** | Development, rapid iteration | Scenario files (conversation plans) |
| **Path B** | Testing deployed agents | Golden Dataset (expected answers) |

## Quick Start

### Prerequisites

```bash
cd evaluation
uv sync
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### Path A: Simulation (Recommended for Development)

```bash
# 1. Run ADK simulator
cd your-agent
rm -rf your_agent/.adk/eval_history/*
uv run adk eval your_agent --config_file_path eval/scenarios/eval_config.json eval_set_with_scenarios

# 2. Convert and evaluate
cd ../evaluation
uv run agent-eval convert --agent-dir ../your-agent/your_agent --output-dir ../your-agent/eval/results
uv run agent-eval evaluate --interaction-file ../your-agent/eval/results/<timestamp>/raw/processed_interaction_sim.csv \
  --metrics-files ../your-agent/eval/metrics/metric_definitions.json \
  --results-dir ../your-agent/eval/results/<timestamp>
uv run agent-eval analyze --results-dir ../your-agent/eval/results/<timestamp> --agent-dir ../your-agent
```

### Path B: Live API

```bash
# 1. Create golden dataset and run interactions
uv run agent-eval create-dataset --input ../your-agent/eval/eval_data/test.json \
  --output ../your-agent/eval/datasets/golden.json --agent-name your_agent
uv run agent-eval interact --app-name your_agent \
  --questions-file ../your-agent/eval/datasets/golden.json --base-url http://localhost:8080

# 2. Evaluate and analyze (same as Path A steps 2-3)
```

## Documentation

| Guide | Description | Key Topics |
|-------|-------------|------------|
| [01-GETTING-STARTED.md](docs/01-GETTING-STARTED.md) | Prerequisites and first run | Installation, GCloud auth, quick start for both paths, agent directory structure |
| [02-EVALUATION-PATHS.md](docs/02-EVALUATION-PATHS.md) | Scenarios vs Golden Datasets | ADK User Simulation setup, scenario files, symlinks, Golden Dataset format, when to use each path |
| [03-METRICS-GUIDE.md](docs/03-METRICS-GUIDE.md) | Defining evaluation metrics | Custom LLM metrics, Vertex AI managed metrics, dataset mapping syntax, available columns reference, score ranges, troubleshooting |
| [04-CLI-REFERENCE.md](docs/04-CLI-REFERENCE.md) | Complete command reference | All commands (`convert`, `create-dataset`, `interact`, `evaluate`, `analyze`) with arguments and examples |
| [05-OUTPUT-FILES.md](docs/05-OUTPUT-FILES.md) | Understanding output files | CSV columns, eval_summary.json structure, deterministic metrics, Q&A log format, file relationships |
| [99-DEVELOPMENT.md](docs/99-DEVELOPMENT.md) | For contributors | Project structure, running tests, adding commands/metrics, code style, release process |

## Output Structure

Each run creates a timestamped folder:

```
eval/results/20260114_143022/
├── eval_summary.json           # Aggregated metrics
├── question_answer_log.md      # Human-readable Q&A transcript
├── gemini_analysis.md          # AI root cause analysis
└── raw/
    ├── processed_interaction_*.csv
    └── evaluation_results_*.csv
```

## Metrics

### Deterministic (Calculated Automatically)

| Metric | Description |
|--------|-------------|
| `latency_metrics` | Total duration, time to first response |
| `cache_efficiency` | KV-cache hit rate |
| `tool_success_rate` | Successful tool calls / total calls |
| `agent_handoffs` | Control transfers between agents |

### LLM-as-Judge (Defined in metrics.json)

| Type | Examples |
|------|----------|
| **Custom** | `response_correctness`, `tool_usage_accuracy` |
| **Managed (Vertex AI)** | `GENERAL_QUALITY`, `TOOL_USE_QUALITY`, `SAFETY` |

## Help

```bash
uv run agent-eval --help
uv run agent-eval <command> --help
```
