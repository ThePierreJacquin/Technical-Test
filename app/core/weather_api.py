"""Client for fetching weather data, primarily using web scraping."""

import httpx
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import settings
from app.models.weather import WeatherData, WeatherCondition
from app.core.scrapers.weather_scraper import WeatherScraper
from app.core.scrapers.playwright_manager import playwright_manager
import logging

logger = logging.getLogger(__name__)


class WeatherCache:
    """Simple in-memory cache for weather data"""

    def __init__(self, ttl_minutes: int = 10):
        """Initializes the cache with a specified TTL."""
        self._cache: Dict[str, tuple[WeatherData, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, city: str) -> Optional[WeatherData]:
        """Get cached weather data if not expired"""
        city_lower = city.lower()
        if city_lower in self._cache:
            data, timestamp = self._cache[city_lower]
            if datetime.now() - timestamp < self.ttl:
                logger.info(f"Cache hit for {city}")
                return data
            else:
                del self._cache[city_lower]
        return None

    def set(self, city: str, data: WeatherData):
        """Cache weather data"""
        self._cache[city.lower()] = (data, datetime.now())
        logger.info(f"Cached weather data for {city}")


class WeatherComClient:
    """Weather client using weather.com scraping as primary source"""

    def __init__(self):
        self.scraper = WeatherScraper()
        self.cache = WeatherCache(ttl_minutes=10)
        self._scraping_enabled = settings.enable_weather_com_scraping

    async def get_weather_by_city(
        self, city: str, session_id: Optional[str] = None
    ) -> Optional[WeatherData]:
        """
        Get weather data with caching and fallback. This is the single entry point.
        """
        # Check cache first
        cached_data = self.cache.get(city)
        if cached_data:
            return cached_data

        if self._scraping_enabled:
            weather_data = await self._scrape_weather(city, session_id)
            if weather_data:
                self.cache.set(city, weather_data)
                return weather_data

        # Fallback to OpenWeather if scraping is disabled or failed
        if settings.enable_openweather_fallback and settings.openweather_api_key:
            logger.warning(f"Falling back to OpenWeather for {city}")
            return await self._get_openweather_data(city)

        return None

    async def _scrape_weather(
        self, city: str, session_id: Optional[str] = None
    ) -> Optional[WeatherData]:
        """
        Scrapes weather data by performing a search, simulating a real user.
        This is the single, robust method for getting data from weather.com.
        """
        logger.info(f"Starting robust weather scrape for '{city}'")

        page = None
        context_to_use = None

        # Determine which browser context to use: authenticated or default
        if session_id:
            from app.core.session_manager import session_manager

            session = await session_manager.get_session(session_id)
            if session and session.is_authenticated:
                logger.info(f"Using authenticated session context for '{city}'")
                context_to_use = session.context

        if not context_to_use:
            logger.info(f"Using default unauthenticated context for '{city}'")
            if not playwright_manager.is_running:
                await playwright_manager.start()
            context_to_use = playwright_manager._default_context

        try:
            page = await context_to_use.new_page()
            # The get_weather method from the scraper class does the full search-and-scrape
            raw_data = await self.scraper.get_weather(page, city)

            if not raw_data:
                logger.error(f"Scraper returned no data for {city}")
                return None

            return self._convert_scraped_data(city, raw_data)

        except Exception as e:
            logger.error(f"Error during robust scrape for {city}: {e}", exc_info=True)
            return None
        finally:
            if page:
                await page.close()

    def _convert_scraped_data(
        self, city: str, raw_data: Dict[str, Any]
    ) -> Optional[WeatherData]:
        """
        Converts the rich scraped data to our WeatherData model.
        """
        if raw_data.get("temp_current") is None:
            logger.error(
                f"Failed to extract temperature for {city}. Aborting conversion."
            )
            return None

        # --- Helper for cleaning numbers ---
        def clean_numeric(text: Optional[str]) -> Optional[float]:
            if not text:
                return None
            match = re.search(r"(-?\d+\.?\d*)", text)
            return float(match.group(1)) if match else None

        # --- Extract and convert all data points ---
        temp_current = clean_numeric(raw_data.get("temp_current"))
        feels_like = clean_numeric(raw_data.get("feels_like")) or temp_current

        wind_full = raw_data.get("wind", "0 mph")
        wind_speed_mph = clean_numeric(wind_full) or 0.0
        wind_speed_ms = round(wind_speed_mph * 0.44704, 1)
        wind_direction_match = re.search(r"^[A-Z]{1,3}", wind_full)
        wind_direction = wind_direction_match.group(0) if wind_direction_match else None

        description = raw_data.get("condition_phrase", "Unknown")

        return WeatherData(
            city=city,
            temperature=temp_current,
            feels_like=feels_like,
            temp_high=clean_numeric(raw_data.get("temp_high")),
            temp_low=clean_numeric(raw_data.get("temp_low")),
            humidity=int(clean_numeric(raw_data.get("humidity")) or 0),
            pressure=raw_data.get("pressure"),
            conditions=WeatherCondition(
                main=description, description=description, icon=""
            ),
            wind_speed=wind_speed_ms,
            wind_direction=wind_direction,
            uv_index=raw_data.get("uv_index"),
            visibility=raw_data.get("visibility"),
            timestamp=datetime.now(),
        )

    async def _get_openweather_data(self, city: str) -> Optional[WeatherData]:
        """Fallback to OpenWeather API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.openweather_base_url}/weather",
                    params={
                        "q": city,
                        "appid": settings.openweather_api_key,
                        "units": "metric",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()

                    weather_data = WeatherData(
                        city=data["name"],
                        country=data["sys"]["country"],
                        temperature=data["main"]["temp"],
                        feels_like=data["main"]["feels_like"],
                        humidity=data["main"]["humidity"],
                        pressure=data["main"]["pressure"],
                        conditions=WeatherCondition(
                            main=data["weather"][0]["main"],
                            description=data["weather"][0]["description"],
                            icon=data["weather"][0]["icon"],
                        ),
                        wind_speed=data["wind"]["speed"],
                        timestamp=datetime.now(),
                    )

                    self.cache.set(city, weather_data)
                    return weather_data

        except Exception as e:
            logger.error(f"OpenWeather API error: {e}")

        return None
