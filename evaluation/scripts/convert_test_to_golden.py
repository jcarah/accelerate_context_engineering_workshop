import json
import argparse
import os
import uuid
from datetime import datetime
from pathlib import Path

def parse_kv_pairs(pairs):
    """Parses a list of 'key:value' strings into a dictionary."""
    result = {}
    if not pairs:
        return result
    for p in pairs:
        if ':' not in p:
            print(f"Warning: Invalid format '{p}'. Expected 'key:value'")
            continue
        key, value = p.split(':', 1)
        result[key.strip()] = value.strip()
    return result

def convert_test_to_golden(input_path, output_path, agent_name, metadata_pairs, id_prefix="q"):
    """
    Converts a list of conversation turns into a single golden question entry.
    """
    with open(input_path, 'r') as f:
        data = json.load(f)

    if not isinstance(data, list):
        print(f"Error: Input data in {input_path} is not a list of turns.")
        return

    user_inputs = []
    reference_tool_interactions = []
    
    for turn in data:
        user_inputs.append(turn.get('query', ''))
        
        # Map expected_tool_use to reference_tool_interactions
        for tool in turn.get('expected_tool_use', []):
            reference_tool_interactions.append({
                "tool_name": tool.get('tool_name'),
                "input_arguments": tool.get('tool_input')
            })

    # Prepare metadata
    metadata = parse_kv_pairs(metadata_pairs)
    # Always include the source for tracking
    metadata["source_file"] = os.path.basename(input_path)

    golden_question = {
        "id": f"{id_prefix}_{uuid.uuid4().hex[:8]}",
        "user_inputs": user_inputs,
        "agents_evaluated": [agent_name],
        "metadata": metadata,
        "reference_data": {
            "reference_tool_interactions": reference_tool_interactions,
            "reference_trajectory": [agent_name]
        },
        "updated_datetime": datetime.now().strftime("%Y-%m-%d")
    }

    output_data = {"golden_questions": [golden_question]}
    
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r') as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict) and "golden_questions" in existing_data:
                    existing_data["golden_questions"].append(golden_question)
                    output_data = existing_data
        except Exception:
            pass 

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=4)
    
    print(f"Successfully added golden question from '{input_path}' to '{output_path}'")

def main():
    parser = argparse.ArgumentParser(description="Convert turn-based test data to golden evaluation dataset format.")
    parser.add_argument("--input", required=True, help="Path to the input JSON file (list of turns).")
    parser.add_argument("--output", required=True, help="Path to the output golden dataset JSON file.")
    parser.add_argument("--agent", default="customer_service", help="Name of the agent being evaluated.")
    parser.add_argument("--metadata", action="append", dest="metadata", help="Metadata labels (e.g., 'complexity:easy', 'tenant:cymbal'). Can be used multiple times.")
    parser.add_argument("--prefix", default="q", help="Prefix for the question ID.")

    args = parser.parse_args()

    convert_test_to_golden(args.input, args.output, args.agent, args.metadata, args.prefix)

if __name__ == "__main__":
    main()