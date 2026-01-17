# Workshop Iteration Log: Retail Location Strategy Agent

## 1. Metrics Comparison Table

| Metric Category | Metric Name | Baseline (v0) | Iteration 1 | Iteration 2 | Delta (v0 ⮕ v1) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy (Judge)** | Strategic Rec Quality (1-5) | - | - | - | - |
| | Tool Use Quality (0-5) | - | - | - | - |
| | Trajectory Accuracy (0-5) | - | - | - | - |
| **Fidelity (Judge)** | State Variable Fidelity (1-5) | - | - | - | - |
| **Trust (Judge)** | Hallucinations (0-1) | - | - | - | - |
| | Safety (0-1) | - | - | - | - |
| **Scale (Det.)** | Avg Input Tokens | - | - | - | - |
| | Avg Turn Latency (s) | - | - | - | - |
| | KV-Cache Hit Rate (%) | - | - | - | - |
| | Total Cost ($) | - | - | - | - |

---

## 2. Iteration History

### Iteration 0: Baseline (Naive Monolith)
*   **Optimization Path:** N/A (Initial State)
*   **Status:** Pending Baseline Run.
*   **Hypothesis:** The agent uses a large amount of tokens due to raw JSON injection from tools. Latency will be high.
