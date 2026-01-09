import json
import unittest
from unittest.mock import MagicMock, patch

from evaluation.agent_client import AgentClient


class TestAgentClient(unittest.TestCase):
    def setUp(self):
        self.base_url = "https://mock.api.dev"
        self.app_name = "test_app"
        self.user_id = "test_user"
        self.token = "mock_token"
        self.client = AgentClient(self.base_url, self.app_name, self.user_id, self.token)

    @patch("subprocess.check_output")
    def test_get_token_fetch(self, mock_subprocess):
        """Test that token is fetched using gcloud if not provided."""
        client = AgentClient(self.base_url, self.app_name, self.user_id)
        mock_subprocess.return_value = "fetched_token\n"
        
        self.assertEqual(client.token, "fetched_token")
        mock_subprocess.assert_called_with(["gcloud", "auth", "print-identity-token"], text=True)

    @patch("requests.request")
    def test_create_session(self, mock_request):
        """Test session creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "session_123"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Test with data
        session_id = self.client.create_session(dataset_id="dataset_abc", foo="bar")
        
        self.assertTrue(session_id.startswith("session_"))
        
        expected_url = f"{self.base_url}/apps/{self.app_name}/users/{self.user_id}/sessions/{session_id}"
        mock_request.assert_called_with(
            "POST", 
            expected_url, 
            headers=self.client._get_headers(), 
            json={"dataset_id": "dataset_abc", "foo": "bar"}
        )

        # Test without data
        session_id_empty = self.client.create_session()
        expected_url_empty = f"{self.base_url}/apps/{self.app_name}/users/{self.user_id}/sessions/{session_id_empty}"
        mock_request.assert_called_with(
            "POST", 
            expected_url_empty, 
            headers=self.client._get_headers(), 
            json=None
        )

    @patch("requests.request")
    def test_run_interaction(self, mock_request):
        """Test sending a message."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success"}
        mock_request.return_value = mock_response

        response = self.client.run_interaction("session_123", "Hello", streaming=True)
        
        self.assertEqual(response, {"status": "success"})
        mock_request.assert_called_with(
            "POST",
            f"{self.base_url}/run",
            headers=self.client._get_headers(),
            json={
                "app_name": self.app_name,
                "user_id": self.user_id,
                "session_id": "session_123",
                "new_message": {"role": "user", "parts": [{"text": "Hello"}]},
                "streaming": True,
            }
        )

    @patch("requests.request")
    def test_get_session_state(self, mock_request):
        """Test retrieving session state."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"state": {"foo": "bar"}}
        mock_request.return_value = mock_response

        state = self.client.get_session_state("session_123")
        self.assertEqual(state, {"state": {"foo": "bar"}})
        
        expected_url = f"{self.base_url}/apps/{self.app_name}/users/{self.user_id}/sessions/session_123"
        mock_request.assert_called_with(
            "GET",
            expected_url,
            headers=self.client._get_headers()
        )

    def test_analyze_trace_and_extract_spans(self):
        """Test trace analysis logic with realistic examples."""
        # Simplified trace data based on examples
        raw_trace = [
            {
                "span_id": 1001,
                "parent_span_id": None,
                "name": "agent_run [MainAgent]",
                "start_time": 1000000000,
                "end_time": 2000000000,
                "attributes": {}
            },
            {
                "span_id": 1002,
                "parent_span_id": 1001,
                "name": "execute_tool call_sql_explorer_agent",
                "start_time": 1100000000,
                "end_time": 1200000000,
                "attributes": {
                    "gen_ai.tool.name": "call_sql_explorer_agent",
                    "gcp.vertex.agent.tool_call_args": '{"question": "test"}',
                    "gcp.vertex.agent.tool_response": '{"result": "ok"}'
                }
            }
        ]

        analyzed = AgentClient.analyze_trace_and_extract_spans(raw_trace)
        
        self.assertEqual(len(analyzed), 1)
        root = analyzed[0]
        self.assertEqual(root['name'], "agent_run [MainAgent]")
        self.assertEqual(root['type'], "AGENT_RUN")
        self.assertEqual(root['details']['agent_name'], "MainAgent")
        
        children = root['children']
        self.assertEqual(len(children), 1)
        child = children[0]
        self.assertEqual(child['type'], "TOOL_CALL")
        self.assertEqual(child['details']['tool_name'], "call_sql_explorer_agent")
        self.assertEqual(child['details']['arguments'], {"question": "test"})
        self.assertEqual(child['details']['response'], {"result": "ok"})

    def test_get_agent_trajectory(self):
        """Test trajectory extraction."""
        # Construct a simple analyzed trace structure
        analyzed_trace = [
            {
                "name": "agent_run[AgentA]",
                "children": [
                    {
                        "name": "agent_run[AgentB]",
                        "children": []
                    }
                ]
            }
        ]
        
        trajectory = AgentClient.get_agent_trajectory(analyzed_trace)
        self.assertEqual(trajectory, ["AgentA", "AgentB"])

    def test_get_tool_interactions(self):
        """Test tool interaction extraction from session events."""
        session_data = {
            "events": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "id": "call_1",
                                    "name": "search_places",
                                    "args": {"query": "coffee"}
                                }
                            }
                        ]
                    }
                },
                {
                    "content": {
                        "parts": [
                            {
                                "functionResponse": {
                                    "id": "call_1",
                                    "name": "search_places",
                                    "response": {"result": "found place"}
                                }
                            }
                        ]
                    }
                },
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "id": "call_2",
                                    "name": "calculate_gap",
                                    "args": {"data": "some_data"}
                                }
                            }
                        ]
                    }
                }
                # call_2 has no response
            ]
        }

        interactions = AgentClient.get_tool_interactions(session_data)
        
        self.assertEqual(len(interactions), 2)
        
        # Check first interaction (completed)
        self.assertEqual(interactions[0]['tool_name'], "search_places")
        self.assertEqual(interactions[0]['input_arguments'], {"query": "coffee"})
        self.assertEqual(interactions[0]['output_result'], "found place")
        self.assertEqual(interactions[0]['call_id'], "call_1")
        
        # Check second interaction (pending/no response)
        self.assertEqual(interactions[1]['tool_name'], "calculate_gap")
        self.assertEqual(interactions[1]['input_arguments'], {"data": "some_data"})
        self.assertEqual(interactions[1].get('status'), "no_response")
        self.assertEqual(interactions[1]['call_id'], "call_2")

    def test_get_sub_agent_trace(self):
        """Test sub-agent trace extraction from session events."""
        session_data = {
            "events": [
                {
                    "author": "user",
                    "content": {"parts": [{"text": "Hello"}]},
                    "timestamp": 1000
                },
                {
                    "author": "RootAgent",
                    "content": {"parts": [{"text": "I will call the sub-agent."}]},
                    "timestamp": 1001
                },
                {
                    "author": "SubAgentA",
                    "content": {"parts": [{"text": "Processing..."}]},
                    "timestamp": 1002
                },
                {
                    "author": "SubAgentA",
                    "content": {"parts": [{"text": "Done."}]},
                    "timestamp": 1003
                }
            ]
        }

        trace = AgentClient.get_sub_agent_trace(session_data)
        
        self.assertEqual(len(trace), 3)
        self.assertEqual(trace[0]['agent_name'], "RootAgent")
        self.assertEqual(trace[0]['text_response'], "I will call the sub-agent.")
        self.assertEqual(trace[1]['agent_name'], "SubAgentA")
        self.assertEqual(trace[1]['text_response'], "Processing...")
        self.assertEqual(trace[2]['agent_name'], "SubAgentA")
        self.assertEqual(trace[2]['text_response'], "Done.")

if __name__ == "__main__":
    unittest.main()
