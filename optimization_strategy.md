# Agent Optimization Strategy & Signal Identification Plan

## 1. Overview & Workshop Objective
This framework guides the technical diagnosis of AI agents during the "hill climbing" optimization exercise. The objective is to transition from simple "Prompt Engineering" to "Architectural Context Engineering" by identifying specific performance signals and mapping them to optimized architectural patterns.

## 2. Core Optimization Principles (The Hill Climbing Framework)

### A. Offload (Move Logic to Tools)
*   **The Signal:** High reasoning errors, hallucinations in deterministic tasks (arithmetic, data aggregation), or long "thinking" traces that result in incorrect logic.
*   **Logic vs. Knowledge:** Use **Offload** when the agent has the correct facts but fails to process them effectively (e.g., failing to sort a list, calculate a sum, or filter a JSON blob). These are **Reasoning** errors that should be moved to a `FunctionTool` or Python Sandbox via Code Execution.

### B. Reduce (Trim the Context Window)
*   **The Signal:** High latency, high prompt costs, and "Lost in the Middle" syndrome where the agent ignores instructions. High `prompt_token_count` relative to task complexity.
*   **The Fix:** Implement `EventsCompactionConfig` to summarize history, or use `include_contents='none'` for stateless utility agents to minimize the active context window.

### C. Retrieve (Dynamic Grounding)
*   **The Signal:** Hallucinations regarding facts, or poor `HALLUCINATION` scores despite high token usage. The prompt is "stuffed" with static data that isn't always relevant.
*   **Logic vs. Knowledge:** Use **Retrieve** when the agent fails due to missing or stale information (e.g., not knowing a specific customer's order history or a specific retail competitor's location). These are **Knowledge** errors that should be fixed by replacing static data blocks with a Retrieval-Augmented Generation (RAG) pattern.

### D. Isolate (Modular Decomposition)
*   **The Signal:** "Monolithic Confusion"—the agent has too many instructions or tools and frequently chooses the wrong one or gets stuck in loops.
*   **The Fix:** Break the monolith into a `SequentialAgent` pipeline or a `Coordinator` pattern with specialized sub-agents, isolating specific tasks into distinct execution contexts.

### E. Cache (Efficiency & Latency)
*   **The Signal:** Low `cache_hit_rate` (KV-Cache efficiency < 50%) despite repetitive multi-turn interactions or large static system instructions. High Time-To-First-Token (TTFT).
*   **The Fix:** Restructure the prompt to keep static content at the beginning and implement `ContextCacheConfig` in the ADK `App` wrapper.

## 3. Performance Dimensions
*   **Quality:** Measured via LLM-as-a-Judge (Rubric-based metrics like `TOOL_USE_QUALITY` and `GENERAL_QUALITY`).
*   **Cost:** Measured via total `token_usage` and estimated USD cost.
*   **Latency:** Measured via `latency_metrics` (TTFT, Total Turn Latency, and Average Turn Latency).

## 4. Analysis Goal
Your diagnosis should identify which specific principle (Offload, Reduce, Retrieve, Isolate, or Cache) will provide the highest ROI for the next step in the agent's optimization journey.

## 5. Justification with Evidence
Every diagnosis (positive or negative) MUST be supported by a combination of quantitative scores and qualitative interaction examples.
*   **Reference Metric Scores:** Cite specific scores from the `Evaluation Summary` or `Detailed Explanations` (e.g., "The agent scored 1.2 on `tool_usage_accuracy`...").
*   **Identify the Question ID:** Reference specific test cases (e.g., `q_billing_01`).
*   **Quote the Interaction:** Provide snippets of user input, tool calls (arguments/responses), or agent text that directly justify the score and the diagnosis.
*   **Connect Signal to Fix:** Explain how the combination of the score and the quoted evidence points directly to one of the optimization principles (e.g., "The low `tool_usage_accuracy` score combined with the agent's failure to handle the math in question `q_retail_05` after seeing 50 rows of JSON indicates it is a prime candidate for **Offloading** to Code Execution").
