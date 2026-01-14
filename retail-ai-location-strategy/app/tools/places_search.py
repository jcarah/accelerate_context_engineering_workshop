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

"""Google Maps Places API search tool for competitor mapping."""

import os
import json
import uuid
from google.adk.tools import ToolContext, FunctionTool
from google.adk.models.llm_request import LlmRequest
from google.genai import types as genai_types
from typing_extensions import override


async def search_places(query: str, tool_context: ToolContext) -> dict:
    """Search for places using Google Maps Places API.

    This tool searches for businesses/places matching the query using the
    Google Maps Places API. It saves the results to a JSON file and returns
    the file name.

    Args:
        query: Search query combining business type and location.
               Example: "fitness studio near KR Puram, Bangalore, India"

    Returns:
        dict: A dictionary containing:
            - status: "success" or "error"
            - file_name: Name of the JSON file with place details
            - count: Number of results found
            - error_message: Error details if status is "error"
    """
    try:
        import googlemaps

        maps_api_key = tool_context.state.get("maps_api_key", "") or os.environ.get(
            "MAPS_API_KEY", ""
        )

        if not maps_api_key:
            return {
                "status": "error",
                "error_message": "Maps API key not found. Set MAPS_API_KEY environment variable or 'maps_api_key' in session state.",
                "file_name": None,
                "count": 0,
            }

        gmaps = googlemaps.Client(key=maps_api_key)
        result = gmaps.places(query)

        places = [
            {
                "name": place.get("name", "Unknown"),
                "address": place.get("formatted_address", place.get("vicinity", "N/A")),
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "price_level": place.get("price_level", "N/A"),
                "types": place.get("types", []),
                "business_status": place.get("business_status", "UNKNOWN"),
                "location": {
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                },
                "place_id": place.get("place_id", ""),
            }
            for place in result.get("results", [])
        ]

        file_name = f"competitor_data_{uuid.uuid4()}.json"
        artifact_data = json.dumps({"results": places}, indent=2)
        await tool_context.save_artifact(
            file_name, genai_types.Part.from_text(artifact_data),
            custom_metadata={"summary": f"Competitor data for query: {query}"}
        )

        return {
            "status": "success",
            "file_name": file_name,
            "count": len(places),
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "file_name": None,
            "count": 0,
        }


class SearchPlacesTool(FunctionTool):
    def __init__(self):
        super().__init__(search_places)

