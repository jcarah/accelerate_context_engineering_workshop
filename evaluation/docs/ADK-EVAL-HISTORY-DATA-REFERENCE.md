# ADK Eval History Data Reference

**Last Updated**: 2026-01-19 (Session 6)

This document provides a comprehensive mapping of data available in ADK eval history files vs. what our converter extracts for evaluation.

---

## Overview

When you run `adk eval`, ADK creates JSON files in `.adk/eval_history/` containing the full trace of the agent's execution. Our converter (`converters.py`) transforms this data into a JSONL format suitable for evaluation.

---

## ADK Eval History Structure

```
{
  "eval_set_result_id": "...",
  "eval_set_result_name": "...",
  "eval_set_id": "eval_set_single",
  "eval_case_results": [
    {
      "eval_set_file": "...",
      "eval_set_id": "...",
      "eval_id": "seattle_coffee_001",
      "final_eval_status": "FAIL",
      "eval_metric_results": [...],
      "overall_eval_metric_results": [...],
      "eval_metric_result_per_invocation": [...],
      "session_id": "___eval___session___...",
      "session_details": { ... },  // THE MAIN DATA SOURCE
      "user_id": "eval_user"
    }
  ],
  "creation_timestamp": 1768843771.85
}
```

---

## session_details: The Primary Data Source

When `session_details` is populated (requires correct `app_name`), it contains:

### Top-Level Fields

| Field | Type | Description | Extracted? |
|-------|------|-------------|------------|
| `id` | string | Session UUID | ✅ Yes → `session_id` |
| `app_name` | string | Agent folder name | ✅ Yes → `app_name` |
| `user_id` | string | User identifier | ✅ Yes → `ADK_USER_ID` |
| `state` | object | Session state variables | ✅ Yes → `extracted_data.state_variables` |
| `events` | array | All conversation events | ✅ Yes → processed into traces |
| `last_update_time` | float | Timestamp of last update | ✅ Yes → `final_session_state.lastUpdateTime` |

### State Variables (Example from Retail Agent)

```json
{
  "__llm_request_key__": "...",
  "parsed_request": {...},
  "target_location": "Seattle, WA",
  "business_type": "coffee shop",
  "additional_context": "analyze the location viability",
  "stages_completed": [...],
  "current_date": "2026-01-19",
  "pipeline_stage": "intake",
  "market_research_findings": {...},
  "competitor_analysis": {...},
  "gap_analysis": {...},
  "strategic_report": {...},
  "html_report_content": "...",
  "infographic_base64": "..."
}
```

**Extraction Status:** ✅ Fully extracted to `extracted_data.state_variables`

### Events Array Structure

Each event in the `events` array:

| Field | Type | Description | Extracted? |
|-------|------|-------------|------------|
| `author` | string | Agent name or "user" | ✅ Yes → used for trace reconstruction |
| `content` | object | Message content | ✅ Yes → parsed for text/tool calls |
| `content.parts` | array | Content parts | ✅ Yes → parsed for function calls |
| `content.role` | string | "user" or "model" | ✅ Yes |
| `timestamp` | float | Event timestamp | ✅ Yes → used for latency |
| `usage_metadata` | object | Token usage data | ✅ Yes → used for token metrics |
| `model_version` | string | Model used | ✅ Yes |

### usage_metadata Structure

```json
{
  "prompt_token_count": 8547,
  "candidates_token_count": 1234,
  "total_token_count": 9781,
  "cached_content_token_count": 0
}
```

**Extraction Status:** ✅ Fully extracted for deterministic metrics

### content.parts Structure

Each part can contain:

| Field | Type | Description | Extracted? |
|-------|------|-------------|------------|
| `text` | string | Text content | ✅ Yes → used for responses |
| `function_call` | object | Tool invocation | ✅ Yes → tool_interactions |
| `function_call.name` | string | Tool name | ✅ Yes |
| `function_call.args` | object | Tool arguments | ✅ Yes |
| `function_call.id` | string | Call ID | ✅ Yes |
| `function_response` | object | Tool result | ✅ Yes → tool_interactions |
| `function_response.name` | string | Tool name | ✅ Yes |
| `function_response.response` | object | Tool output | ✅ Yes |
| `thought` | boolean | Is thinking content | ✅ Yes → thinking_trace |
| `thought_signature` | string | Signed thinking content | ⚠️ Not extracted (encrypted) |

---

## Fallback: eval_metric_result_per_invocation (Format 2)

When `session_details` is `None` (due to `app_name` mismatch), ADK stores data in an alternative format:

```
eval_metric_result_per_invocation[0]:
  └── actual_invocation:
        ├── invocation_id
        ├── user_content: {parts: [...], role: "user"}
        ├── final_response: {parts: [...], role: "model"}
        ├── intermediate_data:
        │     └── invocation_events: [...]
        ├── creation_timestamp
        ├── rubrics: null
        └── app_details:
              └── agent_details: {...}
```

### Data Available in Format 2

| Data | Format 1 (session_details) | Format 2 (actual_invocation) |
|------|---------------------------|------------------------------|
| Events | ✅ `session_details.events` | ✅ `intermediate_data.invocation_events` |
| User input | ✅ In events | ✅ `user_content` |
| Final response | ✅ In events | ✅ `final_response` |
| State variables | ✅ `session_details.state` | ❌ Not available |
| Token usage | ✅ `usage_metadata` per event | ❌ Not available |
| Agent instructions | ❌ Not available | ✅ `app_details.agent_details` |
| Tool declarations | ❌ Not available | ✅ `agent_details[].tool_declarations` |

