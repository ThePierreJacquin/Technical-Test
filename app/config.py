"""Application configuration management using Pydantic's BaseSettings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Defines all configuration settings for the API, loaded from .env file."""

    # API Keys
    openweather_api_key: Optional[str] = None
    google_api_key: str

    # App settings
    debug: bool = True
    log_level: str = "INFO"

    # OpenWeather settings (for fallback)
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    # Weather.com scraping settings
    weather_com_base_url: str = "https://weather.com"
    weather_com_timeout: int = 20
    weather_com_retries: int = 3

    # User agent for scraping
    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    # Rate limiting for scraping
    scraper_delay_seconds: float = 1.0

    # Feature flags
    enable_weather_com_scraping: bool = True
    enable_openweather_fallback: bool = False

    class Config:
        """Pydantic model configuration."""

        env_file = ".env"


settings = Settings()
