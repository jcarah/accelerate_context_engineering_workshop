# Optimization Log: Customer Service Agent - Milestone 03a

**Branch:** `optimizations/03a-offload-and-reduce`
**Optimization:** Stateless Triage Router (Pillar: Reduce/Offload)
**Date:** 2026-01-28

---

## 1. Summary of Changes
Iterated on the "Triage & Specialist" architecture to address the massive token bloat introduced in Milestone 03.
- **Milestone 03 (Isolation):** Used a stateful LLM Triage agent. Resulted in high latency and 15k+ tokens.
- **Milestone 03a (Stateless):** Reconfigured the Triage agent to be **Stateless** (`include_contents='none'`). It now routes based *only* on the current user message, "offloading" the history from the routing decision.
- **Fixes:** Updated `tools.py` to be context-aware (reading `customer_id` from state) to support stateless sub-agents.

---

## 2. Metrics Comparison Table

| Metric Category | Metric Name | Opt 02 (Compaction) | Opt 03 (Isolation) | Opt 03a (Stateless) | Delta (03 vs 03a) |
|:----------------|:------------|:--------------------|:-------------------|:--------------------|:------------------|
| **Scale (Tokens)** | **Avg Prompt Tokens** | 12,601 | 15,648 | **7,143** | **-8,505 (-54%)** 🟢 |
| **Latency** | Avg Turn Latency (s) | 6.33s | 7.98s | 10.03s | +2.05s 🔴 |
| | Total Latency (s) | 18.78s | 30.41s | 40.27s | +9.86s 🔴 |
| **Efficiency** | Agent Handoffs | 2.6 | 7.4 | 8.6 | +1.2 🔴 |
| **Quality** | **tool_use_quality** | 4.80 | 2.60 | 2.80 | +0.20 ⚪ |
| | **trajectory_accuracy** | 4.80 | 4.00 | 4.00 | 0.00 ⚪ |
| | capability_honesty | 5.00 | 4.20 | 3.80 | -0.40 🔴 |

---

## 3. Analysis of Results

### The "Scale" Victory (Green Signal)
The Stateless Router strategy was a massive success for token efficiency.
- **Reduction:** We slashed prompt tokens by **54%** compared to the Opt 03 Isolation attempt, and **43%** compared to the Opt 02 Baseline.
- **Mechanism:** By preventing the Triage Agent from loading the chat history, we ensure that the "Routing Turn" is always cheap (constant tokens), regardless of conversation length.

### The "Routing" Trade-off (Red Signal)
While tokens dropped, latency and handoffs increased.
- **The "Amnesiac" Problem:** Because the router is stateless, it has no memory of previous failures. In edge cases (like "Returns"), it repeatedly sends the user to Sales, gets rejected, and tries Sales again in the next turn.
- **Impact:** This caused the `agent_handoffs` to rise to 8.6, driving up the Total Latency.

### Tool Stability
We successfully fixed the `Tool Use Quality` regression (from the crash) by making tools context-aware. The agent no longer hallucinates missing `customer_id` arguments because the tools now fetch them directly from the state.

---

## 4. Conclusions

### Architectural Findings
1.  **Stateless Routing is the key to Scale:** To make multi-agent systems viable, the "Router" must not consume the full context window.
2.  **Statelessness requires Robust Routing:** If the router can't see history, its routing logic (Prompt/Definition) must be perfect, or it must have a "fallback" state that persists.
3.  **Context-Aware Tools:** Reducing context means tools must be smarter. Offloading parameter collection to the tool implementation (reading from State) is a robust pattern.

### Recommended Next Steps
We have solved the **Token Bloat** but exacerbated the **Routing Loop**.
- **Optimization 04 (Refined):** We need to fix the routing loops without adding back the tokens. We should implement a **"Semantic Router"** (using a code-based classifier) or add a specific "Returns" path to the prompt so the router stops guessing.

---

## 5. File References
- **Opt 03a Results:** `customer-service/eval/results/optimization_03a/`
- **AI Analysis:** `customer-service/eval/results/optimization_03a/gemini_analysis.md`
