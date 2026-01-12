# Agent Optimization Strategy & Signal Identification Plan

This document outlines the strategy for the "Agent Optimization Workshop," identifying the signals that trigger optimization, the plan for applying them, and a synthesis of the research that informs this approach.

## 1. Workshop Strategy: Branch-per-Optimization

**Status:** ✅ Confirmed & Recommended

We will utilize a **Branch-per-Optimization** strategy. This aligns perfectly with the "Iterative Refinement" and "component-wise evaluation" methodologies found in the research.

### Branch Structure
*   `main`: The "Naive Monolith" (Milestone 0). Baseline performance.
*   `optimizations/01-tool-definition`: Optimizing tool descriptions/schemas to reduce token usage and confusion.
*   `optimizations/02-context-compaction`: Implementing "Context Compaction" (removing stale tool outputs) to fight "Context Rot".
*   `optimizations/03-code-execution`: Offloading complex logic to a Python sandbox (MCP) to reduce latency and error rates.
*   `optimizations/04-functional-isolation`: Splitting the monolith into specialized sub-agents (e.g., Planner, Researcher) to solve "Attention Diffusion".
*   `optimizations/05-prefix-caching`: Stabilizing prompt prefixes to maximize KV-cache hit rates (75% cost reduction target).

---

## 2. Signal Identification Plan

We will follow this 5-step process to identify when and what to optimize.

### Step 1: Define Signal Sources
*   **"Context Rot" / Attention Diffusion:** The agent begins to "forget" earlier instructions or hallucinate parameters as the conversation grows.
    *   *Source:* `evaluation/results/.../eval_summary.json` (Low `state_fidelity` scores).
*   **Token Bloat:** excessive input tokens per turn compared to the output "thought" tokens.
    *   *Source:* Vertex AI usage metadata (Input Token Count).
*   **Tool Usage Errors:** The agent calls tools with invalid arguments or hallucinated tools.
    *   *Source:* `evaluation/results/.../evaluation_results_*.csv` (Trace columns showing `ToolError`).
*   **Latency Spikes:** Time-To-First-Token (TTFT) exceeds 500ms or total duration exceeds acceptable limits.
    *   *Source:* Client-side telemetry / Evaluation logs.
*   **Repetitive "Ruts":** The agent enters a loop of calling the same failing tool without changing strategy.
    *   *Source:* Trace logs (repeated tool signatures).

### Step 2: Quantify Signal Impact
We will measure these signals using the following metrics:
*   **Context Efficiency Ratio:** `Input Tokens / Output Tokens`. A ratio > 50:1 indicates a need for **Code Execution** or **Context Compaction**.
*   **State Fidelity Score (1-5):** Measured by our Eval LLM. A score < 3.0 indicates a need for **Functional Isolation** (Sub-agents).
*   **Tool Success Rate:** `% of tool calls returning 200 OK`. A rate < 80% indicates a need for **Tool Definition Optimization**.
*   **KV-Cache Hit Rate:** `% of input tokens retrieved from cache`. A rate < 50% indicates a need for **Prefix Optimization**.

### Step 3: Correlate Signals to Outcomes
*   **High Token Bloat** ➔ **High Cost & Latency** (Direct correlation).
*   **Low State Fidelity** ➔ **Task Failure** (The agent forgets the goal).
*   **Low Tool Success Rate** ➔ **"Reflexion" Loops** (Agent tries to fix itself, wasting more tokens).
*   **Context Rot** ➔ **Hallucination** (Agent invents facts because it cannot find them in the "middle" of the context).

### Step 4: Prioritize Signals by ROI
We will tackle optimizations in this order based on the "Low Hanging Fruit" principle from Anthropic's research:

1.  **Tool Definition/Schema (High Impact, Low Effort):** Fixing ambiguous tools prevents errors immediately.
2.  **Context Compaction (High Impact, Medium Effort):** Removing stale data extends the effective context window.
3.  **Code Execution (High Impact, Medium Effort):** Replaces "chain-of-thought" arithmetic with precise Python execution.
4.  **Functional Isolation (Medium Impact, High Effort):** Re-architecting into sub-agents. Necessary for complex tasks but expensive to implement.
5.  **Prompt Caching (Cost Impact, Low Effort):** Purely financial optimization, applied last to stable prompts.

### Step 5: Benchmark Signal Effectiveness
*   **Baseline (Milestone 0):** Run the full `evalset` against the Monolith. Record "Floor" metrics.
*   **Incremental Benchmarking:** After *each* optimization branch merge, run the *same* `evalset`.
*   **Success Criteria:**
    *   Quality > 4.5/5.0
    *   TTFT < 500ms
    *   Cost Reduction > 75%

---

## 4. Expanded Optimization Strategies (Beyond the 5 Pillars)

Based on a deeper analysis of agent engineering research (Anthropic, Manus, etc.), we are adding three architectural strategies that complement the core "5 Pillars" (Offload, Reduce, Retrieve, Isolate, Cache).

