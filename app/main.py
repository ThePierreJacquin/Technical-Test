"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.core.scrapers.playwright_manager import playwright_manager
from app.core.session_manager import session_manager
from app.middleware.session import SessionMiddleware
import logging

# Import routers individually to avoid circular imports
from app.api.weather import router as weather_router
from app.api.chat import router as chat_router
from app.api.google_calendar import router as google_calendar_router
from app.api.session import router as session_router
from app.api.auth import router as auth_router
from app.api.favorites import router as favorites_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events."""
    # Startup
    logger.info("Starting Weather Agent API")
    if settings.enable_weather_com_scraping:
        await playwright_manager.start(headless=True)
        logger.info("Playwright browser started")

    # Start session manager
    await session_manager.start()
    logger.info("Session manager started")

    yield

    # Shutdown
    logger.info("Shutting down Weather Agent API")

    # Stop session manager first
    await session_manager.stop()
    logger.info("Session manager stopped")

    if playwright_manager.is_running:
        await playwright_manager.stop()
        logger.info("Playwright browser stopped")


app = FastAPI(
    title="Weather Agent API",
    description="Natural language weather queries with task execution",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather_router)
app.include_router(chat_router)
app.include_router(google_calendar_router)
app.include_router(session_router)
app.include_router(auth_router)
app.include_router(favorites_router)


@app.get("/")
async def root():
    """Provides basic information about the running API and its features."""
    return {
        "message": "Weather Agent API",
        "status": "running",
        "features": {
            "weather_scraping": settings.enable_weather_com_scraping,
            "openweather_fallback": settings.enable_openweather_fallback,
        },
    }


@app.get("/health")
async def health_check():
    """Performs a health check of the API and its dependent services."""
    return {
        "status": "healthy",
        "playwright_running": playwright_manager.is_running,
        "active_sessions": session_manager.active_sessions,
    }


@app.get("/sessions")
async def get_sessions():
    """(Admin) Gets information about all active user sessions."""
    return session_manager.get_session_info()
