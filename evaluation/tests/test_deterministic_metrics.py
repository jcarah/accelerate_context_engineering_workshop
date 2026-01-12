import json
import pytest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from evaluation.scripts.deterministic_metrics import (
    calculate_token_usage,
    calculate_latency_metrics,
    calculate_tool_utilization,
    calculate_tool_success_rate,
    evaluate_deterministic_metrics,
    calculate_cache_efficiency,
    calculate_thinking_metrics,
    calculate_grounding_utilization,
    calculate_context_saturation,
    calculate_agent_handoffs,
    calculate_output_density,
    calculate_sandbox_usage,
)


@pytest.fixture
def simple_trace():
    trace_path = (
        Path(__file__).parent
        / "test_data"
        / "deterministic_traces"
        / "simple_trace.json"
    )
    with open(trace_path, "r") as f:
        return json.load(f)


@pytest.fixture
def complex_trace():
    trace_path = (
        Path(__file__).parent
        / "test_data"
        / "deterministic_traces"
        / "complex_trace.json"
    )
    with open(trace_path, "r") as f:
        return json.load(f)


def test_calculate_token_usage(simple_trace):
    score, explanation, details = calculate_token_usage(simple_trace)

    # gemini-1.5-flash: (0.000075, 0.0003) per 1k
    # 1000 prompt, 50 completion
    expected_cost = (1000 / 1000 * 0.000075) + (50 / 1000 * 0.0003)

    assert details["llm_calls"] == 1
    assert details["prompt_tokens"] == 1000
    assert details["completion_tokens"] == 50
    assert pytest.approx(details["estimated_cost_usd"], 0.000001) == expected_cost
    assert "Cost: $" in explanation


def test_calculate_latency_metrics(simple_trace):
    score, explanation, details = calculate_latency_metrics(simple_trace)

    # call_llm: 1700000000200000000 to 1700000002200000000 = 2.0s
    # tool_call: 1700000002300000000 to 1700000003300000000 = 1.0s
    # max_end - min_start: 5.0s (based on invocation span)

    assert details["llm_latency_seconds"] == 2.0
    assert details["tool_latency_seconds"] == 1.0
    assert details["total_latency_seconds"] == 5.0
    assert (
        details["time_to_first_response_seconds"] == 2.2
    )  # (llm_end - root_start) = 2.2 - 0.0 ? No, root starts at 0.0
    # Let's check: sorted_spans[0] is 'invocation' at ...000.
    # llm_end is ...200. (2.2s - 0.0s) = 2.2s.


def test_calculate_tool_utilization(simple_trace):
    score, explanation, details = calculate_tool_utilization(simple_trace)

    assert details["total_tool_calls"] == 1
    assert details["unique_tools_used"] == 1
    assert details["tool_counts"]["search_tool"] == 1


def test_calculate_tool_success_rate(simple_trace):
    score, explanation, details = calculate_tool_success_rate(simple_trace)

    assert details["tool_success_rate"] == 1.0
    assert details["failed_tool_calls"] == 0


def test_calculate_cache_efficiency(complex_trace):
    score, explanation, details = calculate_cache_efficiency(complex_trace)

    # 500 cached / (500 cached + 1500 fresh) = 500/2000 = 0.25
    # Call 1: 500 cached, 500 fresh.
    # Call 2: 0 cached, 1000 fresh.
    # Total Cached: 500. Total Fresh: 1500. Total Input: 2000.
    assert details["total_cached_tokens"] == 500
    assert details["total_fresh_prompt_tokens"] == 1500
    assert details["cache_hit_rate"] == 0.25


def test_calculate_thinking_metrics(complex_trace):
    score, explanation, details = calculate_thinking_metrics(complex_trace)

    # Call 1: 100 thoughts, 200 candidates. Total output = 300.
    # Call 2: 0 thoughts, 50 candidates. Total output = 50.
    # Total thoughts: 100. Total output: 350.
    # Ratio: 100 / 350 = 0.2857...
    assert details["total_thinking_tokens"] == 100
    assert details["turns_with_thinking"] == 1
    assert pytest.approx(details["reasoning_ratio"], 0.001) == 100 / 350


def test_calculate_grounding_utilization(complex_trace):
    score, explanation, details = calculate_grounding_utilization(complex_trace)

    # Call 1: 2 chunks.
    # Call 2: 0 chunks.
    assert details["total_grounding_chunks"] == 2
    assert details["total_grounded_responses"] == 1
    assert score == 2.0


def test_calculate_context_saturation(complex_trace):
    score, explanation, details = calculate_context_saturation(complex_trace)

    # Call 1: 1200 total.
    # Call 2: 1050 total.
    # Max: 1200.
    assert details["max_total_tokens"] == 1200
    assert details["peak_usage_span"] == "call_llm"
    assert score == 1200.0


def test_calculate_agent_handoffs(complex_trace):
    score, explanation, details = calculate_agent_handoffs(complex_trace)

    # 1 "invoke_agent SpecialistAgent"
    assert details["total_handoffs"] == 1
    assert "SpecialistAgent" in details["agents_invoked_list"]
    assert score == 1.0


def test_calculate_output_density(complex_trace):
    score, explanation, details = calculate_output_density(complex_trace)

    # Call 1: 200 candidates (thoughts are excluded from output density in this implementation?
    # Let's check logic: output_tokens = usage.get("candidates_token_count", 0).
    # Yes, standard output density usually focuses on final response length).
    # Call 1: 200. Call 2: 50.
    # Total: 250. Calls: 2. Avg: 125.
    assert details["total_output_tokens"] == 250
    assert details["average_output_tokens"] == 125.0
    assert score == 125.0


def test_calculate_sandbox_usage(complex_trace):
    score, explanation, details = calculate_sandbox_usage(complex_trace)

    # 1 call to "read_file". Matches keyword.
    assert details["total_sandbox_ops"] == 1
    assert "read_file" in details["sandbox_tools_used"]
    assert score == 1.0


def test_evaluate_deterministic_metrics(simple_trace):
    results = evaluate_deterministic_metrics(
        session_state={},
        session_trace=simple_trace,
        agents_evaluated=["my_agent"],
        question_metadata={},
        metrics_to_run=["token_usage", "tool_utilization"],
    )

    assert "token_usage" in results
    assert "tool_utilization" in results
    assert results["token_usage"]["score"] > 0
    assert results["tool_utilization"]["score"] == 1.0
