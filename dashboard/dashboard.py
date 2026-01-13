import gradio as gr
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
from typing import Dict, List, Any, Optional, Tuple

# --- Data Processing Functions ---

def flatten_json(y: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively flattens a nested dictionary.
    Keys are joined by dots (e.g., 'level1.level2.key').
    """
    out = {}

    def flatten(x: Any, name: str = ''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '.')
        elif type(x) is list:
            # We generally skip lists in this simple flattener unless they are simple numeric lists
            pass
        else:
            out[name[:-1]] = x

    flatten(y)
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

# --- Gradio Controller Functions ---

def update_file_and_metric_lists(directory: str) -> Tuple[gr.update, gr.update, gr.update, pd.DataFrame]:
    """
    Loads data from the specified directory, updates UI selectors,
    and returns messages and the loaded DataFrame.
    """
    if not directory or not os.path.isdir(directory):
        error_message = "### <span style='color:red'>Error: The specified path is not a valid directory.</span>"
        return gr.update(visible=True, value=error_message), gr.update(choices=[], value=[]), gr.update(choices=[], value=[]), pd.DataFrame()
    
    df, skipped_files = load_data_from_directory(directory)
    
    message = ""
    if skipped_files > 0:
        message += f"### <span style='color:orange'>Warning: Skipped {skipped_files} corrupt or malformed JSON file(s).</span>\n"

    if df.empty:
        message += "### <span style='color:blue'>Info: No valid JSON files with metrics found in this directory."
        return gr.update(visible=True, value=message), gr.update(choices=[], value=[]), gr.update(choices=[], value=[]), pd.DataFrame()
    
    files = df["experiment_id"].tolist()
    # Filter columns to only those that are likely metrics (numeric) and not metadata
    metrics = [col for col in df.columns if col not in ['experiment_id', 'datetime']]
    metrics.sort()
    
    message += f"### <span style='color:green'>Success: Loaded {len(df)} experiment(s).</span>"
    # For multiselect Dropdown, the value should be an empty list []
    return gr.update(visible=True, value=message), gr.update(choices=files, value=[]), gr.update(choices=metrics, value=[]), df

def generate_dashboard(df: pd.DataFrame, selected_exp_ids: List[str], selected_metrics: List[str]) -> go.Figure:
    """
    Generates a dynamic Plotly figure with vertically stacked subplots.
    """
    if df.empty or not selected_exp_ids or not selected_metrics:
        # Return an empty figure with a message if nothing is selected
        fig = go.Figure()
        fig.update_layout(
            title="Please select a directory, experiments, and metrics to generate plots.",
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

    filtered_df = df[df['experiment_id'].isin(selected_exp_ids)]
    # Sort by datetime so lines connect logically over time/order
    sorted_filtered_df = filtered_df.sort_values('datetime')

    num_metrics = len(selected_metrics)
    
    # Vertical stack layout (1 column) to give each chart maximum space
    rows = num_metrics
    cols = 1

    fig = make_subplots(
        rows=rows, 
        cols=cols, 
        subplot_titles=selected_metrics,
        vertical_spacing=0.08  # Spacing between rows
    )

    for i, metric in enumerate(selected_metrics):
        row = i + 1
        col = 1

        if metric not in sorted_filtered_df.columns:
            continue

        # Plot a single continuous line for the metric across all selected experiments
        # Using a consistent Google Blue for a clean "internal tool" aesthetic
        fig.add_trace(
            go.Scatter(
                x=sorted_filtered_df['experiment_id'],
                y=sorted_filtered_df[metric],
                mode='lines+markers',
                name=metric,
                showlegend=False, # Hiding legend as titles explain the metric
                line=dict(width=3, color='#1A73E8'),
                marker=dict(size=10),
                hovertemplate=f"<b>Exp:</b> %{{x}}<br><b>{metric}:</b> %{{y}}<extra></extra>"
            ),
            row=row,
            col=col
        )
        
        # Update axis labels
        fig.update_xaxes(title_text="Experiment ID", row=row, col=col)
        fig.update_yaxes(title_text="Value", row=row, col=col)

    # Update overall layout
    # Allocate 500px per chart for a spacious, clean view
    height_per_row = 500
    total_height = max(600, rows * height_per_row)

    fig.update_layout(
        title_text="Metric Comparison Trends",
        height=total_height,
        template="plotly_white",
        margin=dict(l=50, r=50, t=80, b=100)
    )

    return fig

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
                label="Directory Path", 
                placeholder="/path/to/json/logs", 
                scale=4,
                container=False 
            )
            update_button = gr.Button("Load / Update Data", scale=1, variant="primary")

        message_area = gr.Markdown(visible=False)

        with gr.Row():
            file_selector = gr.Dropdown(label="Select Experiments", info="Choose runs to compare", multiselect=True)
            metric_selector = gr.Dropdown(label="Select Metrics", info="Choose metrics to visualize", multiselect=True)
            
        generate_button = gr.Button("Generate Dashboard", variant="primary")
        
        # A single Plot component that holds the dynamic subplots below the controls
        dashboard_plot = gr.Plot(label="Analysis Dashboard")

        # --- Event Handlers ---

        update_button.click(
            fn=update_file_and_metric_lists,
            inputs=[directory_input],
            outputs=[message_area, file_selector, metric_selector, df_state]
        )

        generate_button.click(
            fn=generate_dashboard,
            inputs=[df_state, file_selector, metric_selector],
            outputs=[dashboard_plot]
        )

    # Launch configuration
    demo.launch(share=False)

if __name__ == "__main__":
    main()
