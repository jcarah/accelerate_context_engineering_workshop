# Agent Optimization & Evaluation Workshop (Accelerate '26)

**Status:** Implementation Guide  
**Focus:** Context Engineering & Quantitative Evaluation  

## 1. Overview

This workshop guide is designed for technical GTM practitioners to master the transition from **Prompt Engineering** (stateless, token-heavy) to **Context Engineering** (stateful, architectural optimization).

### The Objective
By the end of this workshop, you will learn to:
1.  **Iteratively improve agent performance** using the "Five Pillars" of Context Engineering (Offload, Reduce, Retrieve, Isolate, Cache).
2.  **Measure performance** across Quality, Cost, and Latency axes using a formal evaluation framework.

### The Execution Framework: "The Hill Climb"
We will take an unoptimized **"Monolithic"** agent and dismantle it. We will establish evaluation baselines and then apply architectural patterns to climb the hill toward a production-ready system.

---

## 2. The Context Engineering Toolkit

We are moving away from the "One Prompt to Rule Them All" mindset. We will apply the following five pillars to our agent:

### 1. Offload (Externalizing State)
*   **Definition:** Moving high-token state (raw data, logs, manifests) out of the KV-cache and into a durable Sandbox environment.
*   **Pattern:** Instead of tools returning massive JSON blobs to the chat history, they save data to `artifacts/` and return a file path.

### 2. Reduce (High-Signal Transformation)
*   **Definition:** Shrinking the token footprint without losing the "state of mind."
*   **Pattern:**
    *   **NL2Py (Code Act):** Instead of the LLM reading a CSV to find a row, it writes Python code to query the file.
    *   **Summarization:** Compressing interaction logs into semantic summaries.

### 3. Retrieve (Just-in-Time Access)
*   **Definition:** Pulling data into context only when needed.
*   **Pattern:** Using Vector Search or glob patterns to fetch specific knowledge rather than pre-loading the window with "just-in-case" instructions.

### 4. Isolate (Context Partitioning)
*   **Definition:** Splitting logic into specialized sub-agents to create a "Layered Action Space."
*   **Pattern:** The **"Agent-as-a-Tool"** pattern. A "Manager" delegates a 50-turn task to a "Worker," receiving only the final structured result.

### 5. Cache (Prefix Optimization)
*   **Definition:** Freezing static prompt sections (System Instructions, Tool Schemas) to minimize Latency (TTFT) and Cost.
*   **Pattern:** Structuring prompts to ensure the static prefix is "Cache-Stable."

---

## 3. Implementation Roadmap (The Hill Climb)

This repository is structured to follow the refactoring phases of the workshop.

### Milestone 0: The "Naive" Monolith (Baseline)
*   **State:** A single `Agent` object.
*   **The Problem:** All instructions, routing logic, and tool definitions are stuffed into one massive system prompt. Tool outputs (raw data) are dumped directly into conversation history.
*   **Evaluation Baseline:** High Time-To-First-Token (TTFT), High Cost per turn, and "Attention Diffusion" (hallucinations due to context saturation).

### Milestone 1: Reversible Compaction & Offloading
*   **Goal:** Stop "KV-cache bleed." You don't need to remember everything; you just need to know where it is.
*   **Tasks:**
    *   Refactor "Read" tools to write to the Sandbox (File System) instead of returning text.
    *   Implement **Code Execution** tools to allow the agent to query data via Python instead of reading it.
    *   **Validation:** Verify that `input_token_count` drops significantly while `groundedness` scores remain stable or improve.

### Milestone 2: Functional Isolation (Multi-Agent)
*   **Goal:** Share context by communicating, don't communicate by sharing context.
*   **Tasks:**
    *   Split the Monolith into a **Manager Agent** (Triage) and specialized **Worker Agents**.
    *   Pass state via **Artifacts** (File Paths) rather than Chat History.
    *   **Validation:** Verify `tool_use_quality`. Workers should have 0% hallucination on tools they do not possess.

