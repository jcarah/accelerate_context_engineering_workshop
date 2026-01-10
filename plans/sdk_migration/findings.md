# Findings & Decisions

## Requirements
- Migrate `evaluation/02_agent_run_eval.py` from `EvalTask` to `vertexai.Client`.
- Maintain existing functionality (loading metrics from JSON, aggregating results).
- Ensure backward compatibility with existing CI/CD pipelines (`evaluation.yml`).

## Research Findings
- **Current Implementation:**
    - Uses `vertexai.evaluation.EvalTask` and `PointwiseMetric`.
    - Manually constructs a pandas DataFrame for the dataset.
    - Loops through metrics, creating one `EvalTask` per metric/agent combination.
    - Parses results from `task.evaluate().metrics_table`.
- **Target Implementation:**
    - `vertexai.Client` provides a unified entry point.
    - `client.evals.evaluate(dataset=df, metrics=[metric])` is the direct replacement.
    - `PointwiseMetric` is compatible with the new client.
- **Dependency Check:**
    - `evaluation/pyproject.toml` lists `google-cloud-aiplatform[evaluation,agent-engines]~=1.95.1`.
    - This version is sufficient for `vertexai.Client` features.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| **Reuse `PointwiseMetric`** | The new `client.evals.evaluate` accepts a list of metrics, which can include `PointwiseMetric` instances. Reusing the existing metric instantiation logic reduces risk and effort. |
| **Maintain DataFrame Dataset** | `client.evals.evaluate` accepts a pandas DataFrame, so the existing data preparation logic in `02_agent_run_eval.py` (lines 350-420) can be preserved 100%. |
| **Update Result Parsing** | The return object of `client.evals.evaluate` is an `EvalResult`. We need to verify if `.metrics_table` is still the correct attribute (it usually is) or if we need to access `.summary_metrics` or `.row_based_metrics`. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| N/A | |

## Resources
- [Vertex AI Gen AI Evaluation Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview)
- Existing Code: `evaluation/02_agent_run_eval.py`
