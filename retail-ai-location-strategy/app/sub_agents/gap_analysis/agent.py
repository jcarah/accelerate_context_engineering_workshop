# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Gap Analysis Agent - Part 2B of the Location Strategy Pipeline.

This agent performs quantitative gap analysis using Python code execution
to calculate saturation indices, viability scores, and zone rankings.
"""

from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

from ...config import CODE_EXEC_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ...callbacks import before_gap_analysis, after_gap_analysis


GAP_ANALYSIS_INSTRUCTION = """You are a data scientist analyzing market opportunities using quantitative methods.

Your task is to perform advanced gap analysis on the data collected from previous stages.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Available Data

### MARKET RESEARCH FINDINGS (Part 1):
{market_research_findings}

### COMPETITOR ANALYSIS (Part 2):
The competitor data is provided below as a JSON string for your analysis.

COMPETITORS_JSON = \"\"\"{competitors_json_data}\"\"\"

## Your Mission
Write and execute Python code using `pandas` and `json` to perform a comprehensive quantitative analysis using the COMPETITORS_JSON string.

## Analysis Steps

### Step 1: Load and Validate Data (CRITICAL CIRCUIT BREAKER)
Write Python code to:
1. Load the data using `json.loads(COMPETITORS_JSON)`.
2. **CHECK FOR DATA VALIDITY:**
   - If the list is empty (`[]`), contains 0 items, or is None:
     - Print: "ERROR: DATA_UNAVAILABLE - No competitor data found. Cannot proceed with analysis."
     - **STOP ALL EXECUTION.** Do not calculate metrics. Do not generate a report.
3. If data is valid (>0 items), convert to `pd.DataFrame()` and proceed.
4. Verify the columns: 'name', 'rating', 'reviews', 'price', 'loc'.

### Step 2: Extract Market Fundamentals
From the market research provided above, extract population estimates and demand signals to use as weights in your calculations.

### Step 3: Calculate Zone Metrics (USING CODE)
Compute the following for each identified zone in the dataset:

**Basic Metrics:**
- Competitor count per zone.
- Average competitor rating.
- Total review volume (sum of 'reviews').

**Opportunity Metrics:**
- Market Saturation Index: (Competitor Count × Avg Rating) / Demand Weight.
- Viability Score: A multi-factor weighted score (0-100).

### Step 4: Zone Categorization
Based on your code's output, classify zones as SATURATED, MODERATE, or OPPORTUNITY.

### Step 5: Rank Top Zones
Generate a weighted ranking of the top 3 recommended zones based on the lowest saturation and highest viability scores.

## Code Guidelines
- **CRITICAL**: You MUST use `import pandas as pd` and `import json`.
- Load the data with:
  ```python
  import json
  import pandas as pd
  competitors_list = json.loads(COMPETITORS_JSON)
  df = pd.DataFrame(competitors_list)
  ```
- Print all results in clear markdown tables.
- Handle cases where the JSON string might be empty or malformed.

Execute the code and provide actionable strategic recommendations based ONLY on the quantitative findings from the code output.
"""

gap_analysis_agent = LlmAgent(
    name="GapAnalysisAgent",
    model=CODE_EXEC_MODEL,
    description="Performs quantitative gap analysis using Python code execution for zone rankings and viability scores",
    instruction=GAP_ANALYSIS_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    code_executor=BuiltInCodeExecutor(),
    output_key="gap_analysis",
    before_agent_callback=before_gap_analysis,
    after_agent_callback=after_gap_analysis,
)
