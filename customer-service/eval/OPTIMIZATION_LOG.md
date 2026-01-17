# Workshop Iteration Log: Customer Service Agent

## 1. Metrics Comparison Table

| Metric Category | Metric Name | Baseline (v0) | Iteration 1 | Iteration 2 | Delta (v0 vs. Current) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Quality (Judge)** | Capability Honesty (1-5) | 3.4 | - | - | - |
| | Tool Use Quality (1-5) | 3.6 | - | - | - |
| | Trajectory Accuracy (1-5) | 3.8 | - | - | - |
| **Trust (Judge)** | Hallucinations (0-1) | 0.96 | - | - | - |
| | Safety (0-1) | 1.0 | - | - | - |
| | Rubric Tool Quality (0-1) | 0.9 | - | - | - |
| | Rubric Final Resp Quality (0-1) | 1.0 | - | - | - |
| **Simulator** | User Sim Quality (0-1) | N/A* | - | - | - |
| **Scale (Det.)** | Avg Input Tokens | 22,275 | - | - | - |
| | Avg Turn Latency (s) | 6.21s | - | - | - |
| | KV-Cache Hit Rate (%) | 0.0% | - | - | - |
| | Reasoning Ratio (%) | 67.1% | - | - | - |
| | Estimated Cost (USD) | $0.00** | - | - | - |

*\*Simulator quality failed to record in v0 due to library version mismatch.*
*\*\*Estimated cost reflects a known reporting bug in v0 calculation logic.*

---

## 2. Iteration History

### Iteration 0: Baseline (Naive Monolith)
*   **Optimization Path:** N/A (Initial State)
*   **Diagnostic Signals:**
    *   **Signal 1 (Hallucination):** `capability_honesty` failed (0.0) in Discount Approval. Agent promises discount application despite tool being read-only.
    *   **Signal 2 (Trajectory Noise):** `tool_use_quality` low (2.0) in Cart Scenario. Agent ignores negative constraints ("No cart check") and executes tools prematurely.
    *   **Signal 3 (Scale):** 0% Cache Hit Rate indicates Pillar 5 (Cache) is inactive, driving up latency and potential cost.
*   **Reasoning:** The agent lacks strict functional boundaries. The single "Root Agent" prompt is too broad, leading to inference-time logic drifting and "capability hallucination" where the model assumes tool side-effects that do not exist in the code.

### Iteration 1: [PENDING]
*   **Optimization Path:** Optimization 01: Tool Schema Hardening
*   **Target Signal:** Signal 1 (Hallucination)
*   **Hypothesis:** Replacing generic dictionary descriptions with strict Pydantic models and explicit "Known Limitations" will force the model to acknowledge it cannot apply discounts, raising `capability_honesty`.