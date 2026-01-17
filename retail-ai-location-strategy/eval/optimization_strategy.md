# Agent Optimization Strategy & Signal Identification Plan

**THE OPTIMIZATION FRAMEWORK (Signal-Response Map):**
Analyze the agent's performance specifically through the lens of the following "Signal-Response" framework. Do not give generic advice; map observed failures to these specific architectural fixes.

1.  **Token Bloat & Cost:**
    *   *The Signal:* Input tokens > 100k/turn; `Context Efficiency Ratio` < 10:1 (Input/Output); agent crashes or timeouts on large datasets.
    *   *The Fix:* **Offload** (save data to disk/Artifacts instead of context) or **Reduce** (summarize before ingesting).

2.  **Logic Failure / Hallucination:**
    *   *The Signal:* Agent fails at arithmetic, aggregation, or complex filtering of data; hallucinates values in large JSON blobs.
    *   *The Fix:* **Code Execution** (move logic to Python Sandbox via MCP).

3.  **High Latency & Cost Inefficiency:**
    *   *The Signal:* Low `KV-Cache Hit Rate` (< 50%); high Time-To-First-Token due to reprocessing static system prompts.
    *   *The Fix:* **Prefix Caching** (restructure prompt to keep static content at the front).

4.  **Context Rot / "Lost in the Middle":**
    *   *The Signal:* Agent forgets earlier constraints or strategic goals as the conversation progresses.
    *   *The Fix:* **Context Compaction** or **Attention Structuring** (dynamic goal injection).