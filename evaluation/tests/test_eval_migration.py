import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import json
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

import importlib.util

# Use importlib to load the module with a numeric prefix
script_path = Path(__file__).parent.parent / "02_agent_run_eval.py"
spec = importlib.util.spec_from_file_location("agent_run_eval", script_path)
agent_run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_run_eval)
sys.modules["agent_run_eval"] = agent_run_eval
main = agent_run_eval.main

@patch("agent_run_eval.Client")
@patch("agent_run_eval.aiplatform.init")
@patch("agent_run_eval.pd.read_csv")
@patch("agent_run_eval.load_and_consolidate_metrics")
@patch("agent_run_eval.save_metrics_summary")
def test_client_evaluate_called(mock_save_summary, mock_load_metrics, mock_read_csv, mock_ai_init, mock_client_class):
    # Setup mocks
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Mock return of client.evals.evaluate
    mock_result = MagicMock()
    mock_result.metrics_table = pd.DataFrame({
        "test_metric/score": [5.0],
        "test_metric/explanation": ["Excellent performance."]
    })
    mock_client.evals.evaluate.return_value = mock_result

    # Mock CSV data
    mock_df = pd.DataFrame({
        "question_id": ["1"],
        "user_inputs": ["How is the weather?"],
        "extracted_data": [json.dumps({"weather": "sunny"})],
        "final_session_state": [json.dumps({"status": "complete"})],
        "agents_evaluated": [json.dumps(["data_explorer_agent"])],
        "interaction_datetime": ["2026-01-10T10:00:00"],
        "USER": ["tester"],
        "ADK_USER_ID": ["user-123"],
        "base_url": ["http://localhost:8501"]
    })
    mock_read_csv.return_value = mock_df

    # Mock metrics definitions
    mock_load_metrics.return_value = {
        "test_metric": {
            "metric_type": "llm",
            "agents": ["data_explorer_agent"],
            "dataset_mapping": {"user_query": {"source_column": "user_inputs"}},
            "template": "Rate this: {user_query}"
        }
    }

    # Mock sys.argv and run main
    test_args = ["02_agent_run_eval.py", "--interaction-results-file", "dummy.csv", "--metrics-files", "metrics.json"]
    with patch("sys.argv", test_args):
        with patch("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
            # We mock Path.mkdir to avoid actual filesystem operations
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    # We mock builtins.open to avoid writing temp_consolidated_metrics.json
                    with patch("builtins.open", MagicMock()):
                        # We mock to_csv to avoid writing the output
                        with patch.object(pd.DataFrame, "to_csv"):
                            main()

    # Verify client.evals.evaluate was called
    assert mock_client.evals.evaluate.called
    call_kwargs = mock_client.evals.evaluate.call_args.kwargs
    assert "dataset" in call_kwargs
    assert "metrics" in call_kwargs
    
    # Check if the dataset passed to evaluate has the mapped column
    passed_df = call_kwargs["dataset"]
    assert "user_query" in passed_df.columns
    assert passed_df.iloc[0]["user_query"] == "How is the weather?"

    print("\n✅ Unit test passed: client.evals.evaluate was called with correct parameters.")

if __name__ == "__main__":
    pytest.main([__file__])
