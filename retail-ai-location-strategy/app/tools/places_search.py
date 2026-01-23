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
from google.adk.tools import ToolContext


def search_places(query: str, tool_context: ToolContext) -> dict:
    """Search for places using Google Maps Places API and save results to disk.

    This tool searches for businesses/places matching the query using the
    Google Maps Places API. It saves the full results to 'competitors.json'
    and returns a summary and preview to save context tokens.

    Args:
        query: Search query combining business type and location.
               Example: "fitness studio near KR Puram, Bangalore, India"

    Returns:
        dict: A dictionary containing:
            - status: "success" or "error"
            - message: Status message with file path
            - file_path: Absolute path to competitors.json
            - count: Number of results found
            - preview: First 3 results for context
            - error_message: Error details if status is "error"
    """
    try:
        import googlemaps

        # Get API key from session state first, then fall back to environment variable
        maps_api_key = tool_context.state.get("maps_api_key", "") or os.environ.get("MAPS_API_KEY", "")

        if not maps_api_key:
            return {
                "status": "error",
                "error_message": "Maps API key not found. Set MAPS_API_KEY environment variable or 'maps_api_key' in session state.",
                "preview": [],
                "count": 0,
            }

        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=maps_api_key)

        # Perform places search
        result = gmaps.places(query)

        # Extract and format results
        places = []
        for place in result.get("results", []):
            places.append({
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
            })

        # Offload: Save full results to disk
        filename = "competitors.json"
        with open(filename, "w") as f:
            json.dump(places, f, indent=2)
        
        file_path = os.path.abspath(filename)

        return {
            "status": "success",
            "message": f"Saved {len(places)} results to {file_path}",
            "file_path": file_path,
            "count": len(places),
            "preview": places[:3],  # Return only top 3 to keep context window clean
            "next_page_token": result.get("next_page_token"),
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "preview": [],
            "count": 0,
        }
