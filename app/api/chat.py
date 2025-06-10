"""Main conversational chat endpoint for the agent."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
import httpx

from app.models.chat import ChatRequest, ChatResponse, Message
from app.core.llm_client import GeminiClient
from app.core.weather_api import WeatherComClient
from app.core.session_manager import session_manager, UserSession

# --- Setup ---
router = APIRouter(prefix="/chat", tags=["chat"])
llm_client = GeminiClient()
weather_client = WeatherComClient()
logger = logging.getLogger(__name__)
API_BASE_URL = "http://localhost:8000"
SCRAPE_TIMEOUT = 30.0

# --- Main Chat Endpoint ---


@router.post("/", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest):
    """Handles an incoming user message and orchestrates the agent's response."""

    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is missing.")

    session = await session_manager.get_or_create_session(session_id)
    logger.info(f"Chat request for session {session_id}: '{chat_request.message}'")

    session.chat_history.append(Message(role="user", content=chat_request.message))

    assistant_response_model: ChatResponse

    # --- AGENT'S MAIN REASONING LOOP ---

    # 1. DO I HAVE A PENDING ACTION (e.g., waiting for login confirmation)?
    if session.pending_action:
        logger.info(f"Session has a pending action: {session.pending_action}")

        # Now we check if the user is authenticated.
        refreshed_session = await session_manager.get_session(session.session_id)
        if refreshed_session and refreshed_session.is_authenticated:
            # User has successfully logged in externally.
            logger.info("User is now authenticated. Executing pending action.")
            pending_action = session.pending_action
            session.pending_action = None  # Consume the action
            assistant_response_model = await execute_pending_action(
                session, pending_action
            )
        else:
            # User has not logged in yet. Remind them.
            assistant_response_model = ChatResponse(
                response="It seems you haven't logged in yet. Please use the Authentication tool on the left, and then we can proceed.",
                action_taken="auth_reminder",
            )

    # 2. IF NO PENDING ACTION, IT'S A NEW REQUEST.
    else:
        try:
            # Step 2a: Initial Intent Classification
            intent_result = await llm_client.classify_intent(chat_request.message)
            logger.info(f"Initial LLM classification: {intent_result}")

            # Step 2b: CONTEXT RESOLUTION (The Core Fix)
            # If the intent requires a city but it's missing, resolve it from history.
            if intent_result["intent"] in [
                "weather_query",
                "favorites_management",
            ] and not intent_result.get("city"):
                logger.info(
                    f"Intent '{intent_result['intent']}' requires a city, but it is missing. Attempting to resolve from context."
                )

                # Format the history for the LLM
                history = session.chat_history
                relevant_history = history[:-1]  # History before the current message
                if relevant_history:
                    formatted_history = "\n".join(
                        [f"{msg.role}: {msg.content}" for msg in relevant_history]
                    )

                    prompt = f"""
                    The user's latest request is: "{chat_request.message}"
                    This implies an intent of "{intent_result['intent']}".
                    However, a specific city is missing.
                    
                    Here is the recent conversation history for context:
                    ---
                    {formatted_history}
                    ---
                    
                    Based on the history, what is the specific city the user is referring to?
                    
                    Respond with ONLY the city name (e.g., "Hamburg", "New York, NY"). If you cannot determine the city, respond with the single word "None".
                    """

                    response = await llm_client.model.generate_content_async(prompt)
                    found_city = response.text.strip()

                    if found_city and found_city.lower() != "none":
                        logger.info(
                            f"Resolved city from context: '{found_city}'. Updating intent."
                        )
                        intent_result["city"] = (
                            found_city  # Update the intent object itself
                        )

            logger.info(f"Final intent after context resolution: {intent_result}")

            # Step 2c: Route to handler using the (potentially updated) final intent.
            intent = intent_result.get("intent")
            if intent == "weather_query":
                assistant_response_model = await handle_weather_query(
                    chat_request.message, intent_result
                )
            elif intent == "favorites_management":
                assistant_response_model = await handle_favorites_query(
                    session, intent_result
                )
            elif intent == "calendar_query":
                assistant_response_model = await handle_calendar_query(
                    chat_request.message
                )
            else:
                assistant_response_model = await handle_general_query(
                    chat_request.message
                )

        except Exception as e:
            logger.error(f"Error in chat handler: {e}", exc_info=True)
            assistant_response_model = ChatResponse(
                response="I'm sorry, an unexpected error occurred. Please try again.",
                action_taken="error",
            )

    # Finally, save the assistant's response to history and return it.
    session.chat_history.append(
        Message(role="assistant", content=assistant_response_model.response)
    )
    session.chat_history = session.chat_history[-10:]

    return assistant_response_model


async def execute_pending_action(
    session: UserSession, pending_action: Dict[str, Any]
) -> ChatResponse:
    """Executes a stored action after a required intermediate step (like login)."""
    logger.info(
        f"Re-attempting pending action for session {session.session_id}: {pending_action}"
    )

    if pending_action.get("intent") == "favorites_management":
        # The user has presumably logged in. We just need to re-run the handler.
        return await handle_favorites_query(session, pending_action)

    return ChatResponse(
        response="I'm not sure what we were doing. Could you please ask again?",
        action_taken="pending_action_unknown",
    )


