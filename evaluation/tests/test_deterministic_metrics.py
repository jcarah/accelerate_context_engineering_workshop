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
    evaluate_deterministic_metrics
)

@pytest.fixture
def simple_trace():
    trace_path = Path(__file__).parent / "test_data" / "deterministic_traces" / "simple_trace.json"
    with open(trace_path, "r") as f:
        return json.load(f)

def test_calculate_token_usage(simple_trace):
    score, explanation, details = calculate_token_usage(simple_trace)
    
    # gemini-1.5-flash: (0.000075, 0.0003) per 1k
    # 1000 prompt, 50 completion
    expected_cost = (1000/1000 * 0.000075) + (50/1000 * 0.0003)
    
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
    assert details["time_to_first_response_seconds"] == 2.2 # (llm_end - root_start) = 2.2 - 0.0 ? No, root starts at 0.0
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

def test_evaluate_deterministic_metrics(simple_trace):
    results = evaluate_deterministic_metrics(
        session_state={},
        session_trace=simple_trace,
        agents_evaluated=["my_agent"],
        question_metadata={},
        metrics_to_run=["token_usage", "tool_utilization"]
    )
    
    assert "token_usage" in results
    assert "tool_utilization" in results
    assert results["token_usage"]["score"] > 0
    assert results["tool_utilization"]["score"] == 1.0
