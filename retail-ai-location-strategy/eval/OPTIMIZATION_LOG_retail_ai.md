# Optimization Log: Retail Location Strategy Agent

**Optimization Focus:** Efficiency & Scalability (The "Reduce" Pillar)
**Pattern Applied:** Offload & Minify (Artifact-based Data Handling)
**Date:** January 29, 2026

## 1. Problem Statement: Context Saturation & Latency
The Baseline agent (v0) suffered from "Data Bloat." When the `search_places` tool executed, it returned the raw, un-curated JSON output from the Google Maps API directly into the LLM's context window.

*   **Symptom 1 (Latency):** The LLM spent **164 seconds** on average per turn. A huge portion of this was "Time to First Token" (TTFT) because the model had to ingest and process thousands of tokens of raw JSON before it could start generating a response.
*   **Symptom 2 (Cost):** A single tool call injected 15,000+ tokens of raw JSON (addresses, review IDs, photo references) that were irrelevant to the analytical task.
*   **Symptom 3 (Cognitive Overload):** The sheer volume of raw data degraded the model's ability to follow complex instructions.

## 2. Hypothesis & Rationale
To solve this, we applied the **Offload & Reduce** pattern.

*   **Hypothesis:** Reducing the input context size will directly reduce latency. The LLM does not need to *read* the full dataset to *reason* about it. It only needs a summary (schema/preview) to write code that analyzes the full dataset.
*   **Rationale:**
    *   **Offload:** By saving the heavy data to disk, we remove it from the expensive context window.
    *   **Minify:** By injecting only a "preview," we drastically lower the **Prompt Processing Time** (pre-fill latency).
    *   **JIT Loading:** By shifting the data processing to Python (`pandas`), we avoid the slow, token-by-token generation required for the LLM to "read" and summarize the data itself.

## 3. Implementation: The "Artifact" Pattern

Three specific code changes were made to implement this pipeline.

### A. The Tool (Offloading)
**File:** `app/tools/places_search.py`
We modified the tool to save the full payload to `competitors.json` and return only a 3-item preview.
```python
# ... inside search_places ...
# Save full results to disk (Offload)
with open("competitors.json", "w") as f:
    json.dump(places, f, indent=2)

return {
    "status": "success",
    "message": f"Saved {len(places)} results to competitors.json",
    "preview": places[:3] # Only return 3 items to context
}
```

### B. The Callback (Minification)
**File:** `app/callbacks/pipeline_callbacks.py`
Before the Analysis Agent runs, we intercept the state. We read the file, strip heavy fields (addresses, IDs), and inject a lightweight version into the prompt.
```python
def before_gap_analysis(callback_context):
    # Load raw, strip heavy fields, create minified string
    minified_data = [{"name": i["name"], "rating": i["rating"]} for i in raw_data]
    callback_context.state["competitors_json_data"] = json.dumps(minified_data)
```

### C. The Agent (JIT Loading)
**File:** `app/sub_agents/gap_analysis/agent.py`
The system prompt was updated to instruct the model to load the data via Python, rather than expecting it in the chat history.
```python
GAP_ANALYSIS_INSTRUCTION = """
The competitor data is provided as a JSON string preview.
To perform analysis, LOAD the full data using this code pattern:

import json
import pandas as pd
df = pd.DataFrame(json.loads(COMPETITORS_JSON))
"""
```

## 4. Results: Baseline vs. Optimized

The implementation resulted in massive efficiency gains, validating the hypothesis regarding both tokens and latency.

| Metric | Baseline (v0) | Optimized (v1) | Delta | Impact |
| :--- | :--- | :--- | :--- | :--- |
| **Avg Turn Latency** | 164.7s | **113.4s** | **-31.1%** 🟢 | **Major Win.** User wait time dropped by over 50 seconds per turn. |
| **Total Tokens** | 58,619 | **39,663** | **-32.3%** 🟢 | Significant cost reduction per run. |
| **Reasoning Ratio** | 0.50 | **0.46** | **-8.0%** 🟢 | Less "over-thinking" required to parse data. |
| **Tool Use Quality** | 2.0 / 5 | **3.67 / 5** | **+1.67** 🟢 | Agent effectively uses the artifact pattern. |

## 5. Remaining Work: The "Fail-Open" Integrity Issue

While the **Efficiency** problem is solved, the **Integrity** score remains low (2.33/5).

**The New Problem:**
The optimization made the agent faster, but revealed a behavioral flaw: **"Fail-Open Error Handling."**
In the optimized run (`retail_002`), the `search_places` tool returned 0 results. Because the prompt prioritizes generating a report, the agent ignored the empty dataset and fabricated (hallucinated) the numbers to satisfy the output format.

**Next Optimization Required:**
*   **Focus:** Reliability / Negative Constraints.
*   **Action:** Implement "Circuit Breaker" logic in the system prompt.
    *   *Instruction:* "If `search_places` returns 0 results or an error, you MUST STOP. Do not generate a report with fake numbers. Return a `DataUnavailableError`."