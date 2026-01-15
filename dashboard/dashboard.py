import gradio as gr
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple, Union

# --- Configuration ---

DEFAULT_METRICS_CONFIG = {
    "general_conversation_quality.average": "Quality",
    "safety.average": "Safety",
    "token_usage.prompt_tokens": "Prompt Tokens",
    "tool_success_rate.tool_success_rate": "Tool Success",
    "latency_metrics.total_latency_seconds": "Latency"
}

METRIC_DIRECTIONS = {
    "general_conversation_quality.average": "higher",
    "safety.average": "higher",
    "token_usage.prompt_tokens": "lower",
    "tool_success_rate.tool_success_rate": "higher",
    "latency_metrics.total_latency_seconds": "lower"
}

# --- Data Processing Functions ---

def flatten_json(nested_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively flattens a nested dictionary.
    Keys are joined by dots (e.g., 'level1.level2.key').
    """
    out = {}

    def flatten(x: Any, name: str = ''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            # We generally skip lists in this simple flattener unless they are simple numeric lists
            pass
        else:
            out[name[:-1]] = x

    flatten(nested_dict)
    return out

def parse_metric_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Parses a single JSON file to extract all relevant metrics using recursive flattening.
    Returns a dictionary of metrics or None if parsing fails.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    # Extract core metadata
    experiment_id = data.get("experiment_id", os.path.basename(file_path))
    interaction_datetime = data.get("interaction_datetime")

    if not interaction_datetime:
        return None

    try:
        dt_obj = datetime.fromisoformat(interaction_datetime)
    except ValueError:
        return None

    # Flatten the entire JSON structure
    flat_data = flatten_json(data)

    # Initialize with metadata
    metrics = {
        "experiment_id": experiment_id,
        "datetime": dt_obj
    }

    # Add all numeric values found in the flattened structure
    for key, value in flat_data.items():
        # Exclude metadata we already handled
        if key in ["experiment_id", "interaction_datetime"]:
            continue
            
        # Clean up the key names to be more readable
        # Remove common high-level nesting keys to restore concise titles
        short_key = key.replace("overall_summary.deterministic_metrics.", "")
        short_key = short_key.replace("overall_summary.llm_based_metrics.", "")
        short_key = short_key.replace("overall_summary.", "")
            
        if isinstance(value, (int, float)):
            metrics[short_key] = value
        # Handle string numbers (e.g., "123.45") if necessary, though good JSON logs should be typed.
        elif isinstance(value, str):
            try:
                metrics[short_key] = float(value)
            except ValueError:
                pass

    return metrics

def load_data_from_directory(directory: str) -> Tuple[pd.DataFrame, int]:
    """
    Loads all JSON files from a directory, parses them, and returns a DataFrame
    along with the number of files that were skipped due to errors.
    """
    if not os.path.isdir(directory):
        return pd.DataFrame(), 0

    all_files = [f for f in os.listdir(directory) if f.endswith(".json")]
    
    all_metrics = [
        parse_metric_from_file(os.path.join(directory, filename))
        for filename in all_files
    ]
    
    valid_metrics = [m for m in all_metrics if m is not None]
    skipped_files = len(all_files) - len(valid_metrics)

    if not valid_metrics:
        return pd.DataFrame(), skipped_files

    df = pd.DataFrame(valid_metrics)
    df = df.sort_values(by="datetime").reset_index(drop=True)
    return df, skipped_files

# --- Visualization Helper Functions ---

def _get_color(experiment_id: str, baseline_id: str) -> str:
    """Returns the color for a given experiment (Gray for baseline, Blue for others)."""
    return '#5F6368' if experiment_id == baseline_id else '#1A73E8'

def _calculate_max_values(df: pd.DataFrame, metrics: List[str]) -> Dict[str, float]:
    """Calculates max values for normalization, preventing division by zero."""
    max_values = {}
    for metric in metrics:
        max_val = df[metric].max()
        max_values[metric] = max_val if max_val and max_val > 0 else 1.0
    return max_values

def _generate_scorecard_html(df: pd.DataFrame, baseline_id: str, candidate_ids: List[str]) -> str:
    """Generates the HTML for the Delta Metrics Scorecards."""
    delta_metrics = [m for m in DEFAULT_METRICS_CONFIG.keys() if m in df.columns]
    
    if df.empty or not baseline_id or not candidate_ids or not delta_metrics:
        return ""

    baseline_rows = df[df['experiment_id'] == baseline_id]
    if baseline_rows.empty:
        return ""
        
    baseline_row = baseline_rows.iloc[0]
    
    # Find the latest candidate run based on datetime
    candidate_rows = df[df['experiment_id'].isin(candidate_ids)].sort_values(by='datetime', ascending=False)
    
    if candidate_rows.empty:
        return ""

    latest_cand_row = candidate_rows.iloc[0]
    cards_html = ""
    
    for metric in delta_metrics:
        display_name = DEFAULT_METRICS_CONFIG.get(metric, metric)
        direction = METRIC_DIRECTIONS.get(metric, "higher")
        b_val = baseline_row.get(metric, 0)
        c_val = latest_cand_row.get(metric, 0)
        
        if b_val == 0:
            pct_change = 0
            delta_str = "N/A"
            color = "#5F6368" # Neutral
        else:
            pct_change = ((c_val - b_val) / b_val) * 100
            delta_str = f"{pct_change:+.1f}%"
            
            # Determine color based on direction
            if pct_change == 0:
                color = "#5F6368"
            elif (direction == "higher" and pct_change > 0) or (direction == "lower" and pct_change < 0):
                color = "#188038" # Green (Good)
            else:
                color = "#D93025" # Red (Bad)

        cards_html += f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; flex: 1; min-width: 200px; background: white; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);">
            <div style="font-size: 12px; color: #5f6368; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">{display_name}</div>
            <div style="font-size: 24px; color: {color}; margin: 8px 0; font-weight: bold;">{delta_str}</div>
            <div style="font-size: 12px; color: #70757a;">vs Baseline</div>
        </div>
        """
    
    if not cards_html:
        return ""
        
    return f"<div style='display: flex; flex-wrap: wrap; gap: 16px; width: 100%; margin-bottom: 20px;'>{cards_html}</div>"

# --- Gradio Controller Functions ---

def update_file_and_metric_lists(directory_input: str) -> Tuple[gr.update, gr.update, gr.update, gr.update, pd.DataFrame]:
    """
    Loads data from the specified directory or directories, updates UI selectors,
    and returns messages and the loaded DataFrame.
    """
    if not directory_input:
         error_message = "### <span style='color:red'>Error: Please provide at least one directory path.</span>"
         return gr.update(visible=True, value=error_message), gr.update(choices=[], value=None), gr.update(choices=[], value=[]), gr.update(choices=[], value=[]), pd.DataFrame()

    # Split input by comma or newline to support multiple directories
    raw_directories = [d.strip() for d in directory_input.replace('\n', ',').split(',') if d.strip()]
    
    all_dfs = []
    total_skipped_files = 0
    loaded_directories = []
    
    for directory in raw_directories:
        directory = directory.strip().strip('"').strip("'")
        directory = os.path.expanduser(directory)
        
        # Fallback: If path doesn't exist, try relative to home
        if not os.path.exists(directory):
             home_path = os.path.join(os.path.expanduser("~"), directory)
             if os.path.exists(home_path):
                 directory = home_path

        # If the user provided a full file path, use its parent directory
        if directory and os.path.isfile(directory):
            directory = os.path.dirname(directory)

        if directory and os.path.isdir(directory):
            df, skipped = load_data_from_directory(directory)
            if not df.empty:
                all_dfs.append(df)
                loaded_directories.append(directory)
            total_skipped_files += skipped

    if not all_dfs:
        error_message = "### <span style='color:red'>Error: No valid directories with JSON logs found.</span>"
        return gr.update(visible=True, value=error_message), gr.update(choices=[], value=None), gr.update(choices=[], value=[]), gr.update(choices=[], value=[]), pd.DataFrame()
    
    # Combine all dataframes
    final_df = pd.concat(all_dfs, ignore_index=True)
    # Deduplicate based on experiment_id to avoid duplicates if directories overlap or are repeated
    final_df = final_df.drop_duplicates(subset=['experiment_id'])
    final_df = final_df.sort_values(by="datetime").reset_index(drop=True)
    
    message = ""
    if total_skipped_files > 0:
        message += f"### <span style='color:orange'>Warning: Skipped {total_skipped_files} corrupt or malformed JSON file(s).</span>\n"

    files = final_df["experiment_id"].tolist()
    # Filter columns to only those that are likely metrics (numeric) and not metadata
    metrics = [col for col in final_df.columns if col not in ['experiment_id', 'datetime']]
    metrics.sort()
    
    message += f"### <span style='color:green'>Success: Loaded {len(final_df)} experiment(s) from {len(loaded_directories)} directory(ies).</span>"
    # For multiselect Dropdown, the value should be an empty list []
    return gr.update(visible=True, value=message), gr.update(choices=files, value=None), gr.update(choices=files, value=[]), gr.update(choices=metrics, value=[]), final_df

def generate_bar_chart(df: pd.DataFrame, baseline_id: str, candidate_ids: List[str], selected_metrics: List[str], normalize: bool) -> go.Figure:
    """
    Generates a grouped bar chart to compare metrics.
    """
    if df.empty or not baseline_id or not selected_metrics:
        fig = go.Figure()
        fig.update_layout(
            title="Please select a baseline, metrics, and optionally candidates to generate plots.",
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[{
                "text": "No Data Selected",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 20}
            }]
        )
        return fig

    selected_exp_ids = [baseline_id]
    if candidate_ids:
        selected_exp_ids.extend(candidate_ids)

    filtered_df = df[df['experiment_id'].isin(selected_exp_ids)]
    
    # Split into baseline and candidates to ensure baseline is always first
    baseline_data = filtered_df[filtered_df['experiment_id'] == baseline_id]
    candidates_data = filtered_df[filtered_df['experiment_id'] != baseline_id]
    
    # Sort candidates by datetime, then concatenate with baseline at the front
    sorted_filtered_df = pd.concat([baseline_data, candidates_data.sort_values('datetime')])

    # Calculate max values for normalization
    max_metric_values = _calculate_max_values(sorted_filtered_df, selected_metrics) if normalize else {}

    fig = go.Figure()

    for index, row in sorted_filtered_df.iterrows():
        exp_id = row['experiment_id']
        
        # Prepare data for this experiment
        original_values = [row.get(metric, 0) for metric in selected_metrics]
        if normalize:
            y_values = []
            for val, metric in zip(original_values, selected_metrics):
                max_val = max_metric_values.get(metric, 1.0)
                y_values.append(val / max_val if max_val != 0 else 0)
            hovertemplate = "<b>%{x}</b><br>Normalized: %{y:.2f}<br>Original: %{text}<extra></extra>"
        else:
            y_values = original_values
            hovertemplate = "<b>%{x}</b><br>Value: %{y}<extra></extra>"
        
        # Color logic: Red for baseline, Blue for candidates
        color = _get_color(exp_id, baseline_id)
        
        fig.add_trace(go.Bar(
            name=exp_id,
            x=selected_metrics,
            y=y_values,
            marker_color=color,
            text=[f"{v:.2f}" if isinstance(v, float) else v for v in original_values],
            textposition='auto',
            hovertemplate=hovertemplate
        ))

    fig.update_layout(
        barmode='group',
        title_text="Metric Comparison (Normalized)" if normalize else "Metric Comparison (Absolute)",
        xaxis_title="Metrics",
        yaxis_title="Normalized Score (0-1)" if normalize else "Value",
        template="plotly_white",
        margin=dict(l=50, r=50, t=80, b=100),
        height=600
    )

    return fig

