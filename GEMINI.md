# AI Assistant Context for Workshop

This file provides context for AI coding assistants (Gemini CLI, Claude Code, etc.) to help workshop participants effectively.

---

## Quick Context Load

For full repository context, use [gitingest](https://gitingest.com/jcarah/accelerate_context_engineering_workshop) to generate a context dump you can paste into your AI assistant.

---

## Workshop Overview

This is the **Agent Optimization & Evaluation Workshop** for Google Cloud Accelerate '26.

**Objective:** Teach developers to move from prompt engineering to context engineering, using a production-grade evaluation framework to measure and validate agent improvements.

**Key Concepts:**
- Context Engineering: Systematic management of the model's context window (Offload, Reduce, Retrieve, Isolate, Cache)
- Evaluation Framework: 3-step process (Run Interactions → Evaluate → Analyze)
- Hill Climb Methodology: Iterative optimization from M0 (baseline) to M5 (fully optimized)

---

## Repository Structure

```
accelerate_context_engineering_workshop/
├── WORKSHOP_OVERVIEW.md      # Conceptual guide - start here
├── HOW_TO_USE_REPO.md        # Complete practical guide
├── customer-service/          # Agent A: Multi-turn, reliability focus
├── retail-ai-location-strategy/  # Agent B: Pipeline, scale focus
└── evaluation/                # Shared evaluation CLI (agent-eval)
```

---

## What Participants Are Doing

1. **Running baseline evaluations** on the `main` branch
2. **Checking out optimization branches** (`optimizations/01-tool-definition`, etc.)
3. **Re-running evaluations** to compare before/after metrics
4. **Understanding trade-offs** between quality, cost, and latency

---

## Common Tasks You Should Help With

### Running Evaluations
```bash
# Full pipeline
cd customer-service
rm -rf customer_service/.adk/eval_history/*
uv run adk eval customer_service eval/scenarios/eval_set_with_scenarios.evalset.json

cd ../evaluation
RUN_DIR=$(uv run agent-eval convert --agent-dir ../customer-service/customer_service --output-dir ../customer-service/eval/results | awk -F': ' '/^Run folder:/ {print $2}')
uv run agent-eval evaluate --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl --metrics-files ../customer-service/eval/metrics/metric_definitions.json --results-dir $RUN_DIR
uv run agent-eval analyze --results-dir $RUN_DIR --agent-dir ../customer-service --location global
```

### Creating Custom Metrics
Metrics go in `eval/metrics/metric_definitions.json`. Help participants write custom LLM-as-Judge metrics with clear scoring criteria.

### Debugging Evaluation Issues
- Zero token usage → Check `app_name` matches folder name in evalset
- "conversation_history required" → Using MULTI_TURN metrics on single-turn agent
- Empty dashboard → Using API key instead of Vertex AI

### Understanding Results
- `eval_summary.json` → Aggregated metrics
- `gemini_analysis.md` → Root cause analysis
- Low scores → Map to optimization patterns (see WORKSHOP_OVERVIEW.md)

---

## Optimization Branches

| Branch | Optimization | Focus |
|--------|--------------|-------|
| `main` | Baseline | Establish metrics |
| `optimizations/01-tool-definition` | Tool Hardening | Fix hallucinated parameters |
| `optimizations/02-context-compaction` | Reduce Context | Fix "lost in the middle" |
| `optimizations/03-code-execution` | Offload to Sandbox | Fix token bloat |
| `optimizations/04-functional-isolation` | Sub-agents | Fix routing confusion |
| `optimizations/05-prefix-caching` | Cache Static Content | Fix latency/cost |

---

## Critical Reminders

1. **Always use Vertex AI**, not API keys (evaluation won't work otherwise)
2. **Clear eval_history** before each run: `rm -rf agent/.adk/eval_history/*`
3. **Run `uv sync`** after switching branches
4. **Use `--location global`** for Gemini 2.5 models in analyze command

---

## Key Files to Reference

- `WORKSHOP_OVERVIEW.md` - Conceptual understanding
- `HOW_TO_USE_REPO.md` - All practical instructions
- `optimization_strategy.md` - Context engineering principles
- `[agent]/eval/metrics/metric_definitions.json` - Metric configurations
