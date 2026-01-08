# Agent Optimization & Evaluation Workshop (Accelerate '26)

**Status:** Implementation Guide  
**Focus:** Context Engineering & Quantitative Evaluation  
**Target Audience:** Technical GTM Practitioners

---

## 1. Overview

This workshop guide is designed for technical experts to master the transition from **Prompt Engineering** (stateless, token-heavy) to **Context Engineering** (stateful, architectural optimization).

### The Objective
By the end of this workshop, you will learn to:
1.  **Iteratively improve agent performance** using the "Five Pillars" of Context Engineering (Offload, Reduce, Retrieve, Isolate, Cache).
2.  **Measure performance** across Quality, Cost, and Latency axes using a formal evaluation framework.

### The Execution Framework: "The Hill Climb"
We will achieve this through a "hill climbing" exercise. We will start with a functional but unoptimized "Base Camp" agent. We will establish evaluation baselines and then iteratively apply context engineering principles to climb toward a production-ready system, measuring the delta at every step.

---

## 2. The Agent: Retail AI Location Strategy

For this workshop, we will use the **Retail AI Location Strategy** agent. This is a sophisticated multi-agent pipeline that acts as an autonomous business analyst.

**Use Case:** A user wants to open a physical store (e.g., "A coffee shop in Bangalore"). The agent must research the market, find competitors via Google Maps, run a saturation analysis using Python, and generate a strategic report.

### Architecture

![alt text](retail-ai-location-strategy/assets/images/agent-tools.png)

*   **Code Location:** `retail-ai-location-strategy/`
*   **Documentation:** See `retail-ai-location-strategy/README.md` and `retail-ai-location-strategy/DEVELOPER_GUIDE.md` for deep dives into the tools, schemas, and config.

### Prerequisites
*   Python 3.10+
*   Node.js & npm (for the Frontend)
*   Google Cloud Project with Vertex AI enabled (.env file set)

### Installation & Running

1.  **Navigate to the agent directory:**
    ```bash
    cd retail-ai-location-strategy
    ```

2.  **Install the AG-UI Application:**
    This command installs the Python backend, the React frontend, and sets up the environment.
    ```bash
    make ag-ui-install
    ```

3.  **Run the Application:**
    ```bash
    make ag-ui
    ```
    *   This will launch the UI at `http://localhost:3000`.

4.  **Troubleshooting:**
    If you encounter issues, please refer to the `DEVELOPER_GUIDE.md` inside the agent folder.
---

## 3. The Context Engineering Toolkit

We are moving away from the "One Prompt to Rule Them All" mindset. We will apply the following five pillars to maximize the Signal-to-Noise Ratio. This section outlines the Context Engineering, and how we could possibly translate it to a milestone for the workshop (NEEDS WORK).

#### The Baseline
*   **Theory:** Establish the "Noise Floor." Measure the unoptimized agent's cost, latency, and quality. Identify "Prompt Bloat" and "Attention Diffusion."
*   **Possible Workshop Scenario:** Run the current Retail Strategy Agent. Observe the high token count when the `CompetitorMappingAgent` finds many locations. Observe the latency during the sequential hand-offs.

---

### Pillar 1: Offload (Externalizing State)
The act of moving ephemeral, high-token, or "heavy" state (e.g., raw HTML, massive JSON logs) out of the KV-cache and into a durable environment (Sandbox File System or ADK Artifacts).
*   **Justification:** Reduces "Attention Diffusion" by keeping working memory focused on logic, not raw data.

#### Workshop Milestone (The Retail Scenario):
*   **Current State:** The `CompetitorMappingAgent` queries the Google Maps API and dumps a massive JSON blob of 20+ locations directly into the chat history.
*   **The Fix:** Refactor the tool to **save the data to a file** (e.g., `competitors.json`) in the Sandbox and return only a file path and a brief summary (e.g., *"Found 25 competitors, saved to disk"*).

---

### Pillar 2: Reduce (High-Signal Transformation)
The process of shrinking the token footprint without losing the "state of mind."
*   **NL2Py (Code Act):** Writing code to query/process data in the sandbox rather than feeding raw data into the context.
*   **Semantic Summarization:** Using schema-driven condensation for long histories.
*   **Optimization Note:** This also applies to **Output Tokens**. We aim to optimize single-token attribute names in JSON and concise explanations to reduce latency.

#### Workshop Milestone (The Retail Scenario):
*   **Current State:** The `GapAnalysisAgent` attempts to read the raw JSON text from the prompt to calculate saturation indices. This is expensive and prone to hallucination ("Lost in the Middle").
*   **The Fix:** Implement **Code Execution (Pandas)**. Instruct the agent to write Python code to load the `competitors.json` file and calculate the metrics deterministically.
*   **Bonus Optimization:** Optimize **Output Tokens** by ensuring the agent uses concise JSON keys and minimal verbose explanations during tool use.

---

### Pillar 3: Retrieve (Just-in-Time Access)
Utilizing environment-aware tools or Vector search to pull data into the context window only at the moment of need.

