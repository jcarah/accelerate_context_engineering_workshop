# Agent Optimization & Evaluation Workshop

**Google Cloud Accelerate '26**

Learn to move from trial-and-error prompt engineering to systematic, measurable agent optimization.

---

## Critical Requirement

```
+------------------------------------------------------------------+
|  You MUST use Vertex AI for the evaluation pipeline to work.     |
|                                                                   |
|  Set: GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION             |
|  Do NOT use: GOOGLE_API_KEY (metrics will be empty)              |
+------------------------------------------------------------------+
```

---

## What You'll Do in This Workshop

During this workshop, you will:

1. **Run baseline evaluations** on two agents (Customer Service and Retail AI) to establish starting metrics
2. **Checkout optimization branches** that contain pre-made improvements to the agent source code
3. **Run evaluations on each branch** to measure the impact of the code changes
4. **Compare metrics** between baseline and optimized versions to see what improved (and what didn't)

> **Note:** For the ease of this workshop, you won't modify the agent source code yourself. The optimization branches already contain the code changes. Your job is to run evaluations and interpret the results.

---

## How to Use This Guide

This README is split into two parts:

| Section | Who It's For | What's Inside |
|---------|--------------|---------------|
| **Part 1: Knowing Before Coding** | Everyone | Context covered in the presentation slides. Read if you missed it or want a refresher. |
| **Part 2: Workshop Steps** | Hands-on participants | Step-by-step coding exercises. **Start here if you're ready to code.** |

> **Ready to code?** [Jump to Workshop Step 1](#workshop-step-1-environment-setup)

---

# Part 1: Knowing Before Coding

> **Note:** This section covers what the speakers presented in slides. If you attended the presentation, you can skip directly to [Part 2: Workshop Steps](#part-2-workshop-steps).

## The Problem We're Solving

Prototyping an agent is easy. Graduating it to production is where things fall apart.

| Challenge | The Problem |
|-----------|-------------|
| **The Visibility Gap** | When an agent fails, it doesn't throw a stack trace. It drifts, hallucinates, or gets lost. |
| **The Prompt Trap** | Most optimization stops at prompt engineering. But prompts are fragile. Real improvement requires architectural shifts. |
| **The Validation Hurdle** | Fixing one edge case often degrades another. Without objective measurement, you can't prove optimizations work. |

## The Evaluation Framework

We use a 3-step evaluation process:

```
Step 1: Run Interactions  →  Step 2: Run Evaluation  →  Step 3: Analyze Results
   (Generate traces)          (Grade with metrics)       (AI root cause analysis)
```

| Step | What Happens | Output |
|------|--------------|--------|
| **Interactions** | Run agent through test scenarios | Traces (JSONL) |
| **Evaluation** | Grade interactions with deterministic + LLM metrics | `eval_summary.json` |
| **Analysis** | AI analyzes results, identifies root causes | `gemini_analysis.md` |

## The Test Agents

We use two agents to demonstrate different optimization challenges:

| | Customer Service Agent | Retail AI Agent |
|---|---|---|
| **Problem** | Single agent with 12+ tools. Logic errors, hallucinations. | Processes massive datasets. Token bloat, high latency. |
| **Conversation Type** | Multi-turn (back-and-forth) | Single-turn pipeline |
| **Evaluation Mode** | ADK User Sim | DIY Interactions |
| **Key Metrics** | `trajectory_accuracy`, `tool_use_quality` | `general_quality`, `pipeline_integrity` |

## Context Engineering Principles

> "Context Engineering is the systematic management of the model's context window to maximize Signal-to-Noise Ratio."
>
> **More Context != More Intelligence**

| Principle | When to Apply |
|-----------|---------------|
| **Offload** | Move deterministic logic to tools/code |
| **Reduce** | Summarize history, trim context |
| **Retrieve** | Replace static data with RAG |
| **Isolate** | Split into specialized sub-agents |
| **Cache** | Restructure prompts for prefix caching |

## The Optimization Milestones

| Milestone | Branch | What It Fixes |
|-----------|--------|---------------|
| M0 | `main` | Baseline (no optimizations) |
| M1 | `01-tool-definition` | Tool errors → Stricter schemas |
| M2 | `02-context-compaction` | Context rot → Summarization |
| M3 | `03-functional-isolation` | Wrong tool selection → Sub-agents |
| M4 | `04-offload-and-reduce` | Token bloat → Offload to code |
| M5 | `05-prefix-caching` | High latency → Prefix caching |

---

# Part 2: Workshop Steps

> **You're ready to code!** Follow each step in order. If you get stuck, ask for help.

### About the `agent-eval` CLI

Throughout this workshop, you'll use a CLI tool called `agent-eval`. This is a **reference implementation** we built to act as the "glue" between:
- **OpenTelemetry** traces from ADK
- **Vertex AI Evaluation** service for LLM-as-judge metrics
- **Gemini** for analyzing results

The CLI encapsulates scripts for converting traces, running evaluations, and generating analysis. You can use it as-is for any ADK agent, or tear it apart and adapt it to your customers' specific frameworks.

---

## Workshop Step 1: Environment Setup

**Goal:** Verify your environment is ready to run evaluations.

### 1.1 Check Prerequisites

Run these commands to verify your setup:

```bash
python3 --version  # Must be 3.10, 3.11, or 3.12 (NOT 3.13+)
uv --version       # Must be installed
gcloud auth list   # Must show authenticated account
```

**Missing something?**

| Missing | How to Fix |
|---------|------------|
| Python 3.10-3.12 | Install from [python.org](https://www.python.org/downloads/) |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| gcloud auth | `gcloud auth login && gcloud auth application-default login` |

### 1.2 Set Your Project

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
gcloud auth application-default set-quota-project $GOOGLE_CLOUD_PROJECT
```

### 1.3 Clone and Verify

```bash
git clone <repo-url>
cd accelerate

# Run verification script
./setup_workshop.sh
```

### 1.4 Configure Agent Credentials

**Customer Service Agent:**

```bash
cd customer-service
cp .env.example .env
```

Edit `.env` and set:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

**Retail AI Agent:**

```bash
cd ../retail-ai-location-strategy
cp .env.example .env
```

Edit `.env` and set:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
MAPS_API_KEY=your-maps-api-key
```

> **Note:** `MAPS_API_KEY` is required for competitor mapping. Get it from [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and enable "Places API".

### 1.5 Install Evaluation CLI

```bash
cd ../evaluation
uv sync
```

**Checkpoint:** You should see no errors. You're ready for the next step.

---

## Workshop Step 2: Evaluate the Customer Service Agent

**Goal:** Generate baseline metrics for the Customer Service agent.

This agent is a multi-turn chatbot, so we use **ADK User Sim** to generate realistic conversations. Instead of hand-writing test data, you provide conversation *scenarios* and the simulator uses another model to act as a user interacting with your agent.

The evaluation follows three steps:
1. **Run Interactions** - Generate traces by simulating conversations
2. **Run Evaluation** - Score the traces with quality metrics
3. **Analyze Results** - Interpret what the metrics mean

---

### Step 2A: Run Interactions

First, we need traffic. We'll use ADK User Sim to generate multi-turn conversation traces.

#### 2A.1 Set Up the Simulation

```bash
cd customer-service
uv sync

# Create eval set
uv run adk eval_set create customer_service eval_set_with_scenarios

# Add test scenarios (these define HOW the simulated user behaves)
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json
```

#### 2A.2 Run the Simulation

```bash
uv run adk eval customer_service eval_set_with_scenarios
```

This runs for 2-3 minutes. You'll see simulated conversations in real-time as the "user" interacts with your agent.

#### 2A.3 Convert Traces to Evaluation Format

The `convert` command takes raw ADK traces and standardizes them for the evaluation step.

```bash
cd ../evaluation

uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results
```

Note the output folder path - you'll use it in the next steps.

---

### Step 2B: Run Evaluation

Now we score the interactions using deterministic metrics (latency, cost) and LLM-as-judge quality metrics.

```bash
# Use the folder path from the previous step
RUN_DIR=../customer-service/eval/results/<your-folder-name>

uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline
```

This generates `eval_summary.json` with all the metrics.

---

### Step 2C: Analyze Results

Finally, we interpret what the metrics mean. The `analyze` command uses Gemini to read your agent's source code and evaluation results, then generates actionable insights.

```bash
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service \
  --location global
```

#### Review Your Baseline

You have two options for reviewing results:

**Option 1: AI-Generated Analysis (Recommended)**
```bash
cat $RUN_DIR/gemini_analysis.md
```

This markdown file contains Gemini's interpretation of your results, including root cause analysis and improvement suggestions.

**Option 2: Raw Metrics**
```bash
cat $RUN_DIR/eval_summary.json
```

This JSON file contains all deterministic and LLM-based metrics.

> **Coming Soon:** A Gradio dashboard for visual comparison of evaluation runs. For now, use the files above.

**What to Look For:**

Here's what you might see in the Customer Service baseline:

| Metric | Typical Value | What It Means |
|--------|---------------|---------------|
| `trajectory_accuracy` | ~3.6/5 | Agent sometimes takes wrong paths - room for improvement |
| `tool_use_quality` | ~5.0/5 | Tools are called correctly when used |
| `capability_honesty` | ~2.2/5 | Agent may misrepresent what it can do - a signal to investigate |
| `cache_efficiency.cache_hit_rate` | ~35% | Some caching, but could be better |
| `latency_metrics.total_latency_seconds` | ~40s | Total conversation duration |
| `token_usage.prompt_tokens` | ~22,000 | Input tokens sent to the model |

> **Tip:** See [REFERENCE.md - Deterministic Metrics](REFERENCE.md#deterministic-metrics) for a complete glossary of all available metrics.

---

## Workshop Step 3: Evaluate the Retail AI Agent

**Goal:** Generate baseline metrics for the Retail AI agent.

This agent is a single-turn pipeline (user sends one request, agent runs a full analysis). ADK User Sim is overkill for this pattern, so we use **DIY Interactions** instead - we run the agent against a golden dataset of test queries.

> **Note:** This requires **two terminals** - one for the agent server, one for evaluation.

The same three-step pattern applies:
1. **Run Interactions** - Query the running agent with test inputs
2. **Run Evaluation** - Score the traces with quality metrics
3. **Analyze Results** - Interpret what the metrics mean

---

### Step 3A: Run Interactions

#### 3A.1 Start the Agent (Terminal 1)

```bash
cd retail-ai-location-strategy
uv sync
make dev  # Starts on port 8502
```

**Keep this terminal running.** Open a new terminal for the next steps.

#### 3A.2 Run Test Queries (Terminal 2)

The `interact` command sends queries from your golden dataset to the running agent and collects traces.

```bash
cd evaluation

uv run agent-eval interact \
  --app-name app \
  --questions-file ../retail-ai-location-strategy/eval/eval_data/golden_dataset.json \
  --base-url http://localhost:8502 \
  --results-dir ../retail-ai-location-strategy/eval/results
```

This runs for 3-5 minutes. Note the output folder path for the next steps.

---

### Step 3B: Run Evaluation

```bash
# Use the folder path from the previous step
RUN_DIR=../retail-ai-location-strategy/eval/results/<your-folder-name>

uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_app.jsonl \
  --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline
```

---

### Step 3C: Analyze Results

```bash
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../retail-ai-location-strategy \
  --location global
```

#### Review Your Baseline

**Option 1: AI-Generated Analysis (Recommended)**
```bash
cat $RUN_DIR/gemini_analysis.md
```

**Option 2: Raw Metrics**
```bash
cat $RUN_DIR/eval_summary.json
```

> **Coming Soon:** A Gradio dashboard for visual comparison of evaluation runs. For now, use the files above.

**What to Look For:**

Here's what you might see in the Retail AI baseline:

| Metric | Typical Value | What It Means |
|--------|---------------|---------------|
| `trajectory_accuracy` | ~5.0/5 | Pipeline stages execute in correct order |
| `tool_use_quality` | ~2.0/5 | Tools may be called with suboptimal parameters - investigate |
| `pipeline_integrity` | ~2.3/5 | Some stages may not complete properly - a signal to investigate |
| `general_quality` | ~0.79/1 | Overall response quality is good |
| `latency_metrics.total_latency_seconds` | ~165s | Full pipeline takes several minutes |
| `cache_efficiency.cache_hit_rate` | ~8% | Very low caching - opportunity for optimization |
| `token_usage.prompt_tokens` | ~39,000 | High input tokens - context may be bloated |

> **Tip:** See [REFERENCE.md - Deterministic Metrics](REFERENCE.md#deterministic-metrics) for a complete glossary of all available metrics.

You can now stop the agent in Terminal 1 (`Ctrl+C`).

---

## Workshop Step 4: Hill Climbing with Optimization Branches

**Goal:** Apply optimizations and measure their impact.

You now have **baseline metrics** from Steps 2 and 3. The optimization branches contain pre-made improvements. Your job is to:

1. Checkout an optimization branch
2. Explore what changed in the agent code
3. Run evaluation
4. Compare metrics with baseline
5. Understand the trade-offs

### Choosing Your Path

| If you're working on... | Start with | Then move to |
|-------------------------|------------|--------------|
| Customer Service Agent | Branch 01 | → 02 → 03 |
| Retail AI Agent | Branch 04 | → 05 |

### Go to Your First Optimization Branch

Each optimization branch has its own README with step-by-step instructions.

**Customer Service Path:**
```bash
git checkout optimizations/01-tool-definition
cat README.md  # Follow the branch-specific guide
```

**Retail AI Path:**
```bash
git checkout optimizations/04-offload-and-reduce
cat README.md  # Follow the branch-specific guide
```

The branch README will guide you through:
1. What optimization was applied
2. How to explore the code changes
3. How to run evaluation
4. How to interpret the results
5. How to move to the next branch

---

## Quick Reference

### Full Pipeline: Customer Service (ADK User Sim)

```bash
# From customer-service folder
cd customer-service
rm -rf customer_service/.adk/eval_history/*
rm -f customer_service/*.evalset.json

uv run adk eval_set create customer_service eval_set_with_scenarios
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json
uv run adk eval customer_service eval_set_with_scenarios

# From evaluation folder
cd ../evaluation
RUN_DIR=$(uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results \
  | awk -F': ' '/^Run folder:/ {print $2}')

uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR

uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service \
  --location global
```

### Full Pipeline: Retail AI (DIY Interactions)

```bash
# Terminal 1: Start agent
cd retail-ai-location-strategy && make dev

# Terminal 2: Run evaluation
cd evaluation
RUN_DIR=$(uv run agent-eval interact \
  --app-name app \
  --questions-file ../retail-ai-location-strategy/eval/eval_data/golden_dataset.json \
  --base-url http://localhost:8502 \
  --results-dir ../retail-ai-location-strategy/eval/results \
  | awk -F': ' '/^Run folder:/ {print $2}')

uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_app.jsonl \
  --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR

uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../retail-ai-location-strategy \
  --location global
```

---

## Need Help?

| Resource | What It Contains |
|----------|------------------|
| [REFERENCE.md](REFERENCE.md) | CLI commands, metrics guide, troubleshooting |
| [REFERENCE.md#ai-assistant-setup](REFERENCE.md#ai-assistant-setup-optional) | Gemini CLI setup for AI assistance |
| Speakers | Raise your hand! |

---

## Additional Resources

- [ADK Documentation](https://google.github.io/adk-docs/)
- [ADK User Simulation](https://google.github.io/adk-docs/evaluate/user-sim/)
- [Vertex AI Evaluation](https://cloud.google.com/vertex-ai/docs/generative-ai/evaluation/)
