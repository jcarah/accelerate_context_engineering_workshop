# ADK Data Extraction Analysis

**Generated**: 2026-01-19
**Source**: retail-ai-location-strategy agent eval history

This document provides a field-by-field comparison of what data exists in ADK eval history vs what we extract in the converter.

---

## Summary

| Category | Available in ADK | Extracted | Coverage |
|----------|-----------------|-----------|----------|
| Core session data | 6 fields | 6 fields | 100% |
| State variables | 18 fields | 18 fields | 100% |
| Events | 30 events | 30 events | 100% |
| Event fields | 25 fields per event | ~8 fields used | 32% |
| Token usage | 11 fields | 11 fields | 100% |
| Tool interactions | Full data | Full data | 100% |

---

## Top Level: eval_case_results[0]

| ADK Field | Type | Extracted? | JSONL Location | Notes |
|-----------|------|------------|----------------|-------|
| `eval_set_file` | str | ❌ | - | Not needed for evaluation |
| `eval_set_id` | str | ❌ | - | Not needed for evaluation |
| `eval_id` | str | ✅ | `question_id` | Used as primary identifier |
| `final_eval_status` | int | ❌ | - | ADK's pass/fail status (could be useful) |
| `eval_metric_results` | None/list | ✅ | `adk_score.*` | Passthrough of ADK's own scores |
| `overall_eval_metric_results` | list | ✅ | `adk_score.*` | Passthrough of ADK's own scores |
| `eval_metric_result_per_invocation` | list | ❌ | - | Used as fallback when session_details is None |
| `session_id` | str | ✅ | `session_id` | |
| `session_details` | dict | ✅ | Multiple | Primary data source |
| `user_id` | str | ✅ | `ADK_USER_ID` | |

### Opportunity: `final_eval_status`
Could extract this to show ADK's overall pass/fail determination.

---

## session_details

| ADK Field | Type | Extracted? | JSONL Location |
|-----------|------|------------|----------------|
| `id` | str | ✅ | `session_id`, `final_session_state.id` |
| `app_name` | str | ✅ | `app_name`, `final_session_state.appName` |
| `user_id` | str | ✅ | `ADK_USER_ID`, `final_session_state.userId` |
| `state` | dict (18 keys) | ✅ | `extracted_data.state_variables` + flattened |
| `events` | list (30) | ✅ | `final_session_state.events` (camelCase) |
| `last_update_time` | float | ✅ | `final_session_state.lastUpdateTime` |

**Coverage: 100%**

---

## session_details.state (18 keys)

All state variables are fully extracted:

| State Variable | Type | Extracted? | Notes |
|----------------|------|------------|-------|
| `__llm_request_key__` | str | ✅ | Internal tracking |
| `parsed_request` | dict (3 keys) | ✅ | Contains targetLocation, businessType, additionalContext |
| `target_location` | str | ✅ | |
| `business_type` | str | ✅ | |
| `additional_context` | str | ✅ | |
| `stages_completed` | list (7) | ✅ | Pipeline progress |
| `current_date` | str | ✅ | |
| `pipeline_stage` | str | ✅ | Current stage |
| `pipeline_start_time` | str | ✅ | ISO timestamp |
| `market_research_findings` | str (9982 chars) | ✅ | Research output |
| `competitor_analysis` | str (7317 chars) | ✅ | Analysis output |
| `gap_analysis` | str (4978 chars) | ✅ | Analysis output |
| `gap_analysis_code` | str (7414 chars) | ✅ | Generated code |
| `strategic_report` | dict (10 keys) | ✅ | Full report structure |
| `html_report_content` | str (31KB) | ✅ | Generated HTML |
| `report_generation_result` | str | ✅ | Status message |
| `infographic_base64` | str (1MB) | ✅ | Base64 image |
| `infographic_result` | str | ✅ | Status message |

**Coverage: 100%**

---

## Event Structure (25 fields per event)

Each event in `session_details.events` has these fields:

| ADK Field | Type | Extracted? | Usage | Notes |
|-----------|------|------------|-------|-------|
| `model_version` | str | ⚠️ | In spans only | Could expose as metric |
| `content` | dict | ✅ | Text, tool calls | Primary content |
| `content.parts` | list | ✅ | Parsed for text/function_call | |
| `content.role` | str | ✅ | user/model | |
| `grounding_metadata` | None | ⚠️ | Not found in data | Field exists but was null |
| `partial` | None | ❌ | - | Streaming-related |
| `turn_complete` | None | ❌ | - | Streaming-related |
| `finish_reason` | str | ✅ | `stop_reasons` | STOP, MAX_TOKENS, etc |
| `error_code` | None | ❌ | - | For error handling |
| `error_message` | None | ❌ | - | For error handling |
| `interrupted` | None | ❌ | - | For interruption handling |
| `custom_metadata` | dict | ❌ | - | Contains `__llm_request_key__` |
| `usage_metadata` | dict | ✅ | `per_turn_tokens` | Token counts |
| `live_session_resumption_update` | None | ❌ | - | For live sessions |
| `input_transcription` | None | ❌ | - | For voice |
| `output_transcription` | None | ❌ | - | For voice |
| `avg_logprobs` | None | ❌ | - | Model confidence |
| `logprobs_result` | None | ❌ | - | Token probabilities |
| `cache_metadata` | None | ❌ | - | Caching info |
| `citation_metadata` | None | ❌ | - | Source citations |
| `invocation_id` | str | ❌ | - | Could correlate invocations |
| `author` | str | ✅ | Agent identification | Used for sub_agent_trace |
| `actions` | dict | ⚠️ | Partially | Contains state_delta, transfer_to_agent |
| `long_running_tool_ids` | list | ❌ | - | Async tool tracking |
| `branch` | None | ❌ | - | Branching logic |
| `id` | str | ❌ | - | Event ID |
| `timestamp` | float | ✅ | Latency calculations | |

