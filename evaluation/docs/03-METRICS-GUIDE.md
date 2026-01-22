# Defining Evaluation Metrics

This guide explains how to define metrics for evaluating your ADK agent. The pipeline supports three metric types:

| Type | Description | Example |
|------|-------------|---------|
| **Deterministic** | Auto-calculated from session trace | Token usage, latency, tool success rate |
| **API Predefined** | Built-in Vertex AI metrics | MULTI_TURN_GENERAL_QUALITY, MULTI_TURN_TEXT_QUALITY |
| **Custom LLM** | Your own evaluation prompts | State fidelity, trajectory accuracy |

---

## Quick Start

Metrics are defined in `eval/metrics/metric_definitions.json`:

```json
{
  "metrics": {
    "multi_turn_general_quality": {
      "metric_type": "llm",
      "is_managed": true,
      "managed_metric_name": "MULTI_TURN_GENERAL_QUALITY",
      "use_gemini_format": true,
      "natural_language_guidelines": "Evaluate if the agent maintains context..."
    },
    "trajectory_accuracy": {
      "metric_type": "llm",
      "dataset_mapping": {
        "prompt": { "source_column": "user_inputs" },
        "response": { "source_column": "trace_summary" }
      },
      "template": "Evaluate the agent trajectory...\n{prompt}\n{response}"
    }
  }
}
```

---

## Deterministic Metrics (Auto-calculated)

These metrics are calculated automatically from the session trace. No configuration required.

| Metric | Description | Example Output |
|--------|-------------|----------------|
| `token_usage` | LLM calls, tokens in/out, estimated cost | `{"total_tokens": 15420, "llm_calls": 8}` |
| `latency_metrics` | Total duration, time to first response | `{"total_seconds": 12.5, "first_response": 2.1}` |
| `cache_efficiency` | KV-cache hit rate | `{"hit_rate": 0.45}` |
| `thinking_metrics` | Reasoning token ratio | `{"ratio": 0.15}` |
| `tool_utilization` | Tool calls count, unique tools | `{"total_calls": 5, "unique_tools": 3}` |
| `tool_success_rate` | Success rate, failed tools list | `{"success_rate": 1.0}` |
| `grounding_utilization` | Grounding chunks used | `{"chunks_used": 12}` |
| `context_saturation` | Max tokens in a single turn | `{"max_context": 8192}` |
| `agent_handoffs` | Sub-agent invocations | `{"handoffs": 2}` |
| `output_density` | Average output tokens per turn | `{"avg_output": 450}` |

These appear in `eval_summary.json` under `deterministic_metrics` after every evaluation run.

---

## API Predefined Metrics (Vertex AI)

These use Google's built-in evaluators. Choose between **single-turn** and **multi-turn** variants based on your agent's conversation pattern.

### Choosing Single-Turn vs Multi-Turn Metrics

| Your Agent | Metric to Use | Example |
|------------|---------------|---------|
| **Multi-turn conversation** (user ↔ agent ↔ user ↔ agent) | `MULTI_TURN_*` | Customer service chatbot |
| **Single-turn / pipeline** (user → agent runs pipeline → final response) | `GENERAL_QUALITY`, `TEXT_QUALITY` | Retail location strategy agent |

> **Important**: Using `MULTI_TURN_*` metrics on single-turn agents will fail with error:
> `"Variable conversation_history is required but not provided"`

### Multi-Turn Metrics (for conversational agents)

```json
{
  "multi_turn_general_quality": {
    "metric_type": "llm",
    "is_managed": true,
    "managed_metric_name": "MULTI_TURN_GENERAL_QUALITY",
    "use_gemini_format": true,
    "score_range": {"min": 0, "max": 1, "description": "Passing rate"},
    "natural_language_guidelines": "Evaluate if the agent correctly maintains customer state throughout the conversation. Penalize responses that forget earlier context."
  }
}
```

### Single-Turn Metrics (for pipeline/single-response agents)

