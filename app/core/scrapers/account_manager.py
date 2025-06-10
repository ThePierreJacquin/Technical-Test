"""Manages user account actions on weather.com (login, favorites) using Playwright."""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from app.core.session_manager import UserSession
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AccountManager:
    """Manages weather.com authentication"""

    def __init__(self, timeout: int = 20000):
        self.timeout = timeout
        self.base_url = "https://weather.com"

    async def login(
        self, session: UserSession, email: str, password: str
    ) -> Dict[str, Any]:
        """
        Login to weather.com by navigating directly to the login page
        and robustly checking for success or failure.
        """
        page = await session.context.new_page()
        try:
            logger.info(
                f"Attempting login for session {session.session_id} with email {email}"
            )

            # 1. Go directly to the login page
            await page.goto(
                f"{self.base_url}/login",
                wait_until="domcontentloaded",
                timeout=self.timeout,
            )

            # Handle "already logged in" scenario
            try:
                await page.wait_for_selector("#loginEmail", timeout=2000)
            except PlaywrightTimeout:
                if "/login" not in page.url:
                    logger.info(
                        f"Already authenticated. Redirected to {page.url}. Login successful."
                    )
                    session.is_authenticated = True
                    session.user_data["email"] = email
                    session.user_data["login_time"] = datetime.now().isoformat()
                    return {
                        "success": True,
                        "message": "Session already authenticated.",
                        "session_id": session.session_id,
                        "email": email,
                    }

            # 2. Handle privacy banner if it appears
            await self._handle_privacy_banner(page)

            # 3. Fill and submit the login form
            await asyncio.sleep(0.5)
            await page.click("#loginEmail")
            await page.fill("#loginEmail", email)
            await page.click("#loginPassword")
            await page.fill("#loginPassword", password)

            submit_btn_selector = 'button[type="submit"]:has-text("Sign in")'
            await page.wait_for_selector(
                submit_btn_selector, state="visible", timeout=5000
            )
            submit_btn = page.locator(submit_btn_selector)

            try:
                is_btn_enabled = False
                for _ in range(50):
                    if await submit_btn.is_enabled():
                        is_btn_enabled = True
                        break
                    await asyncio.sleep(0.1)
                if not is_btn_enabled:
                    raise PlaywrightTimeout(
                        "Submit button was not enabled within 5 seconds."
                    )
            except PlaywrightTimeout as e:
                logger.error(f"Timeout waiting for submit button to be enabled: {e}")
                raise

            await submit_btn.click()

            # 4. Robustly detect login success or failure
            error_selector = 'div[class*="MemberLoginForm--serverError"]'
            success_indicator = "body:not(:has(#loginEmail))"

            await page.wait_for_selector(
                f"{error_selector}, {success_indicator}", timeout=15000
            )

            if await page.locator(error_selector).is_visible():
                error_text = await page.locator(error_selector).text_content()
                message = (
                    error_text.strip() if error_text else "Invalid email or password."
                )
                logger.warning(f"Login failed for {email}. Reason: {message}")
                session.is_authenticated = False
                return {
                    "success": False,
                    "message": message,
                    "session_id": session.session_id,
                }

            if "/login" not in page.url:
                logger.info(
                    f"Login successful for session {session.session_id}. Redirected to: {page.url}"
                )
                session.is_authenticated = True
                session.user_data["email"] = email
                session.user_data["login_time"] = datetime.now().isoformat()
                return {
                    "success": True,
                    "message": "Successfully logged in to weather.com",
                    "session_id": session.session_id,
                    "email": email,
                }

            logger.error(
                f"Login for {email} in ambiguous state. Not redirected, but no error found."
            )
            session.is_authenticated = False
            return {
                "success": False,
                "message": "Login status ambiguous. Please try again.",
                "session_id": session.session_id,
            }

        except PlaywrightTimeout as e:
            logger.error(
                f"Login for {email} timed out. The website may be slow or unresponsive. Error: {e}"
            )
            session.is_authenticated = False
            return {
                "success": False,
                "message": "Login process timed out.",
                "session_id": session.session_id,
            }
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during login: {e}", exc_info=True
            )
            session.is_authenticated = False
            return {
                "success": False,
                "message": f"An unexpected error occurred: {str(e)}",
                "session_id": session.session_id,
            }
        finally:
            await page.close()

    async def check_auth_status(self, session: UserSession) -> Dict[str, Any]:
        """(Debugging) Checks authentication status by visiting the homepage."""
        try:
            page = await session.context.new_page()
            try:
                await page.goto(self.base_url, timeout=self.timeout)
                user_indicators = [
                    'div[class*="AccountLinks--userMenu"]',
                    'div[class*="AccountLinks--userName"]',
                    'button[aria-label*="Account"]',
                ]
                is_authenticated = False
                for selector in user_indicators:
                    if await page.locator(selector).count() > 0:
                        is_authenticated = True
                        break
                session.is_authenticated = is_authenticated
                return {
                    "authenticated": is_authenticated,
                    "session_id": session.session_id,
                    "email": session.user_data.get("email"),
                }
            finally:
                await page.close()
        except Exception as e:
            logger.error(f"Auth check error: {e}")
            return {
                "authenticated": False,
                "session_id": session.session_id,
                "error": str(e),
            }

    async def _handle_privacy_banner(self, page: Page):
        """Handle privacy/cookie consent banner if present"""
        try:
            banner_iframe = page.frame_locator("iframe[id^='sp_message_iframe']")
            if banner_iframe:
                await banner_iframe.locator("button:has-text('Accept')").click(
                    timeout=2000
                )
                logger.debug("Accepted privacy banner")
        except PlaywrightTimeout:
            logger.debug("No privacy banner found or it was already handled.")
        except Exception as e:
            logger.warning(f"Could not handle privacy banner: {e}")

    async def list_favorites(self, session: UserSession) -> List[str]:
        """
        Scrapes the main page to get the list of all currently favorited cities.
        This is the reliable source of truth for the user's favorites.
        """
        page = await session.context.new_page()
        try:
            logger.info(f"Listing favorites for session {session.session_id}")
            await page.goto(
                f"{self.base_url}/", wait_until="domcontentloaded", timeout=self.timeout
            )

            # The main container for the saved locations bar
            saved_locations_bar_selector = 'div[aria-label="Saved Locations"]'

            # Wait for the main bar to exist first.
            await page.wait_for_selector(saved_locations_bar_selector, timeout=10000)

            # Now, wait for AT LEAST ONE card to appear inside it. This is crucial.
            # We use a try/except block because there might be zero favorites.
            try:
                first_card_selector = (
                    f"{saved_locations_bar_selector} div.styles--card--R1sP3"
                )
                await page.wait_for_selector(
                    first_card_selector, timeout=5000
                )  # Wait 5s for cards to load
                logger.info("Saved location cards are visible.")
            except PlaywrightTimeout:
                # This is NOT an error. It just means the user has no favorites.
                logger.info("No saved location cards found. User has 0 favorites.")
                return []

            # Use BeautifulSoup to parse the cards
            html_content = await page.inner_html(saved_locations_bar_selector)
            soup = BeautifulSoup(html_content, "lxml")

            favorite_cities = []
            location_cards = soup.select("div.styles--card--R1sP3")

            for card in location_cards:
                # A card is a REAL favorite only if it has the "isFavorite" class on its button
                is_a_favorite = card.select_one(
                    "button.FavoriteStar--isFavorite--ytnei"
                )
                if is_a_favorite:
                    city_name_element = card.select_one(
                        "span.styles--locationName--zoGXR"
                    )
                    if city_name_element:
                        # Normalize whitespace and strip to handle potential text formatting issues
                        city_name = " ".join(
                            city_name_element.get_text(strip=True).split()
                        )
                        favorite_cities.append(city_name)

            logger.info(
                f"Found {len(favorite_cities)} favorited cities: {favorite_cities}"
            )
            return favorite_cities
        except Exception as e:
            logger.error(f"Could not list favorites: {e}", exc_info=True)
            return []  # Return empty list on error
        finally:
            await page.close()

    async def toggle_favorite(
        self, session: UserSession, city: str, add: bool
    ) -> Dict[str, Any]:
        """
        Adds or removes a city from favorites, now using list_favorites for state checking.
        """
        logger.info(
            f"REQUEST: {'Add' if add else 'Remove'} '{city}' for session {session.session_id}"
        )

        # Step 1: Get the current, reliable state of favorites.
        current_favorites = await self.list_favorites(session)
        is_currently_favorited = any(
            city.lower() in fav.lower() for fav in current_favorites
        )

        logger.info(
            f"Current server state: '{city}' is favorited: {is_currently_favorited}. Total: {len(current_favorites)}."
        )

        # Step 2: Determine if an action is needed.
        action_needed = (add and not is_currently_favorited) or (
            not add and is_currently_favorited
        )

        if not action_needed:
            message = f"'{city}' is already in the desired state."
            logger.info(f"Idempotent success: {message}")
            return {"success": True, "message": message, "action_taken": False}

        # Step 3: Enforce business logic (10 favorite limit).
        if add and len(current_favorites) >= 10:
            message = "Cannot add favorite: you have reached the maximum of 10."
            logger.warning(message)
            return {"success": False, "message": message, "action_taken": False}

        # Step 4: Perform the UI action (search and click).
        page = await session.context.new_page()
        try:
            await page.goto(
                f"{self.base_url}/", wait_until="domcontentloaded", timeout=self.timeout
            )

            if not await page.is_visible("#headerSearch_LocationSearch_input"):
                await page.click(
                    'button[aria-label="Search"], span[class*="searchIcon"]'
                )
            await page.wait_for_selector(
                "#headerSearch_LocationSearch_input", timeout=5000
            )

            await page.fill("#headerSearch_LocationSearch_input", "")
            await page.type("#headerSearch_LocationSearch_input", city, delay=50)

            suggestion_sel = 'button[id^="headerSearch_LocationSearch_listbox"]'
            await page.wait_for_selector(suggestion_sel, timeout=10000)

            star_button = page.locator(suggestion_sel).first.locator(
                'button[class*="FavoriteStar--favoriteIcon"]'
            )

            logger.info(
                f"Clicking star button to {'add' if add else 'remove'} '{city}'"
            )
            await star_button.click(force=True)
            await page.wait_for_timeout(2000)  # Wait for action to propagate

            # Step 5: Verify the action by re-listing favorites. This is the most reliable way.
            final_favorites = await self.list_favorites(session)
            final_state_is_favorited = any(
                city.lower() in fav.lower() for fav in final_favorites
            )

            if add and final_state_is_favorited:
                message = f"Successfully added '{city}' to favorites."
                logger.info(f"VERIFIED ADD: {message}")
                return {"success": True, "message": message, "action_taken": True}
            elif not add and not final_state_is_favorited:
                message = f"Successfully removed '{city}' from favorites."
                logger.info(f"VERIFIED REMOVE: {message}")
                return {"success": True, "message": message, "action_taken": True}
            else:
                message = f"Action was performed, but final state for '{city}' could not be verified."
                logger.error(message)
                return {"success": False, "message": message, "action_taken": True}

        except Exception as e:
            logger.error(
                f"An unexpected error occurred during favorite toggle: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": f"An unexpected error occurred: {str(e)}",
            }
        finally:
            await page.close()
