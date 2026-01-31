# Optimization Log: Customer Service Agent - Hill Climb Journey (Gemini 3.0)

**Project:** Cymbal Home & Garden Assistant
**Optimization Path:** Model Swap -> Tool Hardening -> [Next: Context Compaction]

---

## 1. Metrics Comparison Table

| Metric Category | Metric Name | M0: Baseline (2.5) | M0.5: G3 Swap | M1: Hardened (G3) | Delta (M1 vs M0) |
|:----------------|:------------|:------------------:|:-------------:|:-----------------:|:----------------:|
| **Scale** | Avg Prompt Tokens | 20,923 | 19,053 | 14,121 | -6,802 🟢 |
| **Latency** | Avg Turn Latency | 6.76s | 10.29s | 8.81s | +2.05s 🔴 |
| **Trust** | `capability_honesty` | 1.2 / 5.0 | 1.4 / 5.0 | **5.0 / 5.0** | +3.8 🟢 |
| **Quality** | `trajectory_accuracy` | 3.2 / 5.0 | 4.8 / 5.0 | 3.4 / 5.0 | +0.2 ⚪ |
| **Reasoning** | `reasoning_ratio` | 0.71 | 0.67 | 0.75 | +0.04 ⚪ |

---

## 2. Iteration History

### M0: Baseline (Gemini 2.5 Flash)
*   **Observation:** Fast but prone to logical errors. Agent frequently hallucinates capabilities (Video/Email) to satisfy users.
*   **Trajectory Fail (Score 3.2):** Failed to navigate multi-turn returns or complex cart modifications accurately.

### M0.5: Model Swap (Gemini 3.0 Flash Preview)
*   **Optimization Pillar:** Raw Model Intelligence.
*   **Problem Identification:** The smarter model solved the planning issues but exacerbated hallucinations. It became a "High-IQ Liar," confidently claiming it could see video and send emails to be helpful.
*   **Hypothesis:** Swapping to a smarter model solves the **Logic Gap** but requires a secondary optimization to solve the **Honesty Gap**.

### M1: Tool Schema Hardening (Gemini 3.0 + Constrained Tools)
*   **Optimization Pillar:** Reduce / Constrain.
*   **Hypothesis:** Replacing loose parameters with a rigid, self-validating "contract" will prevent hallucinations by enforcing structural integrity before code execution.
*   **Implementation Details (The Fix):**
    *   **Restricts Input:** Used strict Pydantic types and Literals (e.g., `discount_type: Literal["percentage", "flat"]`) to kill "creative" errors and force compliance with backend logic.
    *   **Guide Intent:** Embedded `**KNOWN LIMITATIONS**` (e.g., "AI CANNOT see video") as high-priority signals in Python docstrings so the model grasps specific field requirements instantly during its reasoning phase.
    *   **Gatekeep Logic:** Triggered instant validation failures for policy violations (e.g., >10% discounts). This forced the agent to self-correct and explain limitations to the user rather than hallucinating success.
*   **Analysis of Variance:**
    *   **Trust (🟢): Success (1.4 -> 5.0).** By hardening the "Contract," the agent no longer overpromises. Evidence: In the returns scenario, the agent admitted it couldn't see the video, successfully asking for a text description instead.
    *   **Competence (🔴): Regression (4.8 -> 3.4).** The density of constraints caused **Attention Dilution**. The model became so focused on following the "Don'ts" that it dropped multi-intent instructions (e.g., ignoring one item in a two-item stock check).
    *   **Scale (🟢): Efficiency Gain.** Tokens dropped by ~25% as the hardened definitions were more concise and unambiguous.

---

## 3. Conclusions for Workshop Delivery

**The Story Arc:**

1.  **Baseline (2.5):** Fast but confused. It didn't know what it couldn't do.
2.  **Model Swap (3.0):** Smarter planning, but it became a **"Confident Liar."** Intelligence alone doesn't fix trust; it just makes the hallucinations more convincing.
3.  **Hardening (The Fix):** Applying the **Contract (Restricts/Guide/Gatekeep)** finally makes the agent trustworthy (**Honesty 5.0**). We proved that code-level constraints are required to tame high-IQ models.
4.  **Next Challenge:** We fixed the "Lying" but triggered **"Attention Dilution."** The model is now carrying too much cognitive load from the constraints. We need **Context Compaction** to free up cognitive space.

**Next Step:** Proceed to **Iteration 2: Context Compaction**.