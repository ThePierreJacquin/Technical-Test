"""Singleton manager for Playwright browser instances"""

import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """Manages Playwright browser lifecycle"""

    _instance: Optional["PlaywrightManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Implements the singleton pattern for the PlaywrightManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initializes the manager's state."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._playwright: Optional[Playwright] = None
            self._browser: Optional[Browser] = None
            self._default_context: Optional[BrowserContext] = None

    async def start(self, headless: bool = True, slow_mo: int = 0):
        """Start Playwright and browser"""
        async with self._lock:
            if self._browser:
                return

            logger.info("Starting Playwright browser")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                slow_mo=slow_mo,
                args=[
                    "--disable-geolocation",
                    "--deny-permission-prompts",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                ],
            )

            # Create default context for non-authenticated requests
            self._default_context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )

            logger.info("Playwright browser started successfully")

    async def stop(self):
        """Stop browser and Playwright"""
        async with self._lock:
            if self._default_context:
                await self._default_context.close()
                self._default_context = None

            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            logger.info("Playwright browser stopped")

    @asynccontextmanager
    async def get_page(self):
        """Get a new page from default context"""
        if not self._browser:
            await self.start()

        page = await self._default_context.new_page()
        try:
            yield page
        finally:
            await page.close()

    @asynccontextmanager
    async def get_context(self, storage_state: Optional[dict] = None):
        """Get a new browser context"""
        if not self._browser:
            await self.start()

        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
        }

        if storage_state:
            context_options["storage_state"] = storage_state

        context = await self._browser.new_context(**context_options)
        try:
            yield context
        finally:
            await context.close()

    @property
    def is_running(self) -> bool:
        """Check if browser is running"""
        return self._browser is not None and self._browser.is_connected()


# Global instance
playwright_manager = PlaywrightManager()
