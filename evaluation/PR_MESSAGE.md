# Evaluation Framework Improvements and Documentation Refactor

## Summary

This PR contains significant improvements to the evaluation framework, including bug fixes, documentation reorganization, and enhanced metric definitions for both agents.

## Changes

### Core Fixes

- **Fix NaN in JSON output**: Error fields with NaN values now properly handled to avoid invalid JSON
- **Fix tool interaction Events**: SDK requires dict type for function responses - now wraps list/non-dict responses automatically
- **Add score_range to all metrics**: Every metric definition now includes min/max/description for clarity
- **Compound column mapping**: New feature to select specific state variables instead of entire state objects (prevents RESOURCE_EXHAUSTED errors)
- **Fix custom metrics templates**: All custom metrics now use `{prompt}` and `{response}` placeholders (SDK requirement)
- **Fix grounding metric**: Changed context mapping to use `tool_interactions` for accurate grounding evaluation

### Baseline Results

Added pre-computed baseline evaluation results for both agents in `[agent]/eval/results/baseline/`:
- `eval_summary.json` - Aggregated metrics with score ranges
- `question_answer_log.md` - Detailed Q&A transcript
- `gemini_analysis.md` - AI-powered root cause analysis
- `raw/` - Raw evaluation data

> **Note:** LLM outputs are non-deterministic. We recommend running your own baseline on your branch before making changes for accurate before/after comparisons.

### Documentation Refactor

Reorganized documentation into `evaluation/docs/` with numbered guides:

| File | Description |
|------|-------------|
| `01-GETTING-STARTED.md` | Quick start guide |
| `02-EVALUATION-PATHS.md` | Scenarios vs Golden Datasets, symlinks, ADK simulation |
| `03-METRICS-GUIDE.md` | Defining metrics, SDK requirements, compound mapping |
| `04-CLI-REFERENCE.md` | CLI command reference |
| `05-OUTPUT-FILES.md` | Understanding output files |
| `99-DEVELOPMENT.md` | Development and contribution guide |

Key documentation additions:
- SDK restrictions for custom metrics (must use `{prompt}` and `{response}` placeholders)
- Compound column mapping syntax for large state objects
- Symlinks workflow explanation (edit `eval/scenarios/`, not agent directory)
- ADK User Simulation scenario creation instructions
- Reference-based metrics requiring Path B (golden datasets)
- Rubric verdict behavior (empty type field and no individual scores are normal API behavior)

### Metric Definitions

Updated both `retail-ai-location-strategy` and `customer-service` metric files:
- Added `score_range` to all metrics
- Fixed custom metric templates to use `{prompt}/{response}`
- Implemented compound column mapping for state metrics

---

## Evaluation Results

### Retail Location Strategy Agent

| Metric | Score | Range | Description |
|--------|-------|-------|-------------|
| `strategic_recommendation_quality` | **5.0** | 1-5 | Strategic mastery |
| `tool_usage_effectiveness` | **5.0** | 1-5 | Optimal usage |
| `market_research_depth` | **5.0** | 1-5 | Exceptional depth |
| `state_variable_fidelity` | **3.0** | 1-5 | Moderate alignment |
| `grounding` | **1.0** | 0-1 | All claims grounded |
| `agent_hallucination` | **1.0** | 0-1 | All claims supported |
| `safety` | **1.0** | 0-1 | Safe |
| `final_response_quality` | **0.38** | 0-1 | Passing rate |
| `text_quality` | **0.36** | 0-1 | Passing rate |
| `agent_tool_use_quality` | **0.17** | 0-1 | Passing rate |
| `general_conversation_quality` | **0.10** | 0-1 | Passing rate |
| `instruction_following` | **0.04** | 0-1 | Passing rate |

**Deterministic Metrics:**
- Total latency: 370.9s
- Tool success rate: 100%
- Cache hit rate: 27.4%
- Total tool calls: 15
- Agent handoffs: 5

### Customer Service Agent

| Metric | Score | Range | Description |
|--------|-------|-------|-------------|
| `tool_usage_accuracy` | **4.6** | 0-5 | Effective tool usage |
| `trajectory_accuracy` | **3.0** | 0-5 | Mostly correct trajectory |
| `state_management_fidelity` | **0.4** | 0-5 | Some state captured |
| `agent_hallucination` | **0.86** | 0-1 | Most claims supported |
| `final_response_quality` | **0.80** | 0-1 | Passing rate |
| `general_conversation_quality` | **0.79** | 0-1 | Passing rate |
| `instruction_following` | **0.74** | 0-1 | Passing rate |
| `safety` | **1.0** | 0-1 | Safe |

**Deterministic Metrics:**
- Total latency: 41.8s
- Tool success rate: 100%
- Cache hit rate: 41.1%
- Total tool calls: 4
- Agent handoffs: 4

---

## Dataset Mapping Reference

### Supported Source Columns

| Column | Description |
|--------|-------------|
| `user_inputs` | User's question(s) - JSON list or string |
| `final_response` | Agent's final text response |
| `trace_summary` | Agent trajectory as list of steps |
| `extracted_data` | JSON with state_variables, tool_interactions |
| `session_trace` | Full OpenTelemetry execution trace |
| `reference_data` | Expected answers (Path B only) |

### Nested Lookup Syntax

Access nested fields using colon notation:
- `extracted_data:state_variables`
- `extracted_data:tool_interactions`
- `reference_data:expected_response`

### Compound Column Mapping (New)

For large state objects, use template syntax to select specific variables:

```json
"response": {
  "template": "Location: {extracted_data_target_location}\nBusiness: {extracted_data_business_type}",
  "source_columns": ["extracted_data:target_location", "extracted_data:business_type"]
}
```

---

## Testing

- [x] Retail agent evaluation runs successfully
- [x] Customer service agent evaluation runs successfully
- [x] All custom metrics use correct `{prompt}/{response}` placeholders
- [x] Compound column mapping works for state metrics
- [x] No RESOURCE_EXHAUSTED errors with compound mapping
- [x] JSON output is valid (no NaN values)
- [x] Score ranges appear in evaluation summary

---

## Files Changed

### Evaluation Framework
- `evaluation/src/evaluation/core/data_mapper.py` - Dict wrapping, compound mapping
- `evaluation/src/evaluation/core/evaluator.py` - NaN handling, score_range in output
- `evaluation/src/evaluation/core/deterministic_metrics.py` - Minor fixes
- `evaluation/README.md` - Updated with new docs structure

### Documentation
- `evaluation/docs/01-GETTING-STARTED.md` (new)
- `evaluation/docs/02-EVALUATION-PATHS.md` (new)
- `evaluation/docs/03-METRICS-GUIDE.md` (new)
- `evaluation/docs/04-CLI-REFERENCE.md` (new)
- `evaluation/docs/05-OUTPUT-FILES.md` (new)
- `evaluation/docs/99-DEVELOPMENT.md` (new)
- Deleted: `DATASETS_GUIDE.md`, `METRICS_GUIDE.md`, `OUTPUTS.md`, `TEST_COVERAGE.md`

### Agent Configurations
- `retail-ai-location-strategy/eval/metrics/metric_definitions.json`
- `customer-service/eval/metrics/metric_definitions.json`

---

Co-Authored-By: Claude <noreply@anthropic.com>
