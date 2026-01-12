# Agent Optimization & Evaluation Workshop (Accelerate '26)

> **\[WORKSHOP NOTE:** This repository is currently under active development. The Evaluation Framework is being transitioned to a CLI tool (`adk-eval`). The documentation below reflects the *current stable state* using Python scripts, but mockups of the future CLI experience are included for preview.

**Status:** Implementation Guide  
**Focus:** Context Engineering & Quantitative Evaluation  
**Target Audience:** Technical GTM Practitioners

---

## 1. Overview

This workshop guide is designed for technical experts to master the transition from **Prompt Engineering** (stateless, token-heavy) to **Context Engineering** (stateful, architectural optimization).

### The Objective
By the end of this workshop, you will learn to:
1.  **Iteratively improve agent performance** using the "Five Pillars" of Context Engineering (Offload, Reduce, Retrieve, Isolate, Cache).
2.  **Measure performance** across Quality, Cost, and Latency axes using a production-grade evaluation framework.

### The Execution Framework: "The Hill Climb"
We will achieve this through a "hill climbing" exercise. We start with functional but unoptimized "Base Camp" agents. We establish evaluation baselines, identify failure signals (e.g., hallucinations, latency spikes), and iteratively apply architectural patterns to climb toward a production-ready system.

---

## 2. The Test Subjects (Agents)

We use two distinct agents to demonstrate different classes of problems.

### Agent A: Customer Service (The "Naive Monolith")
*   **Location:** `customer-service/`
*   **The Problem:** A single agent trying to do too much (12+ tools). It suffers from **Logic Errors**, **Hallucinations**, and **Routing Failures**.
*   **The Fix:** We will use this agent to practice **Reliability Optimizations** (Schema Hardening, Functional Isolation, Reflexion).
*   **Setup:**
    ```bash
    cd customer-service
    make install
    make playground
    # See customer-service/README.md for architecture details
    ```

### Agent B: Retail AI Location Strategy (The "Context Dumper")
*   **Location:** `retail-ai-location-strategy/`
*   **The Problem:** A complex multi-agent pipeline that processes massive datasets (Google Maps API). It suffers from **Token Bloat**, **High Latency**, and **High Cost**.
*   **The Fix:** We will use this agent to practice **Scale Optimizations** (Offloading state to files, Code Execution, Prefix Caching).
*   **Setup:**
    ```bash
    cd retail-ai-location-strategy
    make ag-ui-install # or make install
    make ag-ui # or make dev
    # See retail-ai-location-strategy/README.md for deep dives
    ```

---

## 3. The Lab: Production Evaluation Framework

Instead of simple "print statement" debugging, we have built a custom, reusable evaluation pipeline located in `evaluation/`. This serves as a reference architecture for how you might implement CI/CD for agents in the real world.

> **👉 GO DEEPER:** Check out the **[Evaluation README](evaluation/README.md)**.
> It covers advanced topics like the **Simulation Strategy** (how to run offline evaluations without a live server using ADK history), the schema for Golden Datasets, and how to define custom LLM-as-a-Judge metrics.

**Key Components:**
*   **Golden Datasets:** Standardized JSON test cases (Questions + Reference Answers) located in `[agent]/eval/datasets/`.
*   **LLM Judges:** Custom rubrics (e.g., "Did the agent use the correct tool?") located in `[agent]/eval/metrics/`.
*   **Pipeline:** Scripts to run the agent, calculate scores, and generate reports.

### 000 Future State: CLI Experience (Preview)
We are actively refactoring this pipeline into a unified CLI tool: `adk-eval`.
> **Mockup:** In the future, you will simply run:
> ```bash
> uv run adk-eval run --app-name customer_service --questions-file ...
> uv run adk-eval evaluate --metrics-files ...
> uv run adk-eval analyze ...
> ```

### 000 Current State: Running Evaluations (Workshop Guide)

For now, we use the stable Python scripts. Follow these steps to evaluate your agent.

#### Step 1: Run Interactions (Data Collection)
This sends your test questions to the running agent and records the logs.

*   **Mockup Goal:** `adk-eval run`
*   **Actual Command:**
    ```bash
    # Ensure your agent is running on localhost:8080 first!
    uv run python evaluation/01_agent_interaction.py \
      --app-name customer_service \
      --base-url http://localhost:8080 \
      --questions-file customer-service/eval/datasets/golden_dataset.json \
      --results-dir customer-service/eval/results/baseline
    ```

#### Step 2: Calculate Metrics (Scoring)
This runs the Deterministic (latency, cost) and LLM-based (quality) graders.

*   **Mockup Goal:** `adk-eval evaluate`
*   **Actual Command:**
    ```bash
    uv run python evaluation/02_agent_run_eval.py \
      --interaction-results-file customer-service/eval/results/baseline/processed_interaction_customer_service.csv \
      --metrics-files customer-service/eval/metrics/metric_definitions.json \
      --results-dir customer-service/eval/results/baseline
    ```

#### Step 3: Analyze Results (Reporting)
This generates a human-readable Markdown report and an AI-powered root cause analysis.

*   **Mockup Goal:** `adk-eval analyze`
*   **Actual Command:**
    ```bash
    uv run python evaluation/03_analyze_eval_results.py \
      --results-dir customer-service/eval/results/baseline
    ```

---

## 4. Workshop Curriculum: The Optimization Loop

We will follow a strict **Signal-Driven Engineering** loop:
1.  **Measure:** Run the eval pipeline (Steps 1-3 above).
2.  **Identify Signal:** Find the red flag in `eval_summary.json` (e.g., `tool_error_rate > 50%`).
3.  **Optimize:** Apply a specific Context Engineering pattern.
4.  **Verify:** Re-run evals to prove the lift.

---

### Phase 1: Fixing Reliability (Customer Service)

#### Step 1: The "Hallucinating Helper" (Tool Hardening)
**Context:** The agent keeps failing to update the shopping cart because it sends string descriptions instead of integer IDs to the API.

> **\[WORKSHOP TASK:**
> 1.  Run the baseline evaluation (see Section 3).
> 2.  Observe the high failure rate in `tool_usage_accuracy`.
> 3.  **Refactor:** Open `customer-service/customer_service/tools/tools.py` and replace generic dict schemas with strict Pydantic models.
> 4.  Re-run evaluation and verify the score improves.

#### Step 2: The "Overwhelmed Generalist" (Functional Isolation)
**Context:** The agent gets distracted. When asked to "Approve a discount", it hallucinates checking "Plant Pathology Rules" because all instructions are in one massive prompt.

> **\[WORKSHOP TASK:**
> 1.  Run the `analyze` script and check `gemini_analysis.md`.
> 2.  Note the finding: "*Trajectory Noise: Agent introduces irrelevant steps.*"
> 3.  **Refactor:** Split the `root_agent` into a **Triage Agent** that routes to specialized **Sales** and **Support** sub-agents.

#### Step 3: The "Drifting Planner" (Recitation)
**Context:** In long conversations (e.g., scheduling a delivery), the agent forgets the original goal (applying the discount) because it gets "Lost in the Middle" of the context window.

> **\[WORKSHOP TASK:**
> 1.  **Refactor:** Implement **Attention Structuring**. Inject a dynamic `todo.md` block at the *end* of the prompt every turn, forcing the agent to "recite" its remaining tasks before acting.

---

### Phase 2: Fixing Scale (Retail Strategy)

#### Step 4: The "Context Dumper" (Offload & Reduce)
**Context:** The `CompetitorMappingAgent` finds 50 coffee shops and dumps the entire raw JSON response (100k+ tokens) into the chat history. The agent crashes or hallucinates simple math.

> **\[WORKSHOP TASK:**
> 1.  Run a heavy query: "Analyze saturation in Austin, TX".
> 2.  Check `token_usage` metrics. Observe >100k input tokens per turn.
> 3.  **Refactor:** Implement the **Offload** pillar. Modify the tool to save `competitors.json` to disk and enable Code Execution for the agent to analyze it using Pandas.

#### Step 5: The "Expensive Executive" (Prefix Caching)
**Context:** The agent works, but it's slow (8s latency) and expensive because we re-send the same massive system instructions every turn.

> **\[WORKSHOP TASK:**
> 1.  **Refactor:** Implement **Prefix Caching**. Structure the prompt to keep static content (Persona, Tools) at the *start* (Prefix) and dynamic content at the *end*.
> 2.  Verify in the next run that `cache_hit_rate` > 75% and TTFT drops.

---

## 5. Signal Identification Cheatsheet

Use the generated `eval_summary.json` to pick your battle.

| Signal (The Symptom) | Metric / Data Source | Recommended Optimization (The Cure) |
| :--- | :--- | :--- |
| **Context Rot** | `state_fidelity` score drops as conversation length increases. | **Context Compaction** or **Recitation** |
| **Hallucination** | `tool_usage_accuracy` is low; agent invents parameters. | **Tool Hardening (Schema)** |
| **Token Bloat** | Input tokens > 4000/turn; `Context Efficiency Ratio` < 50:1. | **Offload (Code Execution)** |
| **Slow Recovery** | High "Reflexion" count (retries) in traces. | **Reflexion Loop** |
| **High Cost** | Low `KV-Cache Hit Rate` (< 50%). | **Prefix Caching** |
| **General Failure** | Low `Pass^k` (consistency) across diverse tasks. | **Functional Isolation (Sub-agents)** |