def generate_dashboard_view(df: pd.DataFrame, baseline_id: str, candidate_ids: List[str], pinned_metrics: List[str], normalize: bool):
    """
    Generates the bar chart and raw data table.
    """
    # Generate charts using pinned metrics
    bar_fig = generate_bar_chart(df, baseline_id, candidate_ids, pinned_metrics, normalize)
    
    # Generate raw data table with ALL metrics for the selected experiments
    if df.empty or not baseline_id:
        table_df = pd.DataFrame()
    else:
        selected_exp_ids = [baseline_id]
        if candidate_ids:
            selected_exp_ids.extend(candidate_ids)
        
        table_df = df[df['experiment_id'].isin(selected_exp_ids)]
        
        # Ensure readable column order
        cols = table_df.columns.tolist()
        priority_cols = ['experiment_id', 'datetime']
        for col in reversed(priority_cols):
            if col in cols:
                cols.insert(0, cols.pop(cols.index(col)))
        table_df = table_df[cols]

        # Format numeric columns to 2 decimal places for better readability
        numeric_cols = table_df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if col != 'experiment_id':
                table_df[col] = table_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")

    # Generate Delta Metrics HTML Scorecards
    delta_html = _generate_scorecard_html(df, baseline_id, candidate_ids)

    return delta_html, bar_fig, table_df