### Milestone 3: Production Optimization
*   **Goal:** Hit the "Hot Cache" target (TTFT < 500ms).
*   **Tasks:**
    *   Apply `ContextCacheConfig` to freeze core persona and tool definitions.
    *   Audit prompt structure to separate **Static** content from **Dynamic** user turns.

---

## 4. Evaluation Framework

We measure our progress using a strict "Red Team / Blue Team" approach.

### 4.1 Quality Axis
*   **Adaptive Rubrics:** We use a "Judge Agent" to generate rubrics specific to each test case.
*   **Custom Metric - Groundedness:**
    *   *Formula:* Does the agent's final answer cite a file path or specific data point present in the source?
    *   *Target:* >95% Alignment with Ground Truth.

### 4.2 Performance Axis (Latency)
*   **Metric:** TTFT (Time to First Token).
*   **Target:** Milestone 0 (>5s) $\rightarrow$ Milestone 3 (<500ms).

### 4.3 Cost Axis (Token Density)
*   **Metric:** `cached_content_token_count`.
*   **Target:** 75% input token discount via prefix optimization.

---

# (Internal) Workshop Builder's Guide
## 1. Gemini's Recommendation

> When asked which agent could help us better demostrate the Contex Engineering Hill Climb.

For the **"Hill Climb"** exercise, I recommend using the **Retail AI Location Strategy** agent.

**Why?**
Context Engineering is best demonstrated when the model is overwhelmed by *information* rather than just *instructions*.
*   **Customer Service** agents often fail due to logic conflicts, which Gemini 1.5 handles surprisingly well in a monolith.
*   **Retail Strategy** agents deal with *data* (demographics, foot traffic, competitor lists).
    *   **The Problem (Milestone 0):** A naive agent tries to read a 500-row CSV of location data in the context window. It hallucinates stats and costs a fortune.
    *   **The Solution (Milestone 1-2):** This is the perfect canvas to demonstrate **Offload** (saving the CSV to the sandbox), **Reduce** (using Python/Pandas to query it instead of reading it), and **Isolate** (separating the "Data Analyst" from the "Strategy Writer").

---
## 2. Gemini's "Master Plan" for building the repository

> When given the **objective** of reverse-engineering the existing `retail-ai-location-strategy` ADK sample to simulate a "Hill Climb" (as we need to break the clean sample to create a "Milestone 0" that performs poorly, then guide the audience to fix it).

## Phase 1: The Setup (Data & Tooling)

The current sample likely uses small mock data. To make Context Engineering necessary, we need **Context Rot**. We must generate a dataset large enough that it *hurts* the model if pasted directly into the prompt.

**Step 1.1: Generate "Heavy" Mock Data**
Create a file named `location_database_large.csv`.
*   **Content:** 500 rows of retail location data.
*   **Columns:** `location_id`, `address`, `avg_foot_traffic`, `rent_per_sqft`, `competitor_density_score`, `demographic_segment`, `historical_sales_q1`, `historical_sales_q2`, etc.
*   **Why:** If the agent reads this raw text (approx. 30k tokens), it will "diffuse" attention. We *want* the Monolith to fail at finding specific rows in this haystack.

**Step 1.2: Fork the Tools**
We need two versions of the tools in the repo:
1.  `tools_naive.py`: Returns raw data strings (for Milestone 0).
2.  `tools_optimized.py`: Saves to artifacts and returns file paths (for Milestone 1+).

---

## Phase 2: Constructing "Milestone 0" (The Monolith)

This is the starting point for the audience. We need to create a "Villain" agent that is functionally correct but architecturally flawed.

