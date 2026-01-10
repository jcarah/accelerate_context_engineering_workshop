# Evaluation Pipeline

This document provides a comprehensive guide to the evaluation pipeline, a multi-step process designed to test, measure, and analyze the performance of ADK agents in an agent-agnostic way.

## Overview

The pipeline is orchestrated by three core scripts:

1.  **Step 1: `01_agent_interaction.py`**: Runs a set of questions against the agent and records enriched interactions.
2.  **Step 2: `02_agent_run_eval.py`**: (WIP) Calculates performance metrics based on the recorded interactions.
3.  **Step 3: `03_analyze_eval_results.py`**: (WIP) Generates a detailed, AI-powered analysis of the results.

**Note:** We are currently working on **standardizing Steps 2 and 3**. These scripts are being refactored to be more robust and agent-agnostic, ensuring that the team has a clear and consistent way to interpret evaluation scores and strategic insights.

## Step 1: Running Agent Interactions
... (existing content) ...

## Step 2: Agent Evaluation (Work in Progress)

**Objective:** To calculate specific performance metrics (e.g., correctness, safety, latency) for each interaction. 

We are currently defining the standard set of metrics that will apply across all agents.

## Step 3: Result Analysis (Work in Progress)

**Objective:** To generate a comprehensive executive summary of the evaluation run, highlighting strengths, weaknesses, and areas for improvement using Gemini as a judge.

---

## Data Structure: `extracted_data`

The most important output of Step 1 is the `extracted_data` column in the processed CSV. It contains a serialized JSON object with three main keys:

1.  `state_variables`: Every variable found in the agent's final session state.
2.  `tool_interactions`: A chronological list of every tool call made by the agent, including its input arguments and the returned output.
3.  `sub_agent_trace`: A sequence of natural language turns from all agents involved in the conversation.

### Exact Example from Customer Service Agent

Below is an actual row extracted from a successful evaluation run:

```json
{
  "state_variables": {
    "customer_id": "123",
    "customer_profile": "{\n    \"account_number\": \"428765091\",\n    \"customer_id\": \"123\",\n    \"customer_first_name\": \"Alex\",\n    ...}",
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
    {
      "tool_name": "access_cart_information",
      "input_arguments": {
        "customer_id": "123"
      },
      "call_id": "adk-052fdaed-bfec-49f3-a0fe-5c0e61767d88",
      "output_result": {
        "items": [
          {"product_id": "soil-123", "name": "Standard Potting Soil", "quantity": 1},
          {"product_id": "fert-456", "name": "General Purpose Fertilizer", "quantity": 1}
        ],
        "subtotal": 25.98
      }
    }
  ],
  "sub_agent_trace": [
    {
      "agent_name": "customer_service_agent",
      "text_response": "Hello Alex! Welcome back to Cymbal Home & Garden. How can I assist you today? \n",
      "timestamp": 1768002569.10474
    },
    {
      "agent_name": "customer_service_agent",
      "text_response": "Certainly, Alex! I can provide you with your purchase history...",
      "timestamp": 1768002573.884758
    }
  ]
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

**Arguments:**

| Argument | Description | Default |
|---|---|---|
| `--input` | Path to the input JSON file (list of turns). **(Required)** | N/A |
| `--output` | Path to the output golden dataset JSON file. **(Required)** | N/A |
| `--agent` | Name of the agent being evaluated. | `customer_service` |
| `--metadata` | Arbitrary metadata labels (e.g., `key:value`). Can be used multiple times. | N/A |
| `--prefix` | Prefix for the generated question IDs. | `q` |