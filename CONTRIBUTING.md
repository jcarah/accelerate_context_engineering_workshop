# Contributing & Development Guide

> **For workshop maintainers only.** Participants should use [README.md](README.md) and [REFERENCE.md](REFERENCE.md).
>
> **Note:** This file is maintained only in the `main` branch. Optimization branches should reference `main` for the latest team documentation.

**Last Updated:** 2026-01-28

---

## Quick Reference

| What | Where |
|------|-------|
| Workshop guide (participants follow this) | `README.md` |
| Deep dive & CLI reference | `REFERENCE.md` |
| AI assistant context | `GEMINI.md` |
| This file (internal team) | `CONTRIBUTING.md` (main branch only) |

---

## Branch Overview

We have **5 optimization branches** across **2 agents**:

| Agent | Branches | Eval Mode | Key Difference |
|-------|----------|-----------|----------------|
| **Customer Service** | 01, 02, 03 | ADK User Sim | Multi-turn conversations |
| **Retail AI** | 04, 05 | DIY Interactions | Single-turn pipeline |

### Branch Status

| Branch | Agent | Status | Current State |
|--------|-------|--------|---------------|
| `main` | Both | ✅ Ready | Baseline evaluations for both agents |
| `optimizations/01-tool-definition` | Customer Service | ✅ Complete | Up to date with main, has `optimization/` results |
| `optimizations/02-context-compaction` | Customer Service | 📋 Ready to create | Create from 01, implement optimization |
| `optimizations/03-functional-isolation` | Customer Service | ⏳ Blocked | Create from 02 after 02 is done |
| `optimizations/04-offload-and-reduce` | Retail AI | 🔄 In Progress | Up to date with main, needs `optimization/` results |
| `optimizations/05-prefix-caching` | Retail AI | 📋 Ready to create | Create from 04 after 04 is done |

### Branch Dependencies

```
Customer Service Agent (ADK User Sim):
main ──► 01-tool-definition ✅ ──► 02-context-compaction ──► 03-functional-isolation
              (complete)              (create from 01)         (create from 02)

Retail AI Agent (DIY Interactions):
main ──► 04-offload-and-reduce 🔄 ──► 05-prefix-caching
              (needs eval)              (create from 04)
```

---

## Team Contacts

| Person | Responsibilities |
|--------|------------------|
| **Jesse** | Project lead, workshop objectives & core narrative |
| **John** | Context engineering techniques, agents design, hill climbing exercise (branches 01-03) |
| **Hugo** | Technical aspects of branches 04-05, adapting the evaluation framework to external agents |
| **Liz** | Workshop management, testing, train-the-trainers, development experience |
| **Dani** | Evaluation framework and CLI (`agent-eval`) |

---

## Workflow: Customer Service Agent (Branches 01-03)

