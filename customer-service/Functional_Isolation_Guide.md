# Comprehensive Guide: Functional Isolation for AI Agents (Triage & Worker Pattern)

This guide details the end-to-end process of **Functional Isolation**—a technique to solve "Attention Diffusion" and "Trajectory Noise" in AI agents by splitting a monolithic agent into specialized workers. This architecture improves routing accuracy and prevents the agent from getting overwhelmed by conflicting instructions.

## Prerequisites
*   **Python 3.10+** installed.
*   **uv** package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
*   **Google ADK** initialized in your project.

---

## Step 0: Diagnosing the Need for Isolation

How do you know if your agent needs Functional Isolation? Look for a specific pattern in your evaluation reports: **High Technical Success, Low Logical Coherence.**

### The "Overwhelmed Generalist" Pattern
If your agent has access to 10+ tools and diverse instructions (Sales, Support, CRM), look for these signals in your `gemini_analysis.md`:

| Metric | Score | Diagnosis |
| :--- | :--- | :--- |
| **Trajectory Accuracy** | **Low (< 2.0)** | The agent takes a noisy path. It calls irrelevant tools (e.g., checking the cart) before answering a simple question. |
| **Context Saturation** | **High (> 10k tokens)** | The conversation history is bloated with "thinking" steps and redundant tool calls. |
| **Reasoning Ratio** | **High (> 0.6)** | The model spends too much time "thinking" about which tool to use because the list is too long. |

### Concrete Symptoms
1.  **Constraint Confusion:** The agent sees "Planting Rules" while trying to "Approve Discounts" and mixes them up (e.g., asking for a planting date to approve a coupon).
2.  **Phantom Actions:** The agent calls a read-only tool (`get_available_times`) but thinks it "Booked the service" because it's confused about its role.
3.  **Attention Diffusion:** The agent drops tasks in multi-part requests (e.g., "Add soil and email me"). It does the math for the soil but forgets the email because the context window is flooded.

**If you see these signs, proceed to Step 1.**

---

## 1. The Design Philosophy: Triage & Worker

The technical term for this pattern is **Functional Isolation**.

### What is it?
Instead of one "God Object" agent that tries to know everything, you create a hierarchy:
*   **Triage Agent (The Gatekeeper):** Has NO tools. Its ONLY job is to route the user. It is lightweight and fast.
*   **Specialist Agents (The Workers):** Have specific tools and scoped instructions. They wear "blinkers" to focus only on their domain.

### Applying it to AI Agents:
*   **The "Generalist" Way:** You give one agent 50 tools. It gets confused and hallucinates.
*   **The "Specialist" Way:** You give the `SalesAgent` only the 5 tools it needs to sell things. It ignores support questions entirely.

**The Goal:** Reduce the "Search Space" for the LLM so it can't make irrelevant mistakes.

---

## 2. The Solution: Implementing Isolation

### Step 1: Create Specialized Prompts
Define distinct personas for your workers. Each prompt should be laser-focused on one job.

### File: `customer_service/specialist_prompts.py`

```python
TRIAGE_INSTRUCTION = """
You are the Triage Agent. Your ONLY job is to route the user.
- Route to 'sales_agent' for buying/discounts.
- Route to 'support_agent' for help/services.
Do NOT answer the question yourself.
"""

SALES_INSTRUCTION = """
You are the Sales Agent. You handle commercial transactions.
Responsibilities: Inventory, Cart, Discounts.
"""
# ... define SUPPORT_INSTRUCTION similarly
```

### Step 2: Refactor the Agent Definition
Update your main agent file to define the specialists and the root triage agent.

### File: `customer_service/agent.py`

```python
# Define Workers with scoped tools
sales_agent = Agent(
    name="sales_agent",
    instruction=SALES_INSTRUCTION,
    tools=[modify_cart, check_product_availability, ...] # Only sales tools
)

support_agent = Agent(
    name="support_agent",
    instruction=SUPPORT_INSTRUCTION,
    tools=[schedule_planting_service, send_care_instructions, ...] # Only support tools
)

# Define Root Triage Agent (No tools, just routing)
root_agent = Agent(
    name="triage_agent",
    instruction=TRIAGE_INSTRUCTION,
    sub_agents=[sales_agent, support_agent] # Capabilities come from delegation
)
```

