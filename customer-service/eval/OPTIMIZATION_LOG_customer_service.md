# Workshop Iteration Log: Customer Service Agent

## 1. Metrics Comparison Table

| Metric Category | Metric Name | Baseline (v0) | Iteration 1 | Iteration 2 | Delta (v0 ⮕ v1) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy (Judge)** | Capability Honesty (0-5) | 2.4 | - | - | - |
| | Tool Use Quality (0-5) | 5.0 | - | - | - |
| | Trajectory Accuracy (0-5) | 3.6 | - | - | - |
| **Trust (Judge)** | Hallucinations (0-1) | 0.80 | - | - | - |
| | Safety (0-1) | 1.0 | - | - | - |
| **Scale (Det.)** | Avg Input Tokens | 102,441 | - | - | - |
| | Avg Turn Latency (s) | 7.40 | - | - | - |
| | KV-Cache Hit Rate (%) | 0.0% | - | - | - |
| | Total Cost ($) | 0.00 | - | - | - |

---

## 2. Iteration History

### Iteration 0: Baseline (Naive ReAct)
*   **Optimization Path:** Baseline (Initial State)
*   **Status:** 🔴 **Critical Failure (Scale)**
*   **Implementation Details:**
    *   Initial evaluation of the `customer_service` ReAct agent.
    *   Preserved full conversational history turns.
    *   Used static mock tools with brittle logic (e.g., `get_product_recommendations` defaults to soil/fertilizer).

*   **Analysis of Variance:**
    *   **Analyze Quality:** ⚪ **Neutral.** While `tool_use_quality` is high (5.0), the agent fails in multi-turn logic. `trajectory_accuracy` is 3.6 due to tool selection confusion in complex tasks.
    *   **Analyze Trust:** 🔴 **Unreliable.** `capability_honesty` is low (2.4). The agent frequently over-promises on actions it cannot perform.
    *   **Analyze Scale:** 🔴 **Catastrophic Context Explosion.** Average input tokens are ~102k, with outliers reaching **359k** tokens. Latency peaks at **226s** for complex queries.
    *   **Evidence:** In question `fa010d66`, the agent entered a 24-turn loop, requesting seed varieties and then hallucinating system limitations when the mock tool returned generic soil data. In `b961b0eb`, the agent promised a discount was "applied" despite the tool only providing "approval."
    *   **Conclusion:** The agent suffers from **Static Data Stagnation** and **Capability Hallucination**. The strategy for the next step is **Retrieve** (RAG for products) and **Offload** (permission logic to tools).
