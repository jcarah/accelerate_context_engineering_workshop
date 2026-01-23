# Workshop Iteration Log: Retail Location Strategy Agent

## 1. Metrics Comparison Table

| Metric Category | Metric Name | Baseline (v0) | Iteration 1 (Offload) | Delta (v0 ⮕ v1) |
| :--- | :--- | :--- | :--- | :--- |
| **Strategy (Judge)** | Strategic Rec Quality (0-1) | 0.08 | **0.14** | +0.06 ⚪ |
| | Tool Use Quality (0-5) | 5.0 | **5.0** | 0.0 ⚪ |
| | Trajectory Accuracy (0-5) | 4.0 | **4.0** | 0.0 ⚪ |
| | Pipeline Integrity (0-5) | 2.0 | **2.0** | 0.0 🔴 |
| **Trust (Judge)** | Hallucinations (0-1) | 1.0 | **1.0** | 0.0 ⚪ |
| | Safety (0-1) | 1.0 | **1.0** | 0.0 ⚪ |
| **Scale (Det.)** | Avg Input Tokens | 135,448 | **53,515** | -81,933 🟢 |
| | Avg Turn Latency (s) | 325.48s | **197.89s** | -127.59s 🟢 |
| | KV-Cache Hit Rate (%) | 0.0% | **13.15%** | +13.15% 🟢 |

---

## 2. Iteration History

### Iteration 0: Baseline (Naive Monolith)
*   **Optimization Path:** Baseline (Initial State)
*   **Status:** 🔴 **Critical Failure**
*   **Implementation Details:**
    *   Unoptimized `SequentialAgent` pipeline.
    *   Tools return raw JSON directly into the context window.
    *   No caching or event compaction.
*   **Analysis of Variance:**
    *   **Context Saturation:** Extreme token usage (~135k) caused massive latency (~325s).
    *   **Integrity Failure:** The agent failed to perform analysis, often returning only meta-comments about generated images because the context was flooded.
    *   **Conclusion:** The agent suffered from severe context saturation.

### Iteration 1: Offload & Minify Data
*   **Optimization Path:** Optimization 01: Offload Data (Pillar: Reduce)
*   **Status:** 🟠 **Partial Success (Scale Win, Integrity Fail)**
*   **Implementation Details:**
    1.  **Offload:** Modified `search_places` tool in `places_search.py` to save `competitors.json` to disk/artifacts instead of returning the full payload.
    2.  **Minify:** Updated `pipeline_callbacks.py` to read the artifact and inject a *minified* preview into the context state.
    3.  **Instruction Update:** Updated `GapAnalysis` agent to load the full data from disk using `json.loads(COMPETITORS_JSON)` for code execution.
*   **Analysis of Variance:**
    1.  **Scale (Efficiency):** **Massive Win.** Input tokens dropped by **60%** (135k ⮕ 53k) and latency improved by **~40%** (325s ⮕ 197s). The "Offload" strategy successfully decongested the prompt.
    2.  **Integrity (Reliability):** **Persistent Failure.** `pipeline_integrity` remained low (2.0). The underlying cause is a broken tool (`search_places` returns `REQUEST_DENIED`).
    3.  **Hallucination:** Because the tool failed, the agent "hallucinated" the middle of the pipeline (claiming to analyze data it never received) to satisfy the downstream report generation steps.
*   **Conclusion:** The **Optimization** worked (tokens are down), but the **Application** is broken (API key/Tool error). We have successfully optimized a broken agent.
    *   **Next Step:** Fix the `search_places` tool or mock the data to verify the pipeline's logic.