# --- UI and Application Main ---

def main():
    """
    Defines the Gradio UI and launches the application.
    """
    # Use Default theme for a professional "Internal Tool" aesthetic
    with gr.Blocks(theme=gr.themes.Default()) as demo:
        gr.Markdown("# Agent Optimization & Evaluation Workshop (Accelerate '26)")
        gr.Markdown("Compare deterministic and LLM-based metrics across multiple experiment runs.")
        
        # Hidden state to store the main DataFrame
        df_state = gr.State(pd.DataFrame())

        with gr.Row():
            directory_input = gr.Textbox(
                label="Directory Path(s)", 
                placeholder="/path/to/json/logs (comma or newline separated)", 
                scale=4,
                container=False 
            )
            update_button = gr.Button("Load / Update Data", scale=1, variant="primary")

        message_area = gr.Markdown(visible=False)

        with gr.Row():
            baseline_selector = gr.Dropdown(label="Select Baseline", info="Choose the baseline experiment", multiselect=False)
            candidate_selector = gr.Dropdown(label="Select Candidate(s)", info="Choose experiments to compare against baseline", multiselect=True)
            metric_selector = gr.Dropdown(label="Pin Metrics (Charts)", info="Choose key metrics for visual comparison", multiselect=True, scale=1)
            normalize_checkbox = gr.Checkbox(label="Normalize Data (0-1)", value=True, info="Scale metrics to 0-1 range for easier comparison")
            
        generate_button = gr.Button("Generate Dashboard", variant="primary")
        
        # Scorecards at the top
        delta_html = gr.HTML(label="Scorecard")
        
        # A single Plot component that holds the dynamic subplots below the controls
        bar_plot = gr.Plot(label="Metric Comparison (Bar)")
        raw_data_table = gr.Dataframe(label="Raw Data (All Metrics)", interactive=False)

        # --- Event Handlers ---

        update_button.click(
            fn=update_file_and_metric_lists,
            inputs=[directory_input],
            outputs=[message_area, baseline_selector, candidate_selector, metric_selector, df_state]
        )

        generate_button.click(
            fn=generate_dashboard_view,
            inputs=[df_state, baseline_selector, candidate_selector, metric_selector, normalize_checkbox],
            outputs=[delta_html, bar_plot, raw_data_table]
        )

    # Launch configuration
    demo.launch(share=False)

if __name__ == "__main__":
    main()