### Opportunities

1. **`model_version`** - Could track which model was used per turn (e.g., gemini-2.5-flash vs gemini-2.5-pro)

2. **`error_code` / `error_message`** - Could detect and report tool/agent failures

3. **`actions.state_delta`** - Contains the actual state changes per turn, useful for debugging state flow

4. **`actions.transfer_to_agent`** - Explicitly shows agent handoffs

5. **`invocation_id`** - Could correlate related events within a multi-turn conversation

6. **`avg_logprobs`** - Model confidence scores (when available)

---

## usage_metadata (Token Tracking)

Fully extracted. Each event with usage_metadata contains:

| Field | Type | Extracted? | Notes |
|-------|------|------------|-------|
| `prompt_token_count` | int | ✅ | Input tokens |
| `candidates_token_count` | int | ✅ | Output tokens |
| `total_token_count` | int | ✅ | Total |
| `thoughts_token_count` | int | ✅ | Reasoning tokens |
| `cached_content_token_count` | int/None | ✅ | Cached tokens |
| `cache_tokens_details` | None | ✅ | (Usually null) |
| `candidates_tokens_details` | None | ✅ | (Usually null) |
| `prompt_tokens_details` | list | ✅ | Per-modality breakdown |
| `tool_use_prompt_token_count` | None | ✅ | Tool-specific tokens |
| `tool_use_prompt_tokens_details` | None | ✅ | (Usually null) |
| `traffic_type` | None | ✅ | (Usually null) |

**Coverage: 100%**

---

## content.parts Structure

Different part types found in events:

### Type 1: Text Response
```json
{
  "text": "Hello! I can certainly help you with that..."
}
```
**Extracted?** ✅ Yes - used for `sub_agent_trace.text_response`

### Type 2: Text with Thought Signature
```json
{
  "text": "Let me analyze the request...",
  "thought_signature": "<encrypted_signature>"
}
```
**Extracted?** ⚠️ Partial - text extracted, signature ignored (encrypted)

### Type 3: Function Call
```json
{
  "function_call": {
    "id": "adk-xxx",
    "args": {"request": "..."},
    "name": "IntakeAgent",
    "partial_args": null,
    "will_continue": null
  }
}
```
**Extracted?** ✅ Yes - `tool_interactions` with name, args, call_id

### Type 4: Function Response
```json
{
  "function_response": {
    "id": "adk-xxx",
    "name": "IntakeAgent",
    "parts": [...],
    "scheduling": null,
    "will_continue": null
  }
}
```
**Extracted?** ✅ Yes - `tool_interactions.output_result`

### Type 5: Function Call with Thought
```json
{
  "function_call": {...},
  "thought_signature": "<encrypted>"
}
```
**Extracted?** ⚠️ Partial - function_call extracted, signature ignored

---

## What We Generate (Not from ADK)

These fields are synthesized by the converter:

| JSONL Field | Source | Notes |
|-------------|--------|-------|
| `session_trace` | Synthesized from events | OpenTelemetry-style spans |
| `trace_summary` | AgentClient analysis | Trajectory string |
| `latency_data` | Calculated from timestamps | Total, average, per-tool |
| `tool_declarations` | Generated from tool usage | Minimal descriptions |
| `system_instruction` | Placeholder | "You are the {app_name} agent." |
| `request` / `response` | Built from events | Gemini batch format |

---

## Data NOT Extracted (Potential Improvements)

### High Value

| Field | Location | Potential Use |
|-------|----------|---------------|
| `model_version` | Each event | Track model usage, cost by model |
| `actions.state_delta` | Each event | Debug state changes per turn |
| `actions.transfer_to_agent` | Each event | Explicit agent handoff tracking |
| `error_code/message` | Each event | Error detection and reporting |
| `final_eval_status` | Case level | ADK's pass/fail verdict |

### Medium Value

| Field | Location | Potential Use |
|-------|----------|---------------|
| `invocation_id` | Each event | Correlate multi-turn events |
| `custom_metadata` | Each event | Internal tracking keys |
| `avg_logprobs` | Each event | Model confidence metrics |

### Low Value (Rarely Used)

| Field | Location | Notes |
|-------|----------|-------|
| `grounding_metadata` | Each event | Was null in test data |
| `cache_metadata` | Each event | Was null in test data |
| `citation_metadata` | Each event | Was null in test data |
| `partial`, `turn_complete` | Each event | Streaming-related |
| `input/output_transcription` | Each event | Voice-related |
| `branch` | Each event | Branching logic |

---

## Recommendations

### Immediate Improvements

1. **Extract `model_version`** per event to track which models are being used
2. **Extract `actions.transfer_to_agent`** for explicit handoff tracking
3. **Extract `error_code/message`** for failure detection

### Future Improvements

1. **Extract `actions.state_delta`** for state change debugging
2. **Generate better `tool_declarations`** from actual agent tool definitions
3. **Generate better `system_instruction`** from agent prompts

### Verification Commands

```bash
# Check what's in ADK history
python3 -c "
import json, glob
files = glob.glob('app/.adk/eval_history/*.json')
with open(files[0]) as f: data = json.loads(f.read())
case = data['eval_case_results'][0]
print('Keys:', list(case['session_details'].keys()))
"

# Check what's in converted JSONL
python3 -c "
import json
with open('eval/results/TIMESTAMP/raw/processed_interaction_sim.jsonl') as f:
    data = json.loads(f.readline())
print('Extracted data keys:', list(data['extracted_data'].keys()))
"
```
