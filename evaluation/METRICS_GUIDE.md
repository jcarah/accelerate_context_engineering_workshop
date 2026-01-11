# Guide to Defining Evaluation Metrics

This document explains how to create custom evaluation metrics for your agent. The pipeline uses a JSON configuration file to define **LLM-as-a-Judge** metrics, which are evaluated by Vertex AI (Gemini).

## 📄 Metric Definition File

Metrics are defined in a JSON file (e.g., `metrics/metric_definitions_your_agent.json`). The structure is a dictionary where keys are the unique metric names.

```json
{
  "metrics": {
    "my_custom_metric": { ... },
    "my_managed_metric": { ... }
  }
}
```

---

## 🛠️ Schema Reference

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`metric_type`** | `string` | Yes | Must be `"llm"` for this pipeline. |
| **`is_managed`** | `bool` | Yes | `true` to use a Google-predefined rubric (e.g., `TOOL_USE_QUALITY`). `false` to define your own. |
| **`description`** | `string` | Yes | A human-readable summary of what is being measured. |
| **`agents`** | `list` | No | List of `app_name`s this metric applies to. If omitted, applies to all. |
| **`dataset_mapping`** | `object` | Yes | Maps columns from your results CSV to the variables expected by the evaluator. |
| **`managed_metric_name`** | `string` | If Managed | The ID of the Google metric (e.g., `GENERAL_QUALITY`, `TOOL_USE_QUALITY`). |
| **`instruction`** | `string` | If Custom | The high-level task for the LLM judge (e.g., "Evaluate if the SQL is valid"). |
| **`criteria`** | `object` | If Custom | A dictionary of specific questions/checks for the judge. |
| **`rating_scores`** | `object` | If Custom | A 1-5 rubric definition. |

---

## 🔗 Data Mapping (`dataset_mapping`)

This is the most critical part. It tells the evaluator where to find the data to grade.
The keys (e.g., `prompt`, `response`) depend on whether you are using a Custom or Managed metric.

**Supported Source Columns:**
*   `user_inputs` (The user's question)
*   `final_session_state` (Full agent memory)
*   `session_trace` (Full execution trace)
*   `extracted_data` (Parsed state variables)
*   `reference_data` (Expected answers from Golden Dataset)

**Nested Lookup Syntax (`:`):**
You can access nested fields in JSON columns using a colon.
*   `extracted_data:customer_profile` -> Looks inside the `extracted_data` JSON for the `customer_profile` key.
*   `reference_data:reference_trajectory` -> Looks inside `reference_data` for the `reference_trajectory` key.

---

## 📝 Template: Custom LLM Metric

Use this when you want to grade specific business logic (e.g., "Did the agent extract the correct entities?").

```json
"state_capture_accuracy": {
    "metric_type": "llm",
    "is_managed": false,
    "description": "Checks if the agent correctly saved the user's booking details.",
    
    "instruction": "Evaluate if the agent correctly extracted the destination and dates.",
    
    "criteria": {
        "Destination": "Is the destination city correct?",
        "Dates": "Are the check-in and check-out dates valid and in the future?",
        "Completeness": "Are all required fields present?"
    },
    
    "rating_scores": {
        "1": "Completely wrong or empty.",
        "3": "Partially correct; missed one field.",
        "5": "Perfect capture of all details."
    },
    
    "dataset_mapping": {
        "prompt": { "source_column": "user_inputs" },
        "reference": { "source_column": "reference_data:expected_booking" },
        "response": { "source_column": "extracted_data:booking_variable" }
    }
}
```

---

## 🏢 Template: Managed Metric

Use this to leverage Google's pre-tuned rubrics for general quality.

```json
"response_fluency": {
    "metric_type": "llm",
    "is_managed": true,
    "managed_metric_name": "GENERAL_QUALITY",
    "description": "Assess if the response is fluent and helpful.",
    
    "dataset_mapping": {
        "prompt": { "source_column": "user_inputs" },
        "response": { "source_column": "extracted_data:sub_agent_trace" }
    }
}
```

### Special Case: Tool Usage Metrics

**Recommended Approach:** Use a **Custom Metric** (`is_managed: false`) for tool usage evaluation.
Why? The Vertex AI SDK's managed `TOOL_USE_QUALITY` metric has strict type requirements (List of Event Objects) that can conflict with DataFrame inputs. A Custom Metric allows us to robustly flatten the tool interactions into a JSON string, which the LLM judge can then evaluate perfectly.

```json
"tool_usage_accuracy": {
    "metric_type": "llm",
    "is_managed": false,
    "description": "Evaluates if the agent used the correct tools with the correct arguments.",
    "instruction": "Assess whether the tool calls made by the agent were necessary, correct, and effective.",
    "criteria": {
        "Selection": "Did the agent choose the right tool?",
        "Arguments": "Were the arguments correct?",
        "Outcome": "Did it help solve the user's problem?"
    },
    "rating_scores": {
        "1": "Wrong tool or critical error.",
        "5": "Perfect tool usage."
    },
    "dataset_mapping": {
        "prompt": { "source_column": "user_inputs" },
        "response": { "source_column": "extracted_data:sub_agent_trace" },
        "tool_usage": { "source_column": "extracted_data:tool_interactions" }
    }
}
```
