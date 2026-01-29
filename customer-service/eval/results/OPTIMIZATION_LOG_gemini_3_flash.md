# Optimization Log: Customer Service Agent - Gemini 3.0 Flash Swap

**Branch:** `optimizations/00-model-swap`
**Optimization:** Model Swap to Gemini 3.0 Flash Preview (Pillar: Smarter Model)
**Date:** 2026-01-29

---

## 1. Summary of Changes
Switched the underlying LLM from `gemini-2.5-flash` to `gemini-3-flash-preview` and set the location to `global`. This milestone establishes the baseline for the next-generation model without any architectural or context engineering optimizations.

---

## 2. Metrics Summary

| Metric Category | Metric Name | Value (Avg) | Delta (vs M0) | Notes |
|:----------------|:------------|:------------|:--------------|:------|
| **Scale** | Avg Prompt Tokens | 22,688 | +~10k 🔴 | Significant increase in token usage. |
| **Latency** | Avg Turn Latency | 9.47s | +~3s 🔴 | Higher latency with the preview model and global endpoint. |
| **Quality** | `trajectory_accuracy` | 4.0 / 5.0 | +0.4 🟢 | Improved reasoning and tool selection. |
| | `tool_use_quality` | 3.6 / 5.0 | -1.2 🔴 | Regression in strict tool argument adherence. |
| | `capability_honesty` | 1.0 / 5.0 | -1.2 🔴 | Confident hallucinations about video/email capabilities. |

---

## 3. Analysis

### Smarter Reasoning, Lower Discipline
The switch to Gemini 3.0 Flash results in a noticeable bump in `trajectory_accuracy`. The model is better at navigating multi-turn logic. However, this comes at a massive cost in **discipline**. 
- The model consistently lies about its capabilities (e.g., claiming it can "see" video streams).
- It ignores explicit user instructions (e.g., "I don't need to check my cart").

### Context Bloat
Token usage spiked to 22k+ tokens. This is a red signal indicating that the model is consuming and generating significantly more context than necessary for these scenarios. Without **Context Compaction (M2)** or **Offloading (M4)**, this model is too expensive for production use.

---

## 4. Conclusions
Swapping to a more powerful model like Gemini 3.0 Flash improves raw reasoning but exacerbates architectural weaknesses like tool hallucinations and token bloat.

**Recommendation:** Proceed to **Milestone 01 (Tool Hardening)** and **Milestone 02 (Context Compaction)** immediately to rein in the model's verbosity and hallucinations.

---

## 5. File References
- **Results:** `customer-service/eval/results/gemini_3_flash/`
- **Analysis:** `customer-service/eval/results/gemini_3_flash/gemini_analysis.md`
