import argparse
import json
import os
import sys
import glob
import pandas as pd
import uuid
import time
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# --- HELPER: Robust JSON Parsing ---
def robust_json_load(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        data = json.loads(content)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass
        if not isinstance(data, dict):
             print(f"Skipping {file_path}: Root content is not a dictionary.")
             return None
        return data
    except Exception as e:
        print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
        return None

# --- HELPER: CamelCase Conversion ---
def to_camel_case(snake_str: str) -> str:
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def convert_keys_to_camel_case(data: Any) -> Any:
    """Recursively converts dictionary keys from snake_case to camelCase."""
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            new_key = to_camel_case(k)
            new_dict[new_key] = convert_keys_to_camel_case(v)
        return new_dict
    elif isinstance(data, list):
        return [convert_keys_to_camel_case(i) for i in data]
    return data

def recursively_parse_json_strings(data: Any) -> Any:
    """
    Recursively walks a dict/list and attempts to parse any string values
    that look like JSON. Useful for cleaning up double-encoded state.
    """
    if isinstance(data, dict):
        return {k: recursively_parse_json_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursively_parse_json_strings(i) for i in data]
    elif isinstance(data, str):
        data_stripped = data.strip()
        if (data_stripped.startswith("{") and data_stripped.endswith("}")) or \
           (data_stripped.startswith("[") and data_stripped.endswith("]")):
            try:
                parsed = json.loads(data_stripped)
                # Recurse in case the parsed object contains more JSON strings
                return recursively_parse_json_strings(parsed)
            except (json.JSONDecodeError, TypeError):
                return data
    return data

# --- HELPER: Trace Synthesis (OTEL Style) ---
def synthesize_trace_from_events(events: List[Dict[str, Any]], session_id: str, agent_name: str) -> List[Dict[str, Any]]:
    """
    Constructs a synthetic OpenTelemetry-style span trace from a flat list of ADK events.
    """
    spans = []
    
    def create_span(name, start_time, end_time, parent_id, attributes):
        return {
            "name": name,
            "span_id": str(uuid.uuid4().int)[:16],
            "trace_id": str(uuid.uuid4().int)[:32],
            "parent_span_id": parent_id,
            "start_time": int(start_time * 1e9),
            "end_time": int(end_time * 1e9),
            "attributes": attributes
        }

    current_invocation_span = None
    current_agent_span = None
    
    for i, event in enumerate(events):
        timestamp = event.get("timestamp", time.time())
        role = event.get("author")
        
        if role == 'user':
            if current_invocation_span:
                current_invocation_span['end_time'] = int(timestamp * 1e9)
                if current_agent_span:
                    current_agent_span['end_time'] = int(timestamp * 1e9)
                    spans.append(current_agent_span)
                spans.append(current_invocation_span)

            invocation_id = str(uuid.uuid4())
            current_invocation_span = create_span("invocation", timestamp, timestamp + 1, None, {})
            current_agent_span = create_span(
                f"invoke_agent {agent_name}", timestamp, timestamp + 1,
                current_invocation_span['span_id'],
                {"gen_ai.agent.name": agent_name, "gen_ai.conversation.id": session_id}
            )

        elif role != 'user' and current_agent_span:
            content = event.get("content") or {}
            parts = content.get("parts") or []
            
            is_tool = False
            tool_name = "unknown"
            
            for part in parts:
                if "functionCall" in part or "function_call" in part:
                    fc = part.get("functionCall") or part.get("function_call")
                    if fc:
                        is_tool = True
                        tool_name = fc.get("name")
                        break
                if "functionResponse" in part or "function_response" in part:
                    fr = part.get("functionResponse") or part.get("function_response")
                    if fr:
                        is_tool = True
                        tool_name = fr.get("name")
                        break
            
            span_name = f"execute_tool {tool_name}" if is_tool else "call_llm"
            attrs = {
                "gen_ai.system": "gcp.vertex.agent",
                "gen_ai.request.model": event.get("model_version", "unknown"),
            }
            
            usage = event.get("usage_metadata")
            if usage:
                attrs["gen_ai.usage.input_tokens"] = usage.get("prompt_token_count")
                attrs["gen_ai.usage.output_tokens"] = usage.get("candidates_token_count")

            step_span = create_span(span_name, timestamp, timestamp + 1.0, current_agent_span['span_id'], attrs)
            spans.append(step_span)
            
            current_agent_span['end_time'] = step_span['end_time']
            current_invocation_span['end_time'] = step_span['end_time']

    if current_agent_span: spans.append(current_agent_span)
    if current_invocation_span: spans.append(current_invocation_span)
        
    return spans

# --- HELPER: Custom Extract ---
def extract_custom_extract(all_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    custom_trace = []
    for i, event in enumerate(all_events):
        turn_data = {
            "turn_index": i,
            "role": event.get("author"),
            "timestamp": datetime.fromtimestamp(event.get("timestamp", 0)).isoformat() if event.get("timestamp") else None,
            "model": event.get("model_version"),
            "token_usage": event.get("usage_metadata"),
            "content_text": None,
            "tool_calls": [],
            "tool_responses": [],
            "thought": None
        }
        
        content = event.get("content") or {}
        parts = content.get("parts") or []
        text_parts = []
        
        for part in parts:
            if part.get("text"):
                text_parts.append(part["text"])
            if part.get("thought"):
                turn_data["thought"] = part["thought"]
            
            fc = part.get("functionCall") or part.get("function_call")
            if fc:
                turn_data["tool_calls"].append({"name": fc.get("name"), "args": fc.get("args")})
            
            fr = part.get("functionResponse") or part.get("function_response")
            if fr:
                turn_data["tool_responses"].append({
                    "name": fr.get("name"),
                    "response": fr.get("response") or fr.get("content")
                })

        if text_parts:
            turn_data["content_text"] = "\n".join(text_parts)
        custom_trace.append(turn_data)
    return custom_trace

def get_final_response_text(events: List[Dict[str, Any]]) -> str:
    for event in reversed(events):
        if event.get("author") != "user":
            parts = event.get("content", {}).get("parts", [])
            for part in parts:
                if part.get("text"): return part["text"]
    return ""

def process_adk_history_file(file_path: str) -> List[Dict[str, Any]]:
    extracted_rows = []
    data = robust_json_load(file_path)
    if not data: return []

    eval_set_result_id = data.get("eval_set_result_id")
    case_results = data.get("eval_case_results", [])

    for case in case_results:
        if not case.get("session_details"): continue

        # Raw ADK data
        session_details = case["session_details"]
        events = session_details.get("events", [])
        state = session_details.get("state", {})
        
        # 1. Synthetics & Extracts
        synthetic_trace = synthesize_trace_from_events(events, session_details.get("id"), session_details.get("app_name"))
        custom_extract = extract_custom_extract(events)
        
        # 2. System Instructions
        system_instructions = None
        # Look in eval_metric_result_per_invocation -> actual_invocation -> app_details
        invocations = case.get("eval_metric_result_per_invocation", [])
        if invocations:
            app_details = invocations[0].get("actual_invocation", {}).get("app_details") or {}
            agent_details = app_details.get("agent_details") or {}
            if agent_details:
                first_key = next(iter(agent_details))
                system_instructions = agent_details[first_key].get("instructions")

        # 3. Session State & Trace Refactoring (CamelCase)
        # Convert events to camelCase
        camel_events = convert_keys_to_camel_case(events)
        
        # Convert session details to camelCase structure matching 'session_...json'
        # Target: {id, appName, userId, state, events, lastUpdateTime}
        session_object = {
            "id": session_details.get("id"),
            "appName": session_details.get("app_name"),
            "userId": session_details.get("user_id"),
            "state": state, # Keep state content as is (keys are domain specific)
            "events": camel_events,
            "lastUpdateTime": events[-1].get("timestamp") if events else None
        }

        # 4. Metrics (Simple counts)
        tool_calls = 0
        tool_errors = 0
        total_tokens = 0
        turn_count = 0
        unique_tools = set()
        
        for e in events:
            if e.get("author") == "user": turn_count += 1
            meta = e.get("usage_metadata")
            if meta: total_tokens += (meta.get("total_token_count") or 0)
            
            content = e.get("content") or {}
            for p in content.get("parts", []):
                fc = p.get("functionCall") or p.get("function_call")
                if fc: 
                    tool_calls += 1
                    if fc.get("name"): unique_tools.add(fc.get("name"))
                
                fr = p.get("functionResponse") or p.get("function_response")
                if fr:
                    resp = fr.get("response", {})
                    if isinstance(resp, dict) and (resp.get("status") == "error" or "error" in resp):
                        tool_errors += 1

        duration = 0.0
        if events:
            ts = [e.get("timestamp") for e in events if e.get("timestamp")]
            if len(ts) >= 2: duration = ts[-1] - ts[0]

        row = {
            "eval_set_result_id": eval_set_result_id,
            "eval_id": case.get("eval_id"),
            "session_id": session_details.get("id"),
            "agent_name": session_details.get("app_name"),
            "user_id": session_details.get("user_id"),
            "timestamp": datetime.fromtimestamp(events[-1].get("timestamp", 0)).isoformat() if events else None,
            "metric.duration_sec": round(duration, 2),
            "metric.total_tokens": total_tokens,
            "metric.turn_count": turn_count,
            "metric.tool_calls": tool_calls,
            "metric.tool_errors": tool_errors,
            "metric.unique_tools": json.dumps(sorted(list(unique_tools))),
            "final_response": get_final_response_text(events),
            "system_instructions": system_instructions,
            "session_state": json.dumps(session_object), # Full object
            "session_trace": json.dumps(synthetic_trace), # OTEL Spans
            "custom_extract": json.dumps(custom_extract)
        }

        # ADK Scores
        adk_evals = case.get("eval_metric_results") or case.get("overall_eval_metric_results") or []
        for eval_res in adk_evals:
            metric_name = eval_res.get("metric_name")
            score = eval_res.get("score")
            if metric_name is not None:
                row[f"score.{metric_name}"] = score

        extracted_rows.append(row)

    return extracted_rows

def main():
    parser = argparse.ArgumentParser(description="Convert ADK Eval History")
    parser.add_argument("--agent-dir", required=True)
    args = parser.parse_args()

    history_dir = os.path.join(args.agent_dir, ".adk", "eval_history")
    project_root = os.path.dirname(args.agent_dir.rstrip(os.sep))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(project_root, "eval", "eval_data", "interactions")
    output_csv = os.path.join(output_dir, f"run_{timestamp}.csv")

    if not os.path.exists(history_dir):
        print(f"Error: {history_dir} not found.")
        sys.exit(1)

    all_rows = []
    for file_path in glob.glob(os.path.join(history_dir, "*.json")):
        all_rows.extend(process_adk_history_file(file_path))

    if not all_rows:
        print("No valid evaluation runs found.")
        sys.exit(1)

    df = pd.DataFrame(all_rows)
    
    # Sort columns
    cols = list(df.columns)
    first_cols = ["eval_id", "session_id", "agent_name", "timestamp"]
    score_cols = [c for c in cols if c.startswith("score.")]
    metric_cols = [c for c in cols if c.startswith("metric.")]
    big_cols = ["custom_extract", "session_state", "session_trace"]
    others = [c for c in cols if c not in set(first_cols + score_cols + metric_cols + big_cols)]
    
    final_order = first_cols + score_cols + metric_cols + others + big_cols
    final_order = [c for c in final_order if c in df.columns]
    
    os.makedirs(output_dir, exist_ok=True)
    df[final_order].to_csv(output_csv, index=False)
    print(f"Successfully converted {len(df)} interactions.")
    print(f"Saved to: {output_csv}")

if __name__ == "__main__":
    main()