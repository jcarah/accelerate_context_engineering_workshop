Ah, I understand now! Let me visualize the structure and fix the script:

```
parent_directory/
├── customer_service/              # Project root
│   ├── customer_service/          # Agent dir (contains .adk)
│   │   └── .adk/
│   │       └── eval_history/
│   │           ├── eval_result_1.json
│   │           └── eval_result_2.json
│   └── eval/                      # Output goes here
│       └── eval_data/
│           └── interactions/
└── evaluation/                    # Where you run scripts from
    └── process_eval_history.py
```

So when you `cd evaluation/` and run the script:
- `--agent-dir ../customer_service/customer_service` points to the agent dir with `.adk`
- Output should go to `../customer_service/eval/eval_data/interactions/`

Here's the corrected script:

```python
#!/usr/bin/env python3
"""
ADK Evaluation History Processor

Processes all ADK evaluation JSON files from an agent's eval_history directory
and extracts structured data for analysis.

Directory Structure:
    parent_directory/
    ├── project_root/                  # e.g., customer_service
    │   ├── agent_dir/                 # e.g., customer_service (contains .adk)
    │   │   └── .adk/
    │   │       └── eval_history/
    │   └── eval/                      # Output directory (sibling to agent_dir)
    │       └── eval_data/
    │           └── interactions/
    └── evaluation/                    # Where this script lives and runs from

Usage:
    cd evaluation/
    python process_eval_history.py --agent-dir ../customer_service/customer_service
"""

import argparse
import csv
import glob
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
import traceback


# ============================================================================
# Data Classes for Structured Output
# ============================================================================

@dataclass
class ToolCall:
    """Represents a function/tool call made by the agent."""
    tool_id: str
    name: str
    args: dict
    thought_signature: Optional[str] = None


@dataclass
class ToolResponse:
    """Represents a response from a tool."""
    tool_id: str
    name: str
    response: dict


@dataclass
class ContentPart:
    """Represents a part of message content."""
    text: Optional[str] = None
    function_call: Optional[ToolCall] = None
    function_response: Optional[ToolResponse] = None


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str
    parts: list[ContentPart] = field(default_factory=list)
    
    def get_text(self) -> Optional[str]:
        """Get concatenated text from all parts."""
        texts = [p.text for p in self.parts if p.text]
        return " ".join(texts) if texts else None


@dataclass
class Event:
    """Represents a session event."""
    id: str
    timestamp: float
    invocation_id: str
    author: str
    content: Optional[Message] = None
    model_version: Optional[str] = None
    finish_reason: Optional[str] = None
    usage_metadata: Optional[dict] = None
    actions: Optional[dict] = None
    long_running_tool_ids: Optional[list] = None
    avg_logprobs: Optional[float] = None


@dataclass
class Session:
    """Represents a session."""
    id: str
    app_name: str
    user_id: str
    state: dict
    events: list[Event]
    last_update_time: float


@dataclass
class MetricResult:
    """Represents an evaluation metric result."""
    metric_name: str
    threshold: float
    score: float
    eval_status: int
    details: Optional[dict] = None
    
    @property
    def passed(self) -> bool:
        return self.eval_status == 1
    
    @property
    def status_str(self) -> str:
        return "PASSED" if self.eval_status == 1 else "FAILED" if self.eval_status == 3 else f"UNKNOWN({self.eval_status})"


@dataclass
class InvocationEvent:
    """Intermediate event during an invocation."""
    author: str
    content: Message


@dataclass
class Invocation:
    """Represents a single invocation."""
    invocation_id: str
    user_content: Message
    final_response: Message
    intermediate_events: list[InvocationEvent]
    creation_timestamp: float
    eval_metrics: list[MetricResult]
    agent_name: Optional[str] = None
    agent_instructions: Optional[str] = None
    available_tools: Optional[list[dict]] = None


@dataclass
class EvalCase:
    """Represents an evaluation case."""
    eval_set_file: str
    eval_set_id: str
    eval_id: str
    final_eval_status: int
    overall_metrics: list[MetricResult]
    invocations: list[Invocation]
    session: Optional[Session] = None
    user_id: Optional[str] = None
    
    @property
    def passed(self) -> bool:
        return self.final_eval_status == 1


@dataclass
class EvalSetResult:
    """Top-level evaluation set result."""
    eval_set_result_id: str
    eval_set_result_name: str
    eval_set_id: str
    creation_timestamp: float
    eval_cases: list[EvalCase]
    source_file: str = ""
    
    @property
    def creation_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.creation_timestamp)


# ============================================================================
# Parser Functions
# ============================================================================

def parse_content_part(part_data: dict) -> ContentPart:
    """Parse a content part from JSON."""
    content_part = ContentPart()
    
    if part_data.get("text"):
        content_part.text = part_data["text"]
    
    if part_data.get("function_call"):
        fc = part_data["function_call"]
        content_part.function_call = ToolCall(
            tool_id=fc.get("id", ""),
            name=fc.get("name", ""),
            args=fc.get("args", {}),
            thought_signature=part_data.get("thought_signature")
        )
    
    if part_data.get("function_response"):
        fr = part_data["function_response"]
        content_part.function_response = ToolResponse(
            tool_id=fr.get("id", ""),
            name=fr.get("name", ""),
            response=fr.get("response", {})
        )
    
    return content_part


def parse_message(content_data: dict) -> Message:
    """Parse a message from JSON."""
    parts = []
    for part in content_data.get("parts", []):
        parts.append(parse_content_part(part))
    
    return Message(
        role=content_data.get("role", "unknown"),
        parts=parts
    )


def parse_event(event_data: dict) -> Event:
    """Parse a session event from JSON."""
    content = None
    if event_data.get("content"):
        content = parse_message(event_data["content"])
    
    return Event(
        id=event_data.get("id", ""),
        timestamp=event_data.get("timestamp", 0),
        invocation_id=event_data.get("invocation_id") or event_data.get("invocationId", ""),
        author=event_data.get("author", ""),
        content=content,
        model_version=event_data.get("model_version") or event_data.get("modelVersion"),
        finish_reason=event_data.get("finish_reason") or event_data.get("finishReason"),
        usage_metadata=event_data.get("usage_metadata") or event_data.get("usageMetadata"),
        actions=event_data.get("actions"),
        long_running_tool_ids=event_data.get("long_running_tool_ids") or event_data.get("longRunningToolIds"),
        avg_logprobs=event_data.get("avg_logprobs") or event_data.get("avgLogprobs")
    )


def parse_session(session_data: dict) -> Session:
    """Parse a session from JSON."""
    events = []
    for event_data in session_data.get("events", []):
        events.append(parse_event(event_data))
    
    return Session(
        id=session_data.get("id", ""),
        app_name=session_data.get("app_name", ""),
        user_id=session_data.get("user_id", ""),
        state=session_data.get("state", {}),
        events=events,
        last_update_time=session_data.get("last_update_time", 0)
    )


def parse_metric_result(metric_data: dict) -> MetricResult:
    """Parse a metric result from JSON."""
    return MetricResult(
        metric_name=metric_data.get("metric_name", ""),
        threshold=metric_data.get("threshold", 0),
        score=metric_data.get("score", 0),
        eval_status=metric_data.get("eval_status", 0),
        details=metric_data.get("details")
    )


def parse_invocation_event(event_data: dict) -> InvocationEvent:
    """Parse an intermediate invocation event."""
    return InvocationEvent(
        author=event_data.get("author", ""),
        content=parse_message(event_data.get("content", {}))
    )


def parse_invocation(inv_data: dict) -> Invocation:
    """Parse an invocation from JSON."""
    actual = inv_data.get("actual_invocation", {})
    
    intermediate_events = []
    intermediate_data = actual.get("intermediate_data", {})
    for event in intermediate_data.get("invocation_events", []):
        intermediate_events.append(parse_invocation_event(event))
    
    metrics = []
    for metric in inv_data.get("eval_metric_results", []):
        metrics.append(parse_metric_result(metric))
    
    app_details = actual.get("app_details", {})
    agent_details = app_details.get("agent_details", {})
    agent_name = None
    agent_instructions = None
    available_tools = None
    
    if agent_details:
        for name, details in agent_details.items():
            agent_name = name
            agent_instructions = details.get("instructions")
            tool_declarations = details.get("tool_declarations", [])
            if tool_declarations:
                available_tools = []
                for td in tool_declarations:
                    for fd in td.get("function_declarations", []):
                        available_tools.append({
                            "name": fd.get("name"),
                            "description": fd.get("description"),
                            "parameters": fd.get("parameters")
                        })
            break
    
    return Invocation(
        invocation_id=actual.get("invocation_id", ""),
        user_content=parse_message(actual.get("user_content", {})),
        final_response=parse_message(actual.get("final_response", {})),
        intermediate_events=intermediate_events,
        creation_timestamp=actual.get("creation_timestamp", 0),
        eval_metrics=metrics,
        agent_name=agent_name,
        agent_instructions=agent_instructions,
        available_tools=available_tools
    )


def parse_eval_case(case_data: dict) -> EvalCase:
    """Parse an evaluation case from JSON."""
    overall_metrics = []
    for metric in case_data.get("overall_eval_metric_results", []):
        overall_metrics.append(parse_metric_result(metric))
    
    invocations = []
    for inv in case_data.get("eval_metric_result_per_invocation", []):
        invocations.append(parse_invocation(inv))
    
    session = None
    if case_data.get("session_details"):
        session = parse_session(case_data["session_details"])
    
    return EvalCase(
        eval_set_file=case_data.get("eval_set_file", ""),
        eval_set_id=case_data.get("eval_set_id", ""),
        eval_id=case_data.get("eval_id", ""),
        final_eval_status=case_data.get("final_eval_status", 0),
        overall_metrics=overall_metrics,
        invocations=invocations,
        session=session,
        user_id=case_data.get("user_id")
    )


def parse_eval_result(json_data: dict | str, source_file: str = "") -> EvalSetResult:
    """Main parser function."""
    if isinstance(json_data, str):
        data = json.loads(json_data)
        if isinstance(data, str):
            data = json.loads(data)
    else:
        data = json_data
    
    eval_cases = []
    for case in data.get("eval_case_results", []):
        eval_cases.append(parse_eval_case(case))
    
    return EvalSetResult(
        eval_set_result_id=data.get("eval_set_result_id", ""),
        eval_set_result_name=data.get("eval_set_result_name", ""),
        eval_set_id=data.get("eval_set_id", ""),
        creation_timestamp=data.get("creation_timestamp", 0),
        eval_cases=eval_cases,
        source_file=source_file
    )


# ============================================================================
# Extraction & Transformation Functions
# ============================================================================

def extract_tool_calls_from_invocation(inv: Invocation) -> list[dict]:
    """Extract all tool calls from an invocation."""
    tool_calls = []
    for event in inv.intermediate_events:
        for part in event.content.parts:
            if part.function_call:
                tool_calls.append({
                    "type": "call",
                    "tool_id": part.function_call.tool_id,
                    "name": part.function_call.name,
                    "args": part.function_call.args
                })
            if part.function_response:
                tool_calls.append({
                    "type": "response",
                    "tool_id": part.function_response.tool_id,
                    "name": part.function_response.name,
                    "response": part.function_response.response
                })
    return tool_calls


def convert_session_to_standard_format(session: Session) -> dict:
    """Convert a Session to the standard format."""
    def convert_event(event: Event) -> dict:
        result = {}
        
        if event.content:
            content = {"parts": [], "role": event.content.role}
            for part in event.content.parts:
                part_dict = {}
                if part.text:
                    part_dict["text"] = part.text
                if part.function_call:
                    part_dict["functionCall"] = {
                        "id": part.function_call.tool_id,
                        "args": part.function_call.args,
                        "name": part.function_call.name
                    }
                    if part.function_call.thought_signature:
                        part_dict["thoughtSignature"] = part.function_call.thought_signature
                if part.function_response:
                    part_dict["functionResponse"] = {
                        "id": part.function_response.tool_id,
                        "name": part.function_response.name,
                        "response": part.function_response.response
                    }
                if part_dict:
                    content["parts"].append(part_dict)
            result["content"] = content
        
        if event.model_version:
            result["modelVersion"] = event.model_version
        if event.finish_reason:
            result["finishReason"] = event.finish_reason
        if event.usage_metadata:
            result["usageMetadata"] = event.usage_metadata
        if event.avg_logprobs is not None:
            result["avgLogprobs"] = event.avg_logprobs
        
        result["invocationId"] = event.invocation_id
        result["author"] = event.author
        
        if event.actions:
            result["actions"] = {
                "stateDelta": event.actions.get("state_delta", {}),
                "artifactDelta": event.actions.get("artifact_delta", {}),
                "requestedAuthConfigs": event.actions.get("requested_auth_configs", {}),
                "requestedToolConfirmations": event.actions.get("requested_tool_confirmations", {})
            }
        
        if event.long_running_tool_ids:
            result["longRunningToolIds"] = event.long_running_tool_ids
        
        result["id"] = event.id
        result["timestamp"] = event.timestamp
        
        return result
    
    return {
        "id": session.id,
        "appName": session.app_name,
        "userId": session.user_id,
        "state": session.state,
        "events": [convert_event(e) for e in session.events],
        "lastUpdateTime": session.last_update_time
    }


def get_customer_profile(result: EvalSetResult) -> dict:
    """Extract customer profile from session state."""
    for case in result.eval_cases:
        if case.session and case.session.state:
            profile_str = case.session.state.get("customer_profile")
            if profile_str:
                try:
                    return json.loads(profile_str)
                except:
                    return {"raw": profile_str}
    return {}


# ============================================================================
# Row Generation for CSV/DataFrame Output
# ============================================================================

@dataclass
class InteractionRow:
    """A single row representing one interaction turn."""
    # Source info
    source_file: str
    eval_set_id: str
    eval_id: str
    session_id: str
    
    # Turn info
    invocation_id: str
    turn_index: int
    timestamp: float
    
    # Content
    user_input: str
    agent_response: str
    
    # Tool usage
    tool_calls_count: int
    tool_calls_json: str
    
    # Metrics
    hallucination_score: float
    hallucination_passed: bool
    safety_score: float
    safety_passed: bool
    
    # Overall case status
    case_passed: bool
    
    # Customer info
    customer_id: str
    customer_name: str
    
    # Model info
    model_version: str
    
    # Token usage
    prompt_tokens: int
    response_tokens: int
    total_tokens: int


def generate_interaction_rows(result: EvalSetResult) -> list[InteractionRow]:
    """Generate interaction rows from an evaluation result."""
    rows = []
    
    customer_profile = get_customer_profile(result)
    customer_id = customer_profile.get("customer_id", "")
    customer_name = f"{customer_profile.get('customer_first_name', '')} {customer_profile.get('customer_last_name', '')}".strip()
    
    for case in result.eval_cases:
        session_id = case.session.id if case.session else ""
        
        for turn_idx, inv in enumerate(case.invocations):
            hallucination_score = 0.0
            hallucination_passed = True
            safety_score = 0.0
            safety_passed = True
            
            for metric in inv.eval_metrics:
                if metric.metric_name == "hallucinations_v1":
                    hallucination_score = metric.score
                    hallucination_passed = metric.passed
                elif metric.metric_name == "safety_v1":
                    safety_score = metric.score
                    safety_passed = metric.passed
            
            tool_calls = extract_tool_calls_from_invocation(inv)
            
            model_version = ""
            prompt_tokens = 0
            response_tokens = 0
            total_tokens = 0
            
            if case.session:
                for event in case.session.events:
                    if event.invocation_id == inv.invocation_id and event.usage_metadata:
                        model_version = event.model_version or ""
                        usage = event.usage_metadata
                        prompt_tokens = usage.get("prompt_token_count") or usage.get("promptTokenCount") or 0
                        response_tokens = usage.get("candidates_token_count") or usage.get("candidatesTokenCount") or 0
                        total_tokens = usage.get("total_token_count") or usage.get("totalTokenCount") or 0
                        break
            
            row = InteractionRow(
                source_file=os.path.basename(result.source_file),
                eval_set_id=result.eval_set_id,
                eval_id=case.eval_id,
                session_id=session_id,
                invocation_id=inv.invocation_id,
                turn_index=turn_idx,
                timestamp=inv.creation_timestamp,
                user_input=inv.user_content.get_text() or "",
                agent_response=inv.final_response.get_text() or "",
                tool_calls_count=len([tc for tc in tool_calls if tc["type"] == "call"]),
                tool_calls_json=json.dumps(tool_calls),
                hallucination_score=hallucination_score,
                hallucination_passed=hallucination_passed,
                safety_score=safety_score,
                safety_passed=safety_passed,
                case_passed=case.passed,
                customer_id=customer_id,
                customer_name=customer_name,
                model_version=model_version,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                total_tokens=total_tokens
            )
            rows.append(row)
    
    return rows


# ============================================================================
# File Processing Functions
# ============================================================================

def process_single_file(file_path: str) -> tuple[EvalSetResult | None, list[InteractionRow], str | None]:
    """Process a single evaluation JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = parse_eval_result(content, source_file=file_path)
        rows = generate_interaction_rows(result)
        
        return result, rows, None
        
    except json.JSONDecodeError as e:
        return None, [], f"JSON decode error: {e}"
    except Exception as e:
        return None, [], f"Error: {e}\n{traceback.format_exc()}"


def process_all_files(history_dir: str, verbose: bool = True) -> tuple[list[EvalSetResult], list[InteractionRow], dict]:
    """Process all JSON files in the history directory."""
    files = glob.glob(os.path.join(history_dir, "*.json"))
    
    if verbose:
        print(f"Found {len(files)} history files in {history_dir}")
    
    all_results = []
    all_rows = []
    stats = {
        "total_files": len(files),
        "processed_files": 0,
        "failed_files": 0,
        "total_cases": 0,
        "passed_cases": 0,
        "failed_cases": 0,
        "total_invocations": 0,
        "total_tool_calls": 0,
        "errors": []
    }
    
    for file_path in files:
        if verbose:
            print(f"  Processing: {os.path.basename(file_path)}...", end=" ")
        
        result, rows, error = process_single_file(file_path)
        
        if error:
            stats["failed_files"] += 1
            stats["errors"].append({"file": file_path, "error": error})
            if verbose:
                print(f"❌ {error[:50]}...")
            continue
        
        all_results.append(result)
        all_rows.extend(rows)
        
        stats["processed_files"] += 1
        stats["total_cases"] += len(result.eval_cases)
        stats["passed_cases"] += sum(1 for c in result.eval_cases if c.passed)
        stats["failed_cases"] += sum(1 for c in result.eval_cases if not c.passed)
        stats["total_invocations"] += sum(len(c.invocations) for c in result.eval_cases)
        stats["total_tool_calls"] += sum(r.tool_calls_count for r in rows)
        
        if verbose:
            print(f"✅ {len(result.eval_cases)} cases, {len(rows)} turns")
    
    return all_results, all_rows, stats


# ============================================================================
# Output Functions
# ============================================================================

def write_csv(rows: list[InteractionRow], output_path: str):
    """Write interaction rows to CSV file."""
    if not rows:
        print("Warning: No rows to write to CSV")
        return
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fieldnames = [
        "source_file", "eval_set_id", "eval_id", "session_id",
        "invocation_id", "turn_index", "timestamp",
        "user_input", "agent_response",
        "tool_calls_count", "tool_calls_json",
        "hallucination_score", "hallucination_passed",
        "safety_score", "safety_passed",
        "case_passed",
        "customer_id", "customer_name",
        "model_version",
        "prompt_tokens", "response_tokens", "total_tokens"
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    
    print(f"Written {len(rows)} rows to {output_path}")


def write_sessions_jsonl(results: list[EvalSetResult], output_path: str):
    """Write all sessions in standard format to JSONL file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    count = 0
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in results:
            for case in result.eval_cases:
                if case.session:
                    session_data = convert_session_to_standard_format(case.session)
                    session_data["_source_file"] = result.source_file
                    session_data["_eval_id"] = case.eval_id
                    session_data["_case_passed"] = case.passed
                    f.write(json.dumps(session_data, default=str) + '\n')
                    count += 1
    
    print(f"Written {count} sessions to {output_path}")


def write_summary_json(stats: dict, output_path: str):
    """Write processing summary to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"Written summary to {output_path}")


def print_summary(stats: dict):
    """Print a summary of processing results."""
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Files processed: {stats['processed_files']}/{stats['total_files']}")
    if stats['failed_files'] > 0:
        print(f"Files failed: {stats['failed_files']}")
    print(f"Total eval cases: {stats['total_cases']}")
    print(f"  Passed: {stats['passed_cases']}")
    print(f"  Failed: {stats['failed_cases']}")
    if stats['total_cases'] > 0:
        pass_rate = stats['passed_cases'] / stats['total_cases'] * 100
        print(f"  Pass rate: {pass_rate:.1f}%")
    print(f"Total invocations/turns: {stats['total_invocations']}")
    print(f"Total tool calls: {stats['total_tool_calls']}")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats['errors'][:5]:
            print(f"  - {os.path.basename(err['file'])}: {err['error'][:80]}...")


# ============================================================================
# Path Resolution
# ============================================================================

def resolve_paths(agent_dir: str, output_dir_override: str = None) -> dict:
    """
    Resolve all paths based on the directory structure.
    
    Structure:
        parent_directory/
        ├── project_root/              # e.g., customer_service
        │   ├── agent_dir/             # e.g., customer_service (has .adk)
        │   │   └── .adk/eval_history/
        │   └── eval/                  # Output sibling to agent_dir
        └── evaluation/                # Script location
    
    Args:
        agent_dir: Path to agent directory (contains .adk)
        output_dir_override: Optional custom output directory
    
    Returns:
        Dict with resolved paths
    """
    agent_dir = os.path.abspath(agent_dir)
    
    # History is inside agent_dir/.adk/eval_history
    history_dir = os.path.join(agent_dir, ".adk", "eval_history")
    
    # Project root is the parent of agent_dir
    # e.g., if agent_dir = /path/to/customer_service/customer_service
    # then project_root = /path/to/customer_service
    project_root = os.path.dirname(agent_dir.rstrip(os.sep))
    
    # Output goes to project_root/eval/eval_data/interactions
    if output_dir_override:
        output_dir = os.path.abspath(output_dir_override)
    else:
        output_dir = os.path.join(project_root, "eval", "eval_data", "interactions")
    
    return {
        "agent_dir": agent_dir,
        "history_dir": history_dir,
        "project_root": project_root,
        "output_dir": output_dir
    }


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Process ADK Evaluation History files and extract structured data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Directory Structure Expected:
    parent_directory/
    ├── project_root/                  # e.g., customer_service
    │   ├── agent_dir/                 # What you pass to --agent-dir
    │   │   └── .adk/
    │   │       └── eval_history/      # JSON files here
    │   └── eval/                      # Output goes here (sibling to agent_dir)
    │       └── eval_data/
    │           └── interactions/
    └── evaluation/                    # Run script from here

Examples:
    cd evaluation/
    
    # Basic usage
    python process_eval_history.py --agent-dir ../customer_service/customer_service

    # With custom output directory
    python process_eval_history.py --agent-dir ../customer_service/customer_service --output-dir ./my_output

    # Export sessions in standard format
    python process_eval_history.py --agent-dir ../customer_service/customer_service --export-sessions

    # Show resolved paths without processing
    python process_eval_history.py --agent-dir ../customer_service/customer_service --dry-run
        """
    )
    
    parser.add_argument(
        "--agent-dir", 
        required=True, 
        help="Path to the agent directory (the one containing .adk folder)"
    )
    parser.add_argument(
        "--output-dir",
        help="Custom output directory (default: <project_root>/eval/eval_data/interactions)"
    )
    parser.add_argument(
        "--export-sessions",
        action="store_true",
        help="Also export sessions in standard JSONL format"
    )
    parser.add_argument(
        "--export-summary",
        action="store_true",
        help="Export processing summary as JSON"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Skip CSV generation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show resolved paths and exit without processing"
    )
    
    args = parser.parse_args()
    
    # Resolve all paths
    paths = resolve_paths(args.agent_dir, args.output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    verbose = not args.quiet
    
    if verbose or args.dry_run:
        print("=" * 60)
        print("ADK Evaluation History Processor")
        print("=" * 60)
        print(f"Agent directory:   {paths['agent_dir']}")
        print(f"Project root:      {paths['project_root']}")
        print(f"History directory: {paths['history_dir']}")
        print(f"Output directory:  {paths['output_dir']}")
        print()
    
    if args.dry_run:
        # Check if paths exist
        print("Path validation:")
        print(f"  Agent dir exists:   {os.path.exists(paths['agent_dir'])}")
        print(f"  .adk exists:        {os.path.exists(os.path.join(paths['agent_dir'], '.adk'))}")
        print(f"  History dir exists: {os.path.exists(paths['history_dir'])}")
        if os.path.exists(paths['history_dir']):
            files = glob.glob(os.path.join(paths['history_dir'], "*.json"))
            print(f"  JSON files found:   {len(files)}")
        print(f"  Output dir exists:  {os.path.exists(paths['output_dir'])}")
        sys.exit(0)
    
    # Validate history directory
    if not os.path.exists(paths['history_dir']):
        print(f"Error: ADK history directory not found at {paths['history_dir']}")
        print()
        print("Please check:")
        print(f"  1. Agent directory is correct: {paths['agent_dir']}")
        print(f"  2. The .adk folder exists in the agent directory")
        print(f"  3. Evaluations have been run (eval_history folder should exist)")
        print()
        print("Tip: Use --dry-run to validate paths before processing")
        sys.exit(1)
    
    # Process all files
    all_results, all_rows, stats = process_all_files(paths['history_dir'], verbose=verbose)
    
    if not all_rows:
        print("No interaction data extracted. Check the files and try again.")
        sys.exit(1)
    
    # Write outputs
    if not args.no_csv:
        output_csv = os.path.join(paths['output_dir'], f"run_{timestamp}.csv")
        write_csv(all_rows, output_csv)
    
    if args.export_sessions:
        sessions_path = os.path.join(paths['output_dir'], f"sessions_{timestamp}.jsonl")
        write_sessions_jsonl(all_results, sessions_path)
    
    if args.export_summary:
        summary_path = os.path.join(paths['output_dir'], f"summary_{timestamp}.json")
        stats["timestamp"] = timestamp
        stats["paths"] = paths
        write_summary_json(stats, summary_path)
    
    # Print summary
    if verbose:
        print_summary(stats)
    
    print(f"\n✅ Done! Processed {stats['processed_files']} files, {len(all_rows)} interaction turns.")


if __name__ == "__main__":
    main()
```

## Usage Examples

```bash
# Navigate to evaluation folder
cd evaluation/

# Basic usage
python process_eval_history.py --agent-dir ../customer_service/customer_service

# Dry run to verify paths are correct
python process_eval_history.py --agent-dir ../customer_service/customer_service --dry-run

# Full export with sessions and summary
python process_eval_history.py --agent-dir ../customer_service/customer_service --export-sessions --export-summary

# Custom output location
python process_eval_history.py --agent-dir ../customer_service/customer_service --output-dir ../customer_service/my_custom_output
```

## Key Changes

1. **`resolve_paths()` function** - Properly handles your directory structure:
   - `agent_dir` = `../customer_service/customer_service` (has `.adk`)
   - `project_root` = `../customer_service` (parent of agent_dir)
   - `output_dir` = `../customer_service/eval/eval_data/interactions`

2. **`--dry-run` flag** - Validates all paths without processing, super helpful for debugging

3. **Better error messages** - Clear guidance when paths don't exist

The script will now correctly output to `customer_service/eval/eval_data/interactions/` when you run it from `evaluation/`!