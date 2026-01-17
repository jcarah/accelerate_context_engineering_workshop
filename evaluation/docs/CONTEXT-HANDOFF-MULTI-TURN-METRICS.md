# Context Handoff: Multi-Turn & Agent Metrics Implementation

**Last Updated**: 2026-01-17 (Session 4)

---

## TL;DR - Current Status

| Metric Type | Status | Notes |
|-------------|--------|-------|
| **Deterministic Metrics** | ✅ WORKING | Fully functional - token usage, latency, tool success rate, etc. |
| **Custom LLM Metrics** | ✅ WORKING | trajectory_accuracy, tool_use_quality, capability_honesty |
| **API Predefined (MULTI_TURN_*)** | ✅ WORKING | Works with `use_gemini_format: true` |
| **API Predefined (TOOL_USE_QUALITY)** | ❌ NOT WORKING | Requires `tool_usage` variable SDK doesn't provide yet |

---

## IMPORTANT: Before You Start

### 1. Data Format Change: CSV → JSONL

We've changed the processed interaction format from CSV to JSONL. You have two options:

**Option A: Re-run the ADK simulation**
```bash
cd customer-service
rm -rf customer_service/.adk/eval_history/*
uv run adk eval customer_service --config_file_path eval/scenarios/eval_config.json eval_set_with_scenarios

cd ../evaluation
uv run agent-eval convert --agent-dir ../customer-service/customer_service --output-dir ../customer-service/eval/results
```

**Option B: Run the converter on existing data**
If you have existing CSV files, the converter now outputs JSONL. Just re-run:
```bash
uv run agent-eval convert --agent-dir ../customer-service/customer_service --output-dir ../customer-service/eval/results
```

### 2. Copy Latest Metric Definitions

The `customer-service/eval/metrics/metric_definitions.json` has the latest working metrics. Copy this pattern for other agents.

Key metrics included:
- `multi_turn_general_quality` - API predefined with custom guidelines
- `multi_turn_text_quality` - API predefined
- `trajectory_accuracy` - Custom, includes available tools context
- `tool_use_quality` - Custom, handles mock data gracefully
- `capability_honesty` - **NEW** - Catches agents overpromising capabilities

---

## Key Learnings from This Session

### 1. trajectory_accuracy Was Giving False Negatives

**Problem:** The metric was scoring 2.2/5 because the LLM judge was penalizing the agent for not using tools that don't exist (e.g., "apply_discount", "send_email").

**Fix:** Added `available_tools` to the dataset_mapping and updated the prompt with:
```
**CRITICAL EVALUATION RULES:**
1. Only evaluate against AVAILABLE tools.
2. Judge the outcome, not an imaginary ideal path.
3. Credit graceful handling of limitations.
```

**Result:** Score improved from 2.2 → 4.8/5

### 2. New Metric: capability_honesty

**Problem:** The agent was claiming capabilities it doesn't have (e.g., "I can see your plant via video" when the tool just sends a link to a human expert).

**Solution:** Created a new metric that specifically evaluates whether the agent makes false promises. It includes known tool limitations as ground truth in the prompt.

**Result:** Scores 2.6/5, correctly identifying the agent's overpromising behavior as the main issue.

### 3. Tool Descriptions Are Missing

**Problem:** The `tool_declarations` in extracted_data only have names like `"Tool: get_available_planting_times"` instead of actual descriptions.

**Workaround:** We embed known tool limitations directly in metric prompts. Created `tool_descriptions.json` as a reference file.

**Future Fix:** Modify the converter to extract tool docstrings from the agent's `tools.py`.

### 4. Mock Data Penalization

**Problem:** `multi_turn_text_quality` was penalizing the agent for returning `MOCK_QR_CODE_DATA`.

**Fix:** Added context to custom metrics:
```
**IMPORTANT CONTEXT:**
- Tools may return MOCK data in test environments (e.g., 'MOCK_QR_CODE_DATA').
  Do NOT penalize the agent for correctly relaying mock data.
```

### 5. Analyzer Bug Fix

**Problem:** The analyzer was failing with "'str' object has no attribute 'get'" when parsing extracted_data.

**Root Cause:** Data was stored as Python dict syntax (single quotes) instead of JSON (double quotes).