**Step 2.1: The "Kitchen Sink" Prompt**
Create `agents/monolith/prompts.py`.
*   **Action:** Take the system instructions from the *Analyst* agent and the *Strategist* agent in the original sample and merge them into one massive string.
*   **Add Noise:** Add a "Global Policy" section with 2,000 tokens of generic corporate filler (e.g., "Always be polite," "Format dates as ISO," "Ensure compliance with Section 4.2...").
*   **Outcome:** A 4,000+ token system prompt that confuses the model about its primary role.

**Step 2.2: The "Data Dump" Tools**
In `agents/monolith/agent.py`, configure the agent to use `tools_naive.py`.
*   **Crucial Modification:**
    *   *Original Tool:* `get_location_data(id)` -> returns a specific row.
    *   *Naive Tool:* `get_all_location_data()` -> returns the **entire** string content of `location_database_large.csv` directly into the chat history.
*   **The Trap:** When the user asks "Analyze Location 402," the Monolith will call `get_all_location_data`, ingest 30k tokens, and likely hallucinate the specific numbers for Location 402 due to "Lost in the Middle" issues.

---

## Phase 3: Constructing "Milestone 1" (Data Optimization)

This is the solution code for the first exercise (The "Reduce" & "Offload" pillars).

**Step 3.1: The "Offloader" Tool**
Update the tool definition for the audience solution branch.
*   **Code Change:**
    ```python
    # tools_optimized.py
    def get_location_data_file():
        """Returns the file path to the location database."""
        # Instead of returning text, we ensure the file is in the sandbox
        return "/sandbox/location_database_large.csv"
    ```

**Step 3.2: Enable Code Execution (Pandas)**
*   **Configuration:** The audience will enable the `CodeExecutionTool` (standard in ADK/Gemini).
*   **The Shift:** Instead of reading the CSV, the agent writes:
    ```python
    import pandas as pd
    df = pd.read_csv('/sandbox/location_database_large.csv')
    print(df[df['location_id'] == 402])
    ```
*   **Evaluation Win:** 30k tokens (Monolith) $\to$ ~200 tokens (Python Code + Result).

---

## Phase 4: Constructing "Milestone 2" (Architecture Optimization)

This is the solution code for the second exercise (The "Isolate" pillar).

**Step 4.1: Split the Prompts**
Create `agents/sub_agents/`.
*   `analyst_agent.py`: Instructions focused *only* on Python coding and data querying.
*   `strategist_agent.py`: Instructions focused *only* on reading the Analyst's report (markdown artifact) and writing the final business memo.

**Step 4.2: The Orchestrator (Triage)**
Create a simple router logic.
*   **Logic:**
    1.  User Query -> Triage Agent.
    2.  Triage -> Calls `Analyst`.
    3.  `Analyst` -> Generates `report.md` -> Returns path.
    4.  Triage -> Calls `Strategist` (passing `report.md` path).
    5.  `Strategist` -> Reads file -> Returns final answer.

---

## Phase 5: The Evaluation Layer (Proving the Climb)

To demonstrate the "Hill Climb" effectively, we need a mix of **Deterministic Metrics** (from ADK logs/traces) to prove efficiency and **Model-Based Metrics** (from Vertex AI Evaluation Service) to prove quality.

### 5.1 The "Golden" Dataset
Create `evaluation/datasets/questions.json`.
*   *Question:* "What is the rent per sqft for location 123?"
*   *Ground Truth:* Extract the exact number from the CSV (e.g., "$45.20").

### 5.2 Quality Metrics (Vertex AI Evaluation Service)
*Goal: Prove that the Monolith hallucinates data, while the Context-Engineered agent is factually accurate.*

We will define a **`EvalTask`** that runs against your test dataset (`questions.json`).

*   **Metric A: `numerical_accuracy` (The "Hallucination Killer")**
    *   *Type:* Deterministic (Custom Function).
    *   *Why:* The Monolith will try to "read" the 30k token CSV and answer "What is the rent at location 402?" It will likely hallucinate or get the row wrong due to "Lost in the Middle." The Optimized agent (using Pandas/Code Execution) will get it right 100% of the time.
    *   *Implementation:* The script captures the agent's output and compares any numerical values associated with entities against the ground truth CSV row.
    *   *Prediction:* Monolith (~40% Fail) vs Optimized (100% Pass).

