import json
import os
import glob
import uuid
import time
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import AgentClient for consistent trace analysis logic
from evaluation.core.agent_client import AgentClient

def robust_json_load(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
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
        print(f"Warning: Failed to parse {file_path}: {e}")
        return None

def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

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

def synthesize_trace_from_events(
    events: List[Dict[str, Any]], session_id: str, agent_name: str
) -> List[Dict[str, Any]]:
    """
    Constructs a synthetic OpenTelemetry-style span trace from a flat list of ADK events.
    Compatible with AgentClient analysis methods.
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
            "attributes": attributes,
        }

    current_invocation_span = None
    current_agent_span = None

    for i, event in enumerate(events):
        timestamp = event.get("timestamp", time.time())
        role = event.get("author")

        if role == "user":
            if current_invocation_span:
                current_invocation_span["end_time"] = int(timestamp * 1e9)
                if current_agent_span:
                    current_agent_span["end_time"] = int(timestamp * 1e9)
                    spans.append(current_agent_span)
                spans.append(current_invocation_span)

            current_invocation_span = create_span(
                "invocation", timestamp, timestamp + 1, None, {}
            )
            current_agent_span = create_span(
                f"invoke_agent {agent_name}",
                timestamp,
                timestamp + 1,
                current_invocation_span["span_id"],
                {"gen_ai.agent.name": agent_name, "gen_ai.conversation.id": session_id},
            )

        elif role != "user" and current_agent_span:
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
            
            # Map tool attributes for AgentClient analysis
            if is_tool:
                 attrs["gen_ai.tool.name"] = tool_name
                 # Try to extract args/response for proper trace analysis
                 for part in parts:
                    if "functionCall" in part or "function_call" in part:
                        fc = part.get("functionCall") or part.get("function_call")
                        if fc: attrs["gcp.vertex.agent.tool_call_args"] = json.dumps(fc.get("args"))
                    if "functionResponse" in part or "function_response" in part:
                        fr = part.get("functionResponse") or part.get("function_response")
                        if fr: attrs["gcp.vertex.agent.tool_response"] = json.dumps(fr.get("response") or fr.get("content"))

            usage = event.get("usage_metadata")
            if usage:
                attrs["gen_ai.usage.input_tokens"] = usage.get("prompt_token_count")
                attrs["gen_ai.usage.output_tokens"] = usage.get(
                    "candidates_token_count"
                )
                # LLM Response for token counting
                attrs["gcp.vertex.agent.llm_response"] = json.dumps({"usage_metadata": usage})

            step_span = create_span(
                span_name,
                timestamp,
                timestamp + 1.0,
                current_agent_span["span_id"],
                attrs,
            )
            spans.append(step_span)

            current_agent_span["end_time"] = step_span["end_time"]
            current_invocation_span["end_time"] = step_span["end_time"]

    if current_agent_span:
        spans.append(current_agent_span)
    if current_invocation_span:
        spans.append(current_invocation_span)

    return spans

class AdkHistoryConverter:
    def __init__(self, agent_dir: str, questions_file: Optional[str] = None):
        self.agent_dir = agent_dir
        self.golden_map = self._load_golden_map(questions_file) if questions_file else {}

    def _load_golden_map(self, filepath: str) -> Dict[str, Dict[str, Any]]:
        """Loads Golden Dataset to merge reference data based on ID."""
        mapping = {}
        try:
            with open(filepath) as f:
                data = json.load(f)
                questions = data.get("questions") or data.get("golden_questions", [])
                for q in questions:
                    if "id" in q:
                        mapping[q["id"]] = q
        except Exception as e:
            print(f"Warning: Could not load golden dataset: {e}")
        return mapping

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        data = robust_json_load(file_path)
        if not data:
            return []

        case_results = data.get("eval_case_results", [])
        extracted_rows = []

        for case in case_results:
            if not case.get("session_details"):
                continue

            session_details = case["session_details"]
            events = session_details.get("events", [])
            state = session_details.get("state", {})
            eval_id = case.get("eval_id")

            # 1. Synthesize Trace
            app_name = session_details.get("app_name")
            synthetic_trace = synthesize_trace_from_events(
                events, session_details.get("id"), app_name
            )

            # 2. Analyze Trace (using AgentClient logic)
            analyzed_trace = AgentClient.analyze_trace_and_extract_spans(synthetic_trace)
            latency_data = AgentClient.get_latency_from_spans(analyzed_trace)
            trace_summary = AgentClient.get_agent_trajectory(analyzed_trace)
            
            # 3. Reconstruct Session Object (CamelCase for consistency with runtime)
            camel_events = convert_keys_to_camel_case(events)
            final_session_state = {
                "id": session_details.get("id"),
                "appName": app_name,
                "userId": session_details.get("user_id"),
                "state": state,
                "events": camel_events,
                "lastUpdateTime": events[-1].get("timestamp") if events else None,
            }

            # 4. Extracted Data
            # Use AgentClient helpers to ensure consistency
            tool_interactions = AgentClient.get_tool_interactions(final_session_state)
            sub_agent_trace = AgentClient.get_sub_agent_trace(final_session_state)
            
            extracted_data = {
                "state_variables": state,
                "tool_interactions": tool_interactions,
                "sub_agent_trace": sub_agent_trace
            }
            # Flatten state for legacy support if needed, but keeping clean is better.
            # Live path flattens it, so we should too for consistency.
            extracted_data.update(state)

            # 4b. Extract final_response (last agent text response)
            final_response = ""
            if sub_agent_trace:
                # Get the last agent turn with a text response
                for turn in reversed(sub_agent_trace):
                    if turn.get("text_response"):
                        final_response = turn["text_response"]
                        break

            # 5. User Inputs
            user_inputs = []
            for e in events:
                if e.get("author") == "user":
                    content = e.get("content") or {}
                    parts = content.get("parts") or []
                    text = "".join([p.get("text", "") for p in parts])
                    if text: user_inputs.append(text)

            # 6. Merge with Golden Data (if available)
            golden_q = self.golden_map.get(eval_id, {})
            reference_data = golden_q.get("reference_data", {})
            question_metadata = golden_q.get("metadata", {})

            # 7. Construct Row
            row = {
                "question_id": eval_id,
                "session_id": session_details.get("id"),
                "base_url": "simulation",
                "app_name": app_name,
                "ADK_USER_ID": session_details.get("user_id"),
                "status": json.dumps({"boolean": "success"}), # Simulation implies success run
                "run_id": str(uuid.uuid4()), # Generated
                "agents_evaluated": json.dumps([app_name]),
                "user_inputs": json.dumps(user_inputs),
                "question_metadata": json.dumps(question_metadata),
                "interaction_datetime": datetime.now().isoformat(),
                "USER": os.environ.get("USER", "simulator"),
                "reference_data": json.dumps(reference_data),
                "missing_information": json.dumps({"boolean": False}),
                "final_session_state": json.dumps(final_session_state),
                "session_trace": json.dumps(synthetic_trace),
                "latency_data": json.dumps(latency_data),
                "trace_summary": json.dumps(trace_summary),
                "extracted_data": json.dumps(extracted_data),
                "final_response": final_response  # For response_correctness metric
            }
            
            # Preserve ADK Eval Scores as Metadata or separate columns?
            # User wants "same structure as processed_interactions".
            # Processed interactions doesn't have score columns yet (they come from evaluation).
            # But we can keep them as extra columns, they won't hurt.
            adk_evals = case.get("eval_metric_results") or case.get("overall_eval_metric_results") or []
            for eval_res in adk_evals:
                m_name = eval_res.get("metric_name")
                if m_name:
                    row[f"adk_score.{m_name}"] = eval_res.get("score")

            extracted_rows.append(row)

        return extracted_rows

    def run(self) -> pd.DataFrame:
        history_dir = os.path.join(self.agent_dir, ".adk", "eval_history")
        if not os.path.exists(history_dir):
            raise FileNotFoundError(f"History directory not found: {history_dir}")

        all_rows = []
        for file_path in glob.glob(os.path.join(history_dir, "*.json")):
            all_rows.extend(self.process_file(file_path))

        return pd.DataFrame(all_rows)

class TestToGoldenConverter:
    """Converts a list of conversation turns (test data) into a Golden Dataset JSON."""
    
    def __init__(self):
        pass

    def _parse_kv_pairs(self, pairs: Optional[List[str]]) -> Dict[str, str]:
        """Parses a list of 'key:value' strings into a dictionary."""
        result = {}
        if not pairs:
            return result
        for p in pairs:
            if ":" not in p:
                print(f"Warning: Invalid format '{p}'. Expected 'key:value'")
                continue
            key, value = p.split(":", 1)
            result[key.strip()] = value.strip()
        return result

    def convert(self, input_path: str, output_path: str, agent_name: str, 
                metadata_pairs: Optional[List[str]] = None, id_prefix: str = "q"):
        
        with open(input_path, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"Input data in {input_path} is not a list of turns.")

        user_inputs = []
        reference_tool_interactions = []

        for turn in data:
            user_inputs.append(turn.get("query", ""))

            # Map expected_tool_use to reference_tool_interactions
            for tool in turn.get("expected_tool_use", []):
                reference_tool_interactions.append(
                    {
                        "tool_name": tool.get("tool_name"),
                        "input_arguments": tool.get("tool_input"),
                    }
                )

        # Prepare metadata
        metadata = self._parse_kv_pairs(metadata_pairs)
        metadata["source_file"] = os.path.basename(input_path)

        golden_question = {
            "id": f"{id_prefix}_{uuid.uuid4().hex[:8]}",
            "user_inputs": user_inputs,
            "agents_evaluated": [agent_name],
            "metadata": metadata,
            "reference_data": {
                "reference_tool_interactions": reference_tool_interactions,
                "reference_trajectory": [agent_name],
            },
            "updated_datetime": datetime.now().strftime("%Y-%m-%d"),
        }

        output_data = {"golden_questions": [golden_question]}

        if os.path.exists(output_path):
            try:
                with open(output_path, "r") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict) and "golden_questions" in existing_data:
                        existing_data["golden_questions"].append(golden_question)
                        output_data = existing_data
            except Exception:
                pass

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=4)
        
        return output_data
