# Contributing & Development Guide

> **Purpose:** This document is for **workshop developers and maintainers** - not participants.
> It contains internal notes, task tracking, architecture decisions, and development context.
> Participants should use [README.md](README.md) for the workshop and [REFERENCE.md](REFERENCE.md) for deep dives.

**Last Updated:** 2026-01-28

---

## Documentation Structure

The workshop uses **2 user-facing files only**:

**1. README.md** - The Workshop Guide (Linear Flow)
Participants follow this step-by-step, never leaving the file:
```
1. Setup (5 min) - Prerequisites, clone, env vars
2. Baseline Evaluations (15 min)
   - Customer Service: ADK User Sim
   - Retail AI: DIY Interactions
3. Add Custom Metric (10 min)
   - Add recommendation_quality to retail-ai
   - Uses final_response.top_recommendation
4. Optimization Branches (40 min)
   - 01-03: Customer Service optimizations
   - 04-05: Retail AI optimizations
5. Wrap-up - Summary, next steps
```

**2. REFERENCE.md** - Deep Dive & Customization
For those who want more detail or to adapt for their own agents:
- CLI Reference (all commands, flags)
- Metric Types Explained
- How to Adapt for Your Own Agent
- Output Files Explained
- Troubleshooting
- Internal Notes (appendix)

### Tasks
| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | Create new README.md | [x] DONE | Main workshop guide with linear flow |
| 2 | Create REFERENCE.md | [x] DONE | Deep dive, CLI, customization |
| 3 | Add recommendation_quality metric | [x] DONE | Custom metric using final_response:top_recommendation |
| 4 | Remove old docs | [ ] Blocked | Delete WORKSHOP_OVERVIEW.md, HOW_TO_USE_REPO.md, etc. |
| 5 | Update PLAN.md | [x] DONE | This update |

### Key Learnings from Custom Metric Implementation (2026-01-28)

**SDK Requirements for Custom LLM Metrics:**
1. Every field in `dataset_mapping` MUST be used in the template (e.g., if you map `response`, use `{response}`)
2. The SDK requires `prompt` and `response` columns - map them explicitly
3. Use `final_response:field_name` syntax to extract nested fields from structured JSON responses

**Gotcha: String vs Structured Responses:**
- When `final_response` is a **structured JSON**, `final_response:top_recommendation` extracts the nested field
- When `final_response` is a **string** (e.g., clarifying questions), nested access returns empty
- The `retail_003_clarifying` test case scored 0 because the agent returned a string asking for more info

**Files Created:**
- `retail-ai-location-strategy/eval/metrics/metric_definitions_with_recommendation.json` - Alternate metrics file with custom metric
- Results saved to `retail-ai-location-strategy/eval/results/20260128_002521_recommendation/`

**Code Fixes Applied:**
- `evaluation/src/evaluation/core/data_mapper.py`: Fixed nested field access from dict columns in agent_df
- `evaluation/src/evaluation/core/data_mapper.py`: Convert dict/list `response` to JSON string for SDK compatibility

### Content Verification (2026-01-28)

**README.md now includes:**
- Note for testers about branches being updated
- "What You'll Learn" objectives
- "The Agent Performance Paradox" context
- Evaluation Framework explanation (3-step process)
- Test Subjects comparison table (Customer Service vs Retail AI)
- Why ADK User Sim vs DIY Interactions for each agent
- MAPS_API_KEY requirement callout
- Context Engineering Principles
- Optimization Milestones with target metrics
- Complete Quick Reference pipelines for both agents

**REFERENCE.md now includes:**
- Environment Setup (prerequisites, IAM, environments, Vertex AI config)
- Complete CLI Reference (all 5 commands with all flags)
- Interaction Modes explanation (ADK User Sim vs DIY)
- Metrics Deep Dive (deterministic, API predefined, custom LLM)
- Creating Custom Metrics (with examples)
- Structured Response Evaluation (fine-grained field access)
- Output Files (folder structure, eval_summary.json, JSONL fields)
- Data Formats (Golden Dataset, Scenario, Session Input, Processed JSONL)
- Adapting for Your Own Agent
- Creating Custom Simulations
- Troubleshooting (all known issues)
- Understanding Trade-offs
- Context Engineering Principles
- AI Assistant Setup
- Internal Notes (ADK data extraction, development setup, key decisions)

---

## Phase 1: Initial Refactoring (Completed)

---

## Context Summary