---

## 3. Verification: The "Hot Potato" Side Effect

After implementing isolation, you must verify the fix. Be warned: this architecture often introduces a new bug called the **Handoff Loop**.

### 3.1 The Evaluation Run
Run your standard evaluation to generate fresh conversation traces.

```bash
# 1. Run Simulation (Fast, no judges)
# This generates the raw conversation logs
uv run adk eval customer_service eval/scenarios/smoke_test.evalset.json

# 2. Set up your results directory variable for easier copy-pasting
export RUN_DIR="eval/results/my_triage_run"
mkdir -p $RUN_DIR

# 3. Move the fresh logs to your results folder
mv customer_service/.adk/eval_history/*.json $RUN_DIR/

# 4. Run Evaluation (Deep Analysis)
uv run agent-eval evaluate \
  --interaction-file $RUN_DIR/ \
  --metrics-files eval/metrics/metric_definitions.json \
  --results-dir $RUN_DIR \
  --input-label triage_v1 \
  --test-description "Functional Isolation Test"
```

### 3.2 Interpreting the Results (The "Handoff Loop")
Check your `gemini_analysis.md` in `$RUN_DIR`. You might see a **100% Tool Success Rate** (technical success) but a **Low Trajectory Score**.

**Look for this anomaly:**
*   **Metric:** `agent_handoffs` is extremely high (e.g., 10-15 per turn).
*   **Trace Log:** `Triage` -> `Sales` -> `Triage` -> `Sales`...
*   **Diagnosis:** The Triage agent routes to Sales. The Sales agent (being helpful) tries to route *back* or doesn't know it's the "end of the line." It becomes a game of "hot potato."

### 3.3 The Fix: "The Bossy Manager"
To fix the loop, you must explicitly update the prompts to enforce **Stop Conditions**.

*   **Triage Update:** "Once you transfer, STOP. Do not generate text."
*   **Worker Update:** "You are the specialist. EXECUTE the tool. Do NOT transfer back to Triage."

---

## 4. Troubleshooting & Cheat Sheet

**If you get stuck, check these common issues:**

| Symptom | Probable Cause | The Fix |
| :--- | :--- | :--- |
| **Looping Handoffs** | Workers trying to be helpful routers. | Update `specialist_prompts.py`. Tell workers: "You are the end of the line. Execute the tool." |
| **"I cannot help with that"** | Wrong tool assignment. | Check `agent.py`. Did you give `modify_cart` to the Support agent instead of Sales? |
| **500 Errors / Slow Evals** | Too many agents running at once. | 1. Increase `RPM_QUOTA` in `callbacks.py` (e.g., to 100). <br> 2. Run simulation-only (`adk eval` without config) first. |
| **Lost Context** | Triage agent didn't pass info. | Ensure your `InvocationContext` is shared (ADK handles this by default). |

---

## 5. Summary of Benefits

1.  **Focused Attention:** Each agent only sees the tools/rules relevant to its job.
2.  **Reduced Latency:** Smaller context windows mean faster processing for complex turns.
3.  **Modular Debugging:** If "Sales" is broken, you fix the `SalesAgent` without breaking the `SupportAgent`.
4.  **Scalability:** You can add a `BillingAgent` later without retraining the entire system.

## 6. Quick Start Checklist
- [ ] Forensic Audit: Identify "Overwhelmed Generalist" symptoms.
- [ ] Create `specialist_prompts.py` with scoped personas.
- [ ] Refactor `agent.py` to use Triage/Worker structure.
- [ ] Run Smoke Test (no judges) to generate traces.
- [ ] Run `agent-eval` to check for Handoff Loops.
- [ ] Apply "Bossy Manager" prompt fixes if loops occur.