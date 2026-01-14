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
from ...tools.places_search import SearchPlacesTool
from ...callbacks import before_competitor_mapping, after_competitor_mapping


COMPETITOR_MAPPING_INSTRUCTION = """You are a market intelligence analyst.
Your task is to map all competitors in the target area.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}

## Your Mission
1. Call the `search_places` function with a query for the business type in the target location.
2. The tool will return a JSON object with a `file_name` key.
3. Your final output must be ONLY the value of the `file_name` key.
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
    tools=[SearchPlacesTool()],
    output_key="competitor_analysis_artifact_path",
    before_agent_callback=before_competitor_mapping,
    after_agent_callback=after_competitor_mapping,
)