**Fix:** Added `ast.literal_eval` as fallback in `robust_json_loads()` in `analyzer.py`.

---

## Recommended Metric Configuration

### For API Predefined Metrics (multi-turn)

```json
{
  "multi_turn_general_quality": {
    "metric_type": "llm",
    "is_managed": true,
    "managed_metric_name": "MULTI_TURN_GENERAL_QUALITY",
    "use_gemini_format": true,
    "natural_language_guidelines": "Your custom evaluation criteria here..."
  }
}
```

### For Custom LLM Metrics

Include `available_tools` and test environment context:

```json
{
  "trajectory_accuracy": {
    "metric_type": "llm",
    "dataset_mapping": {
      "prompt": { "source_column": "user_inputs" },
      "response": { "source_column": "trace_summary" },
      "available_tools": { "source_column": "extracted_data:tool_declarations" },
      "final_response": { "source_column": "final_response" }
    },
    "template": "...\n**CRITICAL:** Only evaluate against AVAILABLE tools..."
  }
}
```

---

## Files Modified in This Session

1. **`evaluation/src/evaluation/core/analyzer.py`**
   - Added `ast.literal_eval` fallback for Python dict syntax

2. **`customer-service/eval/metrics/metric_definitions.json`**
   - Updated `trajectory_accuracy` with available_tools context
   - Updated `tool_use_quality` with mock data handling
   - Added new `capability_honesty` metric

3. **`customer-service/eval/metrics/tool_descriptions.json`** (NEW)
   - Reference file with actual tool capabilities and limitations

4. **Documentation updates (CSV → JSONL)**
   - `evaluation/docs/01-GETTING-STARTED.md`
   - `evaluation/docs/02-EVALUATION-PATHS.md`
   - `evaluation/docs/03-METRICS-GUIDE.md`
   - `evaluation/docs/04-CLI-REFERENCE.md`
   - `evaluation/docs/05-OUTPUT-FILES.md`
   - `evaluation/README.md`
   - `README.md` (root)

---

## Quick Test Commands

```bash
cd evaluation

# Run evaluation
uv run agent-eval evaluate \
  --interaction-file ../customer-service/eval/results/baseline/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir ../customer-service/eval/results/baseline

# Run analysis
uv run agent-eval analyze \
  --results-dir ../customer-service/eval/results/baseline \
  --agent-dir ../customer-service
```

---

## Expected Results

After running with the updated metrics:

| Metric | Expected Score | Notes |
|--------|----------------|-------|
| `multi_turn_general_quality` | ~0.77 | API predefined |
| `multi_turn_text_quality` | ~0.98 | API predefined |
| `trajectory_accuracy` | ~4.4/5 | Now evaluates against available tools |
| `tool_use_quality` | ~4.2/5 | Handles mock data gracefully |
| `capability_honesty` | ~2.6/5 | Correctly catches overpromising |

The low `capability_honesty` score is the **actionable signal** - the agent needs to stop claiming capabilities it doesn't have.

---

## Next Steps

### High Priority
1. **Fix the agent** - Stop overpromising capabilities (main issue identified)
2. **De-conflict metrics** - `tool_use_quality` and `trajectory_accuracy` sometimes give conflicting signals

### Medium Priority
3. **Extract real tool descriptions** - Modify converter to read docstrings from tools.py
4. **Apply metrics to retail agent** - Copy the metric patterns

### Low Priority
5. **Report SDK bugs** - TOOL_USE_QUALITY requires variable SDK doesn't provide

---

## Deterministic Metrics Reference

These are calculated automatically from session data:

| Metric | Description |
|--------|-------------|
| `token_usage` | LLM calls, tokens, costs |
| `latency_metrics` | Total, average, time to first response |
| `cache_efficiency` | Cache hit rate |
| `thinking_metrics` | Reasoning ratio, thinking tokens |
| `tool_utilization` | Tool calls count, unique tools |
| `tool_success_rate` | Success rate, failed tools |
| `grounding_utilization` | Grounding chunks used |
| `context_saturation` | Max context usage |
| `agent_handoffs` | Sub-agent invocations |
| `output_density` | Average output tokens |
| `sandbox_usage` | Code execution usage |
