# Agent Evaluation Pipeline (`agent-eval`)

A production-grade evaluation framework for ADK agents. This CLI provides advanced metrics beyond ADK's built-in checks, including tool usage accuracy, trajectory analysis, state management fidelity, and AI-powered root cause diagnosis.

## Evaluation Paths Overview

There are two primary ways to evaluate your agent. Choose the one that fits your current development stage:

| Path | Name | Best For | Description |
|------|------|----------|-------------|
| **Path A** | **Simulation** (Development) | Rapid iteration, robustness | Uses **Scenario Plans** (`conversation_scenarios.json`) to guide a simulated user in the ADK environment. |
| **Path B** | **Live API** (Deployed) | Regression testing, stability | Runs fixed **Golden Dataset** queries against your running HTTP server. |

---

## Quick Start

### Prerequisites

```bash
cd evaluation
uv sync
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=your-project-id
```

### Path A: Simulation (Recommended for Development)

**Step 1: Define & Run Simulation**
Write your conversation "plans" in `eval/scenarios/conversation_scenarios.json`. Run the ADK simulator to generate raw interaction logs.

**IMPORTANT**: You must clear the `.adk/eval_history/` directory before each run so that the converter only processes the current simulation (see `rm` command below).
```bash
cd your-agent
rm -rf your_agent/.adk/eval_history/*
uv run adk eval your_agent --config_file_path eval/scenarios/eval_config.json eval_set_with_scenarios
```
*   **Output**:
    ```text
    your_agent/
    └── .adk/
        └── eval_history/
            └── <run_id>.json
    ```

**Step 2: Convert History to CSV**
Transform the raw simulation logs into a flat CSV format.
```bash
cd ../evaluation
uv run agent-eval convert --agent-dir ../your-agent/your_agent --output-dir ../your-agent/eval/results
```
*   **Output**:
    ```text
    your_agent/eval/results/<timestamp>/  # Format: YYYYMMDD_HHMMSS
    └── raw/
        └── processed_interaction_sim.csv
    ```

