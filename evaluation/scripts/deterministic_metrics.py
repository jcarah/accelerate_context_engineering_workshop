"""
Deterministic metrics for evaluating agent execution success.

These metrics provide objective pass/fail measurements by analyzing trace data
and session state, without requiring LLM-as-judge evaluation.
"""

import json
from typing import Any, Dict, List, Tuple

# Pricing per 1K tokens (approximate list prices for prompts <= 200k tokens)
# Format: {model_name: (prompt_price, completion_price)}
# Source: https://ai.google.dev/gemini-api/docs/pricing
MODEL_PRICING = {
    # Gemini 3 (Latest Preview)
    "gemini-3-pro-preview": (0.002, 0.012),      # $2.00 / $12.00 per 1M
    "gemini-3-flash-preview": (0.0005, 0.003),    # $0.50 / $3.00 per 1M
    
    # Gemini 2.5 (Current Flagship)
    "gemini-2.5-pro": (0.00125, 0.01),           # $1.25 / $10.00 per 1M
    "gemini-2.5-flash": (0.0003, 0.0025),         # $0.30 / $2.50 per 1M
    
    # Gemini 2.0
    "gemini-2.0-flash": (0.0001, 0.0004),         # $0.10 / $0.40 per 1M
    "gemini-2.0-flash-exp": (0.0001, 0.0004),     # Same as 2.0 flash
    "gemini-2.0-flash-lite": (0.000075, 0.0003),  # $0.075 / $0.30 per 1M
    
    # Gemini 1.5 (Updated/Reduced Prices)
    "gemini-1.5-pro": (0.00125, 0.01),           # Reduced from 0.0035/0.0105
    "gemini-1.5-pro-001": (0.00125, 0.01),
    "gemini-1.5-flash": (0.000075, 0.0003),       # $0.075 / $0.30 per 1M
    "gemini-1.5-flash-001": (0.000075, 0.0003),
    
    # Legacy
    "gemini-1.0-pro": (0.0005, 0.0015),          # $0.50 / $1.50 per 1M
    "default": (0.0001, 0.0004)                   # Fallback to 2.0 Flash
}

def calculate_token_usage(
    session_trace: List[Dict[str, Any]]
) -> Tuple[float, str, Dict[str, Any]]:
    """
    Informational metric: Track token usage and estimated cost based on the specific model used.
    """
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    llm_calls = 0
    total_cost = 0.0
    models_used = set()
    
    if not session_trace:
         return 0.0, "No trace data available for token usage calculation", {}

    for span in session_trace:
        attributes = span.get('attributes', {})
        
        # Identify model
        model_name = attributes.get('gen_ai.request.model', 'default').lower()
        
        # Check for LLM response with usage metadata
        llm_response = attributes.get('gcp.vertex.agent.llm_response')
        if llm_response:
            try:
                response_data = json.loads(llm_response) if isinstance(llm_response, str) else llm_response
                usage = response_data.get('usage_metadata', {})
                
                if usage:
                    llm_calls += 1
                    models_used.add(model_name)
                    
                    p_tokens = usage.get('prompt_token_count', 0)
                    c_tokens = usage.get('candidates_token_count', 0)
                    t_tokens = usage.get('total_token_count', 0)
                    
                    total_prompt_tokens += p_tokens
                    total_completion_tokens += c_tokens
                    total_tokens += t_tokens
                    
                    # Match model pricing
                    pricing = MODEL_PRICING["default"]
                    for known_model, prices in MODEL_PRICING.items():
                        if known_model in model_name:
                            pricing = prices
                            break
                    
                    call_cost = (p_tokens / 1000 * pricing[0]) + (c_tokens / 1000 * pricing[1])
                    total_cost += call_cost
                    
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
    
    explanation = (
        f"Usage: {llm_calls} LLM calls using {list(models_used)}. "
        f"Tokens: {total_tokens} ({total_prompt_tokens}p + {total_completion_tokens}c). "
        f"Cost: ${total_cost:.6f}"
    )
    
    details = {
        'llm_calls': llm_calls,
        'models_used': list(models_used),
        'total_tokens': total_tokens,
        'prompt_tokens': total_prompt_tokens,
        'completion_tokens': total_completion_tokens,
        'estimated_cost_usd': total_cost
    }
    
    return total_cost, explanation, details


