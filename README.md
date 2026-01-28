# Agent Optimization & Evaluation Workshop

**Google Cloud Accelerate '26**

Learn to move from trial-and-error prompt engineering to systematic, measurable agent optimization.

---

> **Note for Testers (Jan 2026):** The optimization branches (e.g., `optimizations/01-*`) are being updated with the latest evaluation framework. They may not be ready yet. For now, test on `main` by running the baseline evaluation, making changes to agent source code, and re-running to see metrics change.

---

## What You'll Learn

By the end of this workshop, you will:

1. **Measure agent performance** across three dimensions: Quality, Cost, and Latency
2. **Identify failure signals** from evaluation data (hallucinations, context rot, tool errors)
3. **Apply optimization patterns** based on Context Engineering principles
4. **Validate improvements** by comparing before/after metrics

---

## The Agent Performance Paradox

Prototyping an agent is easy. Graduating it to production is where things fall apart.

| Challenge | The Problem |
|-----------|-------------|
| **The Visibility Gap** | When an agent fails, it doesn't throw a stack trace. It drifts, hallucinates, or gets lost. |
| **The Prompt Trap** | Most optimization stops at prompt engineering. But prompts are fragile. Real improvement requires architectural shifts. |
| **The Validation Hurdle** | Fixing one edge case often degrades another. Without objective measurement, you can't prove optimizations work. |

This workshop gives you the tools to close these gaps.

---

## The Evaluation Framework

We use a **Build, Test, Learn, Deploy** cycle with a 3-step evaluation process:

```
1/3 Run Interactions  →  2/3 Run Evaluation  →  3/3 Analyze Results
   (ADK User Sim or       (Vertex AI Metrics)    (Reports + AI Analysis)
    DIY Interactions)
```

| Step | What Happens | Output |
|------|--------------|--------|
| **1/3 Interactions** | Generate traces by running agent through test scenarios | `.adk/eval_history/` or JSONL |
| **2/3 Evaluation** | Grade interactions using deterministic + LLM metrics | `eval_summary.json` |
| **3/3 Analysis** | Turn numbers into decisions with AI root cause analysis | `gemini_analysis.md` |

---

## The Test Subjects

We use two agents to demonstrate different optimization challenges:

| | Customer Service Agent | Retail AI Agent |
|---|---|---|
| **Focus** | Reliability | Scale |
| **Problem** | Single agent with 12+ tools. Suffers from logic errors, hallucinations, routing failures. | Processes massive datasets (Google Maps API). Suffers from token bloat, high latency, high cost. |
| **Conversation Type** | Multi-turn (user ↔ agent ↔ user) | Single-turn pipeline (user → pipeline → response) |
| **Evaluation Mode** | ADK User Sim | DIY Interactions |
| **Key Metrics** | `multi_turn_general_quality`, `trajectory_accuracy` | `general_quality`, `pipeline_integrity` |

---

## Workshop Flow

This workshop takes approximately 90 minutes:

