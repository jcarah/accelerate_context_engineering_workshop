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
> It covers the full CLI reference, both evaluation paths (Simulation vs Live), and how to define custom LLM-as-a-Judge metrics.

**Key Components:**
*   **Simulation Scenarios:** Test scenarios for ADK simulator in `[agent]/eval/scenarios/` ([ADK User Simulation Docs](https://google.github.io/adk-docs/evaluate/user-sim/))
*   **Metric Definitions:** Custom rubrics (e.g., "Did the agent use the correct tool?") in `[agent]/eval/metrics/`
*   **CLI Tool (`agent-eval`):** Unified commands for convert, evaluate, and analyze (use `--help` for options)

### Running a Baseline Evaluation (Customer Service)

Follow these steps to establish a baseline before making optimizations.

#### Step 1: Run ADK Simulator

Generate agent interactions using the native ADK simulator.

```bash
cd customer-service

# IMPORTANT: Clear previous eval history before each baseline
rm -rf customer_service/.adk/eval_history/*

# Run the simulation (scenarios are in eval/scenarios/)
uv run adk eval customer_service \
  --config_file_path eval/scenarios/eval_config.json \
  eval_set_with_scenarios \
  --print_detailed_results
```

> **Why clear `.adk/eval_history/`?** The simulator accumulates traces from ALL runs.
> Without clearing, your new baseline will include stale data from previous runs.

#### Step 2: Convert Traces & Run Evaluation

```bash
cd ../evaluation
uv sync  # First time only

# Convert ADK traces to evaluation format (creates timestamp folder)
uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results

# The CLI prints the next command. Use the timestamp folder:
RUN_DIR=../customer-service/eval/results/<timestamp>

# Run metrics (deterministic + LLM-as-Judge)
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.csv \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline \
  --test-description "Customer Service Baseline"
```

#### Step 3: Analyze Results

Generate human-readable reports and AI-powered root cause analysis.

```bash
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service
```

**Output:** Results in `customer-service/eval/results/<timestamp>/`
```
<timestamp>/
├── eval_summary.json           # Aggregated metrics
├── question_answer_log.md      # Detailed Q&A transcript
├── gemini_analysis.md          # AI root cause diagnosis
└── raw/
    ├── processed_interaction_sim.csv
    └── evaluation_results_*.csv
```

### Pre-Computed Baseline Results

For convenience, we include pre-computed baseline results in `[agent]/eval/results/baseline/`. These were generated on the `main` branch before any optimizations.

> **Important:** LLM outputs are non-deterministic. We recommend running your own baseline evaluation on your branch before making changes. This ensures you have a comparable "before" snapshot in your environment.

#### Retail Location Strategy Baseline

| Metric | Score | Range | Description |
|--------|-------|-------|-------------|
| `strategic_recommendation_quality` | 5.0 | 1-5 | Strategic mastery |
| `tool_usage_effectiveness` | 5.0 | 1-5 | Optimal usage |
| `market_research_depth` | 5.0 | 1-5 | Exceptional depth |
| `state_variable_fidelity` | 3.0 | 1-5 | Moderate alignment |
| `grounding` | 1.0 | 0-1 | All claims grounded |
| `agent_hallucination` | 1.0 | 0-1 | No hallucinations |
| `safety` | 1.0 | 0-1 | Safe |

**Key Deterministic Metrics:**
- Tool success rate: 100%
- Cache hit rate: 27%
- Unique tools used: 5
- Agent handoffs: 5
- Total tool calls: 15

#### Customer Service Baseline

| Metric | Score | Range | Description |
|--------|-------|-------|-------------|
| `tool_usage_accuracy` | 3.6 | 0-5 | Moderate tool usage |
| `trajectory_accuracy` | 2.6 | 0-5 | Needs improvement |
| `state_management_fidelity` | 0.8 | 0-5 | Limited state capture |
| `general_conversation_quality` | 0.80 | 0-1 | Good quality |
| `instruction_following` | 0.62 | 0-1 | Moderate adherence |
| `agent_hallucination` | 0.86 | 0-1 | Mostly supported |
| `safety` | 1.0 | 0-1 | Safe |

**Key Deterministic Metrics:**
- Tool success rate: 100%
- Cache hit rate: 41%
- Total tool calls: 4
- Agent handoffs: 4
- Unique tools used: 2

---

## 4. Workshop Curriculum: The Optimization Loop

We will follow a strict **Signal-Driven Engineering** loop:
1.  **Measure:** Run the eval pipeline (Steps 1-3 above).
2.  **Identify Signal:** Find the red flag in `eval_summary.json` (e.g., `tool_error_rate > 50%`).
3.  **Optimize:** Apply a specific Context Engineering pattern.
4.  **Verify:** Re-run evals to prove the lift.

### Branch Strategy: Branch-per-Optimization

Each optimization is isolated in its own branch, driven by a specific failure signal, and verified by a specific metric:

| Branch | Optimization | Target Metric |
| :--- | :--- | :--- |
| `main` | Baseline ("Naive Monolith") | Establish baseline scores |
| `optimizations/01-tool-definition` | Tool Schema Hardening | `tool_usage_accuracy` > 95% |
| `optimizations/02-context-compaction` | Context Compaction | Reduce "Context Rot" |
| `optimizations/03-code-execution` | Offload to Python Sandbox | `input_tokens` < 4000/turn |
| `optimizations/04-functional-isolation` | Split into Sub-Agents | `trajectory_accuracy` = 5/5 |
| `optimizations/05-prefix-caching` | Prefix Caching | `cache_hit_rate` > 75% |

---

### Phase 1: Fixing Reliability (Customer Service)

#### Step 1: The "Hallucinating Helper" (Tool Hardening)
**Context:** The agent keeps failing to update the shopping cart because it sends string descriptions instead of integer IDs to the API.

*   **Baseline Metrics:** `tool_usage_accuracy: 0.6`, `state_management_fidelity: 0.6`
*   **ADK Sample:** `tool_functions_config`

> **\[WORKSHOP TASK:**
> 1.  Run the baseline evaluation (see Section 3).
> 2.  Observe the high failure rate in `tool_usage_accuracy`.
> 3.  **Refactor:** Open `customer-service/customer_service/tools/tools.py` and replace generic dict schemas with strict Pydantic models.
> 4.  Re-run evaluation and verify the score improves.

#### Step 2: The "Overwhelmed Generalist" (Functional Isolation)
**Context:** The agent gets distracted. When asked to "Approve a discount", it hallucinates checking "Plant Pathology Rules" because all instructions are in one massive prompt.

*   **Baseline Metrics:** `trajectory_accuracy: 1.6`, `unique_agents_count: 1`
*   **ADK Sample:** `workflow_triage`

> **\[WORKSHOP TASK:**
> 1.  Run the `analyze` script and check `gemini_analysis.md`.
> 2.  Note the finding: "*Trajectory Noise: Agent introduces irrelevant steps.*"
> 3.  **Refactor:** Split the `root_agent` into a **Triage Agent** that routes to specialized **Sales** and **Support** sub-agents.

#### Step 3: The "Drifting Planner" (Recitation)
**Context:** In long conversations (e.g., scheduling a delivery), the agent forgets the original goal (applying the discount) because it gets "Lost in the Middle" of the context window.

*   **Baseline Metrics:** Task completion drops significantly after turn 8
*   **ADK Sample:** `memory_checkpoint`

> **\[WORKSHOP TASK:**
> 1.  **Refactor:** Implement **Attention Structuring**. Inject a dynamic `todo.md` block at the *end* of the prompt every turn, forcing the agent to "recite" its remaining tasks before acting.

---

### Phase 2: Fixing Scale (Retail Strategy)

#### Step 4: The "Context Dumper" (Offload & Reduce)
**Context:** The `CompetitorMappingAgent` finds 50 coffee shops and dumps the entire raw JSON response (100k+ tokens) into the chat history. The agent crashes or hallucinates simple math.

*   **Baseline Metrics:** `input_tokens: >100k/turn`, `Context Efficiency Ratio: <10:1`
*   **ADK Sample:** `code_execution_sandbox`

> **\[WORKSHOP TASK:**
> 1.  Run a heavy query: "Analyze saturation in Austin, TX".
> 2.  Check `token_usage` metrics. Observe >100k input tokens per turn.
> 3.  **Refactor:** Implement the **Offload** pillar. Modify the tool to save `competitors.json` to disk and enable Code Execution for the agent to analyze it using Pandas.

#### Step 5: The "Expensive Executive" (Prefix Caching)
**Context:** The agent works, but it's slow (8s latency) and expensive because we re-send the same massive system instructions every turn.

*   **Baseline Metrics:** `cache_hit_rate: ~36%`, `time_to_first_response: >1s`

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