**Step 3: Grade (Evaluate)**
Run your metrics against the CSV generated in Step 2. (See: [custom metric definition](#metric-definition--strategies))
```bash
uv run agent-eval evaluate --interaction-file ../your-agent/eval/results/<timestamp>/raw/processed_interaction_sim.csv \
  --metrics-files ../your-agent/eval/metrics/metric_definitions.json \
  --results-dir ../your-agent/eval/results/<timestamp>
```
*   **Output**:
    ```text
    your_agent/eval/results/<timestamp>/
    ├── eval_summary.json
    ├── question_answer_log.md
    └── raw/
        ├── processed_interaction_sim.csv
        └── evaluation_results_*.csv
    ```

**Step 4: Diagnose (Analyze)**
Generate a detailed AI-powered root cause analysis report.
```bash
uv run agent-eval analyze --results-dir ../your-agent/eval/results/<timestamp> --agent-dir ../your-agent
```
*   **Output**:
    ```text
    your_agent/eval/results/<timestamp>/
    ├── ...
    └── gemini_analysis.md
    ```

### Path B: Live API (Deployed Agents)

**Step 1: Create Golden Dataset**
Transform your queries (e.g., `eval/eval_data/test.json`) into a structured dataset.
```bash
uv run agent-eval create-dataset --input ../your-agent/eval/eval_data/test.json \
  --output ../your-agent/eval/datasets/golden.json --agent-name your_agent
```
*   **Output**:
    ```text
    your_agent/eval/datasets/
    └── golden.json
    ```

**Step 2: Run Live Interactions**
Send queries from your Golden Dataset to your agent API.
```bash
uv run agent-eval interact --app-name your_agent \
  --questions-file ../your-agent/eval/datasets/golden.json --base-url http://localhost:8080
```
*   **Output**:
    ```text
    your_agent/eval/results/<timestamp>/  # Format: YYYYMMDD_HHMMSS
    └── raw/
        └── processed_interaction_live.csv
    ```

**Step 3: Grade (Evaluate)**
Execute metrics against the live interaction CSV. (See: [custom metric definition](#metric-definition--strategies))
```bash
uv run agent-eval evaluate --interaction-file ../your-agent/eval/results/<timestamp>/raw/processed_interaction_live.csv \
  --metrics-files ../your-agent/eval/metrics/metric_definitions.json \
  --results-dir ../your-agent/eval/results/<timestamp>
```
*   **Output**:
    ```text
    your_agent/eval/results/<timestamp>/
    ├── eval_summary.json
    ├── question_answer_log.md
    └── raw/
        ├── processed_interaction_live.csv
        └── evaluation_results_*.csv
    ```

**Step 4: Diagnose (Analyze)**
Generate the AI root cause analysis report based on the live API results.
*   **Output**:
    ```text
    your_agent/eval/results/<timestamp>/
    ├── ...
    └── gemini_analysis.md
    ```
```bash
uv run agent-eval analyze --results-dir ../your-agent/eval/results/<timestamp> --agent-dir ../your-agent
```

---

## Evaluating External Project Agents

If your agent project is located outside of this repository (e.g., `~/code/my-new-agent`), you can still use the `agent-eval` tool. You simply keep the tool here and point the command-line arguments to your external project paths.

### 1. Setup (In this repository)
Ensure the tool is installed:
```bash
cd evaluation
uv sync
```

### 2. Scaffold (In your external project)
Create the required folder structure in your external agent project directory:
```bash
# In ~/code/my-new-agent
mkdir -p eval/metrics eval/datasets eval/results
```
*   **Add `eval/metrics/metric_definitions.json`**: Define your grading criteria using [Binary Decomposition](#opinionated-metric-definition-rules).
*   **Add `eval/test.json`**: Create a simple list of test queries.

### 3. Run Path B (Live API)
This is the easiest method for external projects as it only requires an HTTP connection.

**A. Start your external agent server** (e.g., port 8080).

**B. Run Pipeline** (From the `evaluation/` folder in **this** repo):
```bash
# 1. Create Golden Dataset
uv run agent-eval create-dataset --input ~/code/my-new-agent/eval/test.json --output ~/code/my-new-agent/eval/datasets/golden.json --agent-name my_agent

# 2. Interact (Talk to Live API)
uv run agent-eval interact --app-name my_agent --questions-file ~/code/my-new-agent/eval/datasets/golden.json --base-url http://localhost:8080

# 3. Grade (Evaluate)
uv run agent-eval evaluate --interaction-file ~/code/my-new-agent/eval/results/<timestamp>/raw/processed_interaction_live.csv --metrics-files ~/code/my-new-agent/eval/metrics/metric_definitions.json --results-dir ~/code/my-new-agent/eval/results/<timestamp>
```

### 4. Run Path A (Simulation)
*Note: This specifically requires the external agent to be built with the Google GenAI ADK.*

**A. Run Simulation** (Inside your external project):
```bash
cd ~/code/my-new-agent
uv run adk eval . --config_file_path eval/scenarios/eval_config.json conversation_scenarios
```

**B. Convert & Grade** (From the `evaluation/` folder in **this** repo):
```bash
# Point --agent-dir to your external project root
uv run agent-eval convert --agent-dir ~/code/my-new-agent --output-dir ~/code/my-new-agent/eval/results

# Then proceed with 'evaluate' and 'analyze' pointing to the new results path.
```

---

## Detailed Methodologies

### 1. Development Evaluation (Path A)
*Best for: Rapid iteration, testing how the agent handles unpredictable users, and robust coverage.*

**The Workflow:**
1.  **Define Scenarios**: Write conversation "plans" (e.g., `eval/scenarios/conversation_scenarios.json`).
2.  **Run Simulation** (`adk eval`): Runs agent code directly to simulate conversation.
    *   **Caveat**: Always clear `.adk/eval_history/` before running to ensure only the current session is converted.
    *   **Result**: 
        ```text
        .adk/eval_history/*.json
        ```
3.  **Convert History** (`convert`): Converts raw logs into a flat CSV.
    *   **Result**: 
        ```text
        eval/results/<timestamp>/
        └── raw/
            └── processed_interaction_sim.csv
        ```
4.  **Grade** (`evaluate`): 🏁 **Convergence Point**. Runs metrics against the CSV.
    *   **Result**: 
        ```text
        eval/results/<timestamp>/
        ├── eval_summary.json
        ├── question_answer_log.md
        └── raw/
            └── evaluation_results_*.csv
        ```
5.  **Diagnose** (`analyze`): Generates a root-cause report.
    *   **Result**: 
        ```text
        eval/results/<timestamp>/
        └── gemini_analysis.md
        ```

### 2. Deployed Agent Evaluation (Path B)
*Best for: Testing fixed scripts, regression testing, and ensuring stability.*

**The Workflow:**
1.  **Define Turns**: Write a simple JSON list of queries (e.g., `test.json`).
2.  **Create Dataset** (`create-dataset`): Adds IDs and metadata tags.
    *   **Result**: 
        ```text
        eval/datasets/golden.json
        ```
3.  **Run Interactions** (`interact`): Sends HTTP requests to your agent API.
    *   **Result**: 
        ```text
        eval/results/<timestamp>/
        └── raw/
            └── processed_interaction_live.csv
        ```
4.  **Grade** (`evaluate`): 🏁 **Convergence Point**. Runs metrics against the CSV.
    *   **Result**: 
        ```text
        eval/results/<timestamp>/
        ├── eval_summary.json
        ├── question_answer_log.md
        └── raw/
            └── evaluation_results_*.csv
        ```
5.  **Diagnose** (`analyze`): Gemini analyzes why the live agent failed or passed.
    *   **Result**: 
        ```text
        eval/results/<timestamp>/
        └── gemini_analysis.md
        ```

## Opinionated Metric Definition Rules

This pipeline follows a strict rule of **Binary Decomposition**. Instead of asking an LLM for a vague "Quality" score (1-5), break requirements down into specific True/False assertions.

### 1. Decompose into Binary Assertions
*   **Vague**: "Is the response helpful?"
*   **Binary Decomposition**:
    *   Did the agent provide a direct answer? (Yes/No)
    *   Did the agent mention the user's specific product? (Yes/No)
    *   Did the agent provide a 'next step'? (Yes/No)

### 2. Map the Evidence
Identify exactly which data columns prove or disprove your binary assertions.
*   `user_query` -> `user_inputs`
*   `agent_reply` -> `final_response`
*   `product_context` -> `state_variables:product_name`

### 3. Construct the "Summation" Prompt
Write the prompt to act as a calculator, not a critic. Instruct the LLM to iterate through your assertions, mark them `[x]` or `[ ]`, and then sum the result.

### 4. Enforce "Show Your Work"
To ensure the score is grounded in fact, force the LLM to output the checklist itself in the explanation. This makes the result auditable.

## Metric Definition & Strategies

Metrics are defined in JSON files (e.g., `customer-service/eval/metrics/metric_definitions.json`).

### Standard Metric Types
*   **Quantitative**: Latency, Token Usage, Text Created (Rouge/Bleu).
*   **Qualitative (LLM)**: Binary checklists informed by customer needs (e.g., Agent Routing, Tool Routing, State Storage, Answer Generation).

### Split Strategy
It is recommended to split your metric definitions based on your evaluation path:
*   **`metrics_sim.json` (for Path A)**: Focus on trajectory accuracy, goal completion, safety, and instruction following.
    *   *Goal*: "Is the agent behaving smartly in complex, undefined situations?"
*   **`metrics_live.json` (for Path B)**: Focus on final response matching, tool usage fidelity, and latency.
    *   *Goal*: "Is the deployed agent accurate and fast?"

### How to Add a New Metric
1.  **Open the File**: e.g., `customer-service/eval/metrics/metric_definitions.json`.
2.  **Paste Your Metric**: Use the template below. (See: [Full Metrics Guide](docs/03-METRICS-GUIDE.md))

**Template:**
```json
"my_binary_checklist": {
  "metric_type": "llm",
  "score_range": {
    "min": 0,
    "max": 3,
    "description": "Sum of 3 binary checks: Greeting, Solution, Closing"
  },
  "dataset_mapping": {
    "prompt": { "source_column": "user_inputs" },
    "response": { "source_column": "final_response" }
  },
  "template": "Evaluate the response.\n\nUser: {prompt}\nAgent: {response}\n\nChecklist:\n1. Greeting? (Yes/No)\n2. Solution? (Yes/No)\n3. Closing? (Yes/No)\n\nScore 1 point for each Yes.\n\nResponse Format:\nScore: [Sum]\nExplanation: [Checklist]"
}
```

## Documentation

| Guide | Description | Key Topics |
|-------|-------------|------------|
| [01-GETTING-STARTED.md](docs/01-GETTING-STARTED.md) | Prerequisites and first run | Installation, GCloud auth, quick start for both paths, agent directory structure |
| [02-EVALUATION-PATHS.md](docs/02-EVALUATION-PATHS.md) | Scenarios vs Golden Datasets | ADK User Simulation setup, scenario files, symlinks, Golden Dataset format, when to use each path |
| [03-METRICS-GUIDE.md](docs/03-METRICS-GUIDE.md) | Defining evaluation metrics | Custom LLM metrics, Vertex AI managed metrics, dataset mapping syntax, available columns reference, score ranges, troubleshooting |
| [04-CLI-REFERENCE.md](docs/04-CLI-REFERENCE.md) | Complete command reference | All commands (`convert`, `create-dataset`, `interact`, `evaluate`, `analyze`) with arguments and examples |
| [05-OUTPUT-FILES.md](docs/05-OUTPUT-FILES.md) | Understanding output files | CSV columns, eval_summary.json structure, deterministic metrics, Q&A log format, file relationships |
| [99-DEVELOPMENT.md](docs/99-DEVELOPMENT.md) | For contributors | Project structure, running tests, adding commands/metrics, code style, release process |

## Output Structure

Each run creates a folder named with a timestamp in the format `YYYYMMDD_HHMMSS` (e.g., `20260114_143022`):

```
eval/results/20260114_143022/
├── eval_summary.json           # Aggregated metrics
├── question_answer_log.md      # Human-readable Q&A transcript
├── gemini_analysis.md          # AI root cause analysis
└── raw/
    ├── processed_interaction_*.csv
    └── evaluation_results_*.csv
```