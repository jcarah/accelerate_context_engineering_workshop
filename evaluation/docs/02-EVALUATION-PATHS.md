# Evaluation Paths: Scenarios vs Golden Datasets

This guide explains the two evaluation paths and their different data formats. Understanding the difference between **Scenarios** and **Golden Datasets** is essential for running evaluations correctly.

---

## Overview

The evaluation framework supports two distinct paths for generating agent interactions:

| Aspect | Path A: Simulation | Path B: Live API |
| :--- | :--- | :--- |
| **Use Case** | Development & rapid iteration | Testing deployed agents |
| **Input Format** | Scenario files | Golden Dataset (from ADK test files) |
| **Agent Execution** | ADK Simulator (synthetic) | Live API endpoint |
| **Data Location** | `eval/scenarios/` | `eval/eval_data/` or `eval/datasets/` |

```
PATH A: SIMULATION
==================
eval/scenarios/                   ADK Simulator      agent-eval convert
├── conversation_scenarios.json ──────────────────> .adk/eval_history/ ──>
├── eval_config.json                  (adk eval)           |
└── eval_set.evalset.json                          processed_*.jsonl
                                                           |
                                                   agent-eval evaluate

PATH B: LIVE API
================
eval/eval_data/                   agent-eval         agent-eval interact
└── full_conversation.test.json ──────────────────> golden_dataset.json ──>
                                 (create-dataset)          |
                                                    Live Agent API
                                                           |
                                                   processed_*.jsonl
                                                           |
                                                   agent-eval evaluate
```

---

## Path A: Scenario Files (Simulation)

Scenario files drive the ADK Simulator. The simulator uses an LLM to play the role of a user and generate realistic multi-turn conversations based on your conversation plans.

### Understanding Symlinks

> **IMPORTANT**: The `eval/scenarios/` folder inside your agent directory is typically a **symlink** pointing to the actual source files elsewhere in the project.

```
your-agent/
├── your_agent/
│   └── eval/
│       └── scenarios -> ../../eval/scenarios  # Symlink!
└── eval/
    └── scenarios/                              # Actual source files
        ├── conversation_scenarios.json
        ├── eval_config.json
        └── eval_set_with_scenarios.evalset.json
```

**When editing scenario files:**
- Edit the files in `eval/scenarios/` (the actual source), NOT the symlinked path inside the agent directory
- The symlink allows ADK to find the files while keeping source control clean
- Use `ls -la your_agent/eval/scenarios` to verify it's a symlink

### File Location

```
your-agent/
└── eval/
    └── scenarios/
        ├── conversation_scenarios.json    # Conversation plans
        ├── eval_config.json               # Evaluation criteria
        ├── eval_set_with_scenarios.evalset.json  # Eval set definition
        └── session_input.json             # Initial session state
```

---

## Creating Scenarios (ADK User Simulation)

The ADK User Simulation feature lets you test multi-turn conversations using an LLM-powered simulated user. Here's how to set it up.

