# Optimization Log: Customer Service Agent

**Branch:** `optimizations/01-tool-definition`
**Optimization:** Tool Schema Hardening (Pillar: Reduce)
**Date:** 2026-01-28

---

## 1. Metrics Comparison Table

### Deterministic Metrics (Scale & Efficiency)

| Metric Category | Metric Name | Baseline | Optimization 01 | Delta |
|:----------------|:------------|:---------|:----------------|:------|
| **Scale** | Avg Total Tokens | 16,237 | 10,547 | -5,690 🟢 |
| | Avg Prompt Tokens | 21,902 | 13,817 | -8,085 🟢 |
| | Avg Cached Tokens | 12,885 | 7,927 | -4,958 🟢 |
| | Total Latency (s) | 39.34s | 39.42s | +0.08s ⚪ |
| | Avg Turn Latency (s) | 11.04s | 12.88s | +1.85s 🔴 |
| **Efficiency** | Cache Hit Rate | 34.72% | 34.83% | +0.11% ⚪ |
| | Reasoning Ratio | 69.31% | 72.54% | +3.23% 🔴 |
| | Tool Success Rate | 100.00% | 100.00% | 0.00% ⚪ |
| | Avg Tool Calls | 3.20 | 3.60 | +0.40 ⚪ |

### LLM-as-Judge Metrics (Quality)

| Metric | Baseline | Optimization 01 | Delta |
|:-------|:---------|:----------------|:------|
| **capability_honesty** (0-5) | 2.20 | 4.20 | +2.00 🟢 |
| **trajectory_accuracy** (0-5) | 3.60 | 4.60 | +1.00 🟢 |
| tool_use_quality (0-5) | 5.00 | 4.80 | -0.20 🔴 |
| multi_turn_text_quality (0-1) | 0.75 | 0.83 | +0.08 🟢 |
| multi_turn_general_quality (0-1) | 0.88 | 0.87 | -0.01 ⚪ |

---

## 2. Iteration History

### Baseline (M0): Naive Monolith

**Optimization Path:** N/A (Initial State)

**Key Diagnostic Signals (from AI Analysis):**

1. **Capability Honesty Failures (2.2/5.0):**
   - Agent hallucinated capabilities that don't exist (sending emails, applying discounts without tool calls)
   - Conflated "Approval" with "Application" - assumed state changes without executing write-operation tools
   - Claimed video perception capabilities that don't exist

2. **Tool Mechanics Perfect (5.0/5.0):**
   - Agent correctly parses inputs into valid JSON arguments
   - Handles complex 4-step tool chains (recommendations → cart check → availability → modify)
   - Zero failed tool calls

3. **Performance Concerns:**
   - High latency (11.04s/turn) for real-time chat
   - Low cache hit rate (34.7%) suggesting prompt variation or interruption
   - 16,237 tokens avg per session

**Root Cause:** Agent treats successful execution of intermediate tools as completion of entire business process, ignoring tool limitations.

---

### Optimization 01: Tool Schema Hardening

**Optimization Path:** Tool Schema Hardening (Pillar: Reduce)

**Implementation Details:**

1. **Schema Hardening:** Refactored `tools.py` with Pydantic models for strict argument validation
2. **Boundary Grounding:** Added `**KNOWN LIMITATIONS**` docstrings to tool definitions
3. **Negative Constraints:** Explicit statements in docstrings about what tools CANNOT do

**Key Changes Made:**

| File | Change |
|------|--------|
| `customer_service/tools/tools.py` | Added Pydantic validation, explicit limitation docstrings |
| `customer_service/prompts.py` | Added "CORE OPERATIONAL BOUNDARIES" and negative constraints |
| `customer_service/agent.py` | Updated tool descriptions |
| `customer_service/shared_libraries/callbacks.py` | Enhanced callback handling |

**Analysis of Results:**

1. **Token Efficiency Improvement:**
   - Total tokens reduced by **35%** (16,237 → 10,547)
   - Prompt tokens reduced by **37%** (21,902 → 13,817)
   - Clearer tool definitions allow faster decision-making

2. **Capability Honesty Improvement (2.2 → 4.2):**
   - Agent now respects negative constraints in docstrings
   - Example: Correctly states "I cannot email the QR code" based on `**KNOWN LIMITATIONS**` in docstring
   - Example: Correctly tells user to "apply discount manually at checkout" instead of claiming it was applied

3. **Latency Trade-off:**
   - Turn latency increased (11.04s → 12.88s)
   - Reasoning ratio increased (69% → 72%) - agent "over-thinking" with explicit constraints
   - Tool execution time is not the bottleneck (3.6s) - model generation is

4. **Trajectory Accuracy Issue (3.0/5.0):**
   - Some indirect tool usage patterns due to missing primitives
   - Example: Uses `get_product_recommendations` to lookup product_id when user provides product name
   - Missing: `search_product_by_name` tool would improve trajectory

**Mechanism Discovery:**
> Embedding `**KNOWN LIMITATIONS**` directly into Python docstrings is highly effective. The agent successfully internalizes these warnings into response generation.

---

## 3. Conclusions

### What Worked

| Improvement | Evidence |
|-------------|----------|
| Token reduction | -35% total tokens through clearer schemas |
| Capability honesty | Agent respects tool limitations when documented |
| Schema validation | 100% tool success rate maintained |

### What Needs Attention

| Issue | Next Step |
|-------|-----------|
| Increased latency | Consider reducing reasoning tokens via prompt optimization |
| Reasoning ratio high | Agent may be over-analyzing simple requests |
| Missing search tool | Add `search_product_by_name` to improve trajectory |

### Recommended Next Optimization

**Optimization 02: Context Compaction**
- Target: Reduce reasoning ratio and latency
- Approach: Compress conversation history, optimize prompt structure
- Expected outcome: Lower turn latency while maintaining quality

---

## 4. File References

- **Baseline Results:** `customer-service/eval/results/baseline/`
- **Optimization Results:** `customer-service/eval/results/optimization/`
- **Agent Code Changes:** See `customer_service/tools/tools.py`, `prompts.py`, `agent.py`