"""
This script is an auxiliary tool for quickly testing and debugging the Data Explorer agent.
Its primary purpose is to run a single, hardcoded agent interaction and save the complete
session state and trace data to local files.

By providing a simple way to capture the raw output, this script allows developers to
visually inspect the agent's behavior, understand the data structures, and refine the
main evaluation scripts (like 01_agent_e2e_eval.py) with greater visibility.

Usage:
    uv run python evaluation/00_simple_agent_interaction.py
"""

import argparse
import json
import os
import sys
import asyncio
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_explorer_agent.utils.agent_run_utils import (
    create_session,
    get_session_state,
    get_session_trace,
    get_gcloud_token,
    run_agent_interaction,
)

async def main():
    """Runs a single hardcoded agent interaction and saves the results."""
    parser = argparse.ArgumentParser(description="Run a simple test interaction with the Data Explorer Agent.")
    parser.add_argument("--user_id", type=str, default="danielazamora_test_user", help="The user ID to use.")
    parser.add_argument("--base_url", type=str, default="https://genai.ops.dematic.dev", help="The base URL of the agent service.")
    parser.add_argument("--results_dir", type=str, default="evaluation/results", help="Directory to save the trace results.")
    parser.add_argument("--dataset_id", type=str, default="superior_uniform_eudora_ar", help="The dataset ID for the session.")
    
    args = parser.parse_args()

    # --- Hardcoded question ---
    question_id = "sql_explorer-exact-1"
    user_inputs = ["What are the top 3 busiest locations in the last 6 months?"]

    print(f"--- Running simple interaction for question: '{user_inputs[0]}' ---")

    try:
        token = get_gcloud_token()
        session_id = await asyncio.to_thread(create_session, args.base_url, args.user_id, token, args.dataset_id)

        for turn in user_inputs:
            await asyncio.to_thread(run_agent_interaction, args.base_url, args.user_id, session_id, turn, token)

        final_session_state = await asyncio.to_thread(get_session_state, args.base_url, args.user_id, session_id, token)
        session_trace = await asyncio.to_thread(get_session_trace, args.base_url, session_id, token)

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
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())