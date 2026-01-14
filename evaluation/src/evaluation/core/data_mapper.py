import json
import logging
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from google.genai import types as genai_types
from vertexai import types

logger = logging.getLogger("agent_eval")


def robust_json_loads(x: Any) -> Optional[Union[Dict, List, str]]:
    """Safely parse a JSON string, returning None for invalid or empty inputs."""
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return x
    if not isinstance(x, str) or not x:
        return None
    try:
        return json.loads(x)
    except (json.JSONDecodeError, TypeError):
        return x


def convert_interactions_to_events(val: Any) -> List[types.evals.Event]:
    """
    Converts a list of tool interactions into Vertex AI SDK Event objects.
    """
    interactions = robust_json_loads(val)
    if not isinstance(interactions, list):
        return []

    events = []
    for item in interactions:
        tool_name = item.get("tool_name")
        args = item.get("input_arguments", {})
        response = item.get("output_result", {})

        # 1. Tool Call Event (Model generated)
        fc_part = genai_types.Part.from_function_call(name=tool_name, args=args)
        model_content = genai_types.Content(role="model", parts=[fc_part])
        events.append(types.evals.Event(content=model_content, author="model"))

        # 2. Tool Response Event (System provided)
        fr_part = genai_types.Part.from_function_response(
            name=tool_name, response=response
        )
        tool_content = genai_types.Content(role="tool", parts=[fr_part])
        events.append(types.evals.Event(content=tool_content, author="tool"))

    return events


def get_nested_value(row_val: Any, path: str) -> Any:
    """
    Retrieves a value from a nested dictionary using a dot-separated path.
    Example: path="root:state_variables.customer_profile"
    """
    # 1. Strip the root prefix (e.g., "extracted_data:")
    suffix = path.split(":", 1)[1] if ":" in path else path

    # 2. Split by dot for traversal
    parts = suffix.split(".")

    curr = row_val
    for p in parts:
        if isinstance(curr, dict):
            curr = curr.get(p)
        else:
            return None
    return curr


def map_dataset_columns(
    agent_df: pd.DataFrame,
    original_df: pd.DataFrame,
    mapping: Dict[str, Any],
    metric_name: str,
    metric_tool_use_name: str = "TOOL_USE_QUALITY",
    is_managed_metric: bool = False,
) -> pd.DataFrame:
    """
    Maps columns from the raw agent DataFrame to the evaluation dataset based on the metric config.
    Handles nested JSON lookups and template formatting.
    """
    eval_dataset = pd.DataFrame(index=agent_df.index)

    # 0. Always include standard columns with smart defaults
    # Vertex AI EvalTask for DataFrames works best with strings for prompt/response.
    # We use user_inputs as prompt and trace_summary as response if not explicitly mapped.

    if "user_inputs" in agent_df.columns:
        inputs = agent_df["user_inputs"]
        # Normalize multi-turn lists into a single context string.
        # This avoids 'got multiple values for keyword argument conversation_history' SDK bugs.
        eval_dataset["prompt"] = inputs.apply(
            lambda x: "\n".join(x)
            if isinstance(x, list)
            else str(x)
            if x is not None
            else ""
        )
    else:
        eval_dataset["prompt"] = ""

    # 3. Handle 'response' (Standard default)
    # Priority: final_response (actual agent text) > response > trace_summary (agent names only)
    if "response" not in mapping:
        if "final_response" in agent_df.columns:
            eval_dataset["response"] = agent_df["final_response"].fillna("")
        elif "response" in agent_df.columns:
            eval_dataset["response"] = agent_df["response"].fillna("")
        elif "trace_summary" in agent_df.columns:
            eval_dataset["response"] = agent_df["trace_summary"].fillna("")
        else:
            eval_dataset["response"] = ""

    for placeholder, details in mapping.items():
        if "source_column" in details:
            col_path = details["source_column"]

            # 1. Try exact flattened name
            cands = [
                col_path.replace(":", "."),
                f"extracted_data.{col_path}",
                f"reference_data.{col_path}",
                col_path,
            ]
            source_col = next((c for c in cands if c in agent_df.columns), None)

            val_series = None
            if source_col:
                val_series = agent_df[source_col]
            else:
                # 2. Try nested lookup in original dict columns
                root_key = col_path.split(":")[0] if ":" in col_path else None
                if root_key in original_df.columns:
                    val_series = original_df[root_key].apply(
                        lambda x: get_nested_value(robust_json_loads(x), col_path)
                    )

            if val_series is not None:
                # Special Case: Tool Interactions to Events
                # We use metric_name passed from 02_agent_run_eval.py (which is the managed name if applicable)
                is_tool_metric = metric_name == metric_tool_use_name
                is_event_col = placeholder in ["intermediate_events", "tool_usage"]

                if is_tool_metric and is_event_col:
                    eval_dataset[placeholder] = val_series.apply(
                        convert_interactions_to_events
                    )
                else:
                    # Robust Flattening for custom placeholders (Templates need strings)
                    def normalize_input(x):
                        if isinstance(x, list):
                            try:
                                return "\n".join(x) if x else ""
                            except TypeError:
                                return json.dumps(x)
                        elif isinstance(x, dict):
                            return json.dumps(x)
                        return str(x) if x is not None else ""

                    eval_dataset[placeholder] = val_series.apply(normalize_input)
            else:
                eval_dataset[placeholder] = ""

        elif "template" in details:

            def format_template(row):
                template_vars = {}
                source_cols = details.get("source_columns", [])
                for sc in source_cols:
                    cands = [
                        sc.replace(":", "."),
                        f"extracted_data.{sc}",
                        f"reference_data.{sc}",
                        sc,
                    ]
                    found_sc = next(
                        (c for c in cands if c in row.index and row[c] is not None),
                        None,
                    )
                    template_vars[sc.replace(":", "_")] = (
                        row[found_sc] if found_sc else ""
                    )
                return (
                    details["template"].format(**template_vars)
                    if template_vars
                    else details["template"]
                )

            eval_dataset[placeholder] = agent_df.apply(format_template, axis=1)

    return eval_dataset