| Section | Time | What You'll Do |
|---------|------|----------------|
| [1. Setup](#1-setup) | 10 min | Prerequisites, credentials, verify environment |
| [2. Baseline: Customer Service](#2-baseline-customer-service) | 15 min | Run evaluation using ADK User Sim |
| [3. Baseline: Retail AI](#3-baseline-retail-ai) | 15 min | Run evaluation using DIY Interactions |
| [4. Add Custom Metric](#4-add-custom-metric) | 10 min | Create a fine-grained metric for structured responses |
| [5. Optimization Branches](#5-optimization-branches) | 35 min | Apply optimizations, compare before/after |
| [6. Wrap-up](#6-wrap-up) | 5 min | Summary, next steps |

---

## 1. Setup

### Prerequisites Checklist

```
[ ] Python 3.10-3.12 (not 3.13+)
[ ] uv package manager
[ ] Google Cloud project with Vertex AI API enabled
[ ] Authenticated with gcloud
```

### Quick Verification

```bash
python3 --version  # Must be 3.10, 3.11, or 3.12
uv --version
gcloud auth list
```

### Install uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Google Cloud Authentication

```bash
gcloud auth login
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-project-id"
gcloud auth application-default set-quota-project $GOOGLE_CLOUD_PROJECT
```

### Clone and Configure

```bash
git clone <repo-url>
cd accelerate

# Verify environment
./setup_workshop.sh
```

### Configure Agent Credentials

**Customer Service:**
```bash
cd customer-service
cp .env.example .env
# Edit .env and set:
#   GOOGLE_CLOUD_PROJECT=your-project-id
#   GOOGLE_CLOUD_LOCATION=us-central1
#   GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

**Retail AI:**
```bash
cd ../retail-ai-location-strategy
cp .env.example .env
# Edit .env and set:
#   GOOGLE_CLOUD_PROJECT=your-project-id
#   GOOGLE_CLOUD_LOCATION=us-central1
#   GOOGLE_GENAI_USE_VERTEXAI=TRUE
#   MAPS_API_KEY=your-maps-api-key  # Required for competitor mapping
```

### Install Evaluation CLI

```bash
cd ../evaluation
uv sync
```

You're ready to run evaluations.

---

## 2. Baseline: Customer Service

The Customer Service agent is a multi-turn chatbot. We use **ADK User Sim** to generate realistic conversations because:
- It solves the "cold start" problem - no need for hand-crafted golden datasets
- It tests conversation flows with realistic multi-turn interactions
- It explores agent behavior across many scenarios automatically

### Step 2.1: Run ADK Simulator

```bash
cd customer-service

# Create eval set
uv run adk eval_set create customer_service eval_set_with_scenarios

# Add test scenarios
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json

# Run simulation (generates traces)
uv run adk eval customer_service eval_set_with_scenarios
```

This takes 2-3 minutes. You'll see the simulated conversations in real-time.

### Step 2.2: Convert Traces

```bash
cd ../evaluation

RUN_DIR=$(uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results \
  | awk -F': ' '/^Run folder:/ {print $2}')

echo "Results will be saved to: $RUN_DIR"
```

### Step 2.3: Run Evaluation

```bash
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline
```

### Step 2.4: Analyze Results

```bash
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service \
  --location global
```

### Step 2.5: Review Your Baseline

```bash
# View summary metrics
cat $RUN_DIR/eval_summary.json | head -50

# View AI-generated analysis
cat $RUN_DIR/gemini_analysis.md
```

**Key metrics to note for later comparison:**
- `multi_turn_general_quality` - Overall conversation quality
- `trajectory_accuracy` - Did the agent follow correct steps?
- `tool_use_quality` - Were tools used correctly?
- `token_usage.total_tokens` - Cost indicator

---

## 3. Baseline: Retail AI

The Retail AI agent is a single-turn pipeline that analyzes locations. We use **DIY Interactions** because:
- ADK User Sim is overkill for single-turn pipelines (no multi-turn conversation to simulate)
- Specific queries against a running agent are faster than full simulation
- DIY works against any agent URL (localhost, deployed, or remote) - not just ADK source code

> **MAPS_API_KEY Required:** The Retail AI agent uses Google Maps Places API. Without a valid `MAPS_API_KEY` in your `.env`, the competitor mapping stage will fail. Get your key from [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and enable "Places API".

### Step 3.1: Start the Agent

```bash
cd ../retail-ai-location-strategy
uv sync
make dev  # Starts on port 8502
```

**Keep this terminal running.** Open a new terminal for the next steps.

### Step 3.2: Run Interactions

```bash
cd evaluation

RUN_DIR=$(uv run agent-eval interact \
  --app-name app \
  --questions-file ../retail-ai-location-strategy/eval/eval_data/golden_dataset.json \
  --base-url http://localhost:8502 \
  --results-dir ../retail-ai-location-strategy/eval/results \
  | awk -F': ' '/^Run folder:/ {print $2}')

echo "Results will be saved to: $RUN_DIR"
```

This takes 3-5 minutes as the agent runs its full analysis pipeline.

### Step 3.3: Run Evaluation

```bash
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_app.jsonl \
  --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label baseline
```

### Step 3.4: Analyze Results

```bash
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../retail-ai-location-strategy \
  --location global
```

### Step 3.5: Review Your Baseline

```bash
cat $RUN_DIR/gemini_analysis.md
```

**Key metrics for Retail AI:**
- `general_quality` - Response quality
- `pipeline_integrity` - Did the agent actually run all stages?
- `tool_use_quality` - Were tools called correctly?
- `latency_metrics.total_latency_seconds` - Pipeline duration

You can now stop the agent in the first terminal (`Ctrl+C`).

---

## 4. Add Custom Metric

The Retail AI agent returns structured JSON responses. Let's create a custom metric that evaluates a specific field: `top_recommendation`.

This demonstrates **fine-grained evaluation** of structured outputs.

### Step 4.1: View the Existing Metrics

```bash
# View current metrics
cat ../retail-ai-location-strategy/eval/metrics/metric_definitions.json
```

Note the existing metrics: `general_quality`, `text_quality`, `trajectory_accuracy`, `tool_use_quality`, `pipeline_integrity`.

### Step 4.2: Create a New Metrics File with Your Custom Metric

Instead of modifying the original, create a new file. This lets you compare results with and without your metric.

We've already created `metric_definitions_with_recommendation.json` for you. View it:

```bash
cat ../retail-ai-location-strategy/eval/metrics/metric_definitions_with_recommendation.json | grep -A 30 recommendation_quality
```

**Key elements of the custom metric:**

```json
"recommendation_quality": {
  "metric_type": "llm",
  "agents": ["retail_location_strategy", "app"],
  "score_range": {"min": 0, "max": 5, "description": "0=Poor, 5=Excellent"},

  "dataset_mapping": {
    "prompt": {"source_column": "user_inputs"},
    "response": {"source_column": "trace_summary"},
    "top_recommendation": {"source_column": "final_response:top_recommendation"},
    "total_competitors": {"source_column": "final_response:total_competitors_found"},
    "zones_analyzed": {"source_column": "final_response:zones_analyzed"}
  },
  "template": "...{prompt}...{response}...{top_recommendation}...{total_competitors}...{zones_analyzed}..."
}
```

**Important notes:**
- `dataset_mapping` defines placeholders for the template
- `final_response:top_recommendation` extracts a nested field from the JSON response
- Every field in `dataset_mapping` must be used in the template (e.g., `{response}`)

### Step 4.3: Run Evaluation with New Metric

You can re-use your existing processed interactions - no need to restart the agent!

```bash
cd evaluation

# Use the baseline run folder from Section 3
BASELINE_RUN=../retail-ai-location-strategy/eval/results/baseline

# Create a new results folder for comparison
NEW_RUN=../retail-ai-location-strategy/eval/results/with_custom_metric
mkdir -p $NEW_RUN

# Evaluate with new metric file
uv run agent-eval evaluate \
  --interaction-file $BASELINE_RUN/raw/processed_interaction_app.jsonl \
  --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions_with_recommendation.json \
  --results-dir $NEW_RUN \
  --input-label with-custom-metric

# Analyze
uv run agent-eval analyze \
  --results-dir $NEW_RUN \
  --agent-dir ../retail-ai-location-strategy \
  --location global
```

### Step 4.4: See Your Custom Metric

```bash
cat $NEW_RUN/eval_summary.json | grep -A8 recommendation_quality
```

You should see scores like:
```json
"recommendation_quality": {
    "average": 3.33,
    "score_range": {"min": 0, "max": 5, "description": "0=Poor, 5=Excellent"}
}
```

### Step 4.5: Review Per-Question Scores

```bash
# See detailed scores and explanations
cat $NEW_RUN/question_answer_log.md
```

Example output:
- Capitol Hill coffee shop: **Score 5.0** - Specific location, evidence-based
- Indiranagar bakery: **Score 5.0** - Clear recommendation with data
- Vague "open a shop": **Score 0.0** - No recommendation provided

**Understanding the Score 0.0 for "open a shop":**

This test case (`retail_003_clarifying`) intentionally sends a vague request to test if the agent asks clarifying questions. The agent correctly responded:

> "Hello! I can help with that. To get started, I need a bit more information. First, where are you thinking of opening this shop? Second, what type of shop do you want to open?"

The metric scored 0 because:
1. `final_response` for this case is a **string** (the clarifying question), not a structured JSON
2. When accessing `final_response:top_recommendation`, it returns empty - strings don't have nested fields
3. The metric sees no recommendation and scores 0

**This is expected behavior for this test design.** To properly evaluate clarifying question scenarios, you could:
1. Create a separate metric that evaluates the `final_response` directly (as a string)
2. Or add `final_response` as another template field to give the LLM judge full context

**Key takeaways:**
- `final_response:field_name` syntax extracts nested fields from **structured JSON** responses
- For **string responses** (like clarifying questions), access the full `final_response` directly
- Design your metrics based on the response format your agent produces

---

## 5. Optimization Branches

Now apply optimization patterns and measure their impact.

### Context Engineering Principles

> "Context Engineering is the systematic management of the model's context window to maximize Signal-to-Noise Ratio, protecting the model from Context Rot."
>
> **More Context != More Intelligence**

### The Optimization Milestones

| Milestone | Branch | Optimization | Target Metric |
|-----------|--------|--------------|---------------|
| M0 | `main` | Baseline (Naive Monolith) | Establish baseline scores |
| M1 | `optimizations/01-tool-definition` | Tool Schema Hardening | `tool_use_quality` > 4.0 |
| M2 | `optimizations/02-context-compaction` | Context Compaction | Reduce context rot over turns |
| M3 | `optimizations/03-code-execution` | Offload to Python Sandbox | `input_tokens` < 4000/turn |
| M4 | `optimizations/04-functional-isolation` | Split into Sub-Agents | `trajectory_accuracy` = 5/5 |
| M5 | `optimizations/05-prefix-caching` | Prefix Caching | `cache_hit_rate` > 75% |

### The Optimization Loop

For each branch, you'll:
1. **Checkout** the optimization branch
2. **Run** the evaluation pipeline
3. **Compare** metrics with baseline
4. **Understand** what improved (and any trade-offs)

### Example: Branch 01 - Tool Hardening

```bash
# 1. Checkout the branch
git checkout optimizations/01-tool-definition
cd customer-service
uv sync

# 2. Clear previous eval data
rm -rf customer_service/.adk/eval_history/*

# 3. Run simulation
uv run adk eval customer_service eval_set_with_scenarios

# 4. Convert, Evaluate, Analyze
cd ../evaluation

RUN_DIR=$(uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results \
  | awk -F': ' '/^Run folder:/ {print $2}')

uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label optimization-01

uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service \
  --location global

# 5. Compare with baseline
cat $RUN_DIR/gemini_analysis.md
```

**What to look for:**
- `tool_use_quality` should improve (stricter schemas = fewer tool errors)
- Check `gemini_analysis.md` for specific improvements noted

### Continue with Other Branches

Repeat the process for each optimization branch:

```bash
# Branch 02
git checkout optimizations/02-context-compaction
# ... run pipeline ...

# Branch 03
git checkout optimizations/03-code-execution
# ... run pipeline ...

# Branches 04-05 (Retail AI)
git checkout optimizations/04-functional-isolation
cd retail-ai-location-strategy
# Use DIY path: make dev, then interact/evaluate/analyze

git checkout optimizations/05-prefix-caching
# ... run pipeline ...
```

### Signal Identification Cheatsheet

| Symptom | Metric to Check | Fix (Branch) |
|---------|-----------------|--------------|
| Agent invents tool parameters | `tool_use_quality` < 3.0 | 01 - Tool Hardening |
| Agent forgets earlier context | Quality drops over turns | 02 - Context Compaction |
| Agent chooses wrong tools | `trajectory_accuracy` < 3.0 | 03 - Functional Isolation |
| Token usage exploding | `input_tokens` > 10,000 | 04 - Offloading |
| High latency, low cache hits | `cache_hit_rate` < 50% | 05 - Prefix Caching |

---

## 6. Wrap-up

### What You Learned

1. **Measure** - Run evaluations to get objective metrics
2. **Identify** - Use `gemini_analysis.md` to find root causes
3. **Optimize** - Apply Context Engineering patterns
4. **Verify** - Compare before/after metrics

### Key Files to Remember

| File | Purpose |
|------|---------|
| `eval_summary.json` | Aggregated metrics (the numbers) |
| `gemini_analysis.md` | AI root cause analysis (the why) |
| `question_answer_log.md` | Detailed Q&A transcript |

### Next Steps

1. **Customize metrics** - Add metrics specific to your agent's domain
2. **Add scenarios** - Create conversation scenarios for edge cases
3. **Integrate CI/CD** - Run evaluations on every PR
4. **Apply to your agents** - See [REFERENCE.md](REFERENCE.md) for adapting to external agents

---

## Quick Reference

### Full Pipeline: Customer Service (ADK User Sim)

```bash
# === From customer-service folder ===
cd customer-service

# Clear previous data
rm -rf customer_service/.adk/eval_history/*
rm -f customer_service/*.evalset.json

# Create eval set and add scenarios
uv run adk eval_set create customer_service eval_set_with_scenarios
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json

# Run simulation
uv run adk eval customer_service eval_set_with_scenarios

# === From evaluation folder ===
cd ../evaluation

# Convert traces
RUN_DIR=$(uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results \
  | awk -F': ' '/^Run folder:/ {print $2}')

# Evaluate
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR

# Analyze
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../customer-service \
  --location global

# View results
cat $RUN_DIR/eval_summary.json | head -50
cat $RUN_DIR/gemini_analysis.md
```

### Full Pipeline: Retail AI (DIY Interactions)

```bash
# === Terminal 1: Start the agent ===
cd retail-ai-location-strategy
uv sync
make dev  # Keep running

# === Terminal 2: Run evaluation ===
cd evaluation

# Run interactions
RUN_DIR=$(uv run agent-eval interact \
  --app-name app \
  --questions-file ../retail-ai-location-strategy/eval/eval_data/golden_dataset.json \
  --base-url http://localhost:8502 \
  --results-dir ../retail-ai-location-strategy/eval/results \
  | awk -F': ' '/^Run folder:/ {print $2}')

# Evaluate
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_app.jsonl \
  --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR

# Analyze
uv run agent-eval analyze \
  --results-dir $RUN_DIR \
  --agent-dir ../retail-ai-location-strategy \
  --location global

# View results
cat $RUN_DIR/gemini_analysis.md
```

### Re-running After Changes (Hillclimbing)

**Customer Service:**
```bash
cd customer-service
rm -rf customer_service/.adk/eval_history/*
uv run adk eval customer_service eval_set_with_scenarios
cd ../evaluation
# ... convert, evaluate, analyze (same commands as above)
```

**Retail AI:**
```bash
# Stop agent (Ctrl+C), make changes, restart
cd retail-ai-location-strategy && make dev
# In another terminal, run interact → evaluate → analyze
```

### More Information

See [REFERENCE.md](REFERENCE.md) for:
- Complete CLI reference with all flags
- All metric types explained
- Creating custom simulations
- Troubleshooting guide
- Adapting the framework for your own agents
- Understanding optimization trade-offs

---

## Repository Structure

```
accelerate/
├── README.md                      # This file - workshop guide
├── REFERENCE.md                   # Deep dive - CLI, metrics, customization
├── setup_workshop.sh              # Environment verification
│
├── customer-service/              # Agent A (multi-turn, reliability)
│   ├── customer_service/          # Agent code
│   └── eval/                      # Scenarios, metrics, results
│
├── retail-ai-location-strategy/   # Agent B (pipeline, scale)
│   ├── app/                       # Agent code
│   └── eval/                      # Golden dataset, metrics, results
│
└── evaluation/                    # Shared evaluation CLI
    └── src/evaluation/cli/        # agent-eval commands
```

---

## Critical Requirement

```
+------------------------------------------------------------------+
|  You MUST use Vertex AI for the evaluation pipeline to work.     |
|                                                                   |
|  Set: GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION             |
|  Do NOT use: GOOGLE_API_KEY                                       |
|                                                                   |
|  API keys bypass Vertex AI, resulting in empty metrics.          |
+------------------------------------------------------------------+
```

---

## Additional Resources

- [REFERENCE.md](REFERENCE.md) - Complete CLI and customization guide
- [ADK Documentation](https://google.github.io/adk-docs/)
- [ADK User Simulation](https://google.github.io/adk-docs/evaluate/user-sim/)
- [Vertex AI Evaluation](https://cloud.google.com/vertex-ai/docs/generative-ai/evaluation/)
