# Agent Optimization & Evaluation Workshop Dashboard

This interactive dashboard allows users to visualize and compare metrics from multiple JSON log files. It is designed for use in the Accelerate '26 workshop to analyze agent execution trajectories and performance.

## Features

- **Dynamic Metric Discovery:** Automatically flattens nested JSON structures to find all numeric metrics.
- **Interactive Visualization:** Uses Plotly for zoomable, hover-capable charts.
- **Chronological Trending:** Automatically sorts experiments by the `interaction_datetime` timestamp in the logs, ensuring trend lines flow logically.
- **Robust Error Handling:** Gracefully handles invalid paths, missing metrics, and corrupt JSON files.

## Prerequisites

Ensure you have the necessary Python libraries installed:

```bash
pip install -r requirements.txt
```

## How to Run

1. Navigate to the dashboard directory:
   ```bash
   cd accelerate_context_engineering_workshop/dashboard
   ```
2. Launch the application:
   ```bash
   python3 dashboard.py
   ```
3. Open the URL provided in the console (typically `http://127.0.0.1:7860`).

## Usage

1. **Set Directory:** Enter the path to the directory containing your `.json` log files.
2. **Update Data:** Click "Load / Update Data" to parse the files.
3. **Select Runs:** Use the "Select Experiments" dropdown to choose which logs to compare.
4. **Select Metrics:** Use the "Select Metrics" dropdown to choose which data points to plot.
5. **Generate:** Click "Generate Dashboard" to view the trend charts.
