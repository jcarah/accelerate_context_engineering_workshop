import json
import sys
from pathlib import Path
import pandas as pd
import pytest
from vertexai import types

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from evaluation.utils.data_mapper import map_dataset_columns, get_nested_value, robust_json_loads

class TestDataMapper:
    
    @pytest.fixture
    def sample_df(self):
        """Creates a DataFrame with mixed JSON string and Dict columns."""
        data = {
            "user_inputs": [["turn 1", "turn 2"]], # List of strings (multi-turn)
            "extracted_data": [json.dumps({"state_variables": {"profile": {"name": "Alex"}}})],
            "reference_data": [{"reference_trajectory": ["agent_a", "agent_b"]}],
            "tool_interactions": [json.dumps([
                {"tool_name": "search", "input_arguments": {"q": "foo"}, "output_result": {"res": "bar"}}
            ])]
        }
        return pd.DataFrame(data)

    def test_multi_turn_flattens_to_string(self, sample_df):
        # Default mapping (smart defaults)
        # Should flatten list ["turn 1", "turn 2"] into "turn 1\nturn 2"
        result = map_dataset_columns(sample_df, sample_df, {}, "test_metric")
        
        assert result["prompt"].iloc[0] == "turn 1\nturn 2"
        # Ensure we are NOT creating a conflicting history column
        assert "history" not in result.columns

    def test_mapped_list_flattens_for_templates(self, sample_df):
        # When explicitly mapping a list source to a placeholder, it should flatten
        # (This is used for custom templates)
        mapping = {"custom_placeholder": {"source_column": "user_inputs"}}
        result = map_dataset_columns(sample_df, sample_df, mapping, "test_metric")
        
        assert result["custom_placeholder"].iloc[0] == "turn 1\nturn 2"

    def test_robust_json_loads(self):
        assert robust_json_loads('{"a": 1}') == {"a": 1}
        assert robust_json_loads({"a": 1}) == {"a": 1}
        assert robust_json_loads(None) is None
        assert robust_json_loads("invalid") == "invalid"

    def test_get_nested_value(self):
        obj = {"a": {"b": {"c": 1}}}
        assert get_nested_value(obj, "root:a.b.c") == 1 
        assert get_nested_value(obj, "root:a") == {"b": {"c": 1}}

    def test_tool_use_conversion_managed(self, sample_df):
        """Test that Managed Metrics (TOOL_USE_QUALITY) get Event objects."""
        mapping = {
            "intermediate_events": {
                "source_column": "tool_interactions", 
                "managed_metric_name": "TOOL_USE_QUALITY"
            }
        }
        # metric_name matches managed_metric_name to trigger the logic
        result = map_dataset_columns(sample_df, sample_df, mapping, "TOOL_USE_QUALITY", metric_tool_use_name="TOOL_USE_QUALITY")
        
        events = result["intermediate_events"].iloc[0]
        assert len(events) == 2
        assert isinstance(events[0], types.evals.Event)

    def test_tool_use_flattening_custom(self, sample_df):
        """Test that Custom Metrics get flattened strings for tool usage."""
        mapping = {
            "tool_usage": {
                "source_column": "tool_interactions"
            }
        }
        # metric_name is NOT TOOL_USE_QUALITY, so it should flatten
        result = map_dataset_columns(sample_df, sample_df, mapping, "custom_tool_metric")
        
        # Should be a JSON string or flattened string, NOT a list of Events
        val = result["tool_usage"].iloc[0]
        assert isinstance(val, str)
        assert "search" in val
        assert "input_arguments" in val