These branches use **ADK User Sim** for evaluation. See [README.md - Section 2](README.md#2-baseline-customer-service) for detailed explanation of the evaluation steps.

### Branch 01 is Complete

Branch 01 is up to date with main and has evaluation results in `eval/results/optimization/`. Use it as the starting point for branch 02.

### Creating Branch 02 (from 01)

```bash
# 1. Checkout branch 01
git checkout optimizations/01-tool-definition
git pull origin optimizations/01-tool-definition

# 2. Create branch 02
git checkout -b optimizations/02-context-compaction

# 3. Make your agent code changes in customer-service/customer_service/
# ... implement the context compaction optimization ...

# 4. Run evaluation and save to optimization/ folder
cd customer-service
rm -rf customer_service/.adk/eval_history/*
rm -f customer_service/*.evalset.json

uv run adk eval_set create customer_service eval_set_with_scenarios
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json
uv run adk eval customer_service eval_set_with_scenarios

# 5. Convert traces - output to optimization/ folder directly
cd ../evaluation
uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results/optimization

# 6. Run evaluation
uv run agent-eval evaluate \
  --interaction-file ../customer-service/eval/results/optimization/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir ../customer-service/eval/results/optimization \
  --input-label optimization-02

# 7. Analyze
uv run agent-eval analyze \
  --results-dir ../customer-service/eval/results/optimization \
  --agent-dir ../customer-service \
  --location global

# 8. Use Gemini CLI to compare results (see section below)
# 9. Create OPTIMIZATION_LOG.md
# 10. Commit and push
git add customer-service/
git commit -m "feat: add context compaction optimization with evaluation results"
git push -u origin optimizations/02-context-compaction
```

### Creating Branch 03 (from 02)

Same process as above, but:
- Checkout from `optimizations/02-context-compaction`
- Create `optimizations/03-functional-isolation`
- Your optimization folder will compare against 02's results

---

## Workflow: Retail AI Agent (Branches 04-05)

These branches use **DIY Interactions** for evaluation. See [README.md - Section 3](README.md#3-baseline-retail-ai) for detailed explanation.

**IMPORTANT:** The Retail AI evaluation requires running the agent server. You need **two terminals**.

### Branch 04 Current State

Branch 04 is up to date with main and already has:
- Baseline results in `eval/results/baseline/`
- Agent optimization changes (last 2 pipeline stages disabled)

**Hugo: Before running evaluation, verify the agent changes are still in place:**

```bash
git checkout optimizations/04-offload-and-reduce
git pull origin optimizations/04-offload-and-reduce

# Verify the optimization is applied (stages should be commented out)
grep -n "report_generator\|infographic_generator" retail-ai-location-strategy/app/agent.py

# You should see lines 89-90 commented out:
#        # report_generator_agent,     # Part 4: HTML report generation
#        # infographic_generator_agent,  # Part 5: Infographic generation
```

### Running Evaluation for Branch 04

```bash
# Terminal 1: Start the agent
cd retail-ai-location-strategy
uv sync
make dev  # Keep this running (port 8502)

# Terminal 2: Run evaluation and save to optimization/ folder
cd evaluation

# Run interactions - output directly to optimization/ folder
uv run agent-eval interact \
  --app-name app \
  --questions-file ../retail-ai-location-strategy/eval/eval_data/golden_dataset.json \
  --base-url http://localhost:8502 \
  --results-dir ../retail-ai-location-strategy/eval/results/optimization

# Run evaluation
uv run agent-eval evaluate \
  --interaction-file ../retail-ai-location-strategy/eval/results/optimization/raw/processed_interaction_app.jsonl \
  --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions.json \
  --results-dir ../retail-ai-location-strategy/eval/results/optimization \
  --input-label optimization-04

# Analyze
uv run agent-eval analyze \
  --results-dir ../retail-ai-location-strategy/eval/results/optimization \
  --agent-dir ../retail-ai-location-strategy \
  --location global

# Stop the agent in Terminal 1 (Ctrl+C)
```

### Creating Branch 05 (from 04)

```bash
# 1. Checkout branch 04 (must have optimization/ results first)
git checkout optimizations/04-offload-and-reduce

# 2. Create branch 05
git checkout -b optimizations/05-prefix-caching

# 3. Make your agent code changes in retail-ai-location-strategy/app/
# ... implement the prefix caching optimization ...

# 4. Run evaluation (same as above, but save to optimization/ in branch 05)
# Terminal 1: make dev
# Terminal 2: interact → evaluate → analyze (to optimization/ folder)

# 5. Compare with branch 04's optimization results
# 6. Create OPTIMIZATION_LOG.md
# 7. Commit and push
git add retail-ai-location-strategy/
git commit -m "feat: add prefix caching optimization with evaluation results"
git push -u origin optimizations/05-prefix-caching
```

---

## Using Gemini CLI to Compare Results

The Gemini CLI can read evaluation results and generate comparison reports. Run these prompts from the project root:

### Compare Baseline vs Optimization (Single Branch)

```
Compare the evaluation results in:
- customer-service/eval/results/baseline/eval_summary.json
- customer-service/eval/results/optimization/eval_summary.json

Create an OPTIMIZATION_LOG.md that:
1. Shows a metrics comparison table with baseline, optimization, and delta columns
2. Highlights which metrics improved and which regressed
3. Summarizes the key findings
```

### Compare Across Multiple Optimization Iterations

For branches that build on each other (e.g., 01 → 02 → 03):

```
Compare the evaluation results across these three folders:
- customer-service/eval/results/baseline/eval_summary.json (main branch)
- customer-service/eval/results/optimization/eval_summary.json (branch 01)
- customer-service/eval/results/optimization2/eval_summary.json (branch 02)

Create a comparison table showing how metrics changed across each optimization step.
Identify which optimization had the biggest impact on each metric.
```

### Generate OPTIMIZATION_LOG.md

```
Read the evaluation results in customer-service/eval/results/optimization/
and the agent source code in customer-service/customer_service/.

Create an OPTIMIZATION_LOG.md with:
1. Summary of what was changed in the agent
2. Metrics comparison table (deterministic + LLM metrics)
3. Analysis of trade-offs (did improving one metric hurt another?)
4. Conclusions and recommendations
```

---

## Creating OPTIMIZATION_LOG.md

Each optimization branch should have an `OPTIMIZATION_LOG.md` in the agent's eval folder. See [GEMINI.md](GEMINI.md) for the template.

**Required Sections:**

1. **Summary** - What optimization was applied
2. **Metrics Comparison Table** - Baseline vs Optimization with deltas
3. **Analysis** - What improved, what regressed, trade-offs
4. **Conclusions** - Key takeaways

**Example Table:**

| Metric | Baseline | Optimization | Delta | Notes |
|--------|----------|--------------|-------|-------|
| `tool_use_quality` | 3.2 | 4.5 | +1.3 | Improved with stricter schemas |
| `token_usage.total_tokens` | 15420 | 12300 | -3120 | 20% reduction |
| `latency_metrics.total_seconds` | 12.5 | 14.2 | +1.7 | Slight increase (trade-off) |

---

## Key Gotchas

### Vertex AI is Required

```
MUST use: GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION
DO NOT use: GOOGLE_API_KEY (metrics will be empty)
```

### evalset.json Files

- Auto-generated by `adk eval_set` commands
- Gitignored - don't commit them
- Clear before each run: `rm -f customer_service/*.evalset.json`

### Multi-turn vs Single-turn Metrics

- Customer Service uses `multi_turn_*` metrics (conversation)
- Retail AI uses single-turn metrics like `general_quality`

### Results Folder Naming

- `baseline/` - Results from main branch (no optimizations)
- `optimization/` - Results from the current optimization branch
- `optimization2/`, `optimization3/` - For comparing multiple iterations

---

## Technical Reference

### Evaluation CLI Project Structure

```
evaluation/
├── src/evaluation/
│   ├── cli/main.py             # CLI commands
│   ├── core/
│   │   ├── evaluator.py        # Metric evaluation
│   │   ├── analyzer.py         # Gemini analysis
│   │   ├── converters.py       # ADK trace converter
│   │   ├── data_mapper.py      # Column mapping
│   │   └── deterministic_metrics.py
│   └── interaction/
│       └── agent_client.py     # API client
└── tests/
```

### Development Setup

```bash
cd evaluation
uv sync --dev
uv run pytest tests/ -v
uv run ruff check src/
uv run ruff format src/
```

### Key Development Decisions

| Decision | Rationale |
|----------|-----------|
| JSONL over CSV | Nested JSON requires proper serialization |
| `read_jsonl` over pandas | Avoids ujson "Value is too big" errors |
| Skip auth for localhost | DIY path shouldn't require gcloud token |
| `final_response` as dict | Enables fine-grained field evaluation |
