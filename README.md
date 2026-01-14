# Agent Optimization & Evaluation Workshop (Accelerate '26)

**Focus:** Context Engineering & Quantitative Evaluation
**Target Audience:** Technical GTM Practitioners

---

## 1. Overview

This workshop teaches you to move from **Prompt Engineering** (stateless, token-heavy) to **Context Engineering** (stateful, architectural optimization).

**By the end, you will:**
1. **Iteratively improve agent performance** using the "Five Pillars" of Context Engineering (Offload, Reduce, Retrieve, Isolate, Cache).
2. **Measure performance** across Quality, Cost, and Latency axes using a production-grade evaluation framework.

### The Execution Framework: "The Hill Climb"
We start with functional but unoptimized "Base Camp" agents. We establish evaluation baselines, identify failure signals (e.g., hallucinations, latency spikes), and iteratively apply architectural patterns to climb toward a production-ready system.

---

## 2. Prerequisites

Before starting, ensure you have:

- **Python 3.10-3.12** (not 3.13+)
- **uv** (Python package manager) - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Google Cloud credentials** (one of the following):
  - **Option A: Vertex AI** - A GCP project with Vertex AI API enabled
  - **Option B: AI Studio** - A Google AI Studio API key

To verify your setup after installation, run:
```bash
make verify  # Available in each agent directory
```

---

## 3. The Test Subjects (Agents)

We use two distinct agents to demonstrate different classes of problems.

### Agent A: Customer Service (The "Naive Monolith")

| | |
|---|---|
| **Location** | `customer-service/` |
| **The Problem** | A single agent trying to do too much (12+ tools). Suffers from **Logic Errors**, **Hallucinations**, and **Routing Failures**. |
| **The Fix** | Practice **Reliability Optimizations** (Schema Hardening, Functional Isolation, Reflexion). |
| **Runs on** | `http://localhost:8501` |

**Setup:**
```bash
cd customer-service

# 1. Configure credentials
cp .env.example .env
# Edit .env and set:
#   GOOGLE_CLOUD_PROJECT=your-gcp-project-id
#   GOOGLE_CLOUD_LOCATION=us-central1
#   GOOGLE_GENAI_USE_VERTEXAI=TRUE

# 2. Install dependencies and run
make install
make playground   # or: make dev
```

### Agent B: Retail AI Location Strategy (The "Context Dumper")

| | |
|---|---|
| **Location** | `retail-ai-location-strategy/` |
| **The Problem** | A complex multi-agent pipeline that processes massive datasets (Google Maps API). Suffers from **Token Bloat**, **High Latency**, and **High Cost**. |
| **The Fix** | Practice **Scale Optimizations** (Offloading state to files, Code Execution, Prefix Caching). |
| **Runs on** | `http://localhost:8502` |

**Setup:**
```bash
cd retail-ai-location-strategy

# 1. Configure credentials (note: .env is in project root, not app/)
cp .env.example .env
# Edit .env and set ONE of:
#   Option A (Vertex AI):
#     GOOGLE_GENAI_USE_VERTEXAI=TRUE
#     GOOGLE_CLOUD_PROJECT=your-gcp-project-id
#     GOOGLE_CLOUD_LOCATION=us-central1
#   Option B (AI Studio):
#     GOOGLE_GENAI_USE_VERTEXAI=FALSE
#     GOOGLE_API_KEY=your-ai-studio-api-key
#
# Also set: MAPS_API_KEY=your-maps-api-key

# 2. Install dependencies and run
make install
make dev          # ADK web UI at http://localhost:8502

# OR use the interactive AG-UI dashboard (optional):
make ag-ui-install
make ag-ui        # Frontend at http://localhost:3000, backend at :8502
```

---

## 4. Running Evaluations

We use a custom evaluation pipeline in `evaluation/` as a reference architecture for agent CI/CD.

