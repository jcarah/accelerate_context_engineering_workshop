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

Your task is to map all competitors in the target area using real Google Maps data.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Your Mission
Use the search_places function to get REAL data from Google Maps about existing competitors.
The data will be automatically saved to a file (`competitors.json`) for the quantitative analyst to process.

## Step 1: Search for Competitors
Call the search_places function with queries like:
- "{business_type} near {target_location}"
- Related business types in the same area

## Step 2: Confirm Data Collection
Once the tool confirms the data is saved, your job is complete.
Do NOT attempt to list the competitors or analyze them here, as the full data is offloaded to the file.
Simply confirm that the competitor mapping is complete and the data is ready for the Gap Analysis stage.

## Output
Provide a brief confirmation:
"Competitor data collection complete. [Count] competitors identified and saved to 'competitors.json' for analysis."
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
    include_contents='none',  # Isolate from previous history
    output_key="competitor_analysis",
    before_agent_callback=before_competitor_mapping,
    after_agent_callback=after_competitor_mapping,
)