### Workshop Flow (from presentation slides)

1. **Intro (10m)** - Jesse
2. **Evaluating Agents (5m)** - Jesse - Why agents are different, the visibility gap, prompt trap, validation hurdle
3. **Agentic Evaluation Framework (10m)** - Dani - 3-step process:
   - 1/3 Run Agent Interactions (DIY + ADK User Sim)
   - 2/3 Run Evaluation (Vertex AI GenAI Eval Service)
   - 3/3 Analyze Results (Dashboard + Gemini Markdown)
4. **Agent Optimizations (55m)** - John/Hugo - M0-M5 milestones:
   - M0: Naive Monolith (baseline)
   - M1: Tool Hardening
   - M2: Context Compaction
   - M3: Functional Isolation
   - M4: Offloading
   - M5: Prefix Caching

### Current State Issues

- Documentation fragmented across 10+ markdown files
- Root README mixes workshop content with technical setup
- Developer history docs (ADK extraction analysis, session changelogs) mixed with user-facing docs
- eval_config usage adds latency but isn't needed for our evaluation approach
- evalset.json files append scenarios on each run (stale data accumulates)
- No clear separation between "what is this workshop" and "how do I set it up"

### Target State

- **WORKSHOP_OVERVIEW.md** - Aligns with presentation, explains the evaluation framework
- **HOW_TO_USE_REPO.md** - Technical setup and usage guide
- **DEVELOPER_REFERENCE.md** - Internal team history docs consolidated
- **Root README.md** - Landing page that links to the above
- Clean scenario files, setup script, AI assistant context files

---

## Task List

### Phase 1: Core Documentation (Priority - Do First)

| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | Create WORKSHOP_OVERVIEW.md | [x] DONE | Main workshop README aligned with presentation flow. Explains evaluation framework, hill climb methodology, signal identification, Context Engineering principles. |
| 2 | Create HOW_TO_USE_REPO.md | [x] DONE | Complete practical guide with setup, CLI reference, metrics guide, troubleshooting. All content consolidated from numbered docs. |
| 3 | Create DEVELOPER_REFERENCE.md | [x] DONE | Consolidated internal docs (ADK extraction analysis, session changelogs, multi-turn metrics). Located at `/evaluation/DEVELOPER_REFERENCE.md`. |

### Phase 2: Cleanup & Configuration (Can Run in Parallel)