def calculate_latency_metrics(
    session_trace: List[Dict[str, Any]],
    latency_data: List[Dict[str, Any]] = None
) -> Tuple[float, str, Dict[str, Any]]:
    """
    Calculate latency metrics from the session trace.
    Returns the total latency score (seconds), but details contains granular breakdown.
    """
    total_latency = 0.0
    llm_latency = 0.0
    tool_latency = 0.0
    first_response_latency = None
    average_turn_latency = 0.0
    
    if not session_trace:
        return 0.0, "No trace data available for latency calculation", {}

    # Sort spans by start time to find the true beginning
    sorted_spans = sorted(
        [s for s in session_trace if s.get('start_time')], 
        key=lambda x: x['start_time']
    )
    
    if not sorted_spans:
        return 0.0, "Trace data has no timestamps", {}

    root_start = sorted_spans[0]['start_time']
    
    # Calculate Component Latencies from full trace
    max_end = 0
    for span in session_trace:
        start = span.get('start_time', 0)
        end = span.get('end_time', 0)
        max_end = max(max_end, end)
        duration = (end - start) / 1e9
        name = span.get('name', '')
        
        if name == 'call_llm':
            llm_latency += duration
            # Proxy for Time to First Token: end of first LLM call
            if first_response_latency is None:
                first_response_latency = (end - root_start) / 1e9

        elif 'tool_call' in name or 'execute_tool' in name:
            tool_latency += duration

    # Calculate Total & Average Latency from high-level summary (latency_data)
    # This is preferred as it excludes user think time in multi-turn sessions.
    if latency_data:
        turn_latencies = []
        for item in latency_data:
            if item.get('name') == 'invocation':
                turn_latencies.append(item.get('duration_seconds', 0))
        
        if turn_latencies:
            average_turn_latency = sum(turn_latencies) / len(turn_latencies)
            total_latency = sum(turn_latencies)

    # Fallback: Wall-clock duration from trace if latency_data is missing
    if total_latency == 0.0 and max_end > root_start:
        total_latency = (max_end - root_start) / 1e9  # nanoseconds to seconds

    explanation = (
        f"Total: {total_latency:.4f}s. "
        f"Avg Turn: {average_turn_latency:.4f}s. "
        f"LLM: {llm_latency:.4f}s, Tools: {tool_latency:.4f}s. "
        f"First Response: {first_response_latency if first_response_latency else 0:.4f}s"
    )
    
    details = {
        'total_latency_seconds': total_latency,
        'average_turn_latency_seconds': average_turn_latency,
        'llm_latency_seconds': llm_latency,
        'tool_latency_seconds': tool_latency,
        'time_to_first_response_seconds': first_response_latency
    }
    
    return total_latency, explanation, details


# Registry of all deterministic metrics
DETERMINISTIC_METRICS = {
    'token_usage': calculate_token_usage,
    'latency_metrics': calculate_latency_metrics,
}


def evaluate_deterministic_metrics(
    session_state: Dict[str, Any],
    session_trace: List[Dict[str, Any]],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any],
    metrics_to_run: List[str] = None,
    reference_data: Dict[str, Any] = None,
    metric_definitions: Dict[str, Any] = None,
    latency_data: List[Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Evaluate all specified deterministic metrics.
    """
    if metrics_to_run is None:
        metrics_to_run = list(DETERMINISTIC_METRICS.keys())
    
    results = {}
    for metric_name in metrics_to_run:
        if metric_name not in DETERMINISTIC_METRICS:
            continue
        
        metric_func = DETERMINISTIC_METRICS[metric_name]
        
        try:
            if metric_name == 'latency_metrics':
                score, explanation, details = metric_func(session_trace, latency_data=latency_data)
            else:
                score, explanation, details = metric_func(session_trace)
                
            results[metric_name] = {
                'score': score,
                'explanation': explanation,
                'details': details
            }
        except Exception as e:
            results[metric_name] = {
                'score': 0.0,
                'explanation': f"Error evaluating metric {metric_name}: {str(e)}"
            }
    
    return results
