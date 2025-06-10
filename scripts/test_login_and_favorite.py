"""
weather_com_favorite.py
Simple Playwright script that toggles a city as favorite on weather.com.
Run:
    python weather_com_favorite.py
Prerequisites:
    pip install playwright
    playwright install
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
import re
from playwright.async_api import async_playwright, TimeoutError
from time import sleep
from random import random

# ------------------ PARAMETERS ------------------
EMAIL = "weather.protract723@passinbox.com"  # weather.com account email
PASSWORD = "74mXnpt^8x9Z1bm&FjXc"  # weather.com account password
CITY = "Paris"  # e.g., "Paris"
ADD = True  # True = add, False = remove
COOKIES_FILE = Path("weather_state.json")  # persisted session
HEADLESS = False  # show browser UI
SLOW_MO = 50  # slow-mo milliseconds for visibility
SNAPSHOT_DIR = Path("snapshots")
AUTO_ACCEPT_COOKIES = True  # Click cookie‑consent banner automatically
MAX_LOG_CHARS = 200  # chars to print in console per snapshot
WINDOW_RE = re.compile(r"window\.__data=JSON\.parse\(\"(.+?)\"\);", re.DOTALL)
FRESH_SESSION = True  # Start with clean state each time
# ------------------------------------------

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s"
)

# ---------- main(playwright):


async def toggle_favorite(playwright):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        slow_mo=SLOW_MO,
        args=["--disable-geolocation", "--deny-permission-prompts"],
    )
    context = await browser.new_context(
        storage_state=(
            COOKIES_FILE if (COOKIES_FILE.exists() and not FRESH_SESSION) else None
        )
    )
    page = await context.new_page()

    logging.info("Opening weather.com")
    await page.goto("https://weather.com/")

    # Handle privacy banner
    banner_iframe = page.frame_locator("iframe[id^='sp_message_iframe']")
    accept_btn = banner_iframe.locator("button:has-text('Accept')")

    try:
        logging.info("Waiting for and attempting to click the Accept banner...")
        await accept_btn.click(timeout=1000 * (0.5 + 0.5 * random()))
        logging.info("Successfully clicked the Accept banner.")
    except TimeoutError:
        logging.info("Privacy banner did not appear within 1 second.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while clicking the banner: {e}")

    # Login process
    logging.info("Starting login process")
    try:
        # Hover over the user account button to show dropdown menu
        user_btn = 'button[aria-haspopup="menu"] div[class*="AccountLinks--desktopLoginButton"]'
        await page.wait_for_selector(user_btn, timeout=5000)
        await page.hover(user_btn)
        logging.info("Hovered over user account button")

        # Wait for dropdown menu to appear and click "Sign in" button
        sign_in_btn = (
            'button[class*="AccountLinks--inlineButtonLink"]:has-text("Sign in")'
        )
        await page.wait_for_selector(sign_in_btn, timeout=5000)
        await page.click(sign_in_btn)
        logging.info("Clicked sign in from dropdown")

        # Wait for login form to appear
        await page.wait_for_selector("#loginEmail", timeout=10000)
        sleep(0.5)  # Small delay before starting to type

        # Fill login form with delays
        await page.fill("#loginEmail", "")  # Clear first
        sleep(0.3)  # Pause before typing
        await page.type(
            "#loginEmail", EMAIL, delay=100
        )  # Increased delay between characters
        sleep(0.8)  # Longer pause between fields

        await page.fill("#loginPassword", "")  # Clear first
        sleep(0.3)  # Pause before typing
        await page.type(
            "#loginPassword", PASSWORD, delay=100
        )  # Increased delay between characters
        sleep(0.8)  # Longer pause before submit

        # Wait for submit button to be enabled
        submit_btn = 'button[type="submit"]:has-text("Sign in")'
        await page.wait_for_selector(submit_btn, timeout=5000)

        # Check if button is enabled before clicking
        is_disabled = await page.get_attribute(submit_btn, "disabled")
        if is_disabled:
            logging.info("Waiting for submit button to be enabled...")
            await page.wait_for_function(
                f'document.querySelector("{submit_btn}").disabled === false',
                timeout=10000,
            )

        sleep(1)  # Extra delay before submit
        await page.click(submit_btn)
        logging.info("Submitted login form")

        # Wait for login to complete (look for user account indicator or redirect)
        try:
            await page.wait_for_selector(
                'div[class*="AccountLinks--userMenu"], div[class*="AccountLinks--userName"]',
                timeout=3000,
            )
            logging.info("Login successful")

            # Double-check we're logged in by looking for user indicator
            user_elements = await page.locator(
                'div[class*="AccountLinks--userMenu"], div[class*="AccountLinks--userName"]'
            ).count()
            if user_elements > 0:
                logging.info("Confirmed: User is logged in")
            else:
                logging.warning("Login status unclear")

        except TimeoutError:
            logging.warning("Could not confirm login success, proceeding anyway")

            # Check if we're on login page or main page
            current_url = page.url
            logging.info(f"Current URL: {current_url}")

            # Take a screenshot to see current state
            SNAPSHOT_DIR.mkdir(exist_ok=True)
            login_debug = (
                SNAPSHOT_DIR
                / f"login_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            await page.screenshot(path=login_debug)
            logging.info(f"Login debug screenshot: {login_debug}")

    except Exception as e:
        logging.error(f"Login failed: {e}")

    # Search for city
    logging.info("Searching for %s via header bar", CITY)
    if not await page.is_visible("#headerSearch_LocationSearch_input"):
        await page.click('button[aria-label="Search"], span[class*="searchIcon"]')
    await page.wait_for_selector("#headerSearch_LocationSearch_input")

    sleep(1 + 0.5 * random())
    await page.fill("#headerSearch_LocationSearch_input", "")
    for char in CITY:
        await page.type("#headerSearch_LocationSearch_input", char, delay=100)

    # Wait for suggestions to appear and click star on first one
    suggestion_sel = 'button[id^="headerSearch_LocationSearch_listbox"]'
    try:
        await page.wait_for_selector(suggestion_sel, timeout=5000)
        logging.info("Search suggestions appeared")

        # Get the first suggestion
        first_suggestion = page.locator(suggestion_sel).first
        suggestion_text = await first_suggestion.text_content()
        logging.info(f"First suggestion: {suggestion_text}")

        # Find the star button in the first suggestion
        star_button = first_suggestion.locator(
            'button[class*="FavoriteStar--favoriteIcon"]'
        )

        # Check current favorite state
        star_button_count = await star_button.count()
        if star_button_count == 0:
            logging.error("No star button found in first suggestion")
            return

        is_favorite_locator_count = await star_button.locator(
            ".FavoriteStar--isFavorite--ytnei"
        ).count()
        has_is_favorite_class = is_favorite_locator_count > 0
        has_remove_text = "remove location" in suggestion_text.lower()
        is_favorited = has_is_favorite_class or has_remove_text

        logging.info(
            f"Current favorite state: {'favorited' if is_favorited else 'not favorited'}"
        )
        logging.info(
            f"Action requested: {'add to favorites' if ADD else 'remove from favorites'}"
        )

        # Determine if action is needed
        action_needed = (ADD and not is_favorited) or (not ADD and is_favorited)

        if action_needed:
            try:
                logging.info("Clicking star button...")
                await star_button.click(force=True)

                # Wait for state change
                await page.wait_for_timeout(1500)

                # Verify the action worked by checking text change
                updated_text = await first_suggestion.text_content()
                updated_has_remove = "remove location" in updated_text.lower()
                updated_has_save = "save location" in updated_text.lower()

                if ADD and updated_has_remove:
                    logging.info(
                        f"SUCCESS: {CITY} added to favorites (now shows 'Remove Location')"
                    )
                elif not ADD and updated_has_save:
                    logging.info(
                        f"SUCCESS: {CITY} removed from favorites (now shows 'Save Location')"
                    )
                else:
                    logging.warning(
                        f"Action may have failed. Updated text: {updated_text}"
                    )

            except Exception as e:
                logging.error(f"Error clicking star button: {e}")

        else:
            if ADD and is_favorited:
                logging.info(f"{CITY} is already favorited")
            elif not ADD and not is_favorited:
                logging.info(f"{CITY} is already not favorited")

    except TimeoutError:
        logging.error("No search suggestions appeared")
    except Exception as e:
        logging.error(f"Error with favorite toggle process: {e}")

    # Save session state only if not using fresh session
    if not FRESH_SESSION:
        await context.storage_state(path=COOKIES_FILE)

    await browser.close()


async def _main():
    async with async_playwright() as p:
        await toggle_favorite(p)


if __name__ == "__main__":
    asyncio.run(_main())
