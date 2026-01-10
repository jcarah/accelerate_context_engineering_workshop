# Evaluation Pipeline

This document provides a comprehensive guide to the evaluation pipeline, a multi-step process designed to test, measure, and analyze the performance of ADK agents in an agent-agnostic way.

## Overview

The pipeline is orchestrated by three core scripts:

1.  **Step 1: `01_agent_interaction.py`**: Runs a set of questions against the agent and records enriched interactions.
2.  **Step 2: `02_agent_run_eval.py`**: (WIP) Calculates performance metrics based on the recorded interactions.
3.  **Step 3: `03_analyze_eval_results.py`**: (WIP) Generates a detailed, AI-powered analysis of the results.

**Note:** We are currently working on **standardizing Steps 2 and 3**. These scripts are being refactored to be more robust and agent-agnostic, ensuring that the team has a clear and consistent way to interpret evaluation scores and strategic insights.

## Step 1: Running Agent Interactions

This script runs a dataset of questions against your agent and produces a processed CSV file ready for evaluation.

### Setup

Before running, ensure you are in the `evaluation` directory and have synced the dependencies:

```bash
cd evaluation
uv sync
```

### Usage

```bash
uv run python 01_agent_interaction.py \
  --app-name <agent_app_name> \
  --base-url <agent_service_url> \
  --questions-file <path_to_golden_dataset.json> \
  --results-dir <output_directory> \
  [--state-variable key:value]
```

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--app-name` | The name of the application/agent (e.g., `customer_service`, `app`). **(Required)** | N/A |
| `--base-url` | The base URL where the agent service is running. | `https://genai.ops.dematic.dev` |
| `--questions-file` | One or more paths to JSON files with test questions. **(Required)** | N/A |
| `--user-id` | The user ID for the evaluation session. | `eval_user` |
| `--num-questions` | Number of questions to sample from each file. -1 for all. | `-1` |
| `--results-dir` | Directory to save results. | `evaluation/results` |
| `--state-variable` | Inject state variables during session creation (e.g., `customer_id:123`). Can be used multiple times. | N/A |
| `--runs` | Number of times to run each question (for variance testing). | `1` |

### Example

Running evaluation for the Customer Service agent:

```bash
uv run python 01_agent_interaction.py \
  --app-name customer_service \
  --base-url http://localhost:8501 \
  --questions-file datasets/customer_service_golden.json \
  --state-variable customer_id:123 \
  --results-dir results
```

---

## Data Structure: The Output CSV

The output of Step 1 is a CSV where each row represents a single run of a question.

### Exact Example from Customer Service Agent

Below is an actual row (formatted as JSON for readability) extracted from a successful evaluation run. Note that in the raw CSV, fields containing JSON (like `latency_data`) are stored as strings.

