"""Simple tests for Pydantic models."""

import pytest
from datetime import datetime
from app.models.weather import WeatherData, WeatherCondition


def test_weather_condition_creation():
    """Test creating a weather condition."""
    condition = WeatherCondition(
        main="Sunny",
        description="clear sky",
        icon="01d"
    )
    assert condition.main == "Sunny"
    assert condition.description == "clear sky"


def test_weather_data_creation():
    """Test creating weather data."""
    condition = WeatherCondition(main="Clear", description="sunny", icon="01d")
    
    weather = WeatherData(
        city="Paris",
        temperature=25.0,
        feels_like=27.0,
        humidity=60,
        conditions=condition,
        wind_speed=5.0,
        timestamp=datetime.now()
    )
    
    assert weather.city == "Paris"
    assert weather.temperature == 25.0
    assert weather.humidity == 60


@pytest.mark.parametrize("city", ["Paris", "London", "Tokyo"])
def test_different_cities(city):
    """Test weather data with different cities."""
    condition = WeatherCondition(main="Clear", description="sunny", icon="01d")
    
    weather = WeatherData(
        city=city,
        temperature=20.0,
        feels_like=20.0,
        humidity=50,
        conditions=condition,
        wind_speed=1.0,
        timestamp=datetime.now()
    )
    
    assert weather.city == city