| # | Task | Status | Description |
|---|------|--------|-------------|
| 4 | Streamline simulations | [x] DONE | Cleared evalset.json files (they're auto-generated by `adk eval` and append scenarios). Kept single-scenario files. |
| 5 | Remove eval_config usage | [x] DONE | Removed --config_file_path from all docs. ADK User Sim runs without it for better latency. |
| 6 | Update .env.example files | [x] DONE | Added Vertex AI warning to both agent .env.example files. Removed API key option. |
| 7 | Create setup_workshop.sh | [x] DONE | Environment verification script: checks Python, uv, gcloud, Vertex AI, warns about API keys. |
| 8 | Create GEMINI.md | [x] DONE | AI assistant context file with repo overview, workshop objectives, key patterns. |
| 9 | Audit repository branches | [x] DONE | Branches documented in HOW_TO_USE_REPO.md (main + optimizations/01-05). |
| 10 | Create AGENT_EVAL_REFERENCE.md | [x] DONE | Deep dive on CLI, metrics, output files. Located at `/evaluation/AGENT_EVAL_REFERENCE.md`. |

### Phase 3: Finalization (After Phase 1)

| # | Task | Status | Blocked By | Description |
|---|------|--------|------------|-------------|
| 11 | Clean up old eval docs | [x] DONE | #1, #2, #3 | Removed all numbered docs (01-05) and dev docs. Deleted evaluation/docs/ folder. |
| 13 | Update root README.md | [x] DONE | #1, #2 | Converted to landing page linking to main docs. Added note about agents not needing to run for eval. |
| 12 | Final review | [x] DONE | All above | **Hands-on walkthrough as a developer:** Followed docs step-by-step, ran actual commands, fixed 10+ issues discovered. Both Customer Service (ADK User Sim) and Retail AI (DIY Interactions) pipelines verified end-to-end. |

---

## Current File Structure (After Refactoring)

### Root Level
- `/WORKSHOP_OVERVIEW.md` - Conceptual guide aligned with presentation
- `/HOW_TO_USE_REPO.md` - Complete practical guide (setup, CLI, metrics, troubleshooting)
- `/README.md` - Landing page linking to main docs
- `/GEMINI.md` - AI assistant context file
- `/setup_workshop.sh` - Environment verification script
- `/PLAN.md` - This file (task tracking)

### Evaluation Directory
- `/evaluation/AGENT_EVAL_REFERENCE.md` - Deep dive on agent-eval CLI, metrics, output files
- `/evaluation/DEVELOPER_REFERENCE.md` - Internal team reference (ADK extraction, session changelogs)
- `/evaluation/README.md` - Evaluation module overview (kept as-is)

### Agent Directories (unchanged)
- `/customer-service/` - Customer Service agent with updated `.env.example`
- `/retail-ai-location-strategy/` - Retail AI agent with updated `.env.example`

### Files REMOVED
- `evaluation/docs/` folder (entire directory deleted)
- `evaluation/docs/01-GETTING-STARTED.md` through `05-OUTPUT-FILES.md` (consolidated into main docs)
- `evaluation/docs/ADK-DATA-EXTRACTION-ANALYSIS.md` (consolidated into DEVELOPER_REFERENCE.md)
- `evaluation/docs/ADK-EVAL-HISTORY-DATA-REFERENCE.md` (consolidated into DEVELOPER_REFERENCE.md)
- `evaluation/docs/CONTEXT-HANDOFF-MULTI-TURN-METRICS.md` (consolidated into DEVELOPER_REFERENCE.md)
- `evaluation/docs/99-DEVELOPMENT.md` (consolidated into DEVELOPER_REFERENCE.md)
- All `*.evalset.json` files (auto-generated by `adk eval`)

---

## Content Mapping: Slides to Documentation

| Slide Section | Target Document | Content |
|---------------|-----------------|---------|
| "Why Agents are Different" | WORKSHOP_OVERVIEW.md | Not deterministic, process matters, conversational depth |
| "Evaluation Framework: Build, Test, Learn, Deploy" | WORKSHOP_OVERVIEW.md | 3-step process diagram explanation |
| "1/3 Running Agent Interactions" | WORKSHOP_OVERVIEW.md | DIY interactions + ADK User Sim |
| "2/3 Running Evaluations" | WORKSHOP_OVERVIEW.md | Vertex AI Eval Service, metrics |
| "3/3 Analyzing Results" | WORKSHOP_OVERVIEW.md | Dashboard + Gemini markdown |
| "Context Engineering Pillars" | WORKSHOP_OVERVIEW.md | M0-M5 optimizations overview |
| Prerequisites, Setup | HOW_TO_USE_REPO.md | Python, UV, GCP, Vertex AI |
| Agent Commands | HOW_TO_USE_REPO.md | Customer Service + Retail commands |
| Branch Strategy | HOW_TO_USE_REPO.md | Branch-per-optimization table |

---

## Important Callouts to Include

### Vertex AI Requirement
```
WARNING: You must configure GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION.
Do not use GOOGLE_API_KEY.
The Evaluation Pipeline metrics require Vertex AI traces; API keys will result in empty dashboard charts.
```

### Why No eval_config
```
Note: We skip the ADK eval_config (--config_file_path) because adding it affects simulation latency.
Since we run our own evaluations via the agent-eval CLI, we skip the ADK user-sim eval step.
```

### Agent-Specific READMEs
```
The READMEs in customer-service/ and retail-ai-location-strategy/ are kept as-is from ADK samples
to demonstrate how you can take an existing ADK agent and adapt the evaluation framework for your use case.
```

---

## Progress Log

### 2026-01-27 (Session 1)

- [x] Pulled 20 new commits from team (Liz, John, Hugo)
- [x] Created TEAM_COMMITS_SUMMARY.md with commit details
- [x] Analyzed all existing markdown files
- [x] Reviewed presentation slides (PDF)
- [x] Created comprehensive task list (13 tasks)
- [x] Created WORKSHOP_OVERVIEW.md (conceptual guide aligned with presentation)
- [x] Created HOW_TO_USE_REPO.md (complete practical guide)
- [x] Created DEVELOPER_REFERENCE.md (consolidated internal docs)
- [x] Created AGENT_EVAL_REFERENCE.md (CLI, metrics, output files deep dive)
- [x] Updated root README.md as landing page
- [x] Created setup_workshop.sh (environment verification)
- [x] Created GEMINI.md (AI assistant context)
- [x] Updated .env.example files with Vertex AI warnings
- [x] Cleared evalset.json files and eval_history folders
- [x] Removed all numbered docs (01-05) from evaluation/docs/
- [x] Removed evaluation/docs/ folder entirely
- [x] Moved AGENT_EVAL_REFERENCE.md and DEVELOPER_REFERENCE.md to evaluation/ root
- [x] **COMPLETED:** Task #12 - Final hands-on review as developer

### Fixes Applied During Developer Walkthrough
- Fixed `setup_workshop.sh` "Next steps" to not mention `make playground`
- Fixed `setup_workshop.sh` Vertex AI check to handle auth token refresh gracefully
- Fixed evalset.json cleanup path in HOW_TO_USE_REPO.md (was `eval/scenarios/*.evalset.json`, should be `customer_service/*.evalset.json`)
- Fixed same path in WORKSHOP_OVERVIEW.md Quick Reference
- Removed `_documentation` field from scenario JSON files (ADK Pydantic validation rejects extra fields)
- Streamlined scenario files: 5 scenarios for customer-service, 2 for retail-ai
- Disabled HTML report and infographic generation stages in retail-ai for faster simulation
- Updated agent.py descriptions to match disabled stages
- Fixed `agent_client.py` to skip gcloud auth for localhost URLs (DIY path fix)
- Fixed `interact` command to output JSONL instead of CSV (proper nested JSON handling)
- Fixed `evaluator.py` to use `read_jsonl` instead of `pd.read_json` (handles large JSON values)
- Added request/response fields to processor.py for managed metrics compatibility
- Created golden_dataset.json for retail-ai DIY interactions
- Updated HOW_TO_USE_REPO.md to recommend ADK User Sim for customer-service, DIY for retail-ai

### Evaluation Pipelines Verified
**Customer Service (ADK User Sim):**
- Full pipeline: adk eval → convert → evaluate → analyze
- All 5 scenarios processed, all metrics computed
- Generated eval_summary.json, question_answer_log.md, gemini_analysis.md

**Retail AI (DIY Interactions):**
- Full pipeline: interact → evaluate → analyze
- All 3 golden dataset questions processed (2 full pipeline, 1 clarifying)
- Gemini analysis correctly identified "Hallucination by Simulation" issue (agent simulating tool outputs)
- Pipeline integrity metric caught the issue (score: 1.0/5.0 for fabricated analysis)

---

## Notes for Future Context

If resuming this work in a new session:

### Quick Start
1. Read this PLAN.md first for full context
2. Only **Task #12 (Final Review)** remains - this is a hands-on walkthrough
3. Follow HOW_TO_USE_REPO.md as a new developer would, running actual commands

### Critical ADK Command Syntax
The correct ADK User Sim workflow (verified against official docs):
```bash
# 1. Clear previous data (evalset.json files APPEND, so must clear)
rm -rf customer_service/.adk/eval_history/*
rm -f customer_service/*.evalset.json

# 2. Create eval set
uv run adk eval_set create customer_service eval_set_with_scenarios

# 3. Add scenarios
uv run adk eval_set add_eval_case customer_service eval_set_with_scenarios \
  --scenarios_file eval/scenarios/conversation_scenarios.json \
  --session_input_file eval/scenarios/session_input.json

# 4. Run simulation (NO --config_file_path - it adds latency)
uv run adk eval customer_service eval_set_with_scenarios
```

### Key Terminology
- Use "DIY interactions" and "ADK User Sim" (NOT "Path A / Path B")
- `adk eval` runs against source code directly - NO need to run `make playground` for evaluation

### Critical Requirement
- **MUST use Vertex AI** (GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION)
- **NEVER use GOOGLE_API_KEY** - Evaluation metrics require Vertex AI traces

### Workshop Context
- Target audience: Technical GTM practitioners (not deep ML experts)
- Two agents: Customer Service (multi-turn, reliability) and Retail AI (single-turn, scale)
- Presentation flow: "Why evaluate agents differently" → "3-step framework" → "Hands-on optimizations (M0-M5)"

### Files to Reference
- `/WORKSHOP_OVERVIEW.md` - Conceptual guide (aligns with presentation)
- `/HOW_TO_USE_REPO.md` - Practical setup and usage
- `/evaluation/AGENT_EVAL_REFERENCE.md` - CLI and metrics deep dive
- `/evaluation/DEVELOPER_REFERENCE.md` - Internal team reference
