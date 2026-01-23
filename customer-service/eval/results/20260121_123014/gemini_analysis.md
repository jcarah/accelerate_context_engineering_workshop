# Agent Optimization Strategy & Signal Identification Plan

## 1. Overview & Workshop Objective
This report provides a technical diagnosis of the `customer_service` agent based on the provided evaluation metrics, interaction logs, and source code. The analysis aims to transition the agent from a monolithic "Prompt Engineering" approach to a robust "Architectural Context Engineering" state. The diagnosis focuses on identifying specific performance bottlenecks—specifically regarding capability honesty, state management, and latency—and mapping them to the Hill Climbing optimization framework.

## 2. Analysis Goal: Isolate (Modular Decomposition)
Based on the synthesis of **High Context Saturation** (avg. ~29k prompt tokens), **High Latency** (~10s per turn), and **Low Capability Honesty** (2.93/5), the primary diagnosis is that the agent is suffering from **Monolithic Confusion**.

The agent is attempting to handle too many distinct domains (Cart Management, Plant Care, Booking, Returns, Discount Approvals) within a single execution context (`agent.py` loads 12 distinct tools). This results in hallucinations regarding capabilities and inefficient context usage.

**Recommended Strategy:** **Isolate (Modular Decomposition)**.

## 3. Justification with Evidence

### A. The Signal: Monolithic Confusion & Capability Hallucinations
The most critical signal is the discrepancy between the agent's confidence and its actual capabilities, represented by the **Capability Honesty** score of **2.93/5**. The agent frequently hallucinates the ability to perform actions (viewing videos, sending emails, applying discounts directly) that are not supported by its tool definitions or backend logic.

*   **Metric Reference:** `capability_honesty` (2.93 average) and `latency_metrics.average_turn_latency_seconds` (9.95s).
*   **Evidence (Question ID: `df4c7efb`):**
    *   **Scenario:** The user asks to identify a plant via video.
    *   **Interaction:** The agent sends a link via `send_call_companion_link` (which sends a link to a *human* expert according to standard patterns, or simply sends a link). However, the agent hallucinates that *it* can see the stream.
    *   **Quote:** "Based on what I'm seeing, it appears to be a lovely **Rosemary plant**. It looks quite healthy!"
    *   **Diagnosis:** The agent hallucinated visual perception capabilities because the tool `send_call_companion_link` was available in its context, but the boundary of that tool (it connects to a human, or acts as a placeholder) was not enforced. In a monolithic prompt, the agent conflates the presence of a "video link" tool with multimodal capabilities it does not possess.
    *   **Metric:** The `capability_honesty` for this question was **0.0**.

*   **Evidence (Question ID: `4feff780`):**
    *   **Scenario:** Booking a planting service.
    *   **Interaction:** The agent promises to send a calendar invite and a discount QR code via email.
    *   **Quote:** "Would you like me to send you a calendar invite... Also, would you be interested in receiving... a discount QR code...?"
    *   **Code Analysis:** In `tools.py`, `generate_qr_code` returns a dictionary with `"qr_code_data": "MOCK_QR_CODE_DATA"`. It does *not* have an email delivery mechanism. Similarly, there is no `send_calendar_invite` tool in `agent.py`.
    *   **Diagnosis:** The agent is filling gaps in its monolithic instruction by hallucinating helpful features (calendar invites) that do not exist as executable code.

### B. The Signal: State Management Failures (The "Offload" Necessity)
The agent struggles with determinstic logic that should be handled by code, specifically regarding cart management. While the primary diagnosis is **Isolate**, there is a strong secondary signal for **Offload**—moving state logic out of the LLM and into persistent tool structures.