### Format 2 Advantages

Format 2 has some data NOT available in Format 1:

```json
"app_details": {
  "agent_details": {
    "retail_location_strategy": {
      "name": "retail_location_strategy",
      "instructions": "Your primary role is to orchestrate...",
      "tool_declarations": [
        {
          "function_declarations": [
            {"name": "transfer_to_agent", "description": "Transfer the question..."},
            {"name": "IntakeAgent", "description": "Parses user request..."}
          ]
        }
      ]
    },
    "MarketResearchAgent": {...},
    "CompetitorMappingAgent": {...}
  }
}
```

**Extraction Status:** 🔄 Partially extracted (converter can use this, but currently prefers Format 1)

---

## What We Extract to JSONL

Our converter produces the following fields:

### Core Fields

| JSONL Field | Source | Description |
|-------------|--------|-------------|
| `request` | Built from events | Gemini batch format request |
| `response` | Built from events | Gemini batch format response |
| `question_id` | `case.eval_id` | Evaluation case ID |
| `session_id` | `session_details.id` | Session UUID |
| `app_name` | `session_details.app_name` | Agent folder name |
| `user_inputs` | Extracted from events | List of user messages |
| `final_response` | Last model text | Final agent response |

### Trace Data

| JSONL Field | Source | Used For |
|-------------|--------|----------|
| `session_trace` | Synthesized from events | Latency metrics |
| `trace_summary` | AgentClient analysis | trajectory_accuracy metric |
| `latency_data` | Calculated from spans | Latency metrics |
| `final_session_state` | Reconstructed session | Analysis |

### Extracted Data Object

| JSONL Field | Source | Used For |
|-------------|--------|----------|
| `extracted_data.state_variables` | `session_details.state` | state_variable_fidelity metric |
| `extracted_data.tool_interactions` | Parsed from events | tool_use_quality metric |
| `extracted_data.sub_agent_trace` | Parsed from events | trajectory_accuracy metric |
| `extracted_data.tool_declarations` | Generated from tools used | available_tools context |
| `extracted_data.system_instruction` | Generated placeholder | Context |
| `extracted_data.thinking_trace` | Events with `thought=true` | thinking_metrics |
| `extracted_data.grounding_chunks` | From candidates metadata | grounding_utilization |
| `extracted_data.per_turn_tokens` | `usage_metadata` per event | token_usage metrics |
| `extracted_data.stop_reasons` | From finish_reason | Context |
| `extracted_data.conversation_history` | Built from events | Custom metrics |

### ADK Scores (Passthrough)

| JSONL Field | Source | Description |
|-------------|--------|-------------|
| `adk_score.hallucinations_v1` | `eval_metric_results` | ADK's hallucination score |
| `adk_score.safety_v1` | `eval_metric_results` | ADK's safety score |
| `adk_score.*` | `eval_metric_results` | Other ADK metrics |

---

## Gaps and Opportunities

### Currently Not Extracted

| Data | Location | Potential Use |
|------|----------|---------------|
| `thought_signature` | `content.parts[].thought_signature` | Encrypted, cannot use |
| Grounding sources | `candidates[].grounding_metadata` | Could improve grounding_utilization |
| Model version per call | `event.model_version` | Could track model usage |
| Cache details | `usage_metadata.cached_content_token_count` | Better cache_efficiency |

### Could Be Improved

| Current State | Improvement |
|---------------|-------------|
| `tool_declarations` are minimal | Use Format 2's rich `app_details.agent_details[].tool_declarations` |
| `system_instruction` is placeholder | Use Format 2's `agent_details[].instructions` |
| No multi-agent context | Extract all agent instructions from Format 2 |

### Requires ADK Changes

| Missing Data | Impact |
|--------------|--------|
| Token usage in Format 2 | Can't calculate costs when `app_name` is wrong |
| Real tool descriptions in Format 1 | Must maintain separate tool_descriptions.json |
| Per-turn model version | Can't track model switching |

---

## Verification Commands

### Check session_details availability
```bash
python3 << 'EOF'
import json, glob
files = glob.glob("app/.adk/eval_history/*.json")
with open(files[0]) as f:
    data = json.loads(f.read())
if isinstance(data, str): data = json.loads(data)
sd = data["eval_case_results"][0].get("session_details")
print(f"session_details is None: {sd is None}")
if sd:
    print(f"Events with usage_metadata: {sum(1 for e in sd['events'] if e.get('usage_metadata'))}")
EOF
```

### Check what converter produces
```bash
python3 << 'EOF'
import json
with open("eval/results/TIMESTAMP/raw/processed_interaction_sim.jsonl") as f:
    data = json.loads(f.readline())
print("Keys:", list(data.keys()))
print("Extracted data keys:", list(data.get("extracted_data", {}).keys()))
EOF
```

---

## Related Documentation

- [CONTEXT-HANDOFF-MULTI-TURN-METRICS.md](./CONTEXT-HANDOFF-MULTI-TURN-METRICS.md) - Session context and learnings
- [03-METRICS-GUIDE.md](./03-METRICS-GUIDE.md) - Metric configuration
- [converters.py](../src/evaluation/core/converters.py) - Converter implementation