# ---> SIMPLIFY THIS HANDLER <---
async def handle_favorites_query(
    session: UserSession, intent_result: Dict[str, Any]
) -> ChatResponse:
    """
    Handles favorites actions. Assumes the intent (including city) has already been
    resolved by the main chat handler.
    """
    action = intent_result.get("action")
    city = intent_result.get("city")

    # AUTHENTICATION CHECK
    protected_actions = ["add", "remove", "list", "check"]
    if action in protected_actions:
        refreshed_session = await session_manager.get_session(session.session_id)
        if not refreshed_session or not refreshed_session.is_authenticated:
            session.pending_action = intent_result
            logger.info(
                f"Authentication required. Storing pending action: {intent_result}"
            )
            return ChatResponse(
                response="It looks like you're not logged in. To manage your favorites, please use the 'Authentication' tool on the left to log in first, then we can continue.",
                action_taken="auth_required_prompt_for_user",
            )

    # Tool-calling logic
    async with httpx.AsyncClient() as client:
        headers = {"Cookie": f"weather_session_id={session.session_id}"}
        try:
            if action == "add":
                if not city:
                    return ChatResponse(
                        response="I'm sorry, I couldn't figure out which city you meant. Please specify a city to add.",
                        action_taken="favorites_add_missing_city",
                    )
                resp = await client.post(
                    f"{API_BASE_URL}/favorites/add",
                    json={"city": city},
                    headers=headers,
                    timeout=SCRAPE_TIMEOUT,
                )
                resp.raise_for_status()
                return ChatResponse(
                    response=f"You got it! I've added {city} to your favorites.",
                    action_taken="favorite_added",
                    data=resp.json(),
                )

            elif action == "remove":
                if not city:
                    return ChatResponse(
                        response="Which city would you like to remove?",
                        action_taken="favorites_remove_missing_city",
                    )
                resp = await client.post(
                    f"{API_BASE_URL}/favorites/remove",
                    json={"city": city},
                    headers=headers,
                    timeout=SCRAPE_TIMEOUT,
                )
                resp.raise_for_status()
                return ChatResponse(
                    response=f"All set. {city} has been removed from your favorites.",
                    action_taken="favorite_removed",
                    data=resp.json(),
                )

            elif action == "list":
                resp = await client.get(
                    f"{API_BASE_URL}/favorites/",
                    headers=headers,
                    timeout=SCRAPE_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                if data["count"] == 0:
                    return ChatResponse(
                        response="You don't have any favorite locations saved yet.",
                        action_taken="favorites_listed_empty",
                    )
                else:
                    fav_list = ", ".join(
                        [fav["city_name"] for fav in data["favorites"]]
                    )
                    return ChatResponse(
                        response=f"Here are your favorite locations: {fav_list}.",
                        action_taken="favorites_listed",
                        data=data,
                    )

            elif action == "check":
                if not city:
                    return ChatResponse(
                        response="Which city do you want to check?",
                        action_taken="favorites_check_missing_city",
                    )
                resp = await client.get(
                    f"{API_BASE_URL}/favorites/",
                    headers=headers,
                    timeout=SCRAPE_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                is_fav = any(
                    city.lower() in fav["city_name"].lower()
                    for fav in data["favorites"]
                )
                if is_fav:
                    return ChatResponse(
                        response=f"Yes, {city} is in your list of favorites.",
                        action_taken="favorite_checked_true",
                        data=data,
                    )
                else:
                    return ChatResponse(
                        response=f"No, {city} is not one of your favorite locations.",
                        action_taken="favorite_checked_false",
                        data=data,
                    )

            else:
                return ChatResponse(
                    response="I can help you add, remove, list, or check your favorite cities. What would you like to do?",
                    action_taken="favorites_help",
                )

        except httpx.HTTPStatusError as e:
            error_detail = e.response.json().get("detail", "An unknown error occurred.")
            logger.error(f"Internal API call failed: {error_detail}")
            return ChatResponse(
                response=f"I tried to do that, but something went wrong: {error_detail}",
                action_taken="favorites_action_failed",
            )


async def handle_weather_query(
    message: str, intent_result: Dict[str, Any]
) -> ChatResponse:
    """Handles a weather query by getting data and generating a natural response."""
    city = intent_result.get("city")
    if not city:
        return ChatResponse(
            response="I can get the weather for you, but which city are you interested in?",
            action_taken="weather_query_no_city",
        )

    weather_data = await weather_client.get_weather_by_city(city)
    if not weather_data:
        return ChatResponse(
            response=f"I'm sorry, I couldn't find any weather information for '{city}'.",
            action_taken="city_not_found",
        )

    llm_response = await llm_client.process_weather_query(message, weather_data)
    return ChatResponse(
        response=llm_response["response"],
        action_taken="weather_retrieved",
        data=weather_data.dict(),
    )


async def handle_calendar_query(message: str) -> ChatResponse:
    """Handles a calendar-related query by delegating to the calendar tool."""
    return ChatResponse(
        response="My calendar functions are ready. You can ask me about your next meeting, today's schedule, or your availability.",
        action_taken="calendar_info",
    )


async def handle_general_query(message: str) -> ChatResponse:
    """Handles any general conversation that doesn't map to a specific tool."""
    llm_response = await llm_client.model.generate_content_async(
        f"User said: '{message}'. It's not a specific command. Provide a friendly, conversational response."
    )
    return ChatResponse(
        response=llm_response.text.strip(), action_taken="general_conversation"
    )