**Key Components:**
- **Simulation Scenarios:** Test scenarios in `[agent]/eval/scenarios/` ([ADK Docs](https://google.github.io/adk-docs/evaluate/user-sim/))
- **Metric Definitions:** Custom rubrics in `[agent]/eval/metrics/`
- **CLI Tool (`agent-eval`):** Commands for `convert`, `evaluate`, and `analyze`

> **📚 Advanced Topics:** See **[Evaluation README](evaluation/README.md)** for the full CLI reference, live/remote evaluation, and custom LLM-as-a-Judge metrics.

---

### Baseline Evaluation Quickstart (Customer Service)

Follow these steps to establish a baseline before making optimizations.

#### Step 1: Run ADK Simulator

> ⚠️ **CRITICAL:** Always clear `eval_history` before running a new baseline. The ADK simulator *appends* to this folder on every run. Without clearing, your baseline will include stale data from previous runs, corrupting all metrics.

```bash
cd customer-service

# Clear previous eval history (REQUIRED before each baseline)
rm -rf customer_service/.adk/eval_history/*

# Run the simulation
uv run adk eval customer_service \
  --config_file_path eval/scenarios/eval_config.json \
  eval_set_with_scenarios \
  --print_detailed_results
```

#### Step 2: Convert Traces & Run Evaluation

Might need to make sure that we have the project in env vars

```bash
cd ../evaluation
uv sync  # First time only

# Convert ADK traces to evaluation format
uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results

# Note the timestamp folder printed by the CLI, then:
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

```bash
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service
```

**Output files in `customer-service/eval/results/<timestamp>/`:**

| File | Purpose |
|------|---------|
| `eval_summary.json` | Aggregated metrics - **start here** |
| `gemini_analysis.md` | AI-generated root cause diagnosis |
| `question_answer_log.md` | Detailed Q&A transcript |
| `raw/` | Raw data (processed interactions, evaluation results) |

#### Step 4: Interpret Your Results

**Start with `eval_summary.json`** and look for these red flags:

| Metric | Threshold | If Below, Try... |
|--------|-----------|------------------|
| `tool_usage_accuracy` | < 3.0 | Tool Schema Hardening (optimization 01) |
| `trajectory_accuracy` | < 3.0 | Functional Isolation (optimization 04) |
| `state_management_fidelity` | < 3.0 | Context Compaction (optimization 02) |
| `input_tokens` | > 10,000/turn | Offload to Code Execution (optimization 03) |

Then read `gemini_analysis.md` for AI-identified root causes and specific fix suggestions.

---

## 5. Workshop Curriculum: The Optimization Loop

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

## 6. Signal Identification Cheatsheet

Use the generated `eval_summary.json` to pick your battle.

| Signal (The Symptom) | Metric / Data Source | Recommended Optimization (The Cure) |
| :--- | :--- | :--- |
| **Context Rot** | `state_fidelity` score drops as conversation length increases. | **Context Compaction** or **Recitation** |
| **Hallucination** | `tool_usage_accuracy` is low; agent invents parameters. | **Tool Hardening (Schema)** |
| **Token Bloat** | Input tokens > 4000/turn; `Context Efficiency Ratio` < 50:1. | **Offload (Code Execution)** |
| **Slow Recovery** | High "Reflexion" count (retries) in traces. | **Reflexion Loop** |
| **High Cost** | Low `KV-Cache Hit Rate` (< 50%). | **Prefix Caching** |
| **General Failure** | Low `Pass^k` (consistency) across diverse tasks. | **Functional Isolation (Sub-agents)** |

---

## 7. Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `ModuleNotFoundError: No module named 'customer_service'` | Running from wrong directory | `cd customer-service` before running commands |
| `GOOGLE_CLOUD_PROJECT not set` | Missing or misconfigured `.env` | Check `.env` exists and has correct values (see Section 3) |
| `Port already in use` | Another agent or process on the port | Customer Service uses 8501, Retail uses 8502. Kill conflicting process or change port in Makefile |
| ADK evaluation shows no/stale results | Didn't clear `eval_history` | Run `rm -rf customer_service/.adk/eval_history/*` before each baseline |
| `uv: command not found` | uv not installed | Install via `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Vertex AI authentication errors | Missing ADC or wrong project | Run `gcloud auth application-default login` and verify `GOOGLE_CLOUD_PROJECT` |

---

## 8. Project Structure

```
accelerate_context_engineering_workshop/
├── README.md                          ← You are here
├── customer-service/                  ← Agent A (port 8501)
│   ├── .env.example
│   ├── Makefile
│   ├── customer_service/
│   │   ├── *.evalset.json             ← ADK eval sets live here
│   │   └── .adk/eval_history/         ← Clear before each baseline!
│   └── eval/
│       ├── scenarios/                 ← ADK config & conversation plans
│       ├── metrics/                   ← Metric definitions
│       └── results/<timestamp>/       ← Evaluation outputs
├── retail-ai-location-strategy/       ← Agent B (port 8502)
│   ├── .env                           ← Note: in root, not app/
│   ├── .env.example
│   ├── Makefile
│   └── app/
└── evaluation/                        ← Shared eval CLI
    ├── README.md                      ← Full CLI reference
    └── src/evaluation/cli/
```
