# Test Coverage Analysis: GenAI Evaluation Pipeline

**Date:** 2026-01-11
**Scope:** `evaluation/` directory.
**Context:** Validation for Enterprise Readiness.

## 1. Executive Summary

| Metric | Percentage | Status |
|--------|------------|--------|
| **Total Line Coverage** | **11%** | 🔴 Critical |
| **Agent Client** | 61% | 🟡 Fair |
| **Core Scripts** | 0% | 🔴 Critical |
| **Utilities** | 5% | 🔴 Critical |

**Verdict:** The current test suite is **insufficient** for a production-grade or high-visibility workshop environment. The existing tests are brittle "happy path" checks that mock out almost all logic, resulting in near-zero coverage of the actual business logic.

---

## 2. Detailed Gap Analysis

### 🔴 Critical Gaps (Must Fix)

#### 1. Core Logic Untested (`02_agent_run_eval.py`)
*   **Coverage:** 0%
*   **Risk:** This script contains complex logic for:
    *   Merging metric configurations.
    *   Parallelizing Vertex AI calls.
    *   Mapping nested JSON data to prompts.
    *   Calculating deterministic metrics.
*   **Impact:** If any of this logic fails (e.g., a regex error in data mapping), the entire evaluation crashes.
*   **Recommendation:** Refactor the logic inside `main()` into testable functions (e.g., `prepare_eval_dataset`, `aggregate_results`) and unit test them.

#### 2. Deterministic Metrics Untested (`scripts/deterministic_metrics.py`)
*   **Coverage:** 5%
*   **Risk:** This file defines how "Cost" and "Latency" are calculated.
*   **Impact:** Incorrect cost calculations ($) or latency metrics could mislead workshop participants about their agent's performance.
*   **Recommendation:** Create a dedicated test suite with sample `trace.json` files to verify that cost/latency math is correct.

#### 3. Interaction Resilience Untested (`scripts/run_interactions.py`)
*   **Coverage:** 0%
*   **Risk:** This script handles the concurrent API calls.
*   **Impact:** No tests exist for:
    *   API timeouts.
    *   Rate limiting (429).
    *   Partial failures (some questions fail, others succeed).
*   **Recommendation:** Add integration tests using a mock HTTP server (`pytest-httpserver`) to simulate flakes and errors.

### 🟡 Medium Priority

#### 4. Trace Parsing Complexity (`agent_client.py`)
*   **Coverage:** 61%
*   **Risk:** The `analyze_trace_and_extract_spans` function is complex and fragile.
*   **Impact:** If the Agent Trace format changes slightly, parsing breaks.
*   **Recommendation:** Move this logic to `utils/trace_analysis.py` and test it against a variety of real-world trace dumps.

---

## 3. Plan for Improvement

### Phase 1: Refactor for Testability (Immediate)
*   **Action:** Extract logic from `02_agent_run_eval.py` into a testable class or functions.
*   **Action:** Move trace parsing out of `AgentClient`.

### Phase 2: Add Logic Tests (Workshop Prep)
*   **Action:** Write unit tests for `deterministic_metrics.py` using sample traces.
*   **Action:** Write unit tests for `data_mapping` logic (nested JSON lookups).

### Phase 3: Integration Tests
*   **Action:** Create a "mock agent" test fixture that returns pre-canned responses to verify the full pipeline end-to-end locally.

---

## 4. Test Code Examples

### Recommended Test: Deterministic Metrics
```python
def test_calculate_cost():
    trace = load_sample_trace("simple_chat.json")
    cost = calculate_token_usage(trace)
    assert cost["total_tokens"] == 150
    assert cost["estimated_cost"] == 0.0005
```

### Recommended Test: Data Mapping
```python
def test_nested_mapping():
    row = {"extracted_data": {"user": {"profile": {"age": 25}}}}
    val = get_nested_value(row, "extracted_data:user.profile.age")
    assert val == 25
```