```json
{
  "status": { "boolean": "success" },
  "run_id": 1,
  "question_id": "cs_full_eb4390d8",
  "agents_evaluated": ["customer_service"],
  "user_inputs": [
    "hi",
    "can you please tell me what i purchased before?",
    "Ah yes! the tomato seeds. I planted and they grew but they do not look very healthy any more. Do you have a information on how to take care of them?",
    "yes please",
    "hm, whats currently in my cart?",
    "will that Fertilizer do for the tomatoes?",
    "ok",
    "no thats okey. lets check out now",
    "yes for the 10%!",
    "nop thats all, thanks for the help"
  ],
  "question_metadata": {
    "tenant": "cymbal_home_garden",
    "source_file": "full_conversation.test.json"
  },
  "interaction_datetime": "2026-01-09T23:49:23.176105",
  "session_id": "session_2e42ded4-885a-4384-96b5-75cc3fa84315",
  "base_url": "http://localhost:8501",
  "app_name": "customer_service",
  "ADK_USER_ID": "eval_user",
  "USER": "admin_danielazamora_altostrat_co",
  "reference_data": {
    "reference_tool_interactions": [...],
    "reference_trajectory": ["customer_service"]
  },
  "missing_information": { "boolean": false },
  "latency_data": [
    {
      "name": "invocation",
      "type": "OTHER",
      "duration_seconds": 4.6944,
      "children": [
        {
          "name": "invoke_agent customer_service_agent",
          "type": "OTHER",
          "duration_seconds": 4.6934,
          "children": [
            { "name": "call_llm", "type": "LLM_CALL", "duration_seconds": 4.6725 }
          ]
        }
      ]
    },
    "... (Additional turn latencies omitted for brevity)"
  ],
  "trace_summary": [],
  "session_trace": "... (Detailed trace data, see trace_<app>_<question_id>_<session_id>.json in results/)",
  "final_session_state": "... (Final state object, see session_<app>_<question_id>_<session_id>.json in results/)",
  "extracted_data": {
    "state_variables": {
      "customer_id": "123",
      "customer_profile": "{...}",
      "timer_start": 1768002604.0364587,
      "request_count": 6
    },
    "tool_interactions": [
      {
        "tool_name": "send_care_instructions",
        "input_arguments": {
          "plant_type": "Tomato",
          "delivery_method": "email",
          "customer_id": "123"
        },
        "call_id": "adk-d6bc4d3c-98d4-42b8-8876-f8a493656b3a",
        "output_result": {
          "status": "success",
          "message": "Care instructions for Tomato sent via email."
        }
      },
      "..."
    ],
    "sub_agent_trace": [
      {
        "agent_name": "customer_service_agent",
        "text_response": "Hello Alex! Welcome back to Cymbal Home & Garden...",
        "timestamp": 1768002569.10474
      },
      "..."
    ]
  }
}
``` \"invoke_agent customer_service_agent\", \"type\": \"OTHER\", \"duration_seconds\": 4.1932, \"children\": [{\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 4.1795}]}]}, {\"name\": \"invocation\", \"type\": \"OTHER\", \"duration_seconds\": 6.1406, \"children\": [{\"name\": \"invoke_agent customer_service_agent\", \"type\": \"OTHER\", \"duration_seconds\": 6.1372, \"children\": [{\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 2.3718, \"children\": [{\"name\": \"execute_tool get_product_recommendations\", \"type\": \"TOOL_CALL\", \"duration_seconds\": 0.0019}]}, {\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 3.7351}]}]}, {\"name\": \"invocation\", \"type\": \"OTHER\", \"duration_seconds\": 33.3861, \"children\": [{\"name\": \"invoke_agent customer_service_agent\", \"type\": \"OTHER\", \"duration_seconds\": 33.3821, \"children\": [{\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 3.6283, \"children\": [{\"name\": \"execute_tool access_cart_information\", \"type\": \"TOOL_CALL\", \"duration_seconds\": 0.001}]}, {\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 3.666}]}]}, {\"name\": \"invocation\", \"type\": \"OTHER\", \"duration_seconds\": 5.8602, \"children\": [{\"name\": \"invoke_agent customer_service_agent\", \"type\": \"OTHER\", \"duration_seconds\": 5.8564, \"children\": [{\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 2.9331, \"children\": [{\"name\": \"execute_tool generate_qr_code\", \"type\": \"TOOL_CALL\", \"duration_seconds\": 0.0008}]}, {\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 2.9129}]}]}, {\"name\": \"invocation\", \"type\": \"OTHER\", \"duration_seconds\": 5.7666, \"children\": [{\"name\": \"invoke_agent customer_service_agent\", \"type\": \"OTHER\", \"duration_seconds\": 5.7631, \"children\": [{\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 3.0245, \"children\": [{\"name\": \"execute_tool update_salesforce_crm\", \"type\": \"TOOL_CALL\", \"duration_seconds\": 0.0008}]}, {\"name\": \"call_llm\", \"type\": \"LLM_CALL\", \"duration_seconds\": 2.7259}]}]}]",
  "trace_summary": "[]",
  "session_trace": "... (Detailed trace data, see trace_<app>_<question_id>_<session_id>.json in results/)",
  "final_session_state": "... (Final state object, see session_<app>_<question_id>_<session_id>.json in results/)",
  "extracted_data": {
    "state_variables": {
      "customer_id": "123",
      "customer_profile": "{...}",
      "timer_start": 1768002604.0364587,
      "request_count": 6
    },
    "tool_interactions": [
      {
        "tool_name": "send_care_instructions",
        "input_arguments": {"plant_type": "Tomato", "delivery_method": "email", "customer_id": "123"},
        "call_id": "adk-d6bc4d3c-98d4-42b8-8876-f8a493656b3a",
        "output_result": {"status": "success", "message": "Care instructions sent."}
      },
      "..."
    ],
    "sub_agent_trace": [
      {
        "agent_name": "customer_service_agent",
        "text_response": "Hello Alex! Welcome back...",
        "timestamp": 1768002569.10474
      },
      "..."
    ]
  }
}
```

---

## Extending the Evaluation Framework

### Creating New Evaluation Datasets

You can create raw evaluation datasets using the `adk eval` command provided by the ADK framework. Once you have those files, use our conversion script to move them into the structured format required by this pipeline.

### Importing Existing Test Data

If you have test data in a turn-based format (a list of objects with `query` and `expected_tool_use`), use the `convert_test_to_golden.py` script:

```bash
uv run python scripts/convert_test_to_golden.py \
  --input path/to/your/test_data.json \
  --output datasets/your_new_golden_data.json \
  --agent <agent_app_name> \
  --metadata "complexity:easy" --metadata "domain:retail" \
  --prefix q_prefix
```