```json
{
  "general_quality": {
    "metric_type": "llm",
    "is_managed": true,
    "managed_metric_name": "GENERAL_QUALITY",
    "use_gemini_format": true,
    "score_range": {"min": 0, "max": 1, "description": "Passing rate"},
    "natural_language_guidelines": "Evaluate if the agent correctly processes the request and provides comprehensive analysis."
  },
  "text_quality": {
    "metric_type": "llm",
    "is_managed": true,
    "managed_metric_name": "TEXT_QUALITY",
    "use_gemini_format": true,
    "score_range": {"min": 0, "max": 1, "description": "Passing rate"}
  }
}
```

### Key Configuration

| Field | Required | Description |
|-------|----------|-------------|
| `is_managed` | Yes | Must be `true` |
| `managed_metric_name` | Yes | See table below |
| `use_gemini_format` | Yes | Must be `true` for API metrics |
| `natural_language_guidelines` | No | Custom evaluation criteria (recommended) |

### Available API Predefined Metrics

| Metric | Best For | Score Range |
|--------|----------|-------------|
| `GENERAL_QUALITY` | Single-turn overall quality | 0-1 (passing rate) |
| `TEXT_QUALITY` | Single-turn text coherence | 0-1 (passing rate) |
| `MULTI_TURN_GENERAL_QUALITY` | Multi-turn conversation quality | 0-1 (passing rate) |
| `MULTI_TURN_TEXT_QUALITY` | Multi-turn text coherence | 0-1 (passing rate) |
| `INSTRUCTION_FOLLOWING` | Instruction adherence | 0-1 (passing rate) |
| `GROUNDING` | Factual grounding | 0-1 (passing rate) |
| `SAFETY` | Safety compliance | 0-1 (passing rate) |
| `HALLUCINATION` | Hallucination detection | 0-1 (passing rate) |

---

## Custom LLM Metrics

Create your own evaluation metrics with custom prompts. This gives you full control over what to evaluate.

### Basic Structure

```json
{
  "my_custom_metric": {
    "metric_type": "llm",
    "agents": ["my_agent"],
    "score_range": {"min": 1, "max": 5, "description": "1=Failure, 5=Perfect"},
    "dataset_mapping": {
      "prompt": { "source_column": "user_inputs" },
      "response": { "source_column": "final_response" }
    },
    "template": "Evaluate this interaction...\n\n**User:** {prompt}\n**Agent:** {response}\n\nScore: [1-5]"
  }
}
```

### Dataset Mapping

Map data from your processed results to template variables:

| Placeholder | Source Column | Description |
|-------------|---------------|-------------|
| `prompt` | `user_inputs` | User's messages (JSON list) |
| `response` | `final_response` | Agent's final response |
| `response` | `trace_summary` | Agent trajectory summary |
| Any | `extracted_data:field` | Nested field from extracted_data |

### Nested Field Access

Use `:` to access nested fields in `extracted_data`:

```json
"dataset_mapping": {
  "prompt": { "source_column": "user_inputs" },
  "response": { "source_column": "extracted_data:strategic_report" },
  "tool_interactions": { "source_column": "extracted_data:tool_interactions" },
  "available_tools": { "source_column": "extracted_data:tool_declarations" }
}
```

### Available Extracted Data Fields

| Field | Description |
|-------|-------------|
| `extracted_data:tool_interactions` | List of tool calls with inputs/outputs |
| `extracted_data:tool_declarations` | Available tools (function schemas) |
| `extracted_data:conversation_history` | Full conversation in Content format |
| `extracted_data:sub_agent_trace` | Sub-agent invocation trace |
| `extracted_data:system_instruction` | Agent system prompt |
| `extracted_data:<state_var>` | Any agent-specific state variable |

### Compound Column Mapping

Combine multiple columns into a single template variable:

```json
"dataset_mapping": {
  "prompt": { "source_column": "user_inputs" },
  "response": {
    "template": "Location: {extracted_data_target_location}\nBusiness: {extracted_data_business_type}",
    "source_columns": ["extracted_data:target_location", "extracted_data:business_type"]
  }
}
```

Note: Replace `:` with `_` in template placeholders.

---

## Example Metrics

### Trajectory Accuracy

Evaluate if the agent followed the correct sequence of steps:

