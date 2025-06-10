from fastapi import APIRouter, HTTPException, Request
from app.models.weather import WeatherRequest, WeatherResponse
from app.core.weather_api import WeatherComClient
from app.core.llm_client import GeminiClient

router = APIRouter(prefix="/weather", tags=["weather"])
weather_client = WeatherComClient()
llm_client = GeminiClient()


@router.post("/query", response_model=WeatherResponse)
async def weather_query(request: Request, weather_request: WeatherRequest):
    """Process natural language weather queries with LLM enhancement"""
    try:
        # Get session ID from request
        session_id = getattr(request.state, "session_id", None)

        # Use LLM to classify and extract city
        intent_result = await llm_client.classify_intent(weather_request.query)
        city = intent_result.get("city")

        if not city:
            llm_response = await llm_client.process_weather_query(
                weather_request.query, None
            )
            return WeatherResponse(
                success=False,
                message="Could not identify city in your query",
                natural_answer=llm_response["response"],
            )

        # Get weather data with session
        weather_data = await weather_client.get_weather_by_city(city, session_id)
        if not weather_data:
            llm_response = await llm_client.process_weather_query(
                weather_request.query, None
            )
            return WeatherResponse(
                success=False,
                message=f"City '{city}' not found",
                natural_answer=llm_response["response"],
            )

        # Generate natural response with LLM
        llm_response = await llm_client.process_weather_query(
            weather_request.query, weather_data
        )

        return WeatherResponse(
            success=True,
            data=weather_data,
            message="Weather data retrieved successfully",
            natural_answer=llm_response["response"],
        )

    except Exception as e:
        return WeatherResponse(
            success=False,
            message=f"Error processing weather query: {str(e)}",
            natural_answer="Sorry, I encountered an error processing your request.",
        )


@router.get("/city/{city_name}", response_model=WeatherResponse)
async def get_weather_by_city(request: Request, city_name: str):
    """Get weather for a specific city"""
    try:
        # Get session ID from request
        session_id = getattr(request.state, "session_id", None)

        weather_data = await weather_client.get_weather_by_city(city_name, session_id)
        if not weather_data:
            raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

        # Generate natural description
        llm_response = await llm_client.process_weather_query(
            f"What's the weather like in {city_name}?", weather_data
        )

        return WeatherResponse(
            success=True,
            data=weather_data,
            message="Weather data retrieved successfully",
            natural_answer=llm_response["response"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving weather: {str(e)}"
        )
