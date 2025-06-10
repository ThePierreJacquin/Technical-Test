"""Client for interacting with the Google Gemini LLM."""

import google.generativeai as genai
from app.config import settings
from app.models.weather import WeatherData
from typing import Optional, Dict, Any
import json
import re
import logging

logger = logging.getLogger(__name__)


class GeminiClient:
    """A client to handle interactions with the Google Gemini API."""

    def __init__(self):
        """Initializes the Gemini client and configures the API key."""
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    async def process_weather_query(
        self, query: str, weather_data: Optional[WeatherData] = None
    ) -> Dict[str, Any]:
        """Process weather query and generate natural response"""

        if weather_data:
            # Generate natural response with weather data
            prompt = f"""
            User asked: "{query}"
            
            Weather data for {weather_data.city}, {weather_data.country}:
            - Temperature: {weather_data.temperature}°C (feels like {weather_data.feels_like}°C)
            - Conditions: {weather_data.conditions.description}
            - Humidity: {weather_data.humidity}%
            - Wind speed: {weather_data.wind_speed} m/s
            
            Provide a natural, conversational response to the user's question.
            Be concise but helpful. Answer their specific question (sunny, rainy, hot, etc.).
            """
        else:
            # No weather data - help with query or explain issue
            prompt = f"""
            User asked: "{query}"
            
            This appears to be a weather-related query, but no weather data was found.
            Provide a helpful response explaining what went wrong and how they can rephrase their query.
            Be concise and friendly.
            """

        try:
            response = self.model.generate_content(prompt)
            return {"response": response.text.strip(), "intent": "weather_query"}
        except Exception as e:
            return {
                "response": "Sorry, I had trouble processing your request. Please try again.",
                "intent": "error",
                "error": str(e),
            }

    async def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user intent for action-taking. This prompt explicitly scopes the agent's
        abilities to weather, favorites, and calendar, and omits concepts like 'login'.
        """

        prompt = f"""
        Analyze the user's query and provide a structured JSON output for an automated agent.
        The agent has three primary capabilities: "weather_query", "favorites_management", and "calendar_query".

        Query: "{query}"

        **JSON Output Schema:**
        - "intent": Choose ONE of ["weather_query", "favorites_management", "calendar_query", "general_conversation"].
        - "action":
            - If intent is "favorites_management", choose ONE of ["add", "remove", "list", "check"].
            - For other intents, this is null.
        - "city": Extract the city name if present (e.g., "Paris", "New York, NY").
        - "summary": A brief, one-sentence summary of the user's request.

        **Examples:**

        Query: "What is the weather like in Paris?"
        Output: {{"intent": "weather_query", "action": null, "city": "Paris", "summary": "User is asking for the weather in Paris."}}

        Query: "add London to my favorites"
        Output: {{"intent": "favorites_management", "action": "add", "city": "London", "summary": "User wants to add London to their favorites."}}
        
        Query: "show me my favorite places"
        Output: {{"intent": "favorites_management", "action": "list", "city": null, "summary": "User wants to see their list of favorite locations."}}
        
        Query: "log me in" or "connect to my account"
        Output: {{"intent": "general_conversation", "action": null, "city": null, "summary": "User is asking about account actions which the agent cannot perform directly."}}

        Query: "what's on my schedule?"
        Output: {{"intent": "calendar_query", "action": null, "city": null, "summary": "User is asking about their calendar schedule."}}

        **IMPORTANT**: Respond ONLY with the JSON object, nothing else.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            json_text_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if not json_text_match:
                raise ValueError("LLM did not return a valid JSON object.")

            json_text = json_text_match.group(0)
            result = json.loads(json_text)

            return {
                "intent": result.get("intent", "general_conversation"),
                "action": result.get("action"),
                "city": result.get("city"),
                "confidence": result.get(
                    "confidence", 0.9
                ),  # Removed from prompt, but good to have
                "summary": result.get("summary", "Could not determine user's request."),
            }
        except Exception as e:
            logger.error(f"LLM intent classification failed: {e}", exc_info=True)
            return {
                "intent": "general_conversation",
                "action": None,
                "city": None,
                "confidence": 0.2,
                "summary": "Failed to understand the query.",
            }
