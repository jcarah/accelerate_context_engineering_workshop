import asyncio
import logging
import sys
import os

# Add the current directory to sys.path so we can import customer_service
sys.path.append(os.getcwd())

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from customer_service.agent import root_agent
from google.genai import types as genai_types

# Configure minimal logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def main():
    """Validates the refactored agent by running a sample query."""
    print("=== Initializing Validation Run ===\n")
    
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="customer_service", user_id="test_user", session_id="test_session"
    )
    
    runner = Runner(
        agent=root_agent, 
        app_name="customer_service", 
        session_service=session_service
    )
    
    # Test query that should trigger Sales Specialist
    query = "I'm looking for some recommendations for planting Petunias in Las Vegas."
    print(f"User: {query}\n")
    
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=genai_types.Content(
            role="user", 
            parts=[genai_types.Part.from_text(text=query)]
        ),
    ):
        print(f"DEBUG Event: {event}") # Print everything
        # We expect to see a transfer to sales_agent or a direct response from it
        if event.actions and event.actions.transfer_to_agent:
            print(f"--- Handing over to: {event.actions.transfer_to_agent} ---\n")
            
        if event.is_final_response() and event.content and event.content.parts:
            print(f"Agent Response: {event.content.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
