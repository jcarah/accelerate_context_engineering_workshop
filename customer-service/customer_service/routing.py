# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Semantic Router for offloading triage logic."""

import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types, Client
from pydantic import PrivateAttr


logger = logging.getLogger(__name__)


ROUTER_PROMPT = """

You are a semantic router for a customer service bot.

Your job is to classify the user's request into exactly one of the following categories.


Categories:

- "sales_agent": Questions about buying products, cart management, discounts, coupons, stock availability, or product recommendations.

- "fulfillment_agent": Questions about planting services, scheduling appointments, plant care instructions, or connecting with human experts.

- "ambiguous": If the request is unclear, unrelated to the above, or asks for something we definitely cannot do (like "return a product" or "refund").


Output strictly valid JSON: {"target": "agent_name_or_ambiguous"}

"""


class SemanticRouterAgent(BaseAgent):

    """

    A custom agent that uses a lightweight, ephemeral LLM call to route requests.

    This effectively 'offloads' the routing reasoning from the main conversation history,

    saving tokens and preventing routing loops.

    """

    _client: Client = PrivateAttr()

    _model_name: str = PrivateAttr()



    def __init__(self, model_client: Client, model_name: str, name: str = "triage_agent"):

        super().__init__(name=name)

        self._client = model_client

        self._model_name = model_name



        async def _run_async_impl(



            self, context: InvocationContext



        ) -> AsyncGenerator[Event, None]:



            print("DEBUG: SemanticRouterAgent._run_async_impl called")



            # 1. Get user's last message to analyze



            # We look at the most recent 'user' event



            user_text = ""



            for event in reversed(context.session.events):



                if event.author == "user" and event.content and event.content.parts:



                    user_text = event.content.parts[0].text



                    break



            



            print(f"DEBUG: Found user text: {user_text}")



            



            if not user_text:



                # Fallback if no user text found (unlikely)



                yield Event(



                    author=self.name, 



                    content=types.Content(parts=[types.Part.from_text("I didn't catch that. Could you repeat?")])



                )



                return

    



            # 2. Make a fast, cheap call (using the configured model) - NOT saved to history



            # This is the "Offload" pattern.



            try:



                print(f"DEBUG: Calling model {self._model_name}...")



                # Use the async client (aio)



                response = await self._client.aio.models.generate_content(



                    model=self._model_name,



                    contents=f"{ROUTER_PROMPT}\nUser Request: {user_text}",



                    config=types.GenerateContentConfig(



                        response_mime_type="application/json",



                        temperature=0.0 # Deterministic



                    )



                )



                print(f"DEBUG: Model response: {response.text}")



                



                # 3. Parse decision



                decision = json.loads(response.text)



                target = decision.get("target")



                logger.info(f"[SemanticRouter] User: '{user_text}' -> Target: '{target}'")

    



                # 4. Execute Handoff or Fallback



                if target == "ambiguous":



                    # Handle edge cases like "Returns" without looping



                    yield Event(



                        author=self.name, 



                        content=types.Content(parts=[types.Part.from_text("I can help you with buying products or scheduling planting services. For other requests (like returns), please contact our customer support team directly.")])



                    )



                elif target in ["sales_agent", "fulfillment_agent"]:



                    # The Magic: Instant transfer. The sub-agent will see the USER'S message next.



                    yield Event(



                        author=self.name,



                        actions=EventActions(transfer_to_agent=target)



                    )



                else:



                    # Safety fallback



                    yield Event(



                        author=self.name, 



                        content=types.Content(parts=[types.Part.from_text("I'm not sure how to help with that. Could you rephrase?")])



                    )

    



            except Exception as e:



                logger.error(f"[SemanticRouter] Routing failed: {e}")



                print(f"DEBUG: Exception: {e}")



                yield Event(



                    author=self.name, 



                    content=types.Content(parts=[types.Part.from_text("System error in routing. Please try again.")])



                )