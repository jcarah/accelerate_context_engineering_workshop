"""
This script is an auxiliary tool for quickly testing and debugging an agent.
Its primary purpose is to run a single, hardcoded agent interaction and save the complete
session state and trace data to local files.

Usage:
    uv run python evaluation/00_simple_agent_interaction.py --app_name retail_location_strategy --base_url http://localhost:8080
"""

import argparse
import json
import os
import sys
import asyncio
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.agent_client import AgentClient

def parse_state_variables(state_var_strings):
    state_vars = {}
    if not state_var_strings:
        return state_vars
    for s in state_var_strings:
        if ':' not in s:
            print(f"Warning: Invalid state variable format '{s}'. Expected 'key:value'")
            continue
        key, value = s.split(':', 1)
        state_vars[key.strip()] = value.strip()
    return state_vars

async def main():
    """Runs a single hardcoded agent interaction and saves the results."""
    parser = argparse.ArgumentParser(description="Run a simple test interaction with an Agent.")
    parser.add_argument("--user_id", type=str, default="eval_user", help="The user ID to use.")
    parser.add_argument("--app_name", type=str, required=True, help="The name of the application/agent.")
    parser.add_argument("--base_url", type=str, default="http://localhost:8501", help="The base URL of the agent service.")
    parser.add_argument("--results_dir", type=str, default="evaluation/results", help="Directory to save the trace results.")
    parser.add_argument("--state-variable", action="append", dest="state_variables", help="Inject state variables (e.g., 'key:value').")
    
    args = parser.parse_args()

    # --- Hardcoded question for Retail Location Strategy ---
    question_id = "retail-location-test-1"
    user_inputs = ["I want to open a specialty coffee shop in Indiranagar, Bangalore."]

    print(f"--- Running simple interaction for question: '{user_inputs[0]}' ---")
    print(f"Agent: {args.app_name} | Base URL: {args.base_url}")

    try:
        agent_client = AgentClient(base_url=args.base_url, app_name=args.app_name, user_id=args.user_id)
        state_vars = parse_state_variables(args.state_variables)

        # 1. Create session
        session_id = await asyncio.to_thread(agent_client.create_session, **state_vars)

        # 2. Run interactions
        for turn in user_inputs:
            await asyncio.to_thread(agent_client.run_interaction, session_id, turn)

        # 3. Retrieve state and trace
        final_session_state = await asyncio.to_thread(agent_client.get_session_state, session_id)
        
        try:
            session_trace = await asyncio.to_thread(agent_client.get_session_trace, session_id)
        except RuntimeError as e:
            print(f"Warning: Could not retrieve trace: {e}")
            session_trace = {"error": str(e)}

        # 4. Save results
        if args.results_dir:
            if not os.path.exists(args.results_dir):
                os.makedirs(args.results_dir)

            # Sanitize the question ID for the filename
            question_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', question_id)
            output_file_session = os.path.join(args.results_dir, f"{question_filename}_session.json")
            output_file_trace = os.path.join(args.results_dir, f"{question_filename}_trace.json")

            print(f"Saving session data to: {output_file_session}")
            with open(output_file_session, 'w') as f:
                json.dump(final_session_state, f, indent=4)

            print(f"Saving trace data to: {output_file_trace}")
            with open(output_file_trace, 'w') as f:
                json.dump(session_trace, f, indent=4)

        print("--- Simple interaction completed successfully! ---")

    except Exception as e:
        print(f"--- An error occurred during the simple interaction ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
