import argparse
import json
import os
import sys
from datetime import datetime
import asyncio
import pandas as pd

import requests
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from data_explorer_agent.config import get_settings
from data_explorer_agent.utils.agent_run_utils import (
    create_session,
    run_agent_interaction,
    get_gcloud_token,
)
from data_explorer_agent.utils.bigquery import run_query

def get_golden_questions(filepath):
    try:
        with open(filepath) as f:
            data = json.load(f)
            # First, try the 'questions' key (used by the consolidation script),
            # then fall back to 'golden_questions' for original dataset files.
            return data.get('questions') or data.get('golden_questions', [])
    except FileNotFoundError:
        print(f"Error: Questions file not found at '{filepath}'")
        sys.exit(1)

def filter_questions_by_metadata(questions, filters):
    if not filters:
        return questions
    
    filtered_questions = []
    for question in questions:
        metadata = question.get('metadata', {})
        matches_all_filters = True
        for filter_key, filter_values in filters.items():
            if filter_key not in metadata or metadata[filter_key] not in filter_values:
                matches_all_filters = False
                break
        if matches_all_filters:
            filtered_questions.append(question)
    return filtered_questions

def parse_metadata_filters(filter_strings):
    filters = {}
    if not filter_strings:
        return filters
    for filter_string in filter_strings:
        if ':' not in filter_string:
            print(f"Warning: Invalid filter format '{filter_string}'. Expected 'key:value1,value2'")
            continue
        key, values_str = filter_string.split(':', 1)
        values = [v.strip() for v in values_str.split(',')]
        if key in filters:
            filters[key].extend(values)
        else:
            filters[key] = values
    return filters

async def process_question(question_data, args, token, run_id):
    user_inputs = question_data['user_inputs']
    agents_evaluated = question_data["agents_evaluated"]
    question_id = question_data['id']
    question_metadata = question_data.get('metadata', {})
    reference_data = question_data.get('reference_data', {})

    print(f"\n--- Running interaction for question: '{user_inputs}' (Run {run_id}/{args.runs}) ---")
    try:
        interaction_datetime=datetime.now().isoformat()
        session_id = await asyncio.to_thread(create_session, args.base_url, args.user_id, token, question_metadata.get('tenant'))
        for turn in user_inputs:
            await asyncio.to_thread(run_agent_interaction, args.base_url, args.user_id, session_id, turn, token)

        reference_bq_raw_response = None
        reference_sql = reference_data.get('sql_explorer:reference_sql')
        if reference_sql:
            default_dataset_ref = bigquery.DatasetReference(
                project="edp-d-us-east2-etl",
                dataset_id=question_metadata.get('tenant'),
            )
            reference_bq_raw_response_df = await asyncio.to_thread(run_query, query=reference_sql, default_dataset_id=default_dataset_ref)
            reference_bq_raw_response = reference_bq_raw_response_df.to_json(orient="records")

        new_reference_data = reference_data.copy()
        if reference_bq_raw_response:
            new_reference_data["sql_explorer:reference_bq_raw_response"] = reference_bq_raw_response

        result_dict = {
            "status": json.dumps({"boolean":"success"}), 
            "run_id": run_id,
            "question_id": question_id,
            "agents_evaluated": json.dumps(agents_evaluated),
            "user_inputs": json.dumps(user_inputs),
            "question_metadata": json.dumps(question_metadata),
            "interaction_datetime": interaction_datetime,
            "session_id": session_id,
            "base_url": args.base_url,
            "ADK_USER_ID": args.user_id,
            "USER": args.user,
            "reference_data": json.dumps(new_reference_data),
        }
        print(f"--- Completed interaction for question '{user_inputs}' (Run {run_id}) SUCCESSFULLY ---")
        return result_dict
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        print(f"--- ERROR running interaction for question '{user_inputs}' (Run {run_id}) ---")
        print(error_message)
        return {
            "status": json.dumps({"boolean":"failed","error_message":error_message}), 
            "run_id": run_id, 
            "question_id": question_id, 
            "agents_evaluated": json.dumps(agents_evaluated),
            "user_inputs": json.dumps(user_inputs),
            "question_metadata": json.dumps(question_metadata),
            "interaction_datetime": None,
            "session_id": None,
            "base_url": args.base_url,
            "ADK_USER_ID": args.user_id,
            "USER": args.user,
            "reference_data": json.dumps(reference_data),
            }

async def main():
    parser = argparse.ArgumentParser(description="Run agent interactions for evaluation.")
    parser.add_argument("--user_id", type=str, default="e2e_test_user", help="The user ID to use.")
    parser.add_argument("--base_url", type=str, default="http://localhost:8080", help="The base URL of the agent service.")
    parser.add_argument("--questions_file", type=str, default="tests/datasets/su_golden_questions.json", help="Path to the JSON file with test questions.")
    parser.add_argument("--num_questions", type=int, default=-1, help="Number of questions to run. -1 for all.")
    parser.add_argument("--results_dir", type=str, default="tests/eval/results", help="Directory to save the interaction results.")
    parser.add_argument("--user", type=str, default=os.environ.get("USER"), help="The LDAP of the user running the script.")
    parser.add_argument("--filter", action="append", dest="metadata_filters", help="Filter questions by metadata.")
    parser.add_argument("--runs", type=int, default=1, help="Number of times to run the evaluation for each question.")
    parser.add_argument("--output-csv", type=str, help="Custom output CSV file name.")
    args = parser.parse_args()

    if not args.user:
        parser.error("The --user argument is required or the USER environment variable must be set.")

    if not os.path.exists(args.results_dir):
        os.makedirs(args.results_dir)

    local_golden_questions = get_golden_questions(args.questions_file)
    
    if args.metadata_filters:
        filters = parse_metadata_filters(args.metadata_filters)
        local_golden_questions = filter_questions_by_metadata(local_golden_questions, filters)

    questions_to_run = local_golden_questions
    if args.num_questions != -1:
        questions_to_run = local_golden_questions[:args.num_questions]

    print(f"Running interactions for {len(questions_to_run)} questions ({args.runs} times each)")

    token = get_gcloud_token()
    tasks = []
    for q in questions_to_run:
        for i in range(1, args.runs + 1):
            tasks.append(process_question(q, args, token, i))
            
    task_results = await asyncio.gather(*tasks)

    all_results = []
    for res in task_results:
        all_results.append(res)

    if all_results:
        df = pd.DataFrame(all_results)
        
        output_csv_path = args.output_csv or os.path.join(args.results_dir, f"interaction_{os.path.basename(args.questions_file).replace('.json', '')}.csv")
        df.to_csv(output_csv_path, index=False)
        print(f"Interaction results for {len(all_results)} runs saved to {output_csv_path}")

    failed_questions = [res for res in task_results if json.loads(res.get("status")).get("boolean") == "failed"]
    if failed_questions:
        print("\n--- Summary of Failed Questions ---")
        for failure in failed_questions:
            print(f"\n- Question ID: {failure['question_id']}")
            print(f"  User Input(s): {failure['user_inputs']}")
            status_obj = json.loads(failure.get("status", "{}"))
            print(f"  Error: {status_obj.get('error_message', 'Unknown error')}")
        print("\nSome interactions failed, but all results were saved to the output file.")
    else:
        print(f"\nAll interactions ran successfully!")

if __name__ == "__main__":
    asyncio.run(main())
