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
# limitations under the License.§

"""Agent module for the customer service agent."""

import logging
import warnings
from google.adk import Agent
from .config import Config
from .prompts import GLOBAL_INSTRUCTION, INSTRUCTION
from .shared_libraries.callbacks import (
    rate_limit_callback,
    before_model_compaction,
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

# configure logging __name__
logger = logging.getLogger(__name__)


root_agent = Agent(
    model=configs.agent_settings.model,
    # CACHING OPTIMIZATION: Put static 'INSTRUCTION' first as global_instruction.
    # Put dynamic 'GLOBAL_INSTRUCTION' (customer profile) second.
    global_instruction=INSTRUCTION,
    instruction=GLOBAL_INSTRUCTION,
    name=configs.agent_settings.name,
    tools=[
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
    ],
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
    before_agent_callback=before_agent,
    before_model_callback=[rate_limit_callback, before_model_compaction],
)

from google.adk.apps.app import App, EventsCompactionConfig

# Workshop Demo: Compare Strategies
# Strategy A: LLM-based Summarization (Easy but Slow)
# app = App(
#     root_agent=root_agent,
#     name="customer_service",
#     events_compaction_config=EventsCompactionConfig(
#         compaction_interval=3, overlap_size=1
#     ),
# )

# Strategy B: Manual Compaction (Fast & Precise) -> ACTIVE
app = App(
    root_agent=root_agent,
    name="customer_service",
)
