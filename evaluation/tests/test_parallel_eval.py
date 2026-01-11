import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the module to test
import importlib.util

script_path = Path(__file__).parent.parent / "02_agent_run_eval.py"
spec = importlib.util.spec_from_file_location("agent_run_eval", script_path)
agent_run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_run_eval)
sys.modules["agent_run_eval"] = agent_run_eval

# Access classes and functions
run_single_metric_evaluation = agent_run_eval.run_single_metric_evaluation
# We need to access the instantiated CONFIG object, not the class
CONFIG = agent_run_eval.CONFIG


class TestParallelEval(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_metric = MagicMock()
        self.dataset = pd.DataFrame({"prompt": ["test"]})
        self.metric_df = pd.DataFrame(index=[0])
        self.metric_name = "test_metric"

    @patch("agent_run_eval.parse_eval_result")
    def test_evaluate_single_metric_success(self, mock_parse):
        """Test successful execution of a single metric task."""
        # Setup mocks
        mock_result = MagicMock()
        self.mock_client.evals.evaluate.return_value = mock_result

        expected_parsed_df = pd.DataFrame({"score": [1.0]})
        mock_parse.return_value = expected_parsed_df

        # Run task
        task_args = (
            self.dataset,
            self.mock_metric,
            self.metric_df,
            self.metric_name,
            self.mock_client,
        )
        result_df, name = run_single_metric_evaluation(task_args)

        # Assertions
        self.mock_client.evals.evaluate.assert_called_once()
        self.assertEqual(name, self.metric_name)
        pd.testing.assert_frame_equal(result_df, expected_parsed_df)

    def test_evaluate_single_metric_retry_success(self):
        """Test that the task retries on failure and eventually succeeds."""
        # Setup mocks to fail twice then succeed
        self.mock_client.evals.evaluate.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            MagicMock(),  # Success
        ]

        # We need to mock parse_eval_result inside the function or assume it handles the mock result
        with patch("agent_run_eval.parse_eval_result") as mock_parse:
            mock_parse.return_value = pd.DataFrame()

            # Mock the CONFIG object's attributes directly
            with patch.object(CONFIG, "RETRY_DELAY_SECONDS", 0.01):
                task_args = (
                    self.dataset,
                    self.mock_metric,
                    self.metric_df,
                    self.metric_name,
                    self.mock_client,
                )
                result_df, name = run_single_metric_evaluation(task_args)

        # Assertions
        self.assertEqual(self.mock_client.evals.evaluate.call_count, 3)
        self.assertIsNotNone(result_df)

    def test_evaluate_single_metric_all_fail(self):
        """Test that the task returns None after max retries."""
        # Setup mocks to always fail
        self.mock_client.evals.evaluate.side_effect = Exception("Persistent Failure")

        # Mock the CONFIG object's attributes directly
        with patch.object(CONFIG, "RETRY_DELAY_SECONDS", 0.01):
            with patch.object(CONFIG, "MAX_RETRIES", 2):
                task_args = (
                    self.dataset,
                    self.mock_metric,
                    self.metric_df,
                    self.metric_name,
                    self.mock_client,
                )
                result_df, name = run_single_metric_evaluation(task_args)

        # Assertions
        self.assertEqual(self.mock_client.evals.evaluate.call_count, 2)
        self.assertIsNone(result_df)
        self.assertEqual(name, self.metric_name)


if __name__ == "__main__":
    unittest.main()
