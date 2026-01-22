# Comprehensive Guide: Tool Hardening for AI Agents (Poka-Yoke Pattern)

This guide details the end-to-end process of "Tool Hardening"—a technique to eliminate tool ambiguity and extraction failures in AI agents by enforcing strict schema validation. This approach fixes extraction errors (e.g., failing to identify entities like "Petunias") and prevents "phantom actions" without requiring architectural changes or model retraining.

---

## Step 0: Diagnosing the Need for Hardening

How do you know if your agent needs Tool Hardening? Look for a specific pattern in your evaluation reports: **High Technical Success, Low Semantic Honesty.**

### The "Silent Failure" Pattern
If you run an evaluation (`uv run adk eval ...`) and see results like this, you need hardening:

| Metric | Score | Diagnosis |
| :--- | :--- | :--- |
| **Tool Success Rate** | **100% (1.0)** | The agent is calling *valid* tools (no crashes). |
| **Capability Honesty** | **Low (~1.0)** | The agent is lying about what it did. |
| **Trajectory Accuracy** | **Low (~1.0)** | The agent took the wrong path to solve the user's problem. |

### Concrete Symptoms
1.  **Phantom Actions:** The agent calls a *read-only* tool (e.g., `check_availability`) but tells the user "I have booked your appointment." It confuses *checking* with *doing*.
2.  **Extraction Failure:** The user says "Remove the shovel and add soil," but the agent calls `modify_cart` with an empty list or string garbage because it couldn't parse the complex instruction into your loose arguments.
3.  **Constraint Violation:** The user says "Book at 10:00 AM," but the agent forces a "9-12" slot and then apologizes.

**If you see these signs, proceed to Step 1.**

---

## 1. The Problem: Forensic Audit & Eval Signals

Before implementing a fix, you must identify the symptoms of "loose" tool definitions.

---

## 2. The Design Philosophy: Poka-Yoke (Mistake-Proofing)

The technical term for Tool Hardening is **Poka-Yoke** (Japanese for "mistake-proofing").

### What is it?
Originating from manufacturing (Toyota), Poka-Yoke is any mechanism that helps an operator avoid errors by making it **impossible** to do the wrong thing. 
*   **Real-world example:** A 3-prong electrical plug. You physically cannot plug it in upside down.

### Applying it to AI Agents:
*   **The "Loose" Way (Instructions):** You tell the agent in a text prompt: *"Only book services in 3-hour blocks."* This is like a warning sign. The model can still ignore it and try to book "10:15 AM."
*   **The Poka-Yoke Way (Hardened):** You define a Pydantic model with `Literal["9-12", "13-16"]`. Now, the tool **contract** itself rejects anything else. The model sees the "physical shape" of the tool and is forced to comply before the code even runs.

**The Goal:** Don't just *ask* the AI to be correct; design the interface so that it **cannot** be incorrect.

---

## 3. The Solution: Implementing Tool Hardening

**Step 1: Define Request Schemas**
Instead of passing loose arguments, define a strict `BaseModel` for each tool's input. This acts as a form for the LLM to fill out.

*File: `customer_service/tools/tools.py`*

```python
from pydantic import BaseModel, Field
from typing import Literal, List, Optional

# Define the "Shape" of the data the tool needs
class ModifyCartRequest(BaseModel):
    """Schema for modifying the user's cart."""
    customer_id: str = Field(description="The ID of the customer.")
    # Force the model to generate a structured list, not a string description
    items_to_add: List[CartItem] = Field(default=[], description="List of items to add.")
    items_to_remove: List[str] = Field(default=[], description="List of product_ids to remove.")

class SchedulePlantingServiceRequest(BaseModel):
    """Schema for scheduling a service."""
    customer_id: str = Field(description="The ID of the customer.")
    date: str = Field(description="Target date (YYYY-MM-DD).")
    # Use Literals to enforce valid options at the schema level
    time_range: Literal["9-12", "13-16"] = Field(description="Desired slot. MUST be '9-12' or '13-16'.")
```

