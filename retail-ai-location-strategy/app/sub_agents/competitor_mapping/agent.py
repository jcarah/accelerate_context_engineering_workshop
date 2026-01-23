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

"""Competitor Mapping Agent - Part 2A of the Location Strategy Pipeline.

This agent maps competitors using the Google Maps Places API to get
ground-truth data about existing businesses in the target area.
"""

from google.adk.agents import LlmAgent
from google.genai import types

from ...config import FAST_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ...tools import search_places
from ...callbacks import before_competitor_mapping, after_competitor_mapping


COMPETITOR_MAPPING_INSTRUCTION = """You are a market intelligence analyst specializing in competitive landscape analysis.

Your task is to map and analyze all competitors in the target area using real Google Maps data.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Your Mission
Use the search_places function to get REAL data from Google Maps about existing competitors.

## Step 1: Search for Competitors
Call the search_places function. It will return a preview of the results and save the full dataset to a local file named 'competitors.json'.

## Step 2: Analyze the Results
Based on the preview data and the confirmation of the saved file:
- Note the total number of competitors found.
- Confirm that 'competitors.json' has been successfully created for the next stage (Gap Analysis).
- Analyze the sample of competitors provided in the tool's 'preview' field.

## Step 3: Identify Patterns (Qualitative)
Analyze the competitive landscape based on the available data:
- Geographic Clustering: Are there clear clusters mentioned in addresses?
- Quality Segmentation: What is the rating trend in the preview?

## Step 4: Strategic Assessment
Provide insights on:
- Preliminary underserved opportunities.
- Quality gaps noticed in the sample.
- **IMPORTANT**: Explicitly state that the full quantitative analysis will be performed by the GapAnalysisAgent using the offloaded 'competitors.json' file.

## Output Format
Provide a summary including:
1. Total count of competitors found and location of the data file ('competitors.json').
2. Qualitative breakdown of the previewed competitors.
3. High-level pattern analysis.
4. Strategic instructions for the GapAnalysisAgent.
"""

competitor_mapping_agent = LlmAgent(
    name="CompetitorMappingAgent",
    model=FAST_MODEL,
    description="Maps competitors using Google Maps Places API for ground-truth competitor data",
    instruction=COMPETITOR_MAPPING_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    tools=[search_places],
    output_key="competitor_analysis",
    before_agent_callback=before_competitor_mapping,
    after_agent_callback=after_competitor_mapping,
)
