# Agent Optimization & Evaluation Workshop Dashboard

This interactive dashboard allows users to visualize and compare metrics from multiple JSON log files. It is designed for use in the Accelerate '26 workshop to analyze agent execution trajectories and performance.

## Features

- **Dynamic Metric Discovery:** Automatically flattens nested JSON structures to find all numeric metrics.
- **Interactive Visualization:** Uses Plotly for zoomable, hover-capable charts.
- **Multi-Directory Support:** Load logs from one or multiple paths simultaneously.
- **Native File Browser:** Explore your system to find log files directly within the UI.
- **Production Ready:** Managed with `uv` for reproducible builds, including linting and type-checking configurations.

## Setup & Running

### Option 1: Using `uv` (Recommended)
`uv` is a fast, reproducible dependency manager.

1. **Launch the application**:
   ```bash
   uv run dashboard.py
   ```

### Option 2: Using standard Python
If you cannot use `uv`, you can use standard `pip` and `python`.

1. **Install Dependencies**:
   ```bash
   pip install gradio pandas plotly
   ```
2. **Launch the application**:
   ```bash
   python dashboard.py
   ```

Open the URL provided in the console (typically `http://127.0.0.1:7860`).

## Usage

1. **Locate Logs**: Use the **File Browser** accordion to navigate your system. Selecting `.json` files will automatically populate their parent directories. Alternatively, you can **manually copy and paste** directory paths (comma or newline separated) directly into the **Directory Path(s)** box.
2. **Load Data**: Click **Load / Update Data** to parse all JSON files in the specified directories.
3. **Configure Dashboard**:
    - Select a **Baseline** for comparison.
    - Choose **Candidate(s)** to compare against the baseline.
    - **Pin Metrics** to select which values appear in the bar charts.
    - Toggle **Normalize Data** to scale metrics to a 0-1 range.
4. **Generate**: Click **Generate Dashboard** to view the scorecards, comparison charts, and raw data.
5. **Iterate**: You can change your **Baseline**, **Candidates**, or **Pinned Metrics** at any time and click **Generate Dashboard** again to immediately update the visualizations.

## Development

The project includes pre-configured tools for code quality (requires `uv`):

- **Linting & Formatting**: `uv run ruff check .`
- **Type Checking**: `uv run mypy .`