> **Reference:** [ADK User Simulation Documentation](https://google.github.io/adk-docs/evaluate/user-sim/)

### Step 1: Create Conversation Scenarios

Create `conversation_scenarios.json` with your test scenarios:

```json
{
  "scenarios": [
    {
      "starting_prompt": "I'm thinking about planting some Petunias in my backyard.",
      "conversation_plan": "Ask the agent for recommendations on what soil and fertilizer to use for Petunias. Then, ask the agent to check if the recommended soil is in stock."
    },
    {
      "starting_prompt": "I need help with my order.",
      "conversation_plan": "Ask about order status. If asked for order ID, provide '12345'. Then ask about return policy."
    }
  ]
}
```

| Field | Description |
| :--- | :--- |
| `starting_prompt` | The first message the simulated user sends |
| `conversation_plan` | Natural language instructions for how the conversation should proceed |

**Tips for writing good scenarios:**
- Be specific about what the user wants to accomplish
- Include conditional logic ("If asked for X, provide Y")
- Define the expected conversation arc (start, middle, end)
- Cover edge cases and error scenarios

### Step 2: Create Session Input (Optional)

Create `session_input.json` to define initial session state:

```json
{
  "app_name": "your_agent",
  "user_id": "test_user",
  "session_id": "eval_session"
}
```

> **CRITICAL: `app_name` Must Match Folder Name**
>
> The `app_name` value MUST match the folder name containing your agent's `agent.py` file,
> NOT the agent's internal name defined in code.
>
> | Agent Location | Correct `app_name` |
> |----------------|-------------------|
> | `customer-service/customer_service/agent.py` | `"customer_service"` |
> | `retail-ai-location-strategy/app/agent.py` | `"app"` |
>
> If this is incorrect, the converter will show an error about missing `session_details`
> and your evaluation will have zero values for token usage and state variables.

### Step 3: Create Eval Set Definition

Create `eval_set_with_scenarios.evalset.json`:

```json
{
  "name": "eval_set_with_scenarios",
  "description": "Evaluation scenarios for testing agent behavior",
  "eval_cases": [],
  "initial_session": {
    "source": "file",
    "path": "session_input.json"
  },
  "user_simulator": {
    "type": "conversation_scenario",
    "scenarios_file": "conversation_scenarios.json",
    "user_simulator_config": {
      "model": "gemini-2.5-flash",
      "max_allowed_invocations": 10
    }
  }
}
```

**User Simulator Configuration:**

| Field | Description |
| :--- | :--- |
| `model` | LLM to use for user simulation (default: `gemini-2.5-flash`) |
| `max_allowed_invocations` | Maximum conversation turns before termination |

> Set `max_allowed_invocations` to exceed the longest expected conversation in your scenarios.

### Step 4: Create Eval Config

Create `eval_config.json`:

```json
{
  "criteria": {
    "tool_use_accuracy": {
      "threshold": 0.8
    }
  }
}
```

### Running Path A

```bash
# Step 1: Run ADK Simulator (clear previous history first)
cd your-agent
rm -rf your_agent/.adk/eval_history/*
uv run adk eval your_agent \
  --config_file_path eval/scenarios/eval_config.json \
  eval_set_with_scenarios

# Step 2: Convert to evaluation format
cd ../evaluation
uv run agent-eval convert \
  --agent-dir ../your-agent/your_agent \
  --output-dir ../your-agent/eval/results

# Step 3: Run evaluation
uv run agent-eval evaluate \
  --interaction-file ../your-agent/eval/results/<timestamp>/raw/processed_interaction_sim.jsonl \
  --metrics-files ../your-agent/eval/metrics/metric_definitions.json \
  --results-dir ../your-agent/eval/results/<timestamp>
```

### When to Use Path A

- Rapid development and iteration
- Testing conversation flows without reference answers
- Exploring agent behavior across many scenarios
- No need for exact answer matching

---

## Path B: Golden Datasets (Live API)

Golden Datasets contain test cases with expected answers. These are used to test deployed agents via their API endpoints.

### File Location

```
your-agent/
└── eval/
    ├── eval_data/
    │   └── full_conversation.test.json   # ADK test format (input)
    └── datasets/
        └── golden_dataset.json           # Converted format (output)
```

### ADK Test File Format (Input)

The ADK test format is a list of conversation turns:

```json
[
  {
    "query": "hi",
    "expected_tool_use": [],
    "reference": "Hello! Welcome to our service. How can I help you today?"
  },
  {
    "query": "can you please tell me what I purchased before?",
    "expected_tool_use": [
      {
        "tool_name": "access_cart_information",
        "tool_input": {
          "customer_id": "123"
        }
      }
    ],
    "reference": "Here's a summary of your previous purchases..."
  }
]
```

| Field | Description |
| :--- | :--- |
| `query` | The user's message |
| `expected_tool_use` | List of expected tool calls (for validation) |
| `reference` | The expected/ideal response |

### Golden Dataset Format (Converted)

After running `agent-eval create-dataset`, you get:

```json
{
  "questions": [
    {
      "question_id": "abc123",
      "user_inputs": ["hi"],
      "reference_data": {
        "expected_response": "Hello! Welcome to our service...",
        "expected_tool_use": []
      }
    },
    {
      "question_id": "def456",
      "user_inputs": ["hi", "can you please tell me what I purchased before?"],
      "reference_data": {
        "expected_response": "Here's a summary of your previous purchases...",
        "expected_tool_use": [
          {
            "tool_name": "access_cart_information",
            "tool_input": {"customer_id": "123"}
          }
        ]
      }
    }
  ],
  "metadata": {
    "agent_name": "customer_service",
    "created_at": "2026-01-14T10:00:00Z"
  }
}
```

### Reference Data Fields

The `reference_data` object contains ground truth for evaluation metrics:

| Field | Description |
| :--- | :--- |
| `expected_response` | The expected agent response |
| `expected_tool_use` | List of expected tool calls with arguments |
| `reference_trajectory` | Expected sequence of agents/steps |
| `reference_state_variables` | Expected session state values |

### When to Use Path B

- Testing deployed or remote agents
- Validating against expected answers
- Regression testing with known good responses
- Production readiness verification

### Running Path B

```bash
# Step 1: Convert ADK test file to Golden Dataset
uv run agent-eval create-dataset \
  --input eval/eval_data/full_conversation.test.json \
  --output eval/datasets/golden_dataset.json \
  --agent-name your_agent

# Step 2: Start your agent (in another terminal)
make playground  # or however you run your agent

# Step 3: Run interactions against live agent
uv run agent-eval interact \
  --app-name your_agent \
  --questions-file eval/datasets/golden_dataset.json \
  --base-url http://localhost:8080 \
  --results-dir eval/results

# Step 4: Run evaluation
uv run agent-eval evaluate \
  --interaction-file eval/results/<timestamp>/raw/processed_interaction_*.jsonl \
  --metrics-files eval/metrics/metric_definitions.json \
  --results-dir eval/results/<timestamp>
```

---

## Comparison Table

| Feature | Scenarios (Path A) | Golden Datasets (Path B) |
| :--- | :--- | :--- |
| **Execution** | ADK Simulator (synthetic user) | Live agent API |
| **Input** | Conversation plan (natural language) | Exact user queries |
| **Reference Answers** | None (open-ended) | Expected responses included |
| **Tool Expectations** | Not specified | Can include `expected_tool_use` |
| **Multi-turn** | Simulator generates turns | Explicit turn list |
| **Best For** | Development, exploration | Validation, regression |

---

## Processed JSONL: Common Output Format

Both paths produce the same processed JSONL format for evaluation:

| Column | Description |
| :--- | :--- |
| `question_id` | Unique identifier for the test case |
| `user_inputs` | User messages (JSON list for multi-turn) |
| `final_response` | Agent's final text response |
| `trace_summary` | Agent execution trajectory |
| `extracted_data` | JSON with `state_variables`, `tool_interactions` |
| `session_trace` | Full OpenTelemetry execution trace |
| `reference_data` | Expected answers (Path B only) |

---

## Best Practices

1. **Choose the right path for your goal:**
   - Exploring agent behavior → Path A (Scenarios)
   - Validating specific answers → Path B (Golden Datasets)

2. **Understand symlinks:**
   - Always edit source files, not symlinked paths
   - Use `ls -la` to verify if a path is a symlink
   - The agent directory's `eval/scenarios` typically points to `../../eval/scenarios`

3. **Organize your files:**
   ```
   eval/
   ├── scenarios/          # Path A: Simulation files (source)
   ├── eval_data/          # Path B: ADK test files (source)
   ├── datasets/           # Path B: Golden datasets (converted)
   ├── metrics/            # Metric definitions
   └── results/            # Output from both paths
   ```

4. **Clear simulation history:** Before each Path A baseline run, clear `.adk/eval_history/` to avoid mixing old traces.

5. **Version your test files:** Keep ADK test files and scenario files in version control for regression testing.

---

## Related Documentation

- [01-GETTING-STARTED.md](01-GETTING-STARTED.md) - Quick start guide
- [03-METRICS-GUIDE.md](03-METRICS-GUIDE.md) - Define evaluation metrics
- [05-OUTPUT-FILES.md](05-OUTPUT-FILES.md) - Understanding output files
