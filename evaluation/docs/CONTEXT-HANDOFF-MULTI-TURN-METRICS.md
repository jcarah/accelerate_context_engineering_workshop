# Context Handoff: Agent Evaluation Implementation

**Last Updated**: 2026-01-19 (Session 7)

This document serves two purposes:
1. **For teammates/workshop participants**: Quick reference for common issues and patterns
2. **For AI continuity**: Context to resume development across sessions

---

## Quick Reference

### Metric Types at a Glance

| Type | Status | When to Use |
|------|--------|-------------|
| **Deterministic** | ✅ Working | Always - auto-calculated from traces |
| **Custom LLM** | ✅ Working | When you need specific evaluation criteria |
| **API: Single-turn** | ✅ Working | Pipeline agents (retail-ai) |
| **API: Multi-turn** | ✅ Working | Conversational agents (customer-service) |

### Which API Metrics for Your Agent?

| Your Agent Pattern | Use These | Example Agent |
|-------------------|-----------|---------------|
| User → Agent → User → Agent (back-and-forth) | `MULTI_TURN_GENERAL_QUALITY` | customer-service |
| User → Agent runs pipeline → Final response | `GENERAL_QUALITY`, `TEXT_QUALITY` | retail-ai-location-strategy |

### Why Multiple Scenario Files?

Each agent has two sets of evaluation files:

| File Set | Purpose | Use Case |
|----------|---------|----------|
| `eval_set_single` / `eval_config_single.json` | Quick iteration | Daily development (~2 min) |
| `eval_set_with_scenarios` / `eval_config.json` | Comprehensive | CI/CD, nightly runs (10+ min) |

**Rule of thumb**: Use single-scenario for development, full set for CI/CD.

---

## Common Errors & Fixes

### 1. "Variable conversation_history is required but not provided"

**Cause**: Using `MULTI_TURN_*` metrics on a single-turn agent.

**Fix**: Switch to single-turn metrics:
```json
{
  "general_quality": {
    "managed_metric_name": "GENERAL_QUALITY",
    "use_gemini_format": true
  }
}
```

### 2. Deterministic Metrics Show All Zeros

**Cause**: `app_name` in evalset doesn't match the folder name.

**The Rule**:
```
app_name in evalset.json MUST match the folder containing agent.py
```

| Agent | Folder | Correct app_name |
|-------|--------|------------------|
| customer-service | `customer_service/` | `"customer_service"` |
| retail-ai | `app/` | `"app"` |

**Wrong**:
```json
"session_input": { "app_name": "retail_location_strategy" }  // ❌ Internal name
```

**Correct**:
```json
"session_input": { "app_name": "app" }  // ✅ Folder name
```

### 3. Trajectory Accuracy Penalizing for Missing Tools

**Cause**: LLM judge expects tools that don't exist.

**Fix**: Add `available_tools` to your metric and update the prompt:
```json
"dataset_mapping": {
  "available_tools": { "source_column": "extracted_data:tool_declarations" }
}
```

Add to template:
```
**CRITICAL:** Only evaluate against AVAILABLE tools listed above.
Do NOT penalize for tools that don't exist.
```

### 4. Mock Data Being Penalized

**Cause**: Test environments return mock data like `MOCK_QR_CODE_DATA`.

**Fix**: Add context to custom metrics:
```
**IMPORTANT:** Tools may return MOCK data in test environments.
Do NOT penalize the agent for correctly relaying mock data.
```

---

## Running Evaluations

### Customer Service Agent (Multi-turn)

```bash
cd evaluation

# Evaluate
uv run agent-eval evaluate \
  --interaction-file ../customer-service/eval/results/baseline/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir ../customer-service/eval/results/baseline

# Analyze
uv run agent-eval analyze \
  --results-dir ../customer-service/eval/results/baseline \
  --agent-dir ../customer-service
```

### Retail AI Agent (Single-turn Pipeline)

```bash
# Step 1: Run ADK simulation
cd retail-ai-location-strategy
rm -rf app/.adk  # Clear previous runs
uv run adk eval app --config_file_path eval/scenarios/eval_config_single.json eval_set_single

# Step 2: Convert traces
cd ../evaluation
uv run agent-eval convert \
  --agent-dir ../retail-ai-location-strategy/app \
  --output-dir ../retail-ai-location-strategy/eval/results

# Step 3: Evaluate (use timestamp from step 2)
RUN_DIR=../retail-ai-location-strategy/eval/results/<TIMESTAMP>
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR

# Step 4: Analyze
uv run agent-eval analyze --results-dir $RUN_DIR --agent-dir ../retail-ai-location-strategy
```

---

## Expected Results

### Customer Service Agent