```json
"trajectory_accuracy": {
  "metric_type": "llm",
  "agents": ["my_agent"],
  "score_range": {"min": 0, "max": 5, "description": "0=Wrong, 5=Perfect"},
  "dataset_mapping": {
    "prompt": { "source_column": "user_inputs" },
    "response": { "source_column": "trace_summary" }
  },
  "template": "Evaluate the agent's execution trajectory.\n\n**User Request:**\n{prompt}\n\n**Agent Trajectory:**\n{response}\n\n**Scoring (0-5):**\n- 5: Perfect - logical order, all required steps\n- 3: Mostly correct with minor deviations\n- 0: Completely wrong or empty\n\nScore: [0-5]\nExplanation: [Reasoning]"
}
```

### Tool Usage Quality

Custom metric to evaluate tool usage patterns:

```json
"tool_use_quality": {
  "metric_type": "llm",
  "agents": ["my_agent"],
  "score_range": {"min": 0, "max": 5, "description": "0=Poor, 5=Excellent"},
  "dataset_mapping": {
    "prompt": { "source_column": "user_inputs" },
    "response": { "source_column": "final_response" },
    "tool_interactions": { "source_column": "extracted_data:tool_interactions" },
    "available_tools": { "source_column": "extracted_data:tool_declarations" }
  },
  "template": "Evaluate tool usage for this request.\n\n**User Request:**\n{prompt}\n\n**Available Tools:**\n{available_tools}\n\n**Tool Calls Made:**\n{tool_interactions}\n\n**Final Response:**\n{response}\n\n**Criteria:**\n1. Tool Selection: Were appropriate tools chosen?\n2. Arguments: Were parameters correct?\n3. Coverage: Was research comprehensive?\n4. Efficiency: Were calls logical and non-redundant?\n\n**Scoring (0-5):**\n- 5: Optimal tool usage\n- 3: Acceptable with some issues\n- 0: Failed or no tool usage\n\nScore: [0-5]\nExplanation: [Reasoning]"
}
```

### State Variable Fidelity

Evaluate if state variables were correctly extracted:

```json
"state_variable_fidelity": {
  "metric_type": "llm",
  "agents": ["my_agent"],
  "score_range": {"min": 1, "max": 5, "description": "1=Failure, 5=Perfect"},
  "dataset_mapping": {
    "prompt": { "source_column": "user_inputs" },
    "response": {
      "template": "Location: {extracted_data_target_location}\nBusiness: {extracted_data_business_type}",
      "source_columns": ["extracted_data:target_location", "extracted_data:business_type"]
    }
  },
  "template": "Evaluate state extraction accuracy.\n\n**User Request:**\n{prompt}\n\n**Extracted State:**\n{response}\n\n**Scoring (1-5):**\n- 5: Perfect alignment\n- 3: Partially correct\n- 1: Complete failure\n\nScore: [1-5]\nExplanation: [Reasoning]"
}
```

---

## Tips for Custom Metrics

1. **Be specific** - Define exactly what each score level means
2. **Request structured output** - Ask for `Score: [X]` format for easy parsing
3. **Use score_range** - Documents the expected output range
4. **Filter by agent** - Use `agents` array to apply metrics to specific agents
5. **Use compound mapping** - For large state objects, select only specific fields to reduce token usage

---

## Output Structure

Metrics produce results in `eval_summary.json`:

```json
{
  "deterministic_metrics": {
    "token_usage": {"total_tokens": 15420, "llm_calls": 8},
    "latency_metrics": {"total_seconds": 12.5},
    "tool_success_rate": {"success_rate": 1.0}
  },
  "llm_based_metrics": {
    "multi_turn_general_quality": {
      "average": 0.85,
      "score_range": {"min": 0, "max": 1}
    },
    "trajectory_accuracy": {
      "average": 4.2,
      "score_range": {"min": 0, "max": 5}
    }
  }
}
```

API Predefined metrics also include `rubric_verdicts` with pass/fail details for each evaluation criterion.

---

## Related Documentation

- [01-GETTING-STARTED.md](01-GETTING-STARTED.md) - Quick start guide
- [02-EVALUATION-PATHS.md](02-EVALUATION-PATHS.md) - Understanding input data formats
- [05-OUTPUT-FILES.md](05-OUTPUT-FILES.md) - Understanding output files