#### Workshop Milestone (The Retail Scenario):
*   **Current State:** The `MarketResearchAgent` might dump pages of search results about general demographics.
*   **The Fix:** Ensure the `StrategyAdvisorAgent` only retrieves specific insights (Semantic Summaries) from the research logs, rather than re-reading the raw search output.

---

### Pillar 4: Isolate (Context Partitioning)
Splitting logic into specialized sub-agents to create a "Layered Action Space." This prevents Context Confusion.
*   **ADK Pattern:** The "Agent-as-a-Tool" pattern (e.g., A "Researcher" agent returning only structured JSON to a "Writer" agent).
*   **Extended Isolation:** Note that separating **Guardrail Services** (e.g., Model Armor) and **Tool Discovery** (e.g., RAG-based tool selection) are also critical forms of isolation.

#### Workshop Milestone (The Retail Scenario):
*   **Current State:** Ensure the **Guardrails** and **Tooling** are distinct.
*   **The Fix:** Validate the separation between the `GapAnalysisAgent` (The Coder) and the `StrategyAdvisorAgent` (The Writer). The Writer should never see the raw Python code or error logs, only the final derived insights.

---

### Pillar 5: Cache (Prefix Optimization)
Freezing static portions of the prompt (System Instructions, Tool Schemas, Few-Shot examples) via KV-Cache.
*   **Goal:** Drastic reduction in **TTFT (Time-to-First-Token)** and per-turn API costs.

#### Workshop Milestone (The Retail Scenario):
*   **Current State:** Every turn re-processes the massive Pydantic schema used for the final report.
*   **The Fix:** Apply `ContextCacheConfig` to the `StrategyAdvisorAgent`. Structure the prompt to ensure the heavy schema definition is in the "Static" prefix, while user variables (Location Name) are in the "Dynamic" suffix.

---
## 4. Evaluation Framework

We will measure our progress using a multi-axial approach.

| Axis | Metric | Methodology | Goal |
| :--- | :--- | :--- | :--- |
| **Quality** | Adaptive Rubrics | Use Vertex AI Evaluation Service to generate rubrics specific to the prompt. | High Alignment with Human Raters |
| **Performance** | TTFT | Delta between request start and first token event. | Milestone 0 (>5s) $\rightarrow$ Milestone 3 (<500ms) |
| **Performance** | E2E Latency | Total time for the full chain (Sequencing optimization). | Reduce total wait time |
| **Cost** | Token Efficiency | Ratio of `cached_content_token_count` vs Fresh tokens. | 75% Cost Reduction |
| **Cost** | Output Density | Optimization of JSON keys and verbose explanations. | Reduce unnecessary output tokens |

Here is the isolated **Evaluation Framework** section for your README.

A three-step evaluation pipeline is located in the `evaluation/` directory (read the README within the folder for more details). This pipeline still needs to be adapted.

### Overview of Scripts

We use three core scripts to interact with, measure, and analyze the agent.

#### Step 1: Interaction (`01_agent_interaction.py`)
This script orchestrates the "Golden Dataset" run against the running agent.
*   **Function:** Connects to the ADK Agent via `agent_run_utils`, creates sessions, and records the conversation trace.
*   **Required Changes:**
    *   **Routes:** Validate that `agent_run_utils` points to the correct ADK application routes (e.g., `POST /agent/sessions`, `POST /agent/invoke`).
    *   **State Extraction:** We must modify the schema used by the script (`schemas/eval_state_variables_schema.json`) to capture Retail-specific state variables from the response, such as `market_research_path` or `gap_analysis_result`, rather than the default SQL variables (we also need to modify the agent to appropiately store those variables within the state so that we can retrieve them later on).

#### Step 2: Metrics Calculation (`02_agent_run_eval.py`)
This script processes the raw interaction logs to compute specific scores.
*   **Deterministic Metrics:** We need to validate the script correctly calculates metrics from **traces**, too:
    *   `trace` 
    *   `latency`
    *   `etc` (see calculate_token_usage on deterministic_metrics.py, for example) > many of the metrics in deterministic_metrics can be ifnored, it's just to measure the success on running each subagent of the sql explorer original use case (it's the only script that may be hardcoded)
*   **LLM-as-a-Judge:** We use Vertex AI Eval service to evaluate qualitative aspects. You will find a sample metric definition in `evaluation/metrics/.json` files.

**Example Metric: Data Groundedness**
To verify Milestone 1 (Offloading), we use a metric that checks if the agent actually used the file system.
```json
{
  "metric_name": "data_groundedness",
  "metric_type": "llm",
  "template": "You are a Data Auditor. Review the Agent's execution trace. \n1. Did the agent generate a Python script? \n2. Did the Python script load 'competitors.json' from the sandbox? \nRate 1 (No, Hallucinated) or 5 (Yes, Grounded).",
  "dataset_mapping": {
    "trace_log": "session_trace"
  }
}
```

#### Step 3: Analysis & Storage (`03_analyze_eval_results.py`)
This script generates a final report and pushes data to BigQuery.
*   **Needed Adaptation:** The script is currently configured for another agent. We need to modify the BigQuery table, dataset, and the prompt for the eval summarizer.
