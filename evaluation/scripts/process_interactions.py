import argparse
import json
import os
import sys
import asyncio
import pandas as pd

import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from evaluation.agent_client import AgentClient

async def process_interaction(row, results_dir=None, skip_traces=False):
    question_id = row['question_id']
    session_id = row['session_id']
    base_url = row['base_url']
    app_name = row['app_name']
    user_id = row['ADK_USER_ID']
    row['missing_information'] = json.dumps({"boolean": False}) # Default to False

    try:
        status_ = json.loads(row["status"].replace("'",'"'))
        if status_.get("boolean") == "failed":
            raise ValueError("Interaction failed in the previous step, run the script again or remove the failed rows in the interaction CSV.")

        agent_client = AgentClient(base_url=base_url, app_name=app_name, user_id=user_id)

        final_session_state = await asyncio.to_thread(agent_client.get_session_state, session_id)
        
        if skip_traces:
            print(f"Skipping trace retrieval for session {session_id} (--skip-traces flag enabled)")
            session_trace = None
        else:
            try:
                session_trace = await asyncio.to_thread(agent_client.get_session_trace, session_id)
            except RuntimeError as e:
                print(f"Warning: {e}")
                session_trace = None

        if results_dir:
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)

            question_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', question_id)
            output_file_json = os.path.join(results_dir, f"session_{question_filename}_{session_id}.json")
            output_file_trace_json = os.path.join(results_dir, f"trace_{question_filename}_{session_id}.json")

            def write_output_files():
                with open(output_file_json, 'w') as f:
                    json.dump(final_session_state, f, indent=4)

                with open(output_file_trace_json, 'w') as f:
                    json.dump(session_trace, f, indent=4)

            await asyncio.to_thread(write_output_files)

        if not session_trace:
            print(f"Warning: Failed to retrieve session trace for session {session_id}. Proceeding without trace data.")
            row['latency_data'] = None
            row['trace_summary'] = None
            row['session_trace'] = None
            row['missing_information'] = json.dumps({"boolean": True, "details": "Missing session trace, hence, also latency_data, trace_summary."})
        else:
            analyzed_trace = AgentClient.analyze_trace_and_extract_spans(session_trace)
            row['latency_data'] = json.dumps(AgentClient.get_latency_from_spans(analyzed_trace))
            row['trace_summary'] = json.dumps(AgentClient.get_agent_trajectory(analyzed_trace))
            row['session_trace'] = json.dumps(session_trace)

        extracted_data = {
            "state_variables": {},
            "tool_interactions": [],
            "sub_agent_trace": []
        }
        
        # Extract all state variables
        state = final_session_state.get('state', {})
        if state:
            extracted_data["state_variables"] = state
            # Flatten state variables to top level for easier access in metrics mapping
            extracted_data.update(state)
        
        # Extract tool interactions and sub-agent trace
        extracted_data["tool_interactions"] = AgentClient.get_tool_interactions(final_session_state)
        extracted_data["sub_agent_trace"] = AgentClient.get_sub_agent_trace(final_session_state)
        
        row['final_session_state'] = json.dumps(final_session_state)
        row['extracted_data'] = json.dumps(extracted_data)
        
        return row

    except Exception as e:
        print(f"Error processing session {session_id}: {e}")
        row['final_session_state'] = None
        row['session_trace'] = None
        row['latency_data'] = None
        row['extracted_data'] = None
        row['trace_summary'] = None
        row['tool_interactions'] = None
        row['sub_agent_trace'] = None
        row['missing_information'] = json.dumps({"boolean": True, "details": f"Error processing session and/or trace. Error: {e}"})
        return row

async def main():
    parser = argparse.ArgumentParser(description="Process agent interactions to extract trace and state data.")
    parser.add_argument("--input-csv", required=True, help="Path to the input CSV file with interaction results.")
    parser.add_argument("--results_dir", type=str, default="evaluation/results", help="Directory to save the intermediate results.")
    parser.add_argument("--output-csv", help="Exact path to the output CSV file with enriched data.")
    parser.add_argument("--skip-traces", action="store_true", help="Skip trace retrieval entirely (recommended for ADK 1.15 when trace endpoints are unavailable).")
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)

    if args.skip_traces:
        print("--- Trace retrieval disabled via --skip-traces flag ---")
        print("Evaluation will proceed using session state only. Latency metrics will not be available.")

    tasks = [process_interaction(row, args.results_dir, args.skip_traces) for _, row in df.iterrows()]
    results = await asyncio.gather(*tasks)

    enriched_df = pd.DataFrame(results)
    
    # 1. Get all rows with missing info
    
    missing_data_df = enriched_df.copy()
    missing_data_df['boolean']=missing_data_df['missing_information'].apply(lambda x: json.loads(x).get('boolean'))
    missing_data_df = missing_data_df[missing_data_df["boolean"] == True]
    total_missing = len(missing_data_df)

    # 2. Identify rows where ONLY trace data is missing
    trace_only_missing_mask = (
        missing_data_df['latency_data'].isnull() &
        missing_data_df['trace_summary'].isnull() &
        missing_data_df['session_trace'].isnull() &
        missing_data_df['final_session_state'].notnull() &
        missing_data_df['extracted_data'].notnull()
    )
    trace_missing_df = missing_data_df[trace_only_missing_mask]
    trace_missing_count = len(trace_missing_df)

    # 3. Identify rows where other/more data is missing
    other_missing_df = missing_data_df[~trace_only_missing_mask]
    other_missing_count = len(other_missing_df)

    # 4. Print summary
    print("\n--- Summary of Unsuccessful Interactions ---")
    print(f"Total rows with missing data: {total_missing}/{len(enriched_df)}")

    if trace_missing_count > 0:
        print(f"\nRows with missing trace data only: {trace_missing_count}")
        print("Session IDs:", ", ".join(trace_missing_df['session_id'].astype(str).tolist()))

    if other_missing_count > 0:
        print(f"\nRows with other critical missing data: {other_missing_count}")
        print("Session IDs:", ", ".join(other_missing_df['session_id'].astype(str).tolist()))

    output_csv = args.output_csv or os.path.join(args.results_dir, f"processed_{os.path.basename(args.input_csv)}")
    enriched_df.to_csv(output_csv, index=False)
    print(f"Enriched data saved to {output_csv}")

if __name__ == "__main__":
    asyncio.run(main())