| Metric | Expected | Notes |
|--------|----------|-------|
| `multi_turn_general_quality` | ~0.77 | API predefined |
| `multi_turn_text_quality` | ~0.98 | API predefined |
| `trajectory_accuracy` | ~4.4/5 | Custom metric |
| `capability_honesty` | ~2.6/5 | **Actionable**: Agent overpromises |

### Retail AI Agent

| Metric | Expected | Notes |
|--------|----------|-------|
| `general_quality` | ~0.10 | Single-turn API metric |
| `text_quality` | ~0.38 | Single-turn API metric |
| `trajectory_accuracy` | ~4-5/5 | Custom metric |
| `pipeline_integrity` | ~1.0/5 | **Actionable**: Agent hallucinates analysis |

---

## Metric Configuration Patterns

### Single-Turn API Metrics (Pipeline Agents)

```json
{
  "general_quality": {
    "metric_type": "llm",
    "is_managed": true,
    "managed_metric_name": "GENERAL_QUALITY",
    "use_gemini_format": true,
    "natural_language_guidelines": "Evaluate response quality..."
  }
}
```

### Multi-Turn API Metrics (Conversational Agents)

```json
{
  "multi_turn_general_quality": {
    "metric_type": "llm",
    "is_managed": true,
    "managed_metric_name": "MULTI_TURN_GENERAL_QUALITY",
    "use_gemini_format": true,
    "natural_language_guidelines": "Evaluate conversation quality..."
  }
}
```

### Custom LLM Metrics (Best Practice)

```json
{
  "trajectory_accuracy": {
    "metric_type": "llm",
    "score_range": {"min": 0, "max": 5},
    "dataset_mapping": {
      "prompt": { "source_column": "user_inputs" },
      "response": { "source_column": "trace_summary" },
      "available_tools": { "source_column": "extracted_data:tool_declarations" },
      "final_response": { "source_column": "final_response" }
    },
    "template": "Evaluate the agent trajectory...\n\n**CRITICAL:** Only evaluate against AVAILABLE tools.\n\nScore: [0-5]\nExplanation: [reasoning]"
  }
}
```

---

## Deterministic Metrics Reference

Auto-calculated from session traces - no configuration needed:

| Metric | Description |
|--------|-------------|
| `token_usage` | LLM calls, tokens (prompt/completion/cached), estimated cost |
| `latency_metrics` | Total latency, time to first response, LLM vs tool time |
| `cache_efficiency` | KV-cache hit rate |
| `thinking_metrics` | Reasoning ratio, thinking tokens |
| `tool_utilization` | Total calls, unique tools, per-tool counts |
| `tool_success_rate` | Success rate, failed tools list |
| `agent_handoffs` | Sub-agent invocations |
| `context_saturation` | Max tokens in single turn |
| `output_density` | Average output tokens per turn |
| `sandbox_usage` | Code execution operations |

---

## Implementation Notes (For Developers)

### ADK Eval History Formats

The converter handles two ADK output formats:

| Format | Agent Type | Data Location |
|--------|------------|---------------|
| Format 1 | Multi-turn (customer-service) | `case["session_details"]["events"]` |
| Format 2 | Pipeline (retail-ai) | `case["eval_metric_result_per_invocation"][0]["actual_invocation"]` |

The converter auto-detects the format. If `session_details` is null, it displays an error about `app_name` mismatch.

### Key Files

| File | Purpose |
|------|---------|
| `evaluation/src/evaluation/core/converters.py` | ADK → JSONL conversion |
| `evaluation/src/evaluation/core/analyzer.py` | LLM-based report generation |
| `evaluation/src/evaluation/core/deterministic_metrics.py` | Token/latency metrics |
| `<agent>/eval/metrics/metric_definitions.json` | Metric configurations |

### Known SDK Limitations

1. **TOOL_USE_QUALITY** API metric requires `tool_usage` variable the SDK doesn't provide
2. **Tool descriptions** extracted as `"Tool: name"` instead of actual docstrings
3. **Gemini 3 models** require `location="global"` (handled in analyzer.py)

---

## Session Changelog

### Session 7 (2026-01-19)
- Fixed: Single-turn vs multi-turn metric selection
- Added: `general_quality`, `text_quality` for retail agent
- Updated: Documentation for metric selection

### Session 6 (2026-01-19)
- Fixed: `app_name` must match folder name
- Added: Converter error messaging for misconfiguration
- Created: Single-scenario eval files for quick iteration
- Fixed: Gemini 3 model location handling

### Sessions 1-5
- Built core evaluation pipeline
- Implemented deterministic metrics
- Created custom LLM metrics (trajectory_accuracy, tool_use_quality, capability_honesty)
- Fixed trajectory_accuracy false negatives with available_tools context
- Added mock data handling in metrics
