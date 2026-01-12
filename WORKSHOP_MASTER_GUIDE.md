# Workshop Master Guide: Accelerating Context Engineering

This master curriculum combines the "Hill Climbing" strategy with a prioritized focus on the **Customer Service** agent for initial, accessible optimizations, followed by advanced architectural patterns for the **Retail Strategy** agent.

**Philosophy:** Start simple (Schema/Prompt), move to Architecture (Isolation), fix reliability (Reflexion), and finally optimize for Scale (Offload/Cache).

**Core Philosophy:** "Branch-per-Optimization". Every optimization is a separate branch, driven by a specific failure signal, and verified by a specific evaluation metric.

---

## Phase 1: Customer Service Optimization (The "Naive Monolith")

We begin here because the `customer-service` agent is a "Naive Monolith" (1 agent, 12 tools), making the friction obvious and the fixes high-impact.

### Step 1: The "Hallucinating Helper" (Schema Reduction)
**Goal:** Fix tool ambiguity and extraction failures without changing architecture.

*   **Forensic Audit:** `customer_service/agent.py` exposes 12 diverse tools. Tool definitions in `tools.py` lack strict Pydantic validation. The model confuses `modify_cart` (Sales) with `access_cart_information` (Info).
*   **Eval Signal (Symptom):** **Extraction & Tool Failure**. Agent fails to extract entities like "Petunias" or "Coupon Code" from prompts.
*   **Metric:** **`state_management_fidelity`** (Baseline Score: **1.0**) and **`tool_usage_accuracy`** (Baseline Score: **1.2**).
    *   *Evidence:* Trace logs show: *"AI failed to extract any relevant information from the user's prompt regarding the coupon... AI-generated response does not contain any tool calls"* (Score 0.0).
*   **The Scenario:** "Update my cart to remove the shovel and add 3 bags of soil."
*   **Ambiguity Hook:** "The agent sent a string description to a tool that needs an integer ID. How do we force strict typing without retraining the model?"
*   **The Solution (Pillar: Reduce):**
    *   **Pattern:** **Tool Hardening (Poka-Yoke)**. Use strict Pydantic models for tool arguments.
    *   **ADK Sample:** `tool_functions_config`.
    *   **Outcome:** `tool_usage_accuracy` increases to >95% (No 400 Errors).

### Step 2: The "Overwhelmed Generalist" (Functional Isolation)
**Goal:** Split the context to reduce "Attention Diffusion" and noisy trajectories.

*   **Forensic Audit:** The `root_agent` sees "Planting Instructions" rules while trying to "Approve Discounts." This violates the Single Responsibility Principle.
*   **Eval Signal (Symptom):** **Trajectory Noise**. The agent introduces irrelevant steps (e.g., checking the cart for trees the user already bought) before answering.
*   **Metric:** **`trajectory_accuracy`** (Baseline Score: **2.0** for complex turns).
    *   *Evidence:* Trace logs show: *"agent introduced significant noise and misinterpretation... initial deviation constitutes significant extra steps."*
*   **The Scenario:** "Actually, before I book, can you explain why my leaves are yellow? And does that affect the warranty?"
*   **Ambiguity Hook:** "The agent forgot the booking date because it focused on plant pathology. How do we give it 'blinkers'?"
*   **The Solution (Pillar: Isolate):**
    *   **Pattern:** **Triage & Worker**. Split `root_agent` into `TriageAgent`, `SalesAgent`, and `SupportAgent`.
    *   **ADK Sample:** `workflow_triage`.
    *   **Outcome:** `trajectory_accuracy` stabilizes at 5/5 (Correct Routing).

### Step 2.5: The "Drifting Planner" (Recitation)
**Goal:** Fix "Context Rot" where the agent forgets the original goal during long sub-agent tasks.

*   **Forensic Audit:** Even after isolation, sub-agents can lose track of the overarching transaction (e.g., "Apply discount AND schedule delivery") if they spend 8+ turns on a sub-task like delivery scheduling.
*   **Eval Signal (Symptom):** **Context Rot / Lost in the Middle**. The agent solves the immediate problem (delivery time) but fails to complete the full request (discount).
*   **Metric:** **Task Completion Rate** (Drops significantly after turn 8).
    *   *Evidence:* Trace logs show the "Discount" variable disappearing from the agent's internal thought process as the context window fills with delivery logs.
*   **The Scenario:** User has spent 5 turns discussing delivery windows.
*   **Ambiguity Hook:** "The agent successfully scheduled the delivery but completely forgot to apply the discount code we discussed at the start. How do we make it 'check its list' every time?"
*   **The Solution (Pillar: Isolate / Structure):**
    *   **Pattern:** **Attention Structuring (Recitation)**. Programmatically inject a "State of the World" or `todo.md` block at the *end* of the prompt context every turn. This forces the agent to "recite" its objective before acting.
    *   **ADK Sample:** Custom Prompt Pattern (injecting `<plan>` or `<todo>` block).
    *   **Outcome:** 100% Task Completion for long-horizon tasks; eliminates "Goal Drift."

