# Agent Optimization Strategy & Signal Identification Plan

**THE OPTIMIZATION FRAMEWORK (Signal-Response Map):**
Analyze the agent's performance specifically through the lens of the following "Signal-Response" framework. Do not give generic advice; map observed failures to these specific architectural fixes.

1.  **Context Rot / Attention Diffusion:**
    *   *The Signal:* Low `state_fidelity` scores; agent forgets instructions, hallucinates parameters, or "drifts" as conversation grows.
    *   *The Fix:* **Context Compaction** (remove stale tool outputs), **Attention Structuring** (recitation/goal injection), or **Reduce** strategies.

2.  **Token Bloat & Latency:**
    *   *The Signal:* High Input/Output token ratio (>50:1); high Time-To-First-Token (>500ms); excessive "chain-of-thought" for simple math/logic.
    *   *The Fix:* **Code Execution** (offload logic to Python via MCP), **Reduce** context, or **Prefix Caching** (if cost is the primary issue).

3.  **Tool Fragility & "Reflexion" Loops:**
    *   *The Signal:* Tool errors, invalid arguments, hallucinated tools, or repeated retries ("reflexion loops") visible in the trace.
    *   *The Fix:* **Tool Definition Optimization** (schema clarity) or **Tool Hardening** (Poka-Yoke design patterns).

4.  **Task Failure / Complexity Wall:**
    *   *The Signal:* Low `Pass^k` or `capability_honesty`. Agent succeeds on simple tasks but fails on multi-step complex ones.
    *   *The Fix:* **Functional Isolation** (splitting monolith into sub-agents) or **Dynamic Routing**.