**Step 2: Refactor Tool Signatures**
Update your functions to accept **only** the Pydantic request object. This removes ambiguity about argument order or optionality.

```python
def modify_cart(request: ModifyCartRequest) -> dict:
    """
    Modifies the user's shopping cart.
    
    Args:
        request (ModifyCartRequest): The request details.
    """
    logger.info("Modifying cart for customer ID: %s", request.customer_id)
    # Logic uses the strict object attributes
    return {"status": "success", "message": "Cart updated successfully."}
```

**Step 3: Update Tool Registration**
Ensure your agent is importing and using these updated functions. The ADK will automatically convert the Pydantic models into the JSON schema sent to the LLM.

---

## 3. Verification: The Evaluation Workflow

After hardening the tools, you must verify the fix.

### 3.1 The "Smoke Test" (Fast Feedback)
Run a small subset of scenarios to check for crashes (500 errors) and basic functionality.

**Command:**
```bash
uv run adk eval customer_service eval/scenarios/smoke_test.evalset.json
```
**Success Criteria:**
*   **0% Crash Rate:** No `500 Internal Error` or validation errors in the logs.
*   **Tool Execution:** The logs show the agent successfully calling `modify_cart` with a valid JSON object.

### 3.2 The Full Regression (Deep Analysis)
Run the full evaluation suite to generate a comparative report.

**Command 1 (Simulation):**
```bash
uv run adk eval customer_service eval/scenarios/eval_set_with_scenarios.evalset.json
```

**Command 2 (Post-Process Analysis):**
```bash
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/raw/processed_interaction_sim.jsonl \
  --metrics-files eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label hardened_v1
```

### 3.3 Interpreting the Results
Review the generated `gemini_analysis.md` report.

*   **Metric:** `tool_success_rate` should increase to **>95%**.
*   **Metric:** `state_management_fidelity` should improve as the model now correctly extracts entities into the fields defined by your Pydantic models.
*   **Behavioral Check:** Verify that the agent handles constraints (like "10:00 AM" vs "9-12") correctly. With `Literal["9-12"]`, the model should now apologize or ask for a valid slot instead of hallucinating a "10:00 AM" booking.

---

## 5. Troubleshooting & Cheat Sheet

**If you get stuck, check these common issues:**

| Symptom | Probable Cause | The Fix |
| :--- | :--- | :--- |
| **Log:** `ValidationError` / `400 Bad Request` | The model sent data that violates your Pydantic schema (e.g., string instead of int). | 1. Check your `Field(description=...)`. Is it clear? <br> 2. Ensure types are simple (str, int, float, bool). <br> 3. If using `List[...]`, explicitly say "List of..." in the description. |
| **Behavior:** Agent apologizes repeatedly ("I cannot do that"). | The user asked for something outside your `Literal` constraints (e.g., "10am" when only "9-12" is allowed). | **This is usually a success!** The hardening is working. If it's a valid request, update your `Literal` options in `tools.py`. |
| **Log:** `500 Internal Error` during Eval | Rate limits or the evaluation service is overloaded. | 1. Run the **Smoke Test** (`smoke_test.evalset.json`) instead of the full suite. <br> 2. Check if your `eval_config.json` is running too many metrics at once. |
| **Behavior:** "I have updated the cart" (but no tool called). | The model thinks it *is* the backend. | Ensure your tool function returns a clear status dictionary: `{"status": "success", "message": "..."}`. The model needs this confirmation loop. |
| **Code:** `AttributeError: 'dict' object has no attribute 'x'` | You updated the function signature to accept `request`, but your code still tries to access `request['x']` like a dictionary. | Use dot notation: `request.x`. Pydantic models are objects, not dicts. |

---

## 6. Summary of Benefits

1.  **Eliminates Ambiguity:** The LLM no longer guesses argument order.
2.  **Enforces Constraints:** `Literal` types prevent invalid inputs (like "10am") before they hit your code.
3.  **Improves Extraction:** Explicit fields (`product_id`, `quantity`) force the model to structure unstructured text.
4.  **Reduces Latency:** Clearer schemas reduce the model's "thinking" time required to formulate a tool call.

```