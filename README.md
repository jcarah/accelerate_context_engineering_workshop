# Branch 01: Tool Schema Hardening

**Optimization Focus:** Reduce hallucinated capabilities through stricter tool definitions

---

## What You'll Do on This Branch

In this optimization, we tackle a common agent problem: **the agent lies about what it can do**.

The baseline agent has a `capability_honesty` score of just 2.2/5 - it claims to send emails, apply discounts, and perform actions that its tools don't actually support.

The fix? **Tool Schema Hardening** - adding explicit limitations to tool docstrings so the model knows what it *cannot* do.

---

## Step 1: Explore the Changes

Before running evaluation, take a moment to see what was changed in the agent code.

### 1.1 View the Code Diff

```bash
# See all files changed from main
git diff main...HEAD --stat

# See specific tool changes
git diff main...HEAD -- customer-service/customer_service/tools/tools.py
```

### 1.2 Key Changes to Look For

Open `customer-service/customer_service/tools/tools.py` and look for:

1. **Pydantic Models** - Strict type validation for tool arguments
2. **`KNOWN LIMITATIONS`** - Explicit statements in docstrings about what the tool CANNOT do
3. **Negative Constraints** - Clear boundaries for the model

Example from the code:
```python
"""
...
**KNOWN LIMITATIONS:**
- Cannot send emails
- Cannot apply discounts without user confirmation
- Does not have access to external systems
"""
```

### 1.3 Prompt Changes

```bash
git diff main...HEAD -- customer-service/customer_service/prompts.py
```

Look for "CORE OPERATIONAL BOUNDARIES" section added to the system prompt.

---

## Step 2: Run Evaluation

Now run the evaluation to see if the changes improved the metrics.

### 2A: Run Interactions

```bash
cd customer-service
uv sync

# Clear previous evaluation data
rm -rf customer_service/.adk/eval_history/*
rm -f customer_service/*.evalset.json

# Create eval set and add scenarios
uv run adk eval_set create customer_service eval_set_with_scenarios
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json

# Run the simulation
uv run adk eval customer_service eval_set_with_scenarios
```

### 2B: Run Evaluation

```bash
cd ../evaluation

# Convert traces
uv run agent-eval convert \
  --agent-dir ../customer-service/customer_service \
  --output-dir ../customer-service/eval/results/my_optimization_01

# Run metrics
uv run agent-eval evaluate \
  --interaction-file ../customer-service/eval/results/my_optimization_01/raw/processed_interaction_sim.jsonl \
  --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
  --results-dir ../customer-service/eval/results/my_optimization_01 \
  --input-label optimization-01
```

### 2C: Analyze Results

```bash
uv run agent-eval analyze \
  --results-dir ../customer-service/eval/results/my_optimization_01 \
  --agent-dir ../customer-service \
  --location global
```

---

## Step 3: Review Results

> **Note on Non-Determinism:** LLM-as-judge metrics (like `capability_honesty`, `trajectory_accuracy`) are inherently non-deterministic. Your results may differ from the pre-computed values below due to the probabilistic nature of both the agent and the evaluation model. This is expected - focus on the *direction* of change (improvement vs regression) rather than exact numbers.

---

### Option A: If You Ran the Evaluation

Compare your results against the baseline:

```bash
# View your results
cat ../customer-service/eval/results/my_optimization_01/gemini_analysis.md

# View baseline for comparison
cat ../customer-service/eval/results/baseline/eval_summary.json | head -60
```

**What to look for:**
- Did `capability_honesty` improve? (Baseline was ~2.2/5)
- Did `trajectory_accuracy` improve? (Baseline was ~3.6/5)
- Did `token_usage.prompt_tokens` decrease? (Baseline was ~22,000)

Note the deltas you observe - they may differ from our pre-computed results but should trend in the same direction.

---

### Option B: Following Along (Pre-Computed Results)

If you're following the presentation without running commands, here are our pre-computed results:

**Key Metrics Comparison:**

| Metric | Baseline | Optimization 01 | Delta |
|--------|----------|-----------------|-------|
| `capability_honesty` | 2.2/5 | 4.2/5 | +2.0 |
| `trajectory_accuracy` | 3.6/5 | 4.6/5 | +1.0 |
| `token_usage.prompt_tokens` | ~22,000 | ~14,000 | -37% |
| `latency_metrics.avg_turn_latency` | 11.0s | 12.9s | +1.9s |

**View full pre-computed results:**

```bash
cat ../customer-service/eval/results/optimization/eval_summary.json | head -60
cat ../customer-service/eval/results/OPTIMIZATION_LOG.md
```

---

## Step 4: Understand the Optimization Log

We've prepared a detailed analysis of the optimization. Read through it to understand the changes and their impact:

```bash
cat ../customer-service/eval/results/OPTIMIZATION_LOG.md
```

### Key Insights (Summary)

1. **What Worked:**
   - Token usage dropped 35% due to clearer tool definitions
   - Agent now correctly says "I cannot email the QR code" instead of lying
   - 100% tool success rate maintained

2. **Trade-offs Observed:**
   - Turn latency increased slightly (11s → 13s)
   - Reasoning ratio increased (agent "over-thinking")

3. **Mechanism Discovery:**
   > Embedding `**KNOWN LIMITATIONS**` directly into Python docstrings is highly effective. The agent successfully internalizes these warnings into response generation.

---

## Step 5: Think Through It

Before moving to the next branch, consider these questions:

1. **Why did capability_honesty improve?**
   - The agent now has explicit constraints in tool docstrings
   - It can reference what it *cannot* do, not just what it *can* do

2. **Why did latency increase slightly?**
   - More reasoning tokens as the agent evaluates constraints
   - Trade-off: slower but more honest

3. **What's still missing?**
   - Agent sometimes uses workaround tools (e.g., `get_product_recommendations` to find a product ID)
   - A dedicated `search_product_by_name` tool would improve trajectory accuracy

---

## Step 6: Next Steps

You've completed the Tool Schema Hardening optimization!

**Continue to Branch 02: Context Compaction**

```bash
git checkout optimizations/02-context-compaction
cat README.md
```

Branch 02 addresses the latency and reasoning ratio issues observed in this optimization by compressing conversation history.

---

## Quick Reference

### Files Changed in This Branch

| File | What Changed |
|------|--------------|
| `customer_service/tools/tools.py` | Added Pydantic validation, `KNOWN LIMITATIONS` docstrings |
| `customer_service/prompts.py` | Added "CORE OPERATIONAL BOUNDARIES" section |
| `customer_service/agent.py` | Updated tool descriptions |

### Results Locations

| What | Where |
|------|-------|
| Baseline results | `customer-service/eval/results/baseline/` |
| Pre-computed optimization results | `customer-service/eval/results/optimization/` |
| Your results | `customer-service/eval/results/my_optimization_01/` |
| Optimization log | `customer-service/eval/results/OPTIMIZATION_LOG.md` |

### Need Help?

See [REFERENCE.md](REFERENCE.md) on the main branch for:
- Complete CLI reference
- Metrics glossary
- Troubleshooting guide
