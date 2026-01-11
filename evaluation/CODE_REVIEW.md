# Code Review: GenAI Evaluation Pipeline

**Review Date:** 2026-01-11
**Scope:** `evaluation/` directory (Client-side scripts).
**Context:** Local execution by 1,000+ workshop participants.

---

## 1. Critical Issues (Must Fix)

### 🚨 1.1 Fragile Authentication (`agent_client.py`)
*   **Problem:** The client uses `subprocess.check_output(["gcloud", ...])` to fetch tokens.
*   **Why it's bad:**
    *   **Dependency:** Requires the user to have the Google Cloud CLI installed and on their `$PATH`.
    *   **Performance:** Spawning a subprocess is slow (hundreds of ms).
    *   **Portability:** Fails on environments without `gcloud` (e.g., some lightweight containers or Windows setups with weird paths).
*   **Fix:** Use the standard `google-auth` library.
    ```python
    import google.auth
    import google.auth.transport.requests

    def _fetch_token(self):
        credentials, project = google.auth.default()
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        return credentials.token
    ```

### 🚨 1.2 Unbounded Concurrency (`run_interactions.py`)
*   **Problem:** `asyncio.gather(*tasks)` launches *all* interactions simultaneously.
*   **Why it's bad:**
    *   **Rate Limiting:** Even a single user running 50 questions will hit the target agent with 50 simultaneous requests. This often triggers 429s or 500s on the backend.
*   **Fix:** Wrap the logic in a `Semaphore`.
    ```python
    sem = asyncio.Semaphore(5) # Max 5 concurrent requests
    async def limited_process_question(...):
        async with sem:
            return await process_question(...)
    ```

---

## 2. High Priority Improvements

### 2.1 "God Object" Anti-Pattern (`agent_client.py`)
*   **Problem:** `AgentClient` handles HTTP transport, Authentication, *and* complex Trace Parsing logic (`analyze_trace_and_extract_spans`, 100+ lines).
*   **Violation:** Single Responsibility Principle (SRP).
*   **Fix:** Extract the static analysis methods into a separate `TraceAnalyzer` class or utility module (`evaluation/utils/trace_analyzer.py`).

### 2.2 Hardcoded Trace Endpoints
*   **Problem:** `AgentClient.get_session_trace` tries a list of hardcoded URL patterns (`/debug/trace...`, `/apps/...`).
*   **Risk:** API routes change. If the backend changes its trace path, the client breaks.
*   **Fix:** Accept a `trace_endpoint_template` in the constructor or config.

### 2.3 Dependency Injection (`run_interactions.py`)
*   **Problem:** `AgentClient` is instantiated directly inside the script logic.
*   **Testing:** This makes it impossible to unit test `process_question` without mocking `requests` or `AgentClient` class internals.
*   **Fix:** Pass the `client` instance into functions rather than creating it inside.

---

## 3. Medium Priority Recommendations

### 3.1 Heavy Dependency Usage
*   **Observation:** `pandas` is used in `01_agent_interaction.py` just to sample questions.
*   **Impact:** `pandas` is a massive dependency (~100MB). For simple list sampling, standard Python `random.sample` is sufficient and faster to install.
*   **Fix:** Rewrite `load_and_consolidate_questions` using standard library `collections` and `random`.

### 3.2 Robust Retry Logic
*   **Observation:** `AgentClient` has a simple retry loop.
*   **Improvement:** Use `urllib3`'s `Retry` object (via `requests.adapters.HTTPAdapter`) which handles backoff, specific status codes (429, 500, 502, 503, 504), and `Retry-After` headers automatically.

---

## 4. Code Style & Hygiene

*   **Type Hinting:** Mostly good, but `Any` is used frequently in `AgentClient`. Tighten this up with `TypedDict` or Pydantic models for known Trace structures.
*   **Logging:** `print()` is used extensively. Switch to the `logging` module to allow users to control verbosity (e.g., `--verbose`).
*   **Docstrings:** `run_interactions.py` has good module-level docs, but individual helper functions are missing type hints in some places.

---

## 5. Security Note

*   **PII in Logs:** The script saves `user_inputs` and `final_session_state` to local CSV/JSON files.
*   **Workshop Risk:** If participants enter real PII (e.g., their own email/phone), it persists on disk.
*   **Mitigation:** Add a warning in the `README` or a simple PII redaction utility (regex for emails/phones) before saving to disk.

---

## Summary of Refactoring Plan

1.  **Refactor Auth:** Switch `agent_client.py` to `google.auth`.
2.  **Limit Concurrency:** Add `asyncio.Semaphore` to `run_interactions.py`.
3.  **Extract Logic:** Move trace parsing to `utils/trace_analysis.py`.
4.  **Logging:** Replace `print` with `logging.logger`.
