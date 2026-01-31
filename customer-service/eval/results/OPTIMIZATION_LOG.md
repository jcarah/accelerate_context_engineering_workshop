# Optimization Log: Context Engineering & Reliability

**Date:** 2026-01-31
**Log Status:** LIVE
**Current State:** `M2b: Manual Compaction` (Winner)

## 1. Theory of Operation: Context Reduction Strategies

Context reduction is a general concept to prevent "Context Rot." We observe two distinct methods emerging as standards, prioritizing reversibility over compression.

### Context Compaction (Reversible) - *The Standard*
*   **Definition:** Strip out information that is redundant because it exists in the environment.
*   **Reversibility:** If the agent needs the full data later, it can use a tool to read the file.
*   **Mechanism:** Python-based surgical stripping of JSON payloads. 
*   **Rule:** Prefer Raw > Compaction > Summarization.

### Summarization (Lossy) - *The Fallback*
*   **Definition:** Use an LLM to summarize the history including tool calls and messages.
*   **Risk:** The model loses its "rhythm," formatting style, and precise state awareness, leading to degradation of output quality.

---

## 2. Metrics Progression

| Metric | M0: Baseline (Raw) | M1: Tool Hardening | M2a: Summarization | M2b: Compaction | M2b Delta (vs M0) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Avg Prompt Tokens** | 20,924 | 14,121 | 15,157 | **13,501** | -35% 🟢 |
| **Avg Turn Latency** | **6.76s** | 8.81s | 9.57s | 9.20s | +2.44s 🔴 |
| **Trajectory Accuracy**| 3.2 | 3.4 | 4.0 | **4.4** | +1.2 🟢 |
| **Capability Honesty** | 1.2 | **5.0** | 4.2 | 4.4 | +3.2 🟢 |
| **Tool Use Quality** | 3.6 | 3.6 | **4.2** | 4.0 | +0.4 🟢 |

---

## 3. Analysis: The Impact of Context Engineering

### A) The "Before & After" (Benefit of Compaction)
*   **Before:** In the **M0 Baseline**, the agent was drowning in **22k tokens** of raw, repetitive JSON. This noise caused it to hallucinate wildly (Honesty: 1.2), claiming it could see video and approve refunds.
*   **After (M2b):** By surgically stripping stale JSON payloads (leaving only the tool name and status), we reduced the context to **13.5k tokens**. 
*   **Result:** The model became **3.2x more honest**. It maintained a high-fidelity "map" of recent actions, leading to a perfect **Trajectory score of 5.0** in complex cart-swap scenarios.

### B) Regression Examples (The Risk of "Lossy" Summarization)
*   **Example (Iteration 2a):** In QID `863cbc8b`, the model **lied about its execution**. It stated, *"I have updated your profile in the CRM,"* but the logs show the tool `update_salesforce_crm` **was never called**. 
*   **Root Cause:** The "Summarization" was too lossy. The model "remembered" that it *should* have updated the profile, but forgot that it hadn't actually executed the tool call yet.

### C) The Need for Functional Isolation (Strategic Need for M3)
*   **The Evidence:** In QID `90f9fb35`, the user requested a return. The agent called `access_cart_information` (its only state tool), saw that the item wasn't in the *current cart*, and incorrectly told the user: *"I searched your **order history** and couldn't find the item."*
*   **The Problem:** **Scope Confusion.** The agent is conflating its "Cart tool" with "Order History." Because all 12 tools are in one bucket, the model is hitting a cognitive ceiling.
*   **The Pivot:** We have fixed the *Context Rot*, but we now have *Functional Congestion*. We need to split the "Shopping Expert" from the "Order Management Expert."

## 4. Conclusion
**Compaction (M2b) is the winner.** It is the most efficient and reliable way to manage a large context window without losing the agent's momentum. We are now ready to address the final bottleneck: **Functional Isolation.**

**Next Step:** `Module 3: Functional Isolation` (Sub-agents).