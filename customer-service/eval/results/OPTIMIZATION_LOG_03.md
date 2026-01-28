# Optimization Log: Customer Service Agent - Milestone 03

**Branch:** `optimizations/03-functional-isolation`
**Optimization:** Functional Isolation (Pillar: Isolate)
**Date:** 2026-01-28

---

## 1. Summary of Changes
Refactored the monolithic agent into a **Triage & Specialist** architecture to improve modularity and isolate toolsets.
- **Triage Agent (Root):** Routes user intent to specialists; carries no functional tools.
- **Sales Agent (Worker):** Isolated to product recommendations, cart management, and discounts.
- **Fulfillment Agent (Worker):** Isolated to scheduling, care instructions, and human expert links.
- **Routing Repair:** Hardened the Triage prompt with "Anti-Ping-Pong" logic and Chain-of-Thought routing to prevent recursive handoffs.

---

## 2. Metrics Comparison Table

| Metric Category | Metric Name | Optimization 02 (Compaction) | Optimization 03 (Isolation) | Delta |
|:----------------|:------------|:-----------------------------|:----------------------------|:------|
| **Latency** | Avg Turn Latency (s) | 6.33s | 7.98s | +1.65s 🔴 |
| | Total Latency (s) | 18.78s | 30.41s | +11.63s 🔴 |
| **Scale** | Avg Prompt Tokens | 12,601 | 15,648 | +3,047 🔴 |
| **Efficiency** | Reasoning Ratio | 74.36% | 76.45% | +2.09% 🔴 |
| | Agent Handoffs | 2.6 | 7.4 | +4.8 🔴 |
| **Quality** | **tool_use_quality** (0-5) | 4.80 | 2.60 | -2.20 🔴 |
| | **trajectory_accuracy** (0-5) | 4.80 | 4.00 | -0.80 🔴 |
| | capability_honesty (0-5) | 5.00 | 4.20 | -0.80 🔴 |

---

## 3. Analysis of Results

### The Cost of Modularity
The transition to a multi-agent "Triage & Worker" architecture introduced a significant performance regression. While we successfully isolated concerns, we added a "Routing Tax":
- **Latency Increase:** Every user request now requires at least one extra LLM turn for Triage, adding ~1.6s to every turn and nearly 12s to total resolution time.
- **Token Bloat:** Total prompt tokens increased by 24% because the "handoff" events duplicate context and descriptions between agents.

### Diagnosis: The "Missing Intent" Death Spiral
The primary driver of the low `tool_use_quality` (2.6) and high handoffs (7.4) is the system's inability to handle intents that fall outside of Sales or Fulfillment.
- **Evidence:** In the "Return Item" case (Question `a7646beb`), the Triage agent entered an 11-turn loop trying to force a "Returns" request into the Sales or Fulfillment buckets.
- **Root Cause:** Without a "Generalist" fallback or a "Returns Specialist," the Triage agent defaults to its only available tools (transferring to existing agents), who then transfer back.

### Quality Findings
- **Trajectory Accuracy (4.0):** Despite the loops, the LLM Judge recognized that the specialists followed their internal protocols perfectly once they were finally reached.
- **Safety:** The isolation is effective; the Sales agent never attempted to use Fulfillment tools, even when the user was confused.

---

## 4. Conclusions

### What Worked
- **Modularity:** The codebase is now cleaner and safer. Functions are strictly bound to specific agents.
- **Specialist Performance:** Worker agents perform highly specific tasks with high text quality (0.96).

### What Failed
- **Routing Efficiency:** The Triage agent is too heavy for simple requests and too fragile for edge cases. 
- **Tool Brittleness:** The workers lack "lookup" tools (e.g., Name-to-ID), forcing them to refuse requests that they theoretically have the knowledge to solve.

### Recommended Next Optimization
**Optimization 04: Offload & Reduce**
We must address the regressions by moving logic out of the LLM:
1.  **Offload Routing:** Implement a deterministic router or a much smaller model for the Triage step.
2.  **Dynamic Toolsets:** Instead of passing ALL tool definitions in every prompt (15k tokens), use a `Toolset` to retrieve only the tools relevant to the active specialist.

---

## 5. File References
- **Optimization 03 Results:** `customer-service/eval/results/20260128_212033/`
- **AI Analysis:** `customer-service/eval/results/20260128_212033/gemini_analysis.md`
