# Development Guide

This document is for maintainers and contributors to the evaluation framework.

---

## Project Structure

```
evaluation/
├── src/evaluation/
│   ├── cli/                    # CLI entry points
│   │   └── main.py             # agent-eval command definitions
│   ├── core/                   # Core evaluation logic
│   │   ├── evaluator.py        # Metric evaluation engine
│   │   ├── data_mapper.py      # Column mapping and transformation
│   │   └── deterministic_metrics.py  # Trace-based metrics
│   ├── interaction/            # Agent interaction
│   │   └── agent_client.py     # API client for live agents
│   └── conversion/             # Data format conversion
│       └── adk_converter.py    # ADK trace converter
├── tests/                      # Test suite
├── docs/                       # Documentation (this folder)
└── pyproject.toml              # Package configuration
```

---

## Running Tests

```bash
cd evaluation
uv sync --dev
uv run pytest tests/ -v
```

### Test Coverage

```bash
uv run pytest tests/ --cov=src/evaluation --cov-report=html
open htmlcov/index.html
```

---

## Test Coverage Analysis

**Last Updated:** 2026-01-11

| Component | Coverage | Status | Notes |
|:---|:---|:---|:---|
| `core/deterministic_metrics.py` | 78% | Good | All 11 metric functions unit tested |
| `core/data_mapper.py` | 70% | Good | Core flattening and event conversion verified |
| `interaction/agent_client.py` | 57% | Fair | Happy path tested; retry logic is the main gap |
| `cli/main.py` | 17% | Integration | Validated via end-to-end runs |

### Gap Analysis

#### Medium Priority: Resilience Testing
- **Component:** `agent_client.py`
- **Gap:** Retry loops for network errors and polling are not covered
- **Risk:** Pipeline might crash on flaky networks
- **Recommendation:** Use `pytest-mock` to simulate `ConnectionError`

#### Low Priority: Feature Gaps
- **Component:** `data_mapper.py`
- **Gap:** Custom template formatting logic untested
- **Risk:** Low, as standard column mapping is the default

---

## Adding New Commands

1. Add command function in `src/evaluation/cli/main.py`:
   ```python
   @app.command()
   def my_command(
       arg: str = typer.Option(..., help="Description"),
   ):
       """Command description."""
       # Implementation
   ```

2. Add tests in `tests/test_cli.py`

3. Update documentation in `docs/04-CLI-REFERENCE.md`

---

## Adding New Metrics

### Deterministic Metrics

Add to `src/evaluation/core/deterministic_metrics.py`:

```python
def calculate_my_metric(trace: List[Dict]) -> Dict[str, Any]:
    """Calculate my custom metric from trace data."""
    # Parse trace spans
    # Return metric dict
    return {
        "my_value": 123,
        "my_rate": 0.95,
    }
```

Register in `calculate_all_deterministic_metrics()`.

### LLM Metrics

Add to your agent's `eval/metrics/metric_definitions.json`:

```json
{
  "metrics": {
    "my_custom_metric": {
      "metric_type": "llm",
      "dataset_mapping": {
        "prompt": {"source_column": "user_inputs"},
        "response": {"source_column": "final_response"}
      },
      "template": "Evaluate this response...\n\nScore: [1-5]"
    }
  }
}
```

---

## Code Style

- Use `ruff` for linting and formatting
- Type hints required for all public functions
- Docstrings required for modules, classes, and public functions

```bash
uv run ruff check src/
uv run ruff format src/
```

---

## Release Process

1. Update version in `pyproject.toml`
2. Run full test suite: `uv run pytest tests/ -v`
3. Update CHANGELOG if maintained
4. Create git tag: `git tag v1.x.x`
5. Push: `git push origin main --tags`

---

## Validation History

- **2026-01-14:** Documentation reorganization
- **2026-01-11:** Achieved P0 test coverage goal (78% for deterministic metrics)
- **2026-01-11:** Verified end-to-end flow for Customer Service and Retail agents

---

## Related Documentation

- [01-GETTING-STARTED.md](01-GETTING-STARTED.md) - User quick start
- [03-METRICS-GUIDE.md](03-METRICS-GUIDE.md) - Defining metrics
- [04-CLI-REFERENCE.md](04-CLI-REFERENCE.md) - CLI reference
