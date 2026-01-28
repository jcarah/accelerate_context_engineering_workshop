# Branch Update Plan

**Created:** 2026-01-28
**Objective:** Update optimization branches to sync with main, run evaluations, and track README issues.

---

## Context & Objective

The workshop has optimization branches (01-05) that need to:
1. Be merged with latest `main` branch
2. Keep ONLY agent source code changes from each branch
3. Have evaluations run to create `optimization/` folders alongside `baseline/` in `eval/results/`

### Branch → Agent Mapping

| Branch | Agent | Optimization |
|--------|-------|--------------|
| `optimizations/01-tool-definition` | Customer Service | Tool Schema Hardening |
| `optimizations/02-context-compaction` | Customer Service | Context Compaction |
| `optimizations/03-code-execution` | Customer Service | Offload to Python Sandbox |
| `optimizations/04-functional-isolation` | Retail AI | Split into Sub-Agents |
| `optimizations/05-prefix-caching` | Retail AI | Prefix Caching |

### Expected Folder Structure After Completion

```
customer-service/eval/results/
├── baseline/           # Already exists from main
└── optimization/       # Created after running eval on optimized code

retail-ai-location-strategy/eval/results/
├── baseline/           # Already exists from main
└── optimization/       # Created after running eval on optimized code
```

---

## Current State (Updated 2026-01-28)

**Branches that exist on remote:**
- `origin/optimizations/01-tool-definition` (Customer Service)
- `origin/optimizations/02-context-compaction` (Customer Service)
- `origin/optimizations/03-functional-isolation` (Customer Service)
- `origin/optimizations/04-offload-and-reduce` (Retail AI)

**Branches NOT on remote:**
- `optimizations/05-prefix-caching` (does not exist)

**README vs Actual Branch Names (MISMATCH):**
- README says `03-code-execution` → Actual: `03-functional-isolation`
- README says `04-functional-isolation` → Actual: `04-offload-and-reduce`
- README says `05-prefix-caching` → Does not exist

---

## Task List

### Phase 1: Branch 01 (Customer Service)

- [ ] **1.1** Checkout `optimizations/01-tool-definition`
- [ ] **1.2** Identify agent code changes (diff with main)
- [ ] **1.3** Merge main into branch (resolve conflicts keeping agent code)
- [ ] **1.4** Run Customer Service evaluation pipeline:
  ```bash
  cd customer-service
  rm -rf customer_service/.adk/eval_history/*
  uv run adk eval_set create customer_service eval_set_with_scenarios
  uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
    --scenarios_file eval/scenarios/conversation_scenarios.json \
    --session_input_file eval/scenarios/session_input.json
  uv run adk eval customer_service eval_set_with_scenarios

  cd ../evaluation
  uv run agent-eval convert \
    --agent-dir ../customer-service/customer_service \
    --output-dir ../customer-service/eval/results
  # Rename result folder to "optimization"
  uv run agent-eval evaluate \
    --interaction-file ../customer-service/eval/results/optimization/raw/processed_interaction_sim.jsonl \
    --metrics-files ../customer-service/eval/metrics/metric_definitions.json \
    --results-dir ../customer-service/eval/results/optimization \
    --input-label optimization-01
  uv run agent-eval analyze \
    --results-dir ../customer-service/eval/results/optimization \
    --agent-dir ../customer-service \
    --location global
  ```
- [ ] **1.5** Commit and push changes
- [ ] **1.6** Document any README issues found

### Phase 2: Check Other Branches

- [ ] **2.1** Check if branches 02-05 exist locally or need to be created
- [ ] **2.2** For each existing branch, repeat the process

---

## README Issues Found

Track any discrepancies between README instructions and actual behavior:

| # | Issue | Location | Fix Needed |
|---|-------|----------|------------|
| 1 | (To be filled during execution) | | |

---

## Key Commands Reference

### Customer Service Evaluation (ADK User Sim)
```bash
cd customer-service
rm -rf customer_service/.adk/eval_history/*
uv run adk eval_set create customer_service eval_set_with_scenarios
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json
uv run adk eval customer_service eval_set_with_scenarios

cd ../evaluation
uv run agent-eval convert --agent-dir ../customer-service/customer_service --output-dir ../customer-service/eval/results
uv run agent-eval evaluate --interaction-file <RUN_DIR>/raw/processed_interaction_sim.jsonl --metrics-files ../customer-service/eval/metrics/metric_definitions.json --results-dir <RUN_DIR>
uv run agent-eval analyze --results-dir <RUN_DIR> --agent-dir ../customer-service --location global
```

### Retail AI Evaluation (DIY Interactions)
```bash
# Terminal 1: Start agent
cd retail-ai-location-strategy && make dev

# Terminal 2: Run eval
cd evaluation
uv run agent-eval interact --app-name app --questions-file ../retail-ai-location-strategy/eval/eval_data/golden_dataset.json --base-url http://localhost:8502 --results-dir ../retail-ai-location-strategy/eval/results
uv run agent-eval evaluate --interaction-file <RUN_DIR>/raw/processed_interaction_app.jsonl --metrics-files ../retail-ai-location-strategy/eval/metrics/metric_definitions.json --results-dir <RUN_DIR>
uv run agent-eval analyze --results-dir <RUN_DIR> --agent-dir ../retail-ai-location-strategy --location global
```

---

## Notes

- Each optimization branch should have agent code changes ONLY
- All other files (docs, eval framework, etc.) come from main
- The `baseline/` folder already exists from main branch
- Create `optimization/` folder by renaming timestamped folder after running eval
