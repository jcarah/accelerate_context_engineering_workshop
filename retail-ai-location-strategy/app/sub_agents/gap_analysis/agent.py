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
You have access to a `competitors.json` file containing the raw competitor data found by the previous agent.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Available Data

### MARKET RESEARCH FINDINGS (Part 1):
{market_research_findings}

### COMPETITOR ANALYSIS (Part 2):
{competitor_analysis}

## Your Mission
Write and execute Python code to perform comprehensive quantitative analysis AND competitive landscape mapping.
You MUST load the competitor data from `competitors.json`.

## Analysis Steps

### Step 1: Load and Parse Data
- Load `competitors.json` into a pandas DataFrame.
- Inspect the data structure.
- Clean and prepare the data (handle missing ratings, normalize addresses).

### Step 2: Extract Market Fundamentals
From the market research findings (text above):
- Population estimates
- Income levels (assign numeric scores)
- Infrastructure quality indicators
- Foot traffic patterns

### Step 3: Perform Landscape Analysis (Clustering & Segmentation)
Using Python, analyze the competitor data to identify patterns:
- **Geographic Clustering:** Group competitors by neighborhood/zip code or use coordinate clustering (K-Means if applicable) to identify dense zones vs. gaps.
- **Quality Segmentation:** Categorize competitors by rating tiers (Premium > 4.5, Mid 4.0-4.4, Budget < 4.0).
- **Location Types:** Analyze addresses/types to infer location context (malls, high streets).

### Step 4: Calculate Zone Metrics
For each identified zone/cluster, compute:

**Basic Metrics:**
- Competitor count & density
- Average rating & review volume

**Quality Metrics:**
- Competition Quality Score: Weighted by ratings
- Chain Dominance Ratio: Identify chains vs independents
- High Performer Count (4.5+ rated)

**Opportunity Metrics:**
- Demand Signal: Based on population, income (from research)
- Market Saturation Index: (Competitors × Quality) / Demand
- Viability Score: Multi-factor weighted score

### Step 5: Zone Categorization & Ranking
Classify each zone (SATURATED, MODERATE, OPPORTUNITY) and assign Risk Levels.
Rank the top zones based on the Viability Score.

### Step 6: Output Tables & Insights
Generate clear output tables and a strategic summary.
Your final answer should provide actionable recommendations based on the data.

## Code Guidelines
- Use pandas for data manipulation
- Print all results clearly formatted
- Include intermediate calculations for transparency
- Handle missing data gracefully

Execute the code and provide actionable strategic recommendations based on the quantitative findings.
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
    include_contents='none',  # Isolate from previous history
    output_key="gap_analysis",
    before_agent_callback=before_gap_analysis,
    after_agent_callback=after_gap_analysis,
)