*   **Metric B: `instruction_adherence` (The "Manager" Check)**
    *   *Type:* Model-Based (GenAI-Auto-Rater).
    *   *Why:* In the Monolith (Milestone 0), the prompt is polluted with conflict. The agent might answer briefly when asked for a "detailed memo."
    *   *Rubric:* "Did the response follow the formatting constraints? (e.g., Use Markdown headers, include a 'Risks' section). Rate 1-5."

*   **Metric C: `tool_call_efficiency` (The "Flail" Check)**
    *   *Type:* Computed from Traces.
    *   *Why:* Monoliths often hallucinate tool parameters (e.g., trying to pass a whole paragraph into a `search` tool).
    *   *Formula:* `Successful Tool Calls / Total Tool Calls`.

### 5.3 Performance Metrics (ADK Session Data)
*Goal: Prove that "Less Context = Faster Speed."*

*   **Metric A: `time_to_first_token` (TTFT)**
    *   *For Milestone 3 (Cache):* Measure time from "User hits Enter" to "First word appears."
    *   *The Climb:* Monolith (>4s) vs Cached (<500ms).

*   **Metric B: `e2e_latency` (Reasoning Speed)**
    *   *Definition:* Total time to complete the request.
    *   *Note:* Code Execution (Milestone 1) might actually take *longer* initially than a simple text guess, but it is *correct*. We frame this as "Time to Correct Answer."

### 5.4 Cost & Efficiency Metrics (ADK Session Data)
*Goal: The "Financial" Justification.*

*   **Metric A: `context_utilization_ratio` (The "Signal-to-Noise" Ratio)**
    *   *Definition:* `Input Tokens / Output Tokens`.
    *   *The Climb:* Massive reduction. Monolith pays for 30,000 input tokens per turn. Optimized pays for ~500. This demonstrates the **"Offload"** pillar.

*   **Metric B: `cached_content_token_count`**
    *   *Definition:* The number of tokens flagged as `cached` in the usage metadata.
    *   *The Climb:* 0 tokens (Milestone 0-2) vs ~90% of System Prompt (Milestone 3).

---

## Phase 6: Visualization (The Scorecard)

For the workshop, we will generate this simple table at the end of each notebook execution to visualize the "Hill Climb":

| Metric | Milestone 0 (Monolith) | Milestone 1 (Offload) | Milestone 2 (Multi-Agent) | Milestone 3 (Cache) |
| :--- | :--- | :--- | :--- | :--- |
| **Accuracy (Eval Service)** | 🔴 42% (Hallucinated) | 🟢 **100% (Code Exec)** | 🟢 100% | 🟢 100% |
| **Input Cost (Tokens)** | 🔴 32,500 | 🟢 **450** | 🟡 800 (Overhead) | 🟢 800 (Discounted) |
| **TTFT (Latency)** | 🔴 4.2s | 🟡 3.8s | 🟡 4.0s | 🟢 **0.4s** |
| **Tool Errors** | 🔴 High | 🟢 Zero | 🟢 Zero | 🟢 Zero |

---

## Summary of Repo Prep Tasks

1.  **Generate Data:** `location_database_large.csv` (500 rows).
2.  **Break Code (Monolith):**
    *   Merge prompts.
    *   Make tools return raw text dumps.
3.  **Prepare Solutions (Optimized):**
    *   Separate prompts.
    *   Tools return file paths.
    *   Enable Code Execution.
4.  **Build Eval Scripts:**
    *   Write `verify_csv_data` function (Python) for Vertex EvalTask.
    *   Write `measure_usage` wrapper to calculate token costs and latency via `time.time()`.