### 1. Attention Structuring (Recitation)
*   **Concept:** Beyond simply *reducing* context, we must *structure* it to maximize model performance.
*   **The Technique:** Maintain a persistent "State of the World" or "Goal Artifact" (e.g., a `todo.md` block) that is programmatically injected at the **end** of the prompt context every turn.
*   **Why it works:** Counteracts the "Lost in the Middle" phenomenon. By forcing the goal into the recent context window, it ensures the agent "recites" its objective before acting.
*   **Source:** Manus (Context Engineering), Philschmid.

### 2. Dynamic Routing (Task Classification)
*   **Concept:** "One size fits all" architectures degrade performance on outlier tasks.
*   **The Technique:** Implement a lightweight "Router" layer (using a fast model like Gemini Flash or simple logic) at the entry point. This classifies user intent and directs it to the most appropriate sub-agent or model tier.
*   **Why it works:** Decouples simple tasks from complex ones, optimizing both cost (using cheaper models when possible) and quality (using specialized agents for complex tasks).
*   **Source:** Anthropic (Building Effective Agents).

### 3. Tool Hardening (Poka-Yoke Design)
*   **Concept:** Optimization of the *Interface*, not just the *Agent*.
*   **The Technique:** Design tool schemas that make errors difficult or impossible ("Poka-Yoke").
    *   *Examples:* Using Enums instead of open strings; requiring absolute paths; returning "Did you mean X?" error messages instead of stack traces.
*   **Why it works:** Drastically reduces "Reflexion Loops" (wasted turns trying to fix tool errors), improving TTFT and Success Rate.
*   **Source:** Anthropic (Code Execution with MCP).

---

## 5. The Optimization Loop: Signal-Driven Engineering

We do not apply optimizations blindly. Every architectural change must be driven by a measurable signal from our evaluation framework. This "Measure First" philosophy ensures we solve actual bottlenecks rather than theoretical ones.

### The Signal-Response Map

| Signal (The Symptom) | Metric / Data Source | Recommended Optimization (The Cure) | Research Basis |
| :--- | :--- | :--- | :--- |
| **Context Rot** | `state_fidelity` score drops as conversation length increases. | **Context Compaction** or **Attention Structuring** | *Manus, Philschmid* |
| **Hallucination** | `tool_usage_accuracy` is low; agent invents parameters. | **Tool Definition** or **Tool Hardening** | *Anthropic (ACI)* |
| **Token Bloat** | Input tokens > 4000/turn; `Context Efficiency Ratio` < 50:1. | **Code Execution (MCP)** or **Reduce** | *Anthropic (Code Exec)* |
| **Slow Recovery** | High "Reflexion" count (retries) in traces. | **Tool Hardening (Poka-Yoke)** | *Anthropic* |
| **Drift** | Agent succeeds early but fails late; "Lost in the Middle". | **Attention Structuring (Recitation)** | *Manus* |
| **High Cost** | Low `KV-Cache Hit Rate` (< 50%). | **Prefix Caching** or **Reduce** | *Philschmid* |
| **General Failure** | Low `Pass^k` (consistency) across diverse tasks. | **Dynamic Routing** or **Functional Isolation** | *Anthropic (Routing)* |

### Evaluation Design for Attendees
As you build your evaluation framework, ensure your metrics can capture these specific signals. Don't just measure "Success/Fail". Measure:
1.  **Intermediate State Fidelity:** Does the agent know *where* it is in the plan?
2.  **Tool Argument Validity:** Are the errors coming from the *agent's logic* or the *tool's interface*?
3.  **Token Velocity:** How fast is the context growing vs. value delivered?

---

## 3. Reference Analysis: Synthesis of Key Insights

### 1. Anthropic: Building Effective Agents & Evals
*   **Key Insight:** Start simple. Only add complexity (agents) when simple prompts fail.
*   **Optimization:** **Code Execution** is a massive win. It moves logic out of the "fuzzy" LLM into a deterministic sandbox, reducing tokens by up to 98% for some tasks.
*   **Evals:** "Pass@k" is a better metric than simple accuracy for tool-use. Automated evals are mandatory to prevent regression.

### 2. Manus: Context Engineering
*   **Key Insight:** **"Context Rot"** is real. As context fills, the model gets dumber.
*   **Optimization:** **Context Compaction**. Do not keep full HTML pages in context; extract the text or keep only the URL.
*   **Optimization:** **Tool Masking**. Don't show the agent 100 tools. Show them 5 relevant ones to prevent confusion.
*   **Pattern:** Use a `todo.md` file in the context (or a "Planner" sub-agent) to keep the *goal* fresh in the model's attention.

### 3. Philschmid: Context Engineering Part 2
*   **Key Insight:** **KV-Cache** is the lever for cost/latency.
*   **Optimization:** **Prefix Stability**. Put static instructions (System Prompts, Tool Definitions) *first* and never change them. Put dynamic user data *last*.
*   **Architecture:** "Share context by communicating, not by sharing context." Sub-agents should have fresh, empty context windows and only receive the specific data they need.

### 4. Recursive Language Models (Arxiv)
*   **Key Insight:** Long contexts degrade performance (score %) logarithmically.
*   **Optimization:** **Recursive Decomposition**. Break a 100k token problem into five 20k token problems. This supports the **Functional Isolation** (Sub-agent) strategy.
