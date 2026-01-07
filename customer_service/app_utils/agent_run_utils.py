import requests
import subprocess
import json
import uuid
import re
from datetime import datetime
import time


def get_gcloud_token():
    """Fetches the gcloud identity token."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], text=True
        ).strip()
        return token
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error getting gcloud token: {e}")
        print("Please ensure you are logged in with 'gcloud auth login' and have the necessary permissions.")
        exit(1)

def create_session(base_url, user_id, token, dataset_id):
    """Creates a new session for the agent."""
    session_id = f"session_{uuid.uuid4()}"
    url = f"{base_url}/apps/customer_service/users/{user_id}/sessions/{session_id}"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = {
      "dataset_id": dataset_id
    }
    
    print(f"Creating session: {session_id}...")
    retries = 3
    delay = 1
    for i in range(retries):
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print("Session created successfully.")
            return response.json()["id"]
        except requests.exceptions.RequestException as e:
            if i < retries - 1:
                print(f"Request failed with {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                raise

def run_agent_interaction(base_url, user_id, session_id, question, token):
    """Sends a question to the agent."""
    url = f"{base_url}/run"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "app_name": "data_explorer_agent",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": question}]
        },
        "streaming": False
    }

    print("Sending question to agent...")
    retries = 3
    delay = 1
    for i in range(retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print("Agent processing complete.")
            return response.json()
        except requests.exceptions.RequestException as e:
            if i < retries - 1:
                print(f"Request failed with {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                raise

def get_session_state(base_url, user_id, session_id, token):
    """Retrieves the final state of a session."""
    url = f"{base_url}/apps/data_explorer_agent/users/{user_id}/sessions/{session_id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    print("Retrieving final session state...")
    retries = 3
    delay = 1
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            print(f"[SUCCESS] Retrieving [SESSION DATA] for session {session_id}!")
            return response.json()
        except requests.exceptions.RequestException as e:
            if i < retries - 1:
                print(f"Request failed with {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                raise

def get_agent_trajectory(analyzed_trace):
    trajectory = []
    def traverse(span):
        if 'agent_run' in span.get('name', ''):
            match = re.search(r'\[(.*)\]', span.get('name', ''))
            if match:
                agent_name = match.group(1)
                trajectory.append(agent_name)

        for child in span.get('children', []):
            traverse(child)

    for root in analyzed_trace:
        traverse(root)
    return trajectory

def get_session_trace(base_url, session_id, token):
    """Get the session trace.
    
    Args:
        base_url: Base URL of the agent service
        session_id: Session ID to retrieve trace for
        token: Authentication token
    
    Raises:
        RuntimeError: If trace cannot be retrieved after all retries across all URLs.
    """
    headers = {"Authorization": f"Bearer {token}"}
    base_url_clean = base_url.rstrip("/")
    urls = [
        f"{base_url_clean}/debug/trace/session/{session_id}",
        f"{base_url_clean}/apps/data_explorer_agent/sessions/{session_id}/trace"
    ]
    
    for url in urls:
        delay = 1
        for i in range(5):  # Retry up to 5 times
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 404:
                    print(f"Trace not found at {url}, trying next URL...")
                    break  # Move to the next URL
                response.raise_for_status()
                trace = response.json()
                if trace:
                    print(f"[SUCCESS] Retrieving [TRACE] for session {session_id}!")
                    return trace
                print(f"Trace for session {session_id} is empty, retrying in {delay} seconds...")
            except requests.exceptions.HTTPError as e:
                print(f"HTTP error getting session trace: {e}. Retrying in {delay} seconds...")
            except Exception as e:
                print(f"An unexpected error occurred: {e}. Retrying in {delay} seconds...")
            
            time.sleep(delay)
            delay *= 2
    
    # If we've exhausted all retries on all URLs, raise an exception
    raise RuntimeError(f"Failed to retrieve trace for session {session_id} after trying all URLs and retries")

def get_function_call_response(session_data, function_name):
    """Extracts the response from the SQL explorer sub-agent to the root agent."""
    events = session_data.get('events', [])
    for event in events:
        if event.get('content', {}).get('parts', [{}])[0].get('functionResponse'):
            function_response = event['content']['parts'][0]['functionResponse']
            if function_response.get('name') == function_name:
                return function_response.get('response', {}).get('result', 'N/A')
    return "N/A"

def get_agent_response(session_data, agent_name):
    """Extracts the final natural language response from the session data."""
    events = session_data.get('events', [])
    final_answer_event = next((e for e in reversed(events) if e.get('author') == agent_name and e.get('content', {}).get('parts', [{}])[0].get('text')), None)
    if final_answer_event:
        return final_answer_event.get('content', {}).get('parts', [{}])[0].get('text', 'Response not found.')
    return None


def format_trace(session_state, session_trace, original_question, reference_data=None):
    """Formats the execution trace into a markdown string using spans and state."""
    trace_lines = []
    trace_lines.append("# Agent Execution Trace\n")
    trace_lines.append(f"## 1️⃣ - Initial User Query\n\n**Question:** {original_question}\n")

    analyzed_trace = analyze_trace_and_extract_spans(session_trace)

    def format_span_recursive(span, indent_prefix=""):
        span_type = span.get('type')
        
        # Determine if we should print this span
        should_print = span_type in ['AGENT_RUN', 'TOOL_CALL', 'TOOL_RESPONSE']

        if should_print:
            name = span['name']
            trace_lines.append(f"### {indent_prefix}{name} (`{span_type}`)")
            trace_lines.append(f"> Duration: {span['duration_ms']}ms")

            details = span.get('details', {})
            if details:
                for key, value in details.items():
                    if key in ['agent_name', 'tool_name']:
                        continue
                    trace_lines.append(f"\n**{key}:**\n")
                    if isinstance(value, (dict, list)):
                        value_str = json.dumps(value, indent=2)
                        trace_lines.append(f"```json\n{value_str}\n```")
                    else:
                        trace_lines.append(f"```\n{value}\n```")
            
            # Find and display all LLM child details
            llm_children = [child for child in span.get('children', []) if child.get('type') == 'LLM_CALL']
            if llm_children:
                trace_lines.append(f"\n**LLM Calls:**")
                for i, llm_child in enumerate(llm_children):
                    trace_lines.append(f"\n**LLM Call {i+1}:**\n")
                    llm_details = llm_child.get('details', {})
                    if llm_details:
                        for key, value in llm_details.items():
                            trace_lines.append(f"\n**{key}:**\n")
                            if isinstance(value, (dict, list)):
                                value_str = json.dumps(value, indent=2)
                                trace_lines.append(f"```json\n{value_str}\n```")
                            else:
                                trace_lines.append(f"```\n{value}\n```")

        # Recurse through children
        for child in span.get('children', []):
            new_prefix = f"{indent_prefix}--> " if should_print else indent_prefix
            format_span_recursive(child, new_prefix)

    trace_lines.append("## 2️⃣ - Execution Flow\n")
    for root_span in analyzed_trace:
        format_span_recursive(root_span)

    state = session_state.get('state', {})
    if state:
        trace_lines.append("\n## 3️⃣ - Final Session State\n")
        for key, value in state.items():
            trace_lines.append(f"### {key}\n")
            if isinstance(value, str):
                try:
                    parsed_json = json.loads(value)
                    value_str = json.dumps(parsed_json, indent=2)
                    trace_lines.append(f"```json\n{value_str}\n```\n")
                except (json.JSONDecodeError, TypeError):
                    trace_lines.append(f"```\n{value}\n```\n")
            elif isinstance(value, (dict, list)):
                value_str = json.dumps(value, indent=2)
                trace_lines.append(f"```json\n{value_str}\n```\n")
            else:
                trace_lines.append(f"```\n{value}\n```\n")

    if reference_data:
        trace_lines.append("\n---\n## 4️⃣ - Reference Data\n")
        for key, value in reference_data.items():
            trace_lines.append(f"### {key}\n```\n{value}\n```")

    latency_data = get_latency_from_spans(analyzed_trace)
    if latency_data:
        trace_lines.append("\n## 5️⃣ - Latency Analysis\n")
        trace_lines.append("```json")
        trace_lines.append(json.dumps(latency_data, indent=2))
        trace_lines.append("```\n")

    return "\n".join(trace_lines)



def parse_and_display_trace(session_state, session_trace, original_question, output_file=None, reference_data=None):
    """Parses the final session data and displays the execution trace."""
    formatted_trace = format_trace(session_state, session_trace, original_question, reference_data)
    if output_file:
        with open(output_file, "w") as f:
            f.write(formatted_trace)
    else:
        print(formatted_trace)

def get_function_call_arg(session_data, function_name): 
    """Extracts the input to the SQL explorer sub-agent from the session data."""
    events = session_data.get('events', [])
    tool_call_event = next((e for e in events if e.get('content', {}).get('parts', [{}])[0].get('functionCall')), None)
    if tool_call_event:
        call = tool_call_event['content']['parts'][0]['functionCall']
        if call.get("name") == function_name:
            args = call.get('args', {})
            return args.get('question', 'N/A')
    return "N/A"

def get_state_variable(session_data, variable):
    """Extracts a state variable from the session data."""
    state = session_data.get('state', {})
    return state.get(variable, None)

def get_final_payload_field(session_data, field_name):
    """
    Extracts a field from the final JSON payload event.
    The final payload is generated by the get_final_json_payload callback.
    """
    events = session_data.get('events', [])
    
    # Search for the final JSON payload in events (usually the last text event)
    for event in reversed(events):
        content = event.get('content', {})
        parts = content.get('parts', [])
        for part in parts:
            text = part.get('text', '')
            if text and 'natural_language_response' in text:
                try:
                    # The entire 'text' field is a JSON string, so we parse it first.
                    payload = json.loads(text)
                    # Then, we can access the desired field within the parsed JSON.
                    return payload.get(field_name)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, it might not be the JSON payload we're looking for.
                    continue
    
    return None

def get_event_type(event):
    """Determines the type of an event and extracts relevant details."""
    author = event.get('author', 'unknown')
    content_parts = event.get('content', {}).get('parts', [{}])
    
    event_details = {'author': author}

    if not content_parts:
        event_details['type'] = "empty_event"
        return event_details

    part = content_parts[0]
    if part.get('text'):
        event_details['type'] = "text"
        event_details['content'] = part['text']
        if author == 'user':
            event_details['sub_type'] = "user_request"
        else:
            event_details['sub_type'] = "agent_response"
    elif part.get('functionCall'):
        event_details['type'] = "function_call"
        event_details['tool_name'] = part['functionCall'].get('name', 'unknown_tool')
        event_details['args'] = part['functionCall'].get('args', {})
    elif part.get('functionResponse'):
        event_details['type'] = "function_response"
        event_details['tool_name'] = part['functionResponse'].get('name', 'unknown_tool')
        event_details['response'] = part['functionResponse'].get('response', {})
    else:
        event_details['type'] = "unknown"
        
    return event_details

def get_latency_from_spans(analyzed_trace):
    """
    Extracts latency information from the analyzed trace in a nested dictionary.
    Converts durations from ms to seconds.
    """
    def process_span(span):
        span_type = span.get('type')
        name = span.get('name')

        if span_type == 'HTTP_REQUEST':
            details = span.get('details', {})
            method = details.get('method', '')
            url = details.get('url', '')
            name = f"{method} [{url}]"

        latency_info = {
            "name": name,
            "type": span_type,
            "duration_seconds": round(span.get('duration_ms', 0) / 1000.0, 4),
        }
        children = span.get('children')
        if children:
            latency_info['children'] = [process_span(child) for child in children]
        return latency_info

    return [process_span(root) for root in analyzed_trace]



class _SpanNode:
    """A node in the trace tree, representing a single span."""
    def __init__(self, span_data):
        self.data = span_data
        self.id = span_data.get('span_id')
        self.parent_id = span_data.get('parent_span_id')
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)

def build_trace_tree(trace_data):
    """Builds a tree of spans from raw trace data."""
    span_nodes = {}
    for span in trace_data:
        span_nodes[span['span_id']] = _SpanNode(span)

    root_nodes = []
    for span_id, node in span_nodes.items():
        if node.parent_id and node.parent_id in span_nodes:
            span_nodes[node.parent_id].add_child(node)
        else:
            root_nodes.append(node)
    
    return root_nodes

def extract_span_information(span_node):
    """Extracts and classifies information from a single span node."""
    span_data = span_node.data
    name = span_data.get('name', '')
    attributes = span_data.get('attributes', {})
    
    # Convert nanoseconds to milliseconds for duration
    start_time = span_data.get('start_time', 0)
    end_time = span_data.get('end_time', 0)
    duration_ms = (end_time - start_time) / 1_000_000 if start_time and end_time else 0

    extracted_info = {
        'name': name,
        'span_id': span_data.get('span_id'),
        'parent_span_id': span_data.get('parent_span_id'),
        'duration_ms': round(duration_ms, 2),
        'type': 'OTHER',
        'details': {}
    }

    if name.startswith('agent_run'):
        extracted_info['type'] = 'AGENT_RUN'
        try:
            extracted_info['details']['agent_name'] = name.split('[')[1].split(']')[0]
        except IndexError:
            extracted_info['details']['agent_name'] = 'unknown'
    elif name.startswith('tool_call'):
        extracted_info['type'] = 'TOOL_CALL'
        try:
            tool_name = name.split('[')[1].split(']')[0]
            extracted_info['details']['tool_name'] = tool_name
        except IndexError:
            tool_name = 'unknown'
        
        if 'gcp.vertex.agent.tool_call_args' in attributes:
            try:
                extracted_info['details']['arguments'] = json.loads(attributes['gcp.vertex.agent.tool_call_args'])
            except (json.JSONDecodeError, TypeError):
                extracted_info['details']['arguments'] = attributes['gcp.vertex.agent.tool_call_args']

    elif name.startswith('tool_response'):
        extracted_info['type'] = 'TOOL_RESPONSE'
        try:
            tool_name = name.split('[')[1].split(']')[0]
            extracted_info['details']['tool_name'] = tool_name
        except IndexError:
            tool_name = 'unknown'

        if 'gcp.vertex.agent.tool_response' in attributes:
            try:
                tool_response = json.loads(attributes['gcp.vertex.agent.tool_response'])
                if 'content' in tool_response:
                    extracted_info['details']['response_content'] = tool_response.get('content')
                if 'actions' in tool_response and 'state_delta' in tool_response.get('actions', {}):
                    extracted_info['details']['state_delta'] = tool_response['actions']['state_delta']
            except (json.JSONDecodeError, TypeError):
                extracted_info['details']['raw_response'] = attributes['gcp.vertex.agent.tool_response']

    elif name == 'call_llm':
        extracted_info['type'] = 'LLM_CALL'
        if 'gen_ai.request.model' in attributes:
            extracted_info['details']['model'] = attributes['gen_ai.request.model']
        if 'gcp.vertex.agent.llm_request' in attributes:
            try:
                extracted_info['details']['request'] = json.loads(attributes['gcp.vertex.agent.llm_request'])
            except (json.JSONDecodeError, TypeError):
                pass  # or log error
        if 'gcp.vertex.agent.llm_response' in attributes:
            try:
                extracted_info['details']['response'] = json.loads(attributes['gcp.vertex.agent.llm_response'])
            except (json.JSONDecodeError, TypeError):
                pass  # or log error

    if 'http.method' in attributes:
        extracted_info['type'] = 'HTTP_REQUEST'
        extracted_info['details']['method'] = attributes.get('http.method')
        extracted_info['details']['url'] = attributes.get('http.url')
        extracted_info['details']['status_code'] = attributes.get('http.status_code')

    return extracted_info

def analyze_trace_and_extract_spans(trace_data):
    """
    Analyzes raw trace data to build a tree and extract classified information from each span.
    
    Args:
        trace_data: A list of span dictionaries from the trace JSON file.
        
    Returns:
        A list of dictionaries, where each dictionary represents a root span and its children
        in a nested structure, with extracted and classified information.
    """
    root_nodes = build_trace_tree(trace_data)
    
    def traverse_and_extract(span_node):
        extracted_info = extract_span_information(span_node)
        extracted_info['children'] = [traverse_and_extract(child) for child in span_node.children]
        return extracted_info

    analysis_results = [traverse_and_extract(root) for root in root_nodes]
        
    return analysis_results