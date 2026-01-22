# Friction Log: Accelerate Context Engineering Workshop

**Repository:** https://github.com/jcarah/accelerate_context_engineering_workshop/
**Date:** 2026-01-14
**Status:** Updated

---

## Executive Summary

This log tracks the status of friction points identified in the workshop repository.
**Major progress has been made:** Critical documentation gaps (Setup, .env configuration, Evaluation guidance) have been addressed.
**Current Focus:** The primary remaining friction is a discrepancy between the documentation (which promises a `make verify` command) and the code (which lacks it), along with minor version/configuration inconsistencies.

---

## 1. Active Issues (To Be Fixed)

### 1.1 🔴 CRITICAL: Missing `make verify` Target

**Issue:**
The Main README (Section 2) instructs users to run:
```bash
make verify  # Available in each agent directory
```
However, this target **does not exist** in `customer-service/Makefile` or `retail-ai-location-strategy/Makefile`.

**User Impact:**
- Users follow instructions and get `make: *** No rule to make target 'verify'. Stop.`
- Creates immediate distrust in the documentation.

**Suggested Fix:**
Add the `verify` target to both Makefiles as documented in the log's Phase 2 plan.

### 1.2 🟢 MEDIUM: UV Version Discrepancy

**Issue:**
- `customer-service/Makefile`: Uses `uv/0.8.13`
- `retail-ai-location-strategy/Makefile`: Uses `uv/0.6.12`

**Suggested Fix:**
Standardize both to the latest stable version (e.g., `0.8.13`).

### 1.3 🟢 MEDIUM: Evaluation `convert` Command Output

**Issue:**
`agent-eval convert` prints the run folder but does not provide the copy-pasteable `evaluate` command, forcing users to manually construct paths.

**Suggested Fix:**
Update `evaluation/src/evaluation/cli/convert.py` to print the next steps.

### 1.4 🔵 LOW: Python Version Documentation

**Issue:**
- Retail README correctly specifies "Python 3.10-3.12".
- Customer Service README says "Python 3.10+", which is ambiguous (3.13 is not supported).

**Suggested Fix:**
Update Customer Service README to match Retail.

### 1.5 🔵 LOW: Gitignore Security

**Issue:**
`retail-ai-location-strategy/.env` is tracked in git (or at least not ignored in the root `.gitignore`), posing a risk if users modify it in place.

**Suggested Fix:**
Add `**/.env` to root `.gitignore`.

---

## 2. Resolved Issues (2026-01-14)

The following issues have been **fixed** in the documentation and configuration:

### Documentation Clarity
- ✅ **Unclear Eval README Reference:** Main README now correctly positions the "Deep Dive" link *after* the quickstart.
- ✅ **Evaluation Interpretation:** Added "Step 4: Interpret Your Results" with a metric threshold table to the Main README.
- ✅ **AG-UI Mention:** Added AG-UI setup instructions to the Retail Agent section.

### Configuration & Setup
- ✅ **.env Location:** Retail agent instructions now explicitly state `.env` is in the project root.
- ✅ **Customer Service Setup:** Added explicit `cp .env.example .env` instructions.
- ✅ **Port Numbers:** Added explicit port numbers (8501 vs 8502) to all READMEs.
- ✅ **Makefile Targets:** Added `dev: playground` alias to `customer-service/Makefile` for consistency.
- ✅ **Eval History Cleanup:** Added `⚠️ CRITICAL` warning box about clearing `.adk/eval_history`.

---

## 3. Suggested Next Actions

1.  **Implement `make verify`** in both agent Makefiles (Priority: Critical).
2.  **Bump UV version** in Retail Makefile to match Customer Service.
3.  **Update Customer Service README** to specify "Python 3.10-3.12".

---
