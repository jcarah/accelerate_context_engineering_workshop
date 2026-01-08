"""
Deterministic metrics for evaluating agent execution success.

These metrics provide objective pass/fail measurements by analyzing trace data
and session state, without requiring LLM-as-judge evaluation.
"""

import json
from typing import Any, Dict, List, Tuple

import sys
import os

def calculate_end_to_end_success(
    session_state: Dict[str, Any],
    session_trace: List[Dict[str, Any]],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Calculate end-to-end success metric: binary pass/fail for RAG→SQL→BQ execution.
    
    Success criteria (all must pass):
    - RAG retrieval completed successfully
    - SQL generation completed successfully  
    - BigQuery execution completed without errors
    - Final response was generated
    
    Args:
        session_state: The session state dictionary containing agent outputs
        session_trace: The trace spans from the session
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 for success, 0.0 for failure
    """
    failures = []
    state = session_state.get('state', {})
    
    # Check if this is a negative test case
    if question_metadata and question_metadata.get('tier') == 'negative':
        # For negative tests, success is defined as NOT generating SQL
        generated_sql = state.get('sql_explorer:generated_sql')
        if generated_sql:
            return 0.0, "End-to-end execution FAILED: SQL was generated for a negative test case that should have been blocked."
        else:
            return 1.0, "End-to-end execution SUCCESS: Agent correctly refused to generate SQL for a negative test case."

    # Check if sql_explorer agent was supposed to run
    if 'sql_explorer' not in agents_evaluated:
        return 1.0, "Agent sql_explorer not evaluated in this interaction."
    
    # 1. Check RAG retrieval
    rag_tables = state.get('sql_explorer:rag_relevant_tables', [])
    if not rag_tables or not isinstance(rag_tables, list) or len(rag_tables) == 0:
        failures.append("RAG retrieval failed: No relevant tables retrieved")
    
    # 2. Check SQL generation
    generated_sql = state.get('sql_explorer:generated_sql')
    if not generated_sql or not isinstance(generated_sql, str) or generated_sql.strip() == '':
        failures.append("SQL generation failed: No SQL query generated")
    
    # 3. Check SQL execution status
    sql_status = state.get('sql_explorer:status')
    if sql_status and sql_status != 'success':
        failures.append(f"SQL execution failed: status={sql_status}")
    
    # 4. Check BigQuery execution result
    bq_result = state.get('sql_explorer:sql_execution_result')
    if bq_result is None:
        failures.append("BigQuery execution failed: No execution result returned")
    elif isinstance(bq_result, str):
        # Try to parse as JSON to verify it's valid
        try:
            parsed_result = json.loads(bq_result) if bq_result else None
            # Empty list is OK (valid query, no results), but None/null is not
            if parsed_result is None and bq_result.lower() != 'null':
                failures.append("BigQuery execution failed: Result is null")
        except json.JSONDecodeError:
            failures.append("BigQuery execution failed: Invalid JSON result")
    
    # 5. Check final response generation
    final_response = state.get('nl_final_response_text')
    if not final_response or not isinstance(final_response, str) or final_response.strip() == '':
        failures.append("Response generation failed: No final response generated")
    
    # 6. Check trace for errors
    trace_errors = check_trace_for_errors(session_trace)
    if trace_errors:
        failures.extend(trace_errors)
    
    # Calculate score and explanation
    if failures:
        score = 0.0
        explanation = "End-to-end execution FAILED. Failures detected: " + "; ".join(failures)
    else:
        score = 1.0
        explanation = "End-to-end execution SUCCESS. All stages (RAG retrieval, SQL generation, BigQuery execution, response generation) completed successfully."
    
    return score, explanation


def calculate_deterministic_accuracy_with_threshold(
    session_state: Dict[str, Any],
    reference_bq_response: str,
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any],
    accuracy_threshold: float = 0.8
) -> Tuple[float, str]:
    """
    Calculate deterministic accuracy metric: checks if the agent's natural language response 
    contains the key information from the executed reference SQL results.
    
    This metric provides deterministic evaluation by extracting key data points from the 
    reference SQL execution results and checking if they appear in the agent's response.
    
    Args:
        session_state: The session state dictionary containing agent outputs
        reference_bq_response: JSON string containing the results from executing the reference SQL
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        accuracy_threshold: Minimum proportion of key values that must be found (default 0.8)
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 if key reference data is found, 0.0 otherwise
    """
    state = session_state.get('state', {})
    
    if question_metadata and question_metadata.get('tier') == 'negative':
        return 1.0, "Deterministic accuracy not applicable for negative test cases."

    # Check if we have reference SQL results to compare against
    if not reference_bq_response or not isinstance(reference_bq_response, str) or reference_bq_response.strip() == '':
        return 0.0, "Deterministic accuracy failed: No reference SQL results provided"
    
    # Get the agent's final natural language response
    agent_response = state.get('nl_final_response_text')
    if not agent_response or not isinstance(agent_response, str) or agent_response.strip() == '':
        return 0.0, "Deterministic accuracy failed: No final response generated by agent"
    
    try:
        # Parse the reference SQL results
        reference_data = json.loads(reference_bq_response)
        if not reference_data or not isinstance(reference_data, list):
            return 0.0, "Deterministic accuracy failed: Invalid reference SQL results format"
        
        # Extract key information from the reference results
        key_values = []
        for row in reference_data:
            if isinstance(row, dict):
                # Extract all values from each row, focusing on string/numeric data
                for key, value in row.items():
                    if value is not None:
                        # Convert to string and clean up
                        str_value = str(value).strip()
                        if str_value and str_value.lower() not in ['null', 'none', '']:
                            key_values.append(str_value)
        
        if not key_values:
            return 0.0, "Deterministic accuracy failed: No key values extracted from reference results"
        
        # Clean agent response for comparison
        agent_response_clean = agent_response.strip().lower()
        
        # Check how many key values from reference are found in agent's response
        found_values = []
        for value in key_values:
            value_clean = str(value).strip().lower()
            if _is_value_found_in_response(value_clean, agent_response_clean):
                found_values.append(value)
        
        # Calculate accuracy based on proportion of key values found
        accuracy_ratio = len(found_values) / len(key_values) if key_values else 0
        
        # Use configurable accuracy threshold
        if accuracy_ratio >= accuracy_threshold:
            score = 1.0
            explanation = f"Deterministic accuracy SUCCESS: {len(found_values)}/{len(key_values)} key values found in agent response (need >= {accuracy_threshold:.0%}). Found: {found_values[:5]}{'...' if len(found_values) > 5 else ''}"
        else:
            score = 0.0
            explanation = f"Deterministic accuracy FAILED: Only {len(found_values)}/{len(key_values)} key values found (need >= {accuracy_threshold:.0%}). Missing key data from reference results."
        
        return score, explanation
        
    except json.JSONDecodeError:
        return 0.0, "Deterministic accuracy failed: Could not parse reference SQL results as JSON"
    except Exception as e:
        return 0.0, f"Deterministic accuracy failed: Error processing reference data: {str(e)}"


def _is_value_found_in_response(value_str: str, response_str: str) -> bool:
    """
    Enhanced matching logic that handles number formatting and month variations.
    
    Args:
        value_str: The reference value to find (cleaned, lowercase)
        response_str: The agent response text (cleaned, lowercase)
    
    Returns:
        True if the value is found in the response, accounting for formatting differences
    """
    # Simple direct match first
    if value_str in response_str:
        return True
    
    # Handle numeric values with formatting differences
    if value_str.isdigit():
        # Try to find the number with comma formatting
        try:
            num = int(value_str)
            formatted_num = f"{num:,}".lower()  # Add comma formatting: 25070 -> 25,070
            if formatted_num in response_str:
                return True
        except ValueError:
            pass
    
    # Handle decimal numbers ending in .0 (e.g., "112218.0" should match "112,218")
    if value_str.endswith('.0') and value_str[:-2].isdigit():
        try:
            # Remove .0 and convert to integer, then try comma formatting
            base_num = int(value_str[:-2])
            formatted_num = f"{base_num:,}".lower()
            if formatted_num in response_str:
                return True
            # Also try without comma formatting
            if str(base_num) in response_str:
                return True
        except ValueError:
            pass
    
    # Handle month number to month name mapping
    month_mapping = {
        '1': ['january', 'jan'], '2': ['february', 'feb'], '3': ['march', 'mar'],
        '4': ['april', 'apr'], '5': ['may'], '6': ['june', 'jun'],
        '7': ['july', 'jul'], '8': ['august', 'aug'], '9': ['september', 'sep'],
        '10': ['october', 'oct'], '11': ['november', 'nov'], '12': ['december', 'dec']
    }
    
    if value_str in month_mapping:
        for month_name in month_mapping[value_str]:
            if month_name in response_str:
                return True
    
    # Handle decimal numbers (e.g., 1234.56 vs 1,234.56)
    if '.' in value_str:
        try:
            parts = value_str.split('.')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                integer_part = int(parts[0])
                decimal_part = parts[1]
                
                # Try formatted with comma and decimal
                formatted = f"{integer_part:,}.{decimal_part}".lower()
                if formatted in response_str:
                    return True
                
                # If decimal part is all zeros (like .0, .00), try just the integer with comma
                if decimal_part.strip('0') == '':
                    integer_formatted = f"{integer_part:,}".lower()
                    if integer_formatted in response_str:
                        return True
                    # Also try without comma
                    if str(integer_part) in response_str:
                        return True
                        
        except (ValueError, IndexError):
            pass
    
    return False


def _normalize_timestamp_value(value: Any) -> Any:
    """
    Normalize timestamp/date values to a canonical format for comparison.
    Handles:
    - Unix timestamps (milliseconds) → datetime
    - ISO 8601 strings → datetime
    - Leaves other values unchanged
    """
    from datetime import datetime
    
    # If it's a number (unix timestamp in milliseconds)
    if isinstance(value, (int, float)) and value > 1000000000000:  # Likely a timestamp in ms
        try:
            return datetime.fromtimestamp(value / 1000.0).isoformat()
        except:
            return value
    
    # If it's an ISO 8601 string, normalize it
    if isinstance(value, str):
        # Check for ISO 8601 format
        if 'T' in value or '-' in value:
            try:
                # Parse and re-format to ensure consistency
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.isoformat()
            except:
                return value
    
    return value


def _normalize_row_for_comparison(row: Any) -> Any:
    """
    Recursively normalize a data row for comparison, handling timestamps/dates.
    """
    if isinstance(row, dict):
        return {k: _normalize_timestamp_value(v) for k, v in row.items()}
    elif isinstance(row, list):
        return [_normalize_row_for_comparison(item) for item in row]
    else:
        return _normalize_timestamp_value(row)


def _extract_values_only(row: Any) -> List[Any]:
    """
    Extract only the values from a row, ignoring column names.
    Handles nested structures and normalizes numeric values.
    """
    if isinstance(row, dict):
        values = []
        for v in row.values():
            values.extend(_extract_values_only(v))
        return values
    elif isinstance(row, list):
        values = []
        for item in row:
            values.extend(_extract_values_only(item))
        return values
    else:
        return [row]


def _normalize_numeric_value(value: Any) -> Any:
    """
    Normalize numeric values for comparison:
    - Convert "0.0" to 0
    - Handle float/int equivalence (5.0 == 5)
    """
    if value is None:
        return None
    
    # Handle string representations of numbers
    if isinstance(value, str):
        try:
            # Try to parse as float first
            float_val = float(value)
            # If it's a whole number, return as int
            if float_val == int(float_val):
                return int(float_val)
            return float_val
        except (ValueError, TypeError):
            return value
    
    # Handle numeric types
    if isinstance(value, float):
        if value == int(value):
            return int(value)
        return value
    
    return value


def _is_empty_or_zero_result(data: List[Any]) -> bool:
    """
    Check if a result set represents an empty or zero result.
    Returns True if:
    - Empty list
    - Single row with all zero/null values
    - Single row with a count of 0
    """
    if not data:
        return True
    
    if len(data) == 1 and isinstance(data[0], dict):
        row = data[0]
        # Check if all values are zero, null, or empty
        for value in row.values():
            normalized = _normalize_numeric_value(value)
            if normalized not in (0, None, '', 'null', 'None', 0.0):
                return False
        return True
    
    return False


def _values_match(agent_values: List[Any], ref_values: List[Any]) -> Tuple[bool, float, str]:
    """
    Compare two lists of values, ignoring column names.
    Returns (is_match, match_ratio, explanation).
    """
    if not agent_values and not ref_values:
        return True, 1.0, "Both empty"
    
    if not agent_values or not ref_values:
        return False, 0.0, "One side empty"
    
    # Normalize all values
    agent_normalized = sorted([_normalize_numeric_value(v) for v in agent_values], key=lambda x: str(x))
    ref_normalized = sorted([_normalize_numeric_value(v) for v in ref_values], key=lambda x: str(x))
    
    # Check for exact match
    if agent_normalized == ref_normalized:
        return True, 1.0, "Values match exactly"
    
    # Calculate overlap ratio
    agent_set = set(str(v) for v in agent_normalized if v is not None)
    ref_set = set(str(v) for v in ref_normalized if v is not None)
    
    if not ref_set:
        return True, 1.0, "Reference has no non-null values"
    
    overlap = agent_set & ref_set
    match_ratio = len(overlap) / len(ref_set)
    
    return match_ratio >= 0.8, match_ratio, f"Value overlap: {len(overlap)}/{len(ref_set)}"


def calculate_sql_result_exact_match(
    session_state: Dict[str, Any],
    reference_data: Dict[str, Any],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Calculate deterministic SQL result match: checks if the agent's SQL execution results
    match the reference SQL execution results.
    
    This metric uses a flexible comparison approach:
    1. First tries exact match (including column names)
    2. Falls back to value-only comparison (ignores column names)
    3. Treats both-empty/both-zero results as a match
    
    Normalizes:
    - Timestamp/date formats
    - Numeric values (5.0 == 5)
    - Column name differences (value-only mode)
    
    Args:
        session_state: The session state dictionary containing agent outputs
        reference_data: Dictionary containing reference data including reference SQL results
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 if results match, 0.0 otherwise
    """
    state = session_state.get('state', {})
    
    if question_metadata and question_metadata.get('tier') == 'negative':
        return 1.0, "SQL result exact match not applicable for negative test cases."

    # Get agent's SQL execution result
    agent_sql_result = state.get('sql_explorer:sql_execution_result')
    # Note: Empty string "" is a valid result (means query returned no rows)
    # Only fail if the key is completely missing (None)
    if agent_sql_result is None:
        return 0.0, "SQL result exact match failed: No agent SQL execution result found"
    
    # Get reference SQL execution result
    reference_sql_result = reference_data.get('sql_explorer:reference_bq_raw_response') if reference_data else None
    if reference_sql_result is None:
        return 0.0, "SQL result exact match failed: No reference SQL execution result found"
    
    try:
        # Parse both results as JSON, treating empty strings as empty lists
        def parse_result(result):
            """Parse a result, treating empty string as empty list."""
            if result == "" or result == "[]":
                return []
            if isinstance(result, str):
                return json.loads(result)
            return result
        
        agent_data = parse_result(agent_sql_result)
        reference_data_parsed = parse_result(reference_sql_result)
        
        # Normalize both to lists for comparison
        if not isinstance(agent_data, list):
            agent_data = [agent_data] if agent_data is not None else []
        if not isinstance(reference_data_parsed, list):
            reference_data_parsed = [reference_data_parsed] if reference_data_parsed is not None else []
        
        # Normalize timestamps/dates in both datasets
        agent_data = [_normalize_row_for_comparison(row) for row in agent_data]
        reference_data_parsed = [_normalize_row_for_comparison(row) for row in reference_data_parsed]
        
        # === IMPROVEMENT 1: Both empty/zero results should match ===
        # If both agent and reference return empty/zero results, that's a valid match
        # (The SQL correctly returned no data, which matches the reference)
        agent_is_empty_or_zero = _is_empty_or_zero_result(agent_data)
        ref_is_empty_or_zero = _is_empty_or_zero_result(reference_data_parsed)
        
        if agent_is_empty_or_zero and ref_is_empty_or_zero:
            return 1.0, "SQL result match SUCCESS: Both queries returned empty or zero results"
        
        # Handle LIMIT differences: if row counts differ due to LIMIT, compare only up to the smaller count
        agent_count = len(agent_data)
        ref_count = len(reference_data_parsed)
        
        if agent_count != ref_count:
            min_count = min(agent_count, ref_count)
            if min_count == 0:
                # One is empty, other is not - this is a mismatch
                return 0.0, f"SQL result match FAILED: Row count mismatch - Agent: {agent_count}, Reference: {ref_count}"
            
            # Truncate both to the minimum count
            agent_data = agent_data[:min_count]
            reference_data_parsed = reference_data_parsed[:min_count]
            limit_note = f" (compared first {min_count} rows due to LIMIT differences: Agent={agent_count}, Ref={ref_count})"
        else:
            limit_note = ""
        
        # === TRY 1: Exact match (with column names) ===
        def sort_key(item):
            return json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
        
        agent_sorted = sorted(agent_data, key=sort_key)
        reference_sorted = sorted(reference_data_parsed, key=sort_key)
        
        if agent_sorted == reference_sorted:
            return 1.0, f"SQL result exact match SUCCESS: Both queries returned identical data ({len(agent_data)} rows){limit_note}"
        
        # === TRY 2: Value-only comparison (ignore column names) ===
        # Extract all values from both result sets
        agent_all_values = []
        for row in agent_data:
            agent_all_values.extend(_extract_values_only(row))
        
        ref_all_values = []
        for row in reference_data_parsed:
            ref_all_values.extend(_extract_values_only(row))
        
        values_match, match_ratio, match_explanation = _values_match(agent_all_values, ref_all_values)
        
        if values_match:
            return 1.0, f"SQL result match SUCCESS (value-only): Core values match despite column name differences ({match_ratio:.0%} overlap){limit_note}. {match_explanation}"
        
        # === IMPROVEMENT 3: Check if primary/aggregate values match ===
        # For single-row results with aggregate values, check if the main numeric values match
        if len(agent_data) == 1 and len(reference_data_parsed) == 1:
            agent_row = agent_data[0]
            ref_row = reference_data_parsed[0]
            
            if isinstance(agent_row, dict) and isinstance(ref_row, dict):
                # Extract numeric values from both
                agent_nums = [_normalize_numeric_value(v) for v in agent_row.values() 
                             if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.','',1).replace('-','',1).isdigit())]
                ref_nums = [_normalize_numeric_value(v) for v in ref_row.values() 
                           if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.','',1).replace('-','',1).isdigit())]
                
                if agent_nums and ref_nums:
                    # Check if the primary numeric values match
                    agent_nums_sorted = sorted(agent_nums, key=lambda x: str(x))
                    ref_nums_sorted = sorted(ref_nums, key=lambda x: str(x))
                    
                    if agent_nums_sorted == ref_nums_sorted:
                        return 1.0, f"SQL result match SUCCESS (numeric values): Primary numeric values match exactly{limit_note}"
                    
                    # Check if at least the key aggregate values match (first value in each)
                    if agent_nums_sorted and ref_nums_sorted and agent_nums_sorted[0] == ref_nums_sorted[0]:
                        return 1.0, f"SQL result match SUCCESS (primary value): Primary aggregate value matches{limit_note}"
        
        # Find differences for debugging
        mismatches = []
        for i, (agent_row, ref_row) in enumerate(zip(agent_sorted, reference_sorted)):
            if agent_row != ref_row:
                mismatches.append(f"Row {i}: Agent={agent_row}, Reference={ref_row}")
        
        explanation = f"SQL result match FAILED: Data differences found (value overlap: {match_ratio:.0%}){limit_note}. First few mismatches: {'; '.join(mismatches[:3])}"
        return 0.0, explanation
            
    except json.JSONDecodeError as e:
        return 0.0, f"SQL result exact match failed: JSON parsing error - {str(e)}"
    except Exception as e:
        return 0.0, f"SQL result exact match failed: Error comparing results - {str(e)}"


def calculate_nl_sql_output_groundedness(
    session_state: Dict[str, Any],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any],
    accuracy_threshold: float = 0.8
) -> Tuple[float, str]:
    """
    Calculate NL-to-SQL-output groundedness: checks if the agent's natural language response 
    contains key information from the agent's own SQL execution results.
    
    This metric completes the chain: SQL output → NL response (ensures NL is grounded in actual data).
    Different from deterministic_accuracy which compares NL to reference SQL.
    
    Args:
        session_state: The session state dictionary containing agent outputs
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        accuracy_threshold: Minimum proportion of key values that must be found (default 0.8)
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 if NL is grounded in SQL output, 0.0 otherwise
    """
    state = session_state.get('state', {})
    
    if question_metadata and question_metadata.get('tier') == 'negative':
        return 1.0, "NL SQL output groundedness not applicable for negative test cases."
    
    # Get agent's SQL execution result (not reference)
    agent_sql_result = state.get('sql_explorer:sql_execution_result')
    if not agent_sql_result:
        return 0.0, "NL SQL output groundedness failed: No agent SQL execution result found"
    
    # Get the agent's final natural language response
    agent_response = state.get('nl_final_response_text')
    if not agent_response or not isinstance(agent_response, str) or agent_response.strip() == '':
        return 0.0, "NL SQL output groundedness failed: No final response generated by agent"
    
    try:
        # Parse the agent's SQL execution results
        if isinstance(agent_sql_result, str):
            agent_data = json.loads(agent_sql_result)
        else:
            agent_data = agent_sql_result
            
        if not agent_data or not isinstance(agent_data, list):
            return 0.0, "NL SQL output groundedness failed: Invalid agent SQL execution result format"
        
        # Extract key information from the agent's SQL results
        key_values = []
        for row in agent_data:
            if isinstance(row, dict):
                # Extract all values from each row, focusing on string/numeric data
                for key, value in row.items():
                    if value is not None:
                        # Convert to string and clean up
                        str_value = str(value).strip()
                        if str_value and str_value.lower() not in ['null', 'none', '']:
                            key_values.append(str_value)
        
        if not key_values:
            return 0.0, "NL SQL output groundedness failed: No key values extracted from agent SQL results"
        
        # Clean agent response for comparison
        agent_response_clean = agent_response.strip().lower()
        
        # Check how many key values from SQL output are found in agent's NL response
        found_values = []
        for value in key_values:
            value_clean = str(value).strip().lower()
            if _is_value_found_in_response(value_clean, agent_response_clean):
                found_values.append(value)
        
        # Calculate accuracy based on proportion of key values found
        accuracy_ratio = len(found_values) / len(key_values) if key_values else 0
        
        # Adaptive threshold: Lower threshold for large result sets
        # For >100 values, use 50% threshold instead of 80% (NL can't include all values)
        effective_threshold = accuracy_threshold
        if len(key_values) > 100:
            effective_threshold = max(0.5, accuracy_threshold * 0.625)  # 80% * 0.625 = 50%
        
        # Use adaptive threshold
        if accuracy_ratio >= effective_threshold:
            score = 1.0
            threshold_note = f"{effective_threshold:.0%}" if effective_threshold != accuracy_threshold else f"{accuracy_threshold:.0%}"
            explanation = f"NL SQL output groundedness SUCCESS: {len(found_values)}/{len(key_values)} key values from SQL output found in NL response (need >= {threshold_note}). NL response is grounded in actual SQL data."
        else:
            score = 0.0
            threshold_note = f"{effective_threshold:.0%}" if effective_threshold != accuracy_threshold else f"{accuracy_threshold:.0%}"
            explanation = f"NL SQL output groundedness FAILED: Only {len(found_values)}/{len(key_values)} key values from SQL output found in NL response (need >= {threshold_note}). NL response may contain fabricated or missing data."
        
        return score, explanation
        
    except json.JSONDecodeError:
        return 0.0, "NL SQL output groundedness failed: Could not parse agent SQL execution results as JSON"
    except Exception as e:
        return 0.0, f"NL SQL output groundedness failed: Error processing agent SQL data: {str(e)}"


def calculate_deterministic_accuracy(
    session_state: Dict[str, Any],
    reference_data: Dict[str, Any],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Calculate deterministic accuracy: Composite metric combining SQL correctness and NL groundedness.
    
    This is the primary executive metric that answers: "Is the agent working correctly?"
    
    Components:
    1. SQL Result Exact Match: Does agent SQL get the RIGHT data? (vs reference)
    2. NL SQL Output Groundedness: Does NL response match SQL output? (internal consistency)
    
    Both must pass for overall success (1.0), otherwise 0.0.
    Sub-scores are preserved in explanation for debugging.
    
    Args:
        session_state: The session state dictionary containing agent outputs
        reference_data: Dictionary containing reference data including reference SQL results
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        
    Returns:
        Tuple of (score, explanation) where:
        - score: 1.0 if both SQL match AND NL groundedness pass, 0.0 otherwise
        - explanation: Combined explanation with sub-scores for debugging
    """
    # Component 1: SQL Result Exact Match (correctness)
    sql_score, sql_explanation = calculate_sql_result_exact_match(
        session_state, reference_data, agents_evaluated, question_metadata
    )
    
    # Component 2: NL SQL Output Groundedness (consistency)
    grounded_score, grounded_explanation = calculate_nl_sql_output_groundedness(
        session_state, agents_evaluated, question_metadata, accuracy_threshold=0.8
    )
    
    # Both must pass for overall success
    overall_score = 1.0 if (sql_score == 1.0 and grounded_score >= 0.8) else 0.0
    
    # Build composite explanation
    sql_status = "✓" if sql_score == 1.0 else "✗"
    grounded_status = "✓" if grounded_score >= 0.8 else "✗"
    
    explanation = (
        f"Deterministic accuracy: {overall_score:.0f} "
        f"(SQL correctness {sql_status}, NL groundedness {grounded_status}). "
        f"SQL: {sql_explanation[:100]}{'...' if len(sql_explanation) > 100 else ''}. "
        f"NL: {grounded_explanation[:100]}{'...' if len(grounded_explanation) > 100 else ''}."
    )
    
    return overall_score, explanation


def check_trace_for_errors(session_trace: List[Dict[str, Any]]) -> List[str]:
    """
    Check the session trace for error indicators in spans.
    
    Args:
        session_trace: List of trace spans
        
    Returns:
        List of error messages found in the trace
    """
    errors = []
    
    for span in session_trace:
        attributes = span.get('attributes', {})
        
        # Check for BigQuery errors
        if span.get('name', '').startswith('BigQuery'):
            has_errors = attributes.get('hasErrors')
            if has_errors is True:
                errors.append(f"BigQuery error detected in span: {span.get('name')}")
        
        # Check for general error status in span
        status = span.get('status', {})
        if isinstance(status, dict):
            status_code = status.get('status_code') or status.get('code')
            if status_code == 'ERROR' or status_code == 2:  # ERROR enum value
                description = status.get('description', 'Unknown error')
                errors.append(f"Error in span {span.get('name')}: {description}")
    
    return errors


def calculate_sql_execution_success(
    session_state: Dict[str, Any],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Binary metric: Did the SQL query execute successfully in BigQuery?
    
    Args:
        session_state: The session state dictionary
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 for success, 0.0 for failure
    """
    if 'sql_explorer' not in agents_evaluated:
        return 1.0, "SQL explorer agent not evaluated"
    
    if question_metadata and question_metadata.get('tier') == 'negative':
        state = session_state.get('state', {})
        sql_status = state.get('sql_explorer:status')
        if sql_status == 'success':
            return 0.0, "SQL execution FAILED: Query was executed for a negative test case."
        else:
            return 1.0, "SQL execution SUCCESS: Agent correctly avoided executing a query for a negative test case."

    state = session_state.get('state', {})
    sql_status = state.get('sql_explorer:status')
    bq_result = state.get('sql_explorer:sql_execution_result')
    
    if sql_status == 'success' and bq_result is not None:
        return 1.0, "SQL execution successful: Query executed and returned results"
    else:
        reason = f"status={sql_status}, result={'present' if bq_result else 'missing'}"
        return 0.0, f"SQL execution failed: {reason}"


def calculate_rag_retrieval_success(
    session_state: Dict[str, Any],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Binary metric: Did RAG retrieval return at least one relevant table?
    
    Args:
        session_state: The session state dictionary
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 for success, 0.0 for failure
    """
    if 'sql_explorer' not in agents_evaluated:
        return 1.0, "SQL explorer agent not evaluated"

    if question_metadata and question_metadata.get('tier') == 'negative':
        state = session_state.get('state', {})
        rag_tables = state.get('sql_explorer:rag_relevant_tables', [])
        if rag_tables:
            return 0.0, "RAG retrieval FAILED: RAG was triggered for a negative test case."
        else:
            return 1.0, "RAG retrieval SUCCESS: Agent correctly avoided RAG for a negative test case."

    state = session_state.get('state', {})
    rag_tables = state.get('sql_explorer:rag_relevant_tables', [])
    
    if isinstance(rag_tables, list) and len(rag_tables) > 0:
        return 1.0, f"RAG retrieval successful: Retrieved {len(rag_tables)} relevant table(s)"
    else:
        return 0.0, "RAG retrieval failed: No relevant tables retrieved"


def calculate_sql_generation_success(
    session_state: Dict[str, Any],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Binary metric: Was a SQL query successfully generated?
    
    Args:
        session_state: The session state dictionary
        agents_evaluated: List of agents that should have been evaluated
        question_metadata: Metadata about the question being evaluated.
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 for success, 0.0 for failure
    """
    if 'sql_explorer' not in agents_evaluated:
        return 1.0, "SQL explorer agent not evaluated"

    if question_metadata and question_metadata.get('tier') == 'negative':
        state = session_state.get('state', {})
        generated_sql = state.get('sql_explorer:generated_sql')
        if generated_sql:
            return 0.0, "SQL generation FAILED: SQL was generated for a negative test case."
        else:
            return 1.0, "SQL generation SUCCESS: Agent correctly refused to generate SQL for a negative test case."

    state = session_state.get('state', {})
    generated_sql = state.get('sql_explorer:generated_sql')
    
    if generated_sql and isinstance(generated_sql, str) and generated_sql.strip():
        return 1.0, "SQL generation successful: Valid SQL query generated"
    else:
        return 0.0, "SQL generation failed: No valid SQL query generated"


def calculate_response_generation_success(
    session_state: Dict[str, Any]
) -> Tuple[float, str]:
    """
    Binary metric: Was a final natural language response generated?
    
    Args:
        session_state: The session state dictionary
        
    Returns:
        Tuple of (score, explanation) where score is 1.0 for success, 0.0 for failure
    """
    state = session_state.get('state', {})
    final_response = state.get('nl_final_response_text')
    
    if final_response and isinstance(final_response, str) and final_response.strip():
        return 1.0, "Response generation successful: Natural language response generated"
    else:
        return 0.0, "Response generation failed: No final response generated"


def calculate_token_usage(
    session_trace: List[Dict[str, Any]]
) -> Tuple[float, str, Dict[str, Any]]:
    """
    Informational metric: Track token usage and estimated cost.
    
    Args:
        session_trace: The trace spans from the session
        
    Returns:
        Tuple of (total_cost, explanation, details_dict) where details includes token counts and cost breakdown
    """
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    llm_calls = 0
    
    # Pricing per 1K tokens (example rates - adjust as needed)
    PROMPT_PRICE_PER_1K = 0.00025  # $0.00025 per 1K prompt tokens
    COMPLETION_PRICE_PER_1K = 0.0005  # $0.0005 per 1K completion tokens
    
    for span in session_trace:
        attributes = span.get('attributes', {})
        
        # Check for LLM response with usage metadata
        llm_response = attributes.get('gcp.vertex.agent.llm_response')
        if llm_response:
            try:
                response_data = json.loads(llm_response) if isinstance(llm_response, str) else llm_response
                usage = response_data.get('usage_metadata', {})
                
                if usage:
                    llm_calls += 1
                    prompt_tokens = usage.get('prompt_token_count', 0)
                    completion_tokens = usage.get('candidates_token_count', 0)
                    total_span_tokens = usage.get('total_token_count', 0)
                    
                    total_prompt_tokens += prompt_tokens
                    total_completion_tokens += completion_tokens
                    total_tokens += total_span_tokens
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
    
    # Calculate cost
    prompt_cost = (total_prompt_tokens / 1000) * PROMPT_PRICE_PER_1K
    completion_cost = (total_completion_tokens / 1000) * COMPLETION_PRICE_PER_1K
    total_cost = prompt_cost + completion_cost
    
    explanation = (
        f"Token usage tracked: {llm_calls} LLM calls, "
        f"{total_tokens} total tokens "
        f"({total_prompt_tokens} prompt + {total_completion_tokens} completion), "
        f"estimated cost: ${total_cost:.6f}"
    )
    
    details = {
        'llm_calls': llm_calls,
        'total_tokens': total_tokens,
        'prompt_tokens': total_prompt_tokens,
        'completion_tokens': total_completion_tokens,
        'estimated_cost_usd': total_cost,
        'prompt_cost_usd': prompt_cost,
        'completion_cost_usd': completion_cost
    }
    
    return total_cost, explanation, details


# Registry of all deterministic metrics
DETERMINISTIC_METRICS = {
    'end_to_end_success': calculate_end_to_end_success,
    'sql_execution_success': calculate_sql_execution_success,
    'rag_retrieval_success': calculate_rag_retrieval_success,
    'sql_generation_success': calculate_sql_generation_success,
    'response_generation_success': calculate_response_generation_success,
    'deterministic_accuracy': calculate_deterministic_accuracy,  # Composite: SQL match + NL groundedness
    'nl_sql_output_groundedness': calculate_nl_sql_output_groundedness,  # Component metric (for debugging)
    'sql_result_exact_match': calculate_sql_result_exact_match,  # Component metric (for debugging)
    'token_usage': calculate_token_usage,
}


def evaluate_deterministic_metrics(
    session_state: Dict[str, Any],
    session_trace: List[Dict[str, Any]],
    agents_evaluated: List[str],
    question_metadata: Dict[str, Any],
    metrics_to_run: List[str] = None,
    reference_data: Dict[str, Any] = None,
    metric_definitions: Dict[str, Any] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Evaluate all specified deterministic metrics.
    
    Args:
        session_state: The session state dictionary
        session_trace: The trace spans from the session
        agents_evaluated: List of agents that were evaluated
        question_metadata: Metadata about the question being evaluated.
        metrics_to_run: Optional list of specific metrics to run. If None, runs all.
        reference_data: Optional dictionary containing reference data (needed for deterministic_accuracy)
        metric_definitions: Optional dictionary containing metric definitions with thresholds
        
    Returns:
        Dictionary mapping metric names to their results:
        {
            'metric_name': {
                'score': 0.0 or 1.0,
                'explanation': 'detailed explanation',
                'details': {...}  # optional additional data
            }
        }
    """
    if metrics_to_run is None:
        metrics_to_run = list(DETERMINISTIC_METRICS.keys())
    
    results = {}
    for metric_name in metrics_to_run:
        if metric_name not in DETERMINISTIC_METRICS:
            continue
        
        metric_func = DETERMINISTIC_METRICS[metric_name]
        
        try:
            # Check function signature to pass correct args
            if metric_name == 'response_generation_success':
                score, explanation = metric_func(session_state)
                results[metric_name] = {
                    'score': score,
                    'explanation': explanation
                }
            elif metric_name == 'deterministic_accuracy':
                # Composite metric: SQL correctness + NL groundedness
                # Requires full reference_data dict (not just BQ response)
                if reference_data:
                    score, explanation = calculate_deterministic_accuracy(
                        session_state, reference_data, agents_evaluated, question_metadata
                    )
                    results[metric_name] = {
                        'score': score,
                        'explanation': explanation
                    }
                else:
                    results[metric_name] = {
                        'score': 0.0,
                        'explanation': 'Deterministic accuracy skipped: No reference data provided'
                    }
            elif metric_name == 'nl_sql_output_groundedness':
                # Get accuracy threshold from metric definitions, default to 0.8
                accuracy_threshold = 0.8  # default
                if metric_definitions and metric_name in metric_definitions:
                    accuracy_threshold = metric_definitions[metric_name].get('accuracy_threshold', 0.8)
                
                score, explanation = calculate_nl_sql_output_groundedness(
                    session_state, agents_evaluated, question_metadata, accuracy_threshold
                )
                results[metric_name] = {
                    'score': score,
                    'explanation': explanation
                }
            elif metric_name == 'sql_result_exact_match':
                # This metric needs the full reference_data dict, not just the BQ response
                if reference_data:
                    score, explanation = metric_func(session_state, reference_data, agents_evaluated, question_metadata)
                    results[metric_name] = {
                        'score': score,
                        'explanation': explanation
                    }
                else:
                    results[metric_name] = {
                        'score': 0.0,
                        'explanation': 'SQL result exact match skipped: No reference data provided'
                    }
            elif metric_name == 'token_usage':
                total_cost, explanation, details = metric_func(session_trace)
                results[metric_name] = {
                    'score': total_cost,  # Cost as the score
                    'explanation': explanation,
                    'details': details
                }
            elif metric_name == 'end_to_end_success':
                score, explanation = metric_func(session_state, session_trace, agents_evaluated, question_metadata)
                results[metric_name] = {
                    'score': score,
                    'explanation': explanation
                }
            else:
                # Default case for most metrics: session_state, agents_evaluated
                score, explanation = metric_func(session_state, agents_evaluated, question_metadata)
                results[metric_name] = {
                    'score': score,
                    'explanation': explanation
                }
        except Exception as e:
            results[metric_name] = {
                'score': 0.0,
                'explanation': f"Error evaluating metric: {str(e)}"
            }
    
    return results

