"""Weather.com scraping service using Playwright"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import re
from bs4 import BeautifulSoup
from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class WeatherScraper:
    """Scrapes weather data from weather.com"""

    def __init__(self, timeout: int = 20000):
        """Initializes the scraper with a navigation timeout."""
        self.timeout = timeout
        self.base_url = "https://weather.com"

    async def get_weather(self, page: Page, city: str) -> Optional[Dict[str, Any]]:
        """Get weather data for a city using existing page"""
        try:
            logger.info(f"Scraping weather for {city}")

            # Navigate to weather.com
            await page.goto(self.base_url, timeout=self.timeout)

            # Handle privacy banner if it appears
            await self._handle_privacy_banner(page)

            # Search for city
            await self._search_city(page, city)

            temperature_selector = ".CurrentConditions--tempValue--zUBSz"
            logger.info(
                f"Waiting for weather data to load for '{city}' by looking for selector: {temperature_selector}"
            )
            await page.wait_for_selector(temperature_selector, timeout=self.timeout)
            logger.info("Temperature element found. Page has loaded.")

            # Give the page a brief moment to settle after the element appears
            await asyncio.sleep(1)

            # Extract weather data
            html_content = await page.content()
            weather_data = self._extract_weather_data(html_content)

            # Add metadata
            weather_data["city"] = city
            weather_data["scraped_at"] = datetime.now().isoformat()

            return weather_data

        except PlaywrightTimeout:
            logger.error(
                f"Timeout while scraping weather for {city}. Either the city was not found or the page is too slow."
            )
            await page.screenshot(path=f"scraping_timeout_{city}.png")
            logger.error(f"Screenshot saved to scraping_timeout_{city}.png")
            return None
        except Exception as e:
            logger.error(f"Error scraping weather for {city}: {e}", exc_info=True)
            return None

        except PlaywrightTimeout:
            logger.error(f"Timeout while scraping weather for {city}")
            return None
        except Exception as e:
            logger.error(f"Error scraping weather for {city}: {e}")
            return None

    async def get_weather_with_context(
        self, context: BrowserContext, city: str
    ) -> Optional[Dict[str, Any]]:
        """Get weather data using a browser context (for authenticated sessions)"""
        page = await context.new_page()
        try:
            return await self.get_weather(page, city)
        finally:
            await page.close()

    async def _handle_privacy_banner(self, page: Page):
        """Handle privacy/cookie consent banner if present"""
        try:
            banner_iframe = page.frame_locator("iframe[id^='sp_message_iframe']")
            accept_btn = banner_iframe.locator("button:has-text('Accept')")
            await accept_btn.click(timeout=1000)
            logger.info("Accepted privacy banner")
        except PlaywrightTimeout:
            logger.debug("No privacy banner found")
        except Exception as e:
            logger.warning(f"Error handling privacy banner: {e}")

    async def _search_city(self, page: Page, city: str):
        """Search for a city in the weather.com search bar"""
        start_url = page.url
        # Ensure search is visible
        if not await page.is_visible("#headerSearch_LocationSearch_input"):
            await page.click('button[aria-label="Search"], span[class*="searchIcon"]')

        await page.wait_for_selector("#headerSearch_LocationSearch_input")
        await asyncio.sleep(0.5)  # Small delay for stability

        # Clear and type city name
        await page.fill("#headerSearch_LocationSearch_input", "")
        await page.type("#headerSearch_LocationSearch_input", city, delay=50)

        # Click first suggestion or press Enter
        suggestion_sel = 'button[id^="headerSearch_LocationSearch_listbox"]'
        try:
            await page.wait_for_selector(suggestion_sel, timeout=3000)
            await page.click(f"{suggestion_sel}:first-child")
            logger.info(f"Clicked suggestion for {city}")
        except PlaywrightTimeout:
            logger.info("No suggestions, submitting search")
            await page.press("#headerSearch_LocationSearch_input", "Enter")

        try:
            logger.info(f"Waiting for URL to change from {start_url}...")
            await page.wait_for_url(
                lambda url: url != start_url and "weather.com/weather/today" in url,
                timeout=10000,
            )
            logger.info(f"Successfully navigated to new URL: {page.url}")
        except PlaywrightTimeout:
            logger.error(
                f"Page URL did not change after searching for '{city}'. Search may have failed."
            )

    def _extract_weather_data(self, html_content: str) -> Dict[str, Any]:
        """
        Extracts comprehensive weather information using data-testid attributes for robustness.
        """
        soup = BeautifulSoup(html_content, "lxml")
        data = {}

        # --- Main Current Conditions ---
        current_section = soup.find(
            "div", {"data-testid": "CurrentConditionsContainer"}
        )
        if current_section:
            data["temp_current"] = self._get_text(
                current_section, '[data-testid="TemperatureValue"]'
            )
            data["condition_phrase"] = self._get_text(
                current_section, '[data-testid="wxPhrase"]'
            )

            # Extract Day/Night High/Low from the primary header
            day_night_temps = current_section.select(
                '.CurrentConditions--tempHiLoValue--Og9IG [data-testid="TemperatureValue"]'
            )
            if len(day_night_temps) >= 2:
                data["temp_high"] = self._get_text(day_night_temps[0])
                data["temp_low"] = self._get_text(day_night_temps[1])

        # --- Today's Details Card ---
        details_section = soup.find("section", {"data-testid": "TodaysDetailsModule"})
        if details_section:
            data["feels_like"] = self._get_text(
                details_section,
                '[data-testid="FeelsLikeSection"] [data-testid="TemperatureValue"]',
            )

            # Extract all detail list items
            list_items = details_section.select(
                '[data-testid="WeatherDetailsListItem"]'
            )
            for item in list_items:
                label = self._get_text(
                    item, '[data-testid="WeatherDetailsLabel"]'
                ).lower()
                value = self._get_text(item, '[data-testid="wxData"]')

                if "wind" in label:
                    data["wind"] = value
                elif "humidity" in label:
                    data["humidity"] = value
                elif "uv index" in label:
                    data["uv_index"] = value
                elif "pressure" in label:
                    # Extract the pressure value and trend
                    pressure_value = self._get_text(
                        item, '[data-testid="PressureValue"]'
                    )
                    trend_arrow = item.select_one('svg[aria-label*="arrow"]')
                    trend = (
                        "rising"
                        if trend_arrow and "up" in trend_arrow.get("aria-label", "")
                        else "falling"
                    )
                    data["pressure"] = f"{pressure_value} ({trend})"
                elif "visibility" in label:
                    data["visibility"] = value

        logger.info(f"Robust extraction found rich raw data: {data}")
        return data

    def _get_text(self, parent_element, selector=None):
        """Helper to safely extract text from a selector within a parent element."""
        if selector:
            element = parent_element.select_one(selector)
        else:
            element = parent_element

        if element:
            return element.get_text(strip=True)
        return None

    def _clean_temperature(self, temp_str: Optional[str]) -> Optional[int]:
        """Extracts numeric temperature from a string like '72°'."""
        if not temp_str:
            return None
        match = re.search(r"(-?\d+)", temp_str)  # Handles negative temps
        return int(match.group(1)) if match else None
