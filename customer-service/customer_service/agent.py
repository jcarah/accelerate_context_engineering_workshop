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

"""Agent module for the isolated customer service agent ecosystem."""

import logging
import warnings
from google.adk import Agent
from .config import Config
from .prompts import (
    GLOBAL_INSTRUCTION,
    TRIAGE_INSTRUCTION,
    SALES_INSTRUCTION,
    FULFILLMENT_INSTRUCTION
)
from .shared_libraries.callbacks import (
    rate_limit_callback,
    before_agent,
    before_tool,
    after_tool
)
from .tools.tools import (
    send_call_companion_link,
    approve_discount,
    sync_ask_for_approval,
    update_salesforce_crm,
    access_cart_information,
    modify_cart,
    get_product_recommendations,
    check_product_availability,
    schedule_planting_service,
    get_available_planting_times,
    send_care_instructions,
    generate_qr_code,
)

warnings.filterwarnings("ignore", category=UserWarning, module=".*pydantic.*")

configs = Config()
logger = logging.getLogger(__name__)

# --- Worker Agents (Specialists) ---

sales_agent = Agent(
    name="sales_agent",
    model=configs.agent_settings.model,
    global_instruction=GLOBAL_INSTRUCTION,
    instruction=SALES_INSTRUCTION,
    description="Expert in products, cart management, discounts, and recommendations.",
    tools=[
        access_cart_information,
        modify_cart,
        get_product_recommendations,
        check_product_availability,
        approve_discount,
        sync_ask_for_approval,
        generate_qr_code,
    ],
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
    before_agent_callback=before_agent,
    before_model_callback=rate_limit_callback,
)

fulfillment_agent = Agent(
    name="fulfillment_agent",
    model=configs.agent_settings.model,
    global_instruction=GLOBAL_INSTRUCTION,
    instruction=FULFILLMENT_INSTRUCTION,
    description="Expert in scheduling services, care instructions, and human connections.",
    tools=[
        schedule_planting_service,
        get_available_planting_times,
        send_care_instructions,
        send_call_companion_link,
        update_salesforce_crm,
    ],
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
    before_agent_callback=before_agent,
    before_model_callback=rate_limit_callback,
)

# --- Root Agent (Stateless LlmRouter) ---

root_agent = Agent(
    name="triage_agent",
    model=configs.agent_settings.model,
    instruction=TRIAGE_INSTRUCTION,
    # Pillar: Reduce/Offload
    # This prevents the router from re-reading long chat histories.
    # It only sees the current message, making it faster and cheaper.
    include_contents='none', 
    sub_agents=[sales_agent, fulfillment_agent],
    before_agent_callback=before_agent,
    before_model_callback=rate_limit_callback,
)

from google.adk.apps.app import App, EventsCompactionConfig

app = App(
    root_agent=root_agent,
    name="customer_service",
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10, overlap_size=1
    ),
)