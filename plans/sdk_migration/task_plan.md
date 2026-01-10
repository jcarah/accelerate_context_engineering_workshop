# Task Plan: Migrate Evaluation SDK to Vertex AI Client

## Goal
Refactor `evaluation/02_agent_run_eval.py` to replace the legacy `EvalTask` interface with the modern `vertexai.Client` and `client.evals.evaluate` API, ensuring compatibility with the latest Google Cloud AI Platform features.

## Current Phase
Phase 2: Refactoring

## Phases
### Phase 1: Requirements & Discovery
- [x] Analyze `02_agent_run_eval.py` to understand current implementation ✓
- [x] Check `pyproject.toml` for `google-cloud-aiplatform` version compatibility (needs >=1.38, have ~1.95.1) ✓
- [x] Document findings in `findings.md` ✓
- **Status:** complete

### Phase 2: Refactoring
- [ ] Import `Client` from `vertexai`
- [ ] Initialize `client` with project/location
- [ ] Replace `EvalTask` loop with `client.evals.evaluate` calls
- [ ] Update result parsing logic for `EvalResult` objects
- **Status:** in_progress

### Phase 3: Testing & Verification
- [ ] Create unit tests (`evaluation/tests/test_eval_migration.py`) mocking `vertexai.Client` to verify the new call structure.
- [ ] Run unit tests: `uv run pytest evaluation/tests/test_eval_migration.py`
- [ ] Run full script `02_agent_run_eval.py` with a small sample dataset (integration test).
- [ ] Verify output CSV structure and summary JSON.
- **Status:** pending

### Phase 4: Delivery
- [ ] Commit changes
- [ ] Update `DEVELOPER_GUIDE.md` if necessary
- **Status:** pending

## Key Questions
1. Does `client.evals.evaluate` support `PointwiseMetric` objects directly? (Yes, per documentation)
2. Does the return type `EvalResult` expose metrics in the same way `EvalTask.evaluate()` did? (Structure is slightly different, requires mapping)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use `vertexai.Client` | Recommended path forward for Gen AI evaluation on Google Cloud. |
| Keep `PointwiseMetric` | Compatible with new Client API, minimizes code churn for template definitions. |
| Add Unit Tests | Mocking `vertexai.Client` ensures logic correctness without incurring API costs or latency. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| | | |

## Notes
- **Context Management:** This file serves as the "Attention Anchor" to prevent goal drift during the refactoring code edits.
- **Reference:** `evaluation/02_agent_run_eval.py` lines 430-465 contain the main `EvalTask` loop to replace.