### Step 3: The "Stuck in a Loop" (Reflexion)
**Goal:** Enable autonomous error recovery.

*   **Forensic Audit:** `schedule_planting_service` expects "YYYY-MM-DD". If the model sends "July 25th", the API errors, and the agent gives up.
*   **Eval Signal (Symptom):** **Slow Recovery / Task Failure**. The agent hits an API error and apologizes instead of fixing it.
*   **Metric:** **`response_correctness`** / **Task Completion Rate**.
*   **The Scenario:** "Book me for next Tuesday at 9am." (API returns `ValueError`).
*   **Ambiguity Hook:** "The agent just apologized and quit. How do we make it read the error log and fix its own mistake?"
*   **The Solution (Pillar: Reflexion):**
    *   **Pattern:** **Self-Correction Loop**. A wrapper or sub-agent catches tool errors and re-prompts the model with the error message.
    *   **ADK Sample:** `plugin_reflect_tool_retry`.
    *   **Outcome:** 100% success on formatting edge cases; Completion Rate > 90%.

---

## Phase 2: Retail Strategy Optimization (The "Context Dumper")

Now that we've fixed logic and routing, we tackle Scale and Cost in the `retail-ai-location-strategy` pipeline.

### Step 4: The "Context Dumper" (Offload & Reduce)
**Goal:** Stop flooding the context window with raw data.

*   **Forensic Audit:** `places_search.py` returns raw JSON lists (20+ items). `GapAnalysisAgent` injects this directly into the prompt via f-strings.
*   **Eval Signal (Symptom):** **Token Bloat & Quality Collapse**. The agent hallucinates counts and outputs lists of internal tool names instead of answers.
*   **Metric:** **`strategic_recommendation_quality`** (Baseline Score: **-1.0**) and **Total Token Count** (~112k tokens).
    *   *Evidence:* Trace logs show: *"AI-generated response provides a list of internal tool/agent names rather than an actual answer... It fails to address the user's request."*
*   **The Scenario:** "Analyze coffee shop saturation in Austin, TX." (Returns 40+ locations).
*   **Ambiguity Hook:** "We just paid for 5,000 tokens of raw JSON just to do simple addition. How do we keep the data 'nearby' but out of the prompt?"
*   **The Solution (Pillar: Offload):**
    *   **Pattern:** **Artifacts & Code Execution**. Tool writes to `competitors.json`. Agent uses Python (Pandas) to query it.
    *   **ADK Sample:** `context_offloading_with_artifact` + `agent_engine_code_execution`.
    *   **Outcome:** 80% input token reduction; 100% math accuracy.

### Step 5: The "Expensive Executive" (Prefix Caching)
**Goal:** Optimize "Time to First Token" (TTFT) and Cost.

*   **Forensic Audit:** The `SequentialAgent` pipeline re-sends static system instructions for 6 sub-agents every single turn.
*   **Eval Signal (Symptom):** **High Latency & Low Cache Efficiency**. TTFT is near **9 seconds** for complex sessions.
*   **Metric:** **`latency_metrics.time_to_first_response_seconds`** (8.99s) and **`cache_hit_rate`** (Baseline: **0.22**).
*   **The Scenario:** User spends 15 turns refining a report.
*   **Ambiguity Hook:** "Why are we paying to re-read the Agent Persona 15 times? How do we 'freeze' the static brain?"
*   **The Solution (Pillar: Cache):**
    *   **Pattern:** **Prefix Caching**. Structure prompts to keep static content (Tools, Personas) at the front.
    *   **ADK Sample:** `cache_analysis`.
    *   **Outcome:** 75% Cost Reduction; TTFT < 500ms.

---

## Evaluation Reference Map
All optimizations are verified using the metrics defined in `evaluation/metrics/metric_definitions_customer_service.json`:

| Optimization | Target Metric | Signal (Baseline) | Success Criteria |
| :--- | :--- | :--- | :--- |
| **1. Tool Hardening** | `tool_usage_accuracy` | 1.2 (No tool calls) | Rate > 95% (No 400 Errors) |
| **2. Isolation** | `trajectory_accuracy` | 2.0 (Noisy steps) | Score 5/5 (Correct Routing) |
| **2.5 Recitation** | `task_completion_rate` | Fails on long-horizon | 100% Completion (Turn 8+) |
| **3. Reflexion** | `response_correctness` | Baseline fails on Error | Completion Rate > 90% |
| **4. Offload** | **`state_management_fidelity`** | -1.0 (Component lists) | Token Count < 1000/turn |
| **5. Cache** | `cache_hit_rate` | 0.22 (Low hit rate) | Hit Rate > 0.75 |