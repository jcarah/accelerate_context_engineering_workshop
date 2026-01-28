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

"""Hardened Tools module for the customer service agent."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional, List
from pydantic import BaseModel, Field
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# --- Pydantic Schemas for Tool Inputs ---

class CartItem(BaseModel):
    """Schema for an item in the shopping cart."""
    product_id: str = Field(description="The unique identifier for the product (e.g., 'soil-456').")
    quantity: int = Field(description="The number of units for this item.")

class DiscountApprovalRequest(BaseModel):
    """Schema for a discount approval request."""
    discount_type: Literal["percentage", "flat"] = Field(description="The type of discount requested.")
    value: float = Field(description="The numeric value of the discount.")
    reason: str = Field(description="The business justification for the discount (e.g., 'Competitor match').")

class QRGenerationRequest(BaseModel):
    """Schema for generating a discount QR code."""
    discount_value: float = Field(description="Value of the discount (e.g. 10 for 10%).")
    discount_type: Literal["percentage", "fixed"] = Field(description="The type of discount.")
    expiration_days: int = Field(default=30, description="Days until the QR code expires.")

class CRMUpdateDetails(BaseModel):
    """Schema for updating customer CRM records."""
    customer_id: str = Field(description="The ID of the customer.")
    appointment_date: Optional[str] = Field(None, description="Date of service (YYYY-MM-DD).")
    appointment_time: Optional[str] = Field(None, description="Time slot (e.g., '9-12').")
    services: Optional[str] = Field(None, description="Description of services performed.")
    notes: Optional[str] = Field(None, description="Additional context for the CRM update.")

# --- Hardened Tools ---

def send_call_companion_link(phone_number: str) -> dict:
    """
    Sends a link to the user's phone number to start a video session.

    **KNOWN LIMITATIONS:** 
    * This tool ONLY sends the link. 
    * The AI agent CANNOT see the video stream or identify plants visually. 
    * After sending the link, you must ask the user to describe the plant textually.

    Args:
        phone_number (str): The phone number to send the link to.
    """
    logger.info("Sending call companion link to %s", phone_number)
    return {"status": "success", "message": f"Link sent to {phone_number}"}


def approve_discount(request: DiscountApprovalRequest) -> dict:
    """
    Approve the flat rate or percentage discount requested by the user.

    **KNOWN LIMITATIONS:**
    * This tool is for internal logic checks ONLY.
    * It does NOT directly apply the discount to a user's cart or session.
    """
    if request.value > 10:
        logger.info("Denying %s discount of %s", request.discount_type, request.value)
        return {"status": "rejected", "message": "discount too large. Must be 10 or less."}
    
    logger.info("Approving a %s discount of %s because %s", request.discount_type, request.value, request.reason)
    return {"status": "ok"}

def sync_ask_for_approval(request: DiscountApprovalRequest) -> dict:
    """
    Asks the manager for approval for a discount.

    **KNOWN LIMITATIONS:**
    * This tool ONLY provides an approval status.
    * It DOES NOT apply the discount to the purchase or cart.
    * After approval, you MUST inform the user that the discount is ready but cannot be applied automatically.

    Args:
        request (DiscountApprovalRequest): Structured approval request.
    """
    logger.info("Asking for approval for a %s discount of %s because %s", request.discount_type, request.value, request.reason)
    return {"status": "approved"}


def update_salesforce_crm(request: CRMUpdateDetails) -> dict:
    """
    Updates the Salesforce CRM with customer details.

    **KNOWN LIMITATIONS:**
    * This tool is for record-keeping only.
    * It does not trigger external notifications or change billing status.

    Args:
        request (CRMUpdateDetails): Structured CRM data.
    """
    logger.info("Updating Salesforce CRM for customer ID %s", request.customer_id)
    return {"status": "success", "message": "Salesforce record updated."}


def access_cart_information(customer_id: str) -> dict:
    """
    Retrieves the current contents of the user's shopping cart.

    **KNOWN LIMITATIONS:**
    * This tool is READ-ONLY. It cannot modify items.

    Args:
        customer_id (str): The ID of the customer.
    """
    logger.info("Accessing cart information for customer ID: %s", customer_id)
    return {
        "items": [
            {"product_id": "soil-123", "name": "Standard Potting Soil", "quantity": 1},
            {"product_id": "fert-456", "name": "General Purpose Fertilizer", "quantity": 1},
        ],
        "subtotal": 25.98,
    }


def modify_cart(customer_id: str, items_to_add: List[CartItem], items_to_remove: List[str]) -> dict:
    """
    Modifies the user's shopping cart by adding and/or removing items.

    **KNOWN LIMITATIONS:**
    * You MUST specify the exact product_id.
    * You cannot modify prices or apply discounts using this tool.

    Args:
        customer_id (str): The ID of the customer.
        items_to_add (list[CartItem]): List of items to add.
        items_to_remove (list[str]): List of product_ids to remove.
    """
    logger.info("Modifying cart for customer ID: %s", customer_id)
    return {"status": "success", "message": "Cart updated successfully."}


def get_product_recommendations(plant_type: str, customer_id: Optional[str] = None) -> dict:
    """
    Provides product recommendations based on the type of plant.

    Args:
        plant_type: The type of plant (e.g., 'Petunias').
        customer_id: Optional customer ID for personalization.
    """
    logger.info("Getting recommendations for %s", plant_type)
    if plant_type.lower() == "petunias":
        return {"recommendations": [
            {"product_id": "soil-456", "name": "Bloom Booster Potting Mix"},
            {"product_id": "fert-789", "name": "Flower Power Fertilizer"}
        ]}
    return {"recommendations": [{"product_id": "soil-123", "name": "Standard Potting Soil"}]}


def check_product_availability(product_id: str, store_id: str) -> dict:
    """
    Checks if a product is in stock at a specific location.

    Args:
        product_id: The ID of the product.
        store_id: The ID of the store (e.g., 'Main Store' or 'pickup').
    """
    logger.info("Checking availability for %s at %s", product_id, store_id)
    return {"available": True, "quantity": 10, "store": store_id}


def schedule_planting_service(customer_id: str, date: str, time_range: str, details: str) -> dict:
    """
    Schedules a planting service appointment.

    **KNOWN LIMITATIONS:**
    * Valid time ranges are only '9-12' and '13-16'.

    Args:
        customer_id: The ID of the customer.
        date: Target date (YYYY-MM-DD).
        time_range: Desired slot (e.g., '9-12').
        details: Planting details.
    """
    logger.info("Scheduling service for %s on %s", customer_id, date)
    return {
        "status": "success",
        "appointment_id": str(uuid.uuid4()),
        "date": date,
        "time": time_range,
    }


def get_available_planting_times(date: str) -> list[str]:
    """
    Retrieves available time slots for planting services.

    Args:
        date: Target date (YYYY-MM-DD).
    """
    return ["9-12", "13-16"]


def send_care_instructions(customer_id: str, plant_type: str, delivery_method: Literal["email", "sms"]) -> dict:
    """
    Sends plant care instructions to the user.

    Args:
        customer_id: The ID of the customer.
        plant_type: The type of plant.
        delivery_method: 'email' or 'sms'.
    """
    return {"status": "success", "message": f"Sent via {delivery_method}."}


def generate_qr_code(request: QRGenerationRequest, tool_context: ToolContext) -> dict:
    """
    Generates a discount QR code.

    **KNOWN LIMITATIONS:**
    * QR codes CANNOT be sent via email; they are displayed in the chat interface only.

    Args:
        request (QRGenerationRequest): Structured QR request.
        tool_context (ToolContext): Runtime context.
    """
    # Defensive: Ensure request is a Pydantic model
    if isinstance(request, dict):
        try:
            request = QRGenerationRequest(**request)
        except Exception as e:
            return {"status": "error", "message": f"Invalid request format: {e}"}

    # Retrieve customer_id from state, fallback to "unknown" if missing
    customer_profile = tool_context.state.get("customer_profile", {})
    # Handle case where profile might be a JSON string or dict
    if isinstance(customer_profile, str):
        import json
        try:
            customer_profile = json.loads(customer_profile)
        except:
            customer_profile = {}
            
    customer_id = customer_profile.get("customer_id", "unknown_customer")

    if request.discount_type == "percentage" and request.discount_value > 10:
        return {"status": "error", "message": "percentage must be <= 10%"}
    
    expiration_date = (datetime.now() + timedelta(days=request.expiration_days)).strftime("%Y-%m-%d")
    return {
        "status": "success",
        "qr_code_data": f"MOCK_QR_{customer_id}_DATA",
        "expiration_date": expiration_date,
    }