*   **Metric Reference:** `tool_use_quality` (Score 2.0 on `5046d7f2`) and `trajectory_accuracy` (Score 3.0 on `2c79e2d0`).
*   **Evidence (Question ID: `b691e894` & `fa010d66`):**
    *   **Scenario:** User attempts to add items to the cart.
    *   **Code Context:** In `tools.py`, `modify_cart` returns a static success message (`"status": "success"`), but `access_cart_information` returns a static list of items (Potting Soil, Fertilizer) that *never changes*. The tools share no state.
    *   **Interaction:** The agent calls `modify_cart`, receives "success", then calls `access_cart_information`, sees the items are missing, and apologizes for a "technical issue."
    *   **Quote:** "I sincerely apologize, Alex, but it seems we're still encountering a technical issue with the cart system. Despite my attempts to add... they are not appearing in your cart."
    *   **Diagnosis:** The agent is correctly interpreting the tool outputs (which are inconsistent), but because the logic is split between a stateless LLM and stateless mock functions, the conversation fails. The high token usage (29k+ prompts in `fa010d66`) confirms the agent is flailing to resolve this state mismatch.

### C. The Signal: Context Saturation & Latency
The agent is carrying a massive context window, likely due to a heavy `GLOBAL_INSTRUCTION` combined with the definitions of 12 distinct tools.

*   **Metric Reference:** `token_usage.prompt_tokens` (Average **28,960**) and `latency_metrics.total_latency_seconds` (Average **37.4s**).
*   **Analysis:**
    *   For simple queries like "I want to return this" (`a7646beb`), the agent still processes ~12k tokens and takes ~62 seconds total latency (20s per turn).
    *   This indicates that the prompt contains instructions for *every possible scenario* (Returns, Sales, Support, Botany), forcing the model to process irrelevant instructions for every turn.
    *   **Diagnosis:** This confirms the need to **Reduce** the active context window, which is best achieved via **Isolate** (breaking the agent into specialized sub-agents).

## 4. Technical Diagnosis Summary
The agent is currently a **Monolith** suffering from high cognitive load and state synchronization issues.

1.  **Capability Dishonesty:** The agent hallucinates capabilities (vision, email attachments, cart updates) because it has too many tools available and insufficient constraints in its system prompt.
2.  **Stateless Tool Chain:** The tools defined in `tools.py` are mock functions that do not share state (e.g., `modify_cart` does not affect `access_cart_information`). This forces the agent into loops where it tries to correct "technical issues" that are actually implementation bugs.
3.  **Inefficient Context:** The average prompt size (~29k tokens) is excessively high for the task complexity, directly causing high latency (~10s/turn) and high reasoning costs.

## 5. Recommended Optimization Path

### Step 1: Fix the Foundation (Offload)
Before architectural changes, the underlying tool logic must be fixed. The agent cannot succeed if `modify_cart` and `access_cart_information` are not synchronized.
*   **Action:** Rewrite `tools.py` to use a shared in-memory state or a simple database so that `modify_cart` actually updates the data returned by `access_cart_information`.

### Step 2: Implement Isolate (Modular Decomposition)
Break the `customer_service` agent into specialized sub-agents.
*   **`SalesAgent`**: Has tools: `get_product_recommendations`, `check_product_availability`.
*   **`CartAgent`**: Has tools: `access_cart_information`, `modify_cart`.
*   **`ServiceAgent`**: Has tools: `schedule_planting_service`, `get_available_planting_times`.
*   **`SupportAgent`**: Has tools: `send_care_instructions`, `send_call_companion_link`, `generate_qr_code`.
*   **Benefit:** This will drastically **Reduce** the prompt token count per turn (lowering latency and cost) and reduce capability hallucinations by ensuring the agent only sees tools relevant to the current scope.

### Step 3: Retrieve (Dynamic Grounding)
For the "Organic Fertilizer" issue (`5046d7f2`), the agent failed to filter products because the tool `get_product_recommendations` logic was insufficient.
*   **Action:** Instead of relying on the LLM to filter a static list, implement a **Retrieve** pattern (RAG) or enhance the tool to accept specific filter parameters (e.g., `is_organic=True`), offloading the search logic to code.