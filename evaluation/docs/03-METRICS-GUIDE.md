# Defining Evaluation Metrics

This document explains how to create evaluation metrics for your agent. The pipeline supports both **Custom LLM Metrics** (using your own prompts) and **Managed Rubric Metrics** (using Google's pre-built evaluators via Vertex AI).

---

## Metric Definition File

Metrics are defined in a JSON file (e.g., `eval/metrics/metric_definitions.json`). The structure is a dictionary where keys are the unique metric names.

```json
{
  "metrics": {
    "my_custom_metric": { ... },
    "my_managed_metric": { ... }
  }
}
```

---

## Schema Reference

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `metric_type` | `string` | Yes | Must be `"llm"` for this pipeline. |
| `is_managed` | `bool` | No | `true` to use a Vertex AI managed rubric metric. `false` (default) for custom. |
| `description` | `string` | No | A human-readable summary of what is being measured. |
| `agents` | `list` | No | List of `app_name`s this metric applies to. If omitted, applies to all. |
| `dataset_mapping` | `object` | Yes | Maps columns from your results CSV to the variables expected by the evaluator. |
| `managed_metric_name` | `string` | If Managed | The ID of the Vertex AI metric (e.g., `GENERAL_QUALITY`, `TOOL_USE_QUALITY`). |
| `template` | `string` | If Custom | The full prompt template for the LLM judge with placeholders. |
| `score_range` | `object` | Recommended | Score range info: `{"min": 0, "max": 5, "description": "..."}` |

---

## Data Mapping (`dataset_mapping`)

This is the most critical part. It tells the evaluator where to find the data to grade.

### SDK Requirement: `prompt` and `response` Keys

> **IMPORTANT**: The Vertex AI SDK requires `prompt` and `response` columns in the dataset. Your `dataset_mapping` must include these two keys, even for custom metrics.

For **custom LLM metrics**, you map your source data to `prompt` and `response`:

```json
"dataset_mapping": {
  "prompt": {
    "source_column": "user_inputs"
  },
  "response": {
    "source_column": "extracted_data:state_variables"
  }
}
```

Then your template uses `{prompt}` and `{response}` placeholders:

```
**User Request:**
{prompt}

**Agent State:**
{response}
```

### Mapping Syntax

```json
"dataset_mapping": {
  "placeholder_name": {
    "source_column": "column_path",
    "default": "optional_default_value"
  }
}
```

- **`placeholder_name`**: The variable name used in the template or expected by managed metrics
- **`source_column`**: Path to the data in the processed CSV
- **`default`**: Optional fallback value if the column is not found

### Supported Source Columns

| Column | Description |
| :--- | :--- |
| `user_inputs` | The user's question(s) - JSON list or string |
| `final_response` | The agent's final text response |
| `trace_summary` | Agent trajectory as list of steps |
| `extracted_data` | JSON containing state variables & tool interactions |
| `session_trace` | Full OpenTelemetry execution trace |
| `reference_data` | Expected answers from Golden Dataset |

### Nested Lookup Syntax (`:`)

Access nested fields in JSON columns using a colon:
- `extracted_data:state_variables` → State variables from extracted_data
- `extracted_data:tool_interactions` → Tool call logs from extracted_data
- `reference_data:expected_response` → Expected response from reference_data

### Compound Column Mapping (Template Syntax)

When you need to combine multiple source columns into a single `prompt` or `response` value, use the template syntax instead of `source_column`. This is useful for:
- Reducing token usage by selecting only specific state variables
- Avoiding RESOURCE_EXHAUSTED errors from large state objects
- Creating structured input from multiple data sources

**Syntax:**
```json
"dataset_mapping": {
  "response": {
    "template": "Location: {extracted_data_target_location}\nBusiness: {extracted_data_business_type}",
    "source_columns": ["extracted_data:target_location", "extracted_data:business_type"]
  }
}
```

**Key points:**
1. Use `template` instead of `source_column` in the mapping
2. List all source columns in `source_columns` array
3. In the template, replace `:` with `_` for placeholder names (e.g., `extracted_data:target_location` → `{extracted_data_target_location}`)

**Full Example:**
```json
"state_variable_fidelity": {
  "metric_type": "llm",
  "agents": ["my_agent"],
  "score_range": {"min": 1, "max": 5, "description": "1=Failure, 5=Perfect"},
  "dataset_mapping": {
    "prompt": {
      "source_column": "user_inputs"
    },
    "response": {
      "template": "Target Location: {extracted_data_target_location}\nBusiness Type: {extracted_data_business_type}\nParsed Request: {extracted_data_parsed_request}",
      "source_columns": ["extracted_data:target_location", "extracted_data:business_type", "extracted_data:parsed_request"]
    }
  },
  "template": "Evaluate state extraction...\n\n**User Request:**\n{prompt}\n\n**Extracted State:**\n{response}\n\nScore: [1-5]"
}
```

> **Tip**: Use compound mapping instead of `extracted_data:state_variables` when the full state object is large. This reduces token usage and prevents RESOURCE_EXHAUSTED errors.

---

## Custom LLM Metrics

Use custom metrics when you want to evaluate specific business logic with your own rubric.

### Template Requirements

> **SDK Restriction**: Custom templates **must** use `{prompt}` and `{response}` as placeholder names. The Vertex AI SDK validates that all dataset columns have corresponding placeholders in the template.

### Correct Custom Metric Pattern

```json
"state_variable_fidelity": {
  "metric_type": "llm",
  "agents": ["my_agent"],
  "score_range": {"min": 1, "max": 5, "description": "1=Complete failure, 5=Perfect alignment"},
  "dataset_mapping": {
    "prompt": {
      "source_column": "user_inputs"
    },
    "response": {
      "source_column": "extracted_data:state_variables"
    }
  },
  "template": "You are evaluating an AI Agent's state management.\n\n**User Request:**\n{prompt}\n\n**Final State Variables:**\n{response}\n\n**Scoring (1-5):**\n- 5: Perfect alignment\n- 1: Complete failure\n\nScore: [1-5]\nExplanation: [Reasoning]"
}
```

Key points:
1. **`dataset_mapping`** uses `prompt` and `response` as keys (not custom names)
2. **`template`** uses `{prompt}` and `{response}` placeholders
3. **Template text** can describe what prompt/response represent (e.g., "User Request", "State Variables")

### Custom Metric Tips

1. **Be specific in your rubric** - Define exactly what each score level means
2. **Include the score_range field** - Documents the expected output range
3. **Request structured output** - Ask for `Score: X` format for easy parsing
4. **Test your prompts** - Run a few examples to validate scoring behavior
5. **Use compound mapping for large data** - If the full `state_variables` or `tool_interactions` object is too large, use compound column mapping to select only specific fields (see [Compound Column Mapping](#compound-column-mapping-template-syntax))

---

## Score Ranges

The `score_range` field documents the expected score range for each metric. This is included in the evaluation summary output.

### Custom Metric Ranges

Define your scoring scale in the template and document it in `score_range`:

```json
"score_range": {"min": 1, "max": 5, "description": "1=Failure, 5=Perfect"}
```

### Managed Metric Ranges

| Metric | Range | Description |
| :--- | :--- | :--- |
| `GENERAL_QUALITY` | 0-1 | Passing rate (rubrics passed / total) |
| `TEXT_QUALITY` | 0-1 | Passing rate (rubrics passed / total) |
| `INSTRUCTION_FOLLOWING` | 0-1 | Passing rate (rubrics passed / total) |
| `SAFETY` | 0 or 1 | Binary: 0=unsafe, 1=safe |
| `FINAL_RESPONSE_QUALITY` | 0-1 | Passing rate (rubrics passed / total) |
| `TOOL_USE_QUALITY` | 0-1 | Passing rate (rubrics passed / total) |
| `HALLUCINATION` | 0-1 | Rate of supported claims (1=no hallucinations) |
| `GROUNDING` | 0-1 | Rate of grounded claims |
| `FINAL_RESPONSE_MATCH` | 0 or 1 | Binary: 0=no match, 1=match |

---

## Managed Rubric Metrics (Vertex AI)

Managed metrics use Google's pre-built evaluators. Each has specific input requirements.

> **Reference**: [Vertex AI Rubric Metric Details](https://cloud.google.com/vertex-ai/generative-ai/docs/models/rubric-metric-details)

### Basic Metrics (require `prompt` + `response`)

| Metric Name | Score Range | Description |
| :--- | :--- | :--- |
| `GENERAL_QUALITY` | 0-1 | Comprehensive quality evaluation |
| `TEXT_QUALITY` | 0-1 | Linguistic quality (fluency, coherence) |
| `INSTRUCTION_FOLLOWING` | 0-1 | Adherence to prompt constraints |
| `SAFETY` | 0/1 | Policy violation check |

**Example:**
```json
"general_quality": {
  "metric_type": "llm",
  "is_managed": true,
  "managed_metric_name": "GENERAL_QUALITY",
  "score_range": {"min": 0, "max": 1, "description": "Passing rate: 0=all failed, 1=all passed"},
  "dataset_mapping": {
    "prompt": { "source_column": "user_inputs" },
    "response": { "source_column": "final_response" }
  }
}
```

### Agent Metrics (require `intermediate_events`)

These metrics evaluate agent tool usage and are critical for agentic workflows.

| Metric Name | Score Range | Description |
| :--- | :--- | :--- |
| `TOOL_USE_QUALITY` | 0-1 | Tool selection, parameters, sequence |
| `FINAL_RESPONSE_QUALITY` | 0-1 | Comprehensive agent response quality |
| `HALLUCINATION` | 0-1 | Factuality check against tool outputs |

**Required Inputs:**
- `prompt`: User's request
- `developer_instruction`: Agent's system prompt (can be empty)
- `tool_declarations`: List of available tools (can be empty `[]`)
- `intermediate_events`: Tool calls and responses (converted to Event objects)

**Example - TOOL_USE_QUALITY:**
```json
"agent_tool_use_quality": {
  "metric_type": "llm",
  "is_managed": true,
  "managed_metric_name": "TOOL_USE_QUALITY",
  "score_range": {"min": 0, "max": 1, "description": "Passing rate"},
  "dataset_mapping": {
    "prompt": { "source_column": "user_inputs" },
    "developer_instruction": {
      "source_column": "extracted_data:system_instruction",
      "default": ""
    },
    "tool_declarations": {
      "source_column": "extracted_data:tool_declarations",
      "default": "[]"
    },
    "intermediate_events": {
      "source_column": "extracted_data:tool_interactions"
    }
  }
}
```

> **Note**: The `intermediate_events` column is automatically converted to Vertex AI `Event` objects by the data mapper. The source format should be:
> ```json
> [
>   {"tool_name": "search", "input_arguments": {...}, "output_result": {...}},
>   ...
> ]
> ```

### Context-Based Metrics

| Metric Name | Score Range | Required Inputs |
| :--- | :--- | :--- |
| `GROUNDING` | 0-1 | prompt, response, context |
| `FINAL_RESPONSE_MATCH` | 0/1 | prompt, response, reference |

---

## Reference-Based Metrics and Evaluation Paths

Some metrics require **reference data** (ground truth expected answers). Understanding when these work is important.

### Metrics Requiring Reference Data

| Metric | Required Reference | Path A (Simulation) | Path B (Golden Dataset) |
| :--- | :--- | :--- | :--- |
| `FINAL_RESPONSE_MATCH` | `reference_data:expected_response` | Returns `null` | Works |
| Custom trajectory metrics | `reference_data:reference_trajectory` | Returns `null` | Works |
| State validation metrics | `reference_data:reference_state_variables` | Returns `null` | Works |

### Why Path A Cannot Provide Reference Data

**Path A (Simulation)** uses the ADK User Simulator with conversation scenarios. The scenarios define:
- `starting_prompt`: Initial user message
- `conversation_plan`: How the conversation should proceed

However, scenarios **do not include expected answers** because:
1. The LLM user simulator dynamically generates follow-up questions
2. The agent's responses depend on real-time tool outputs
3. There's no predetermined "correct" answer

### When to Use Path B

If your evaluation requires comparing against expected answers, use **Path B (Golden Datasets)**:

```json
// eval/eval_data/test.json format supports reference data
[
  {
    "query": "What's my order status?",
    "expected_tool_use": [{"tool_name": "get_order", "tool_input": {"id": "123"}}],
    "reference": "Your order #123 is shipped and arriving tomorrow."
  }
]
```

### What Happens with Missing Reference Data?

When a reference-based metric runs without reference data:
- **Score**: Returns `null`
- **Error**: None (graceful handling)
- **Other metrics**: Continue to work normally

You can safely include metrics like `FINAL_RESPONSE_MATCH` in your metric definitions - they simply won't produce scores for Path A runs.

---

## Output Structure

Each metric produces results with the following structure:

### Standard Output
```json
{
  "score": 4.5,
  "explanation": "The response correctly addressed..."
}
```

### Managed Rubric Metrics (with verdicts)

Managed rubric metrics return detailed verdicts from the Vertex AI API:

```json
{
  "score": 0.75,
  "rubric_verdicts": [
    {
      "evaluated_rubric": {
        "content": {"property": {"description": "The response is helpful."}},
        "type": "CONTENT_REQUIREMENT:HELPFULNESS",
        "importance": "HIGH"
      },
      "verdict": true,
      "reasoning": "The response directly addresses the user's question..."
    },
    {
      "evaluated_rubric": {
        "content": {"property": {"description": "The response is accurate."}},
        "type": "FACTUAL_ACCURACY:CORRECTNESS"
      },
      "reasoning": "The response contains an inaccuracy..."
    }
  ]
}
```

**Understanding Rubric Verdicts:**
- **`score`**: Overall passing rate (verdicts passed / total verdicts)
- **`verdict`**: `true` for passed, absent or `false` for failed
- **`type`**: Category from API (e.g., `INTENT:ADDRESS_USER_QUERY`). Some metrics return empty type
- **`reasoning`**: Explanation for the verdict
- **`importance`**: `HIGH`, `MEDIUM`, or `LOW` (affects score weight)

> **Note**: The API does not provide individual scores per rubric - only pass/fail verdicts. The overall score is the weighted pass rate. Empty `type` fields are normal API behavior for some metrics like TEXT_QUALITY and INSTRUCTION_FOLLOWING.

### Overall Summary (with score ranges)

The evaluation summary includes score ranges for LLM metrics:
```json
"llm_based_metrics": {
  "strategic_recommendation_quality": {
    "average": 4.25,
    "score_range": {"min": 1, "max": 5, "description": "1=Failure, 5=Strategic mastery"}
  },
  "general_conversation_quality": {
    "average": 0.85,
    "score_range": {"min": 0, "max": 1, "description": "Passing rate"}
  }
}
```

---

## Deterministic Metrics

In addition to LLM-based metrics, the pipeline calculates deterministic metrics automatically from the execution trace:

| Metric | Description |
|--------|-------------|
| `latency_metrics` | Total duration, avg turn latency, time to first response |
| `cache_efficiency` | KV-cache hit rate, cached vs fresh tokens |
| `thinking_metrics` | Reasoning ratio (thinking / output tokens) |
| `tool_utilization` | Total and unique tool calls |
| `tool_success_rate` | Successful calls / total calls |
| `context_saturation` | Max tokens in any single turn |
| `agent_handoffs` | Control transfers between agents |

These are calculated from the `session_trace` column and do not require metric definitions.

---

## Related Documentation

- [01-GETTING-STARTED.md](01-GETTING-STARTED.md) - Quick start guide
- [02-EVALUATION-PATHS.md](02-EVALUATION-PATHS.md) - Understanding input data formats
- [05-OUTPUT-FILES.md](05-OUTPUT-FILES.md) - Understanding output files
