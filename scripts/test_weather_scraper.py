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
from pathlib import Path
import re
from bs4 import BeautifulSoup
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
# ------------------------------------------

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s"
)
# ---------- utils ----------


def extract_weather_info_from_html(html_content):
    soup = BeautifulSoup(html_content, "lxml")
    weather_data = {}

    current_section = soup.find(
        "section", attrs={"data-testid": "CurrentConditionsContainer"}
    )
    if current_section:
        current = {}
        current["location"] = (
            current_section.select_one(".CurrentConditions--location--yub4l").get_text(
                strip=True
            )
            if current_section.select_one(".CurrentConditions--location--yub4l")
            else None
        )
        current["last_updated"] = (
            current_section.select_one(".CurrentConditions--timestamp--LqnOd").get_text(
                strip=True
            )
            if current_section.select_one(".CurrentConditions--timestamp--LqnOd")
            else None
        )
        current["temperature"] = (
            current_section.select_one(".CurrentConditions--tempValue--zUBSz").get_text(
                strip=True
            )
            if current_section.select_one(".CurrentConditions--tempValue--zUBSz")
            else None
        )
        current["description"] = (
            current_section.select_one(
                ".CurrentConditions--phraseValue---VS-k"
            ).get_text(strip=True)
            if current_section.select_one(".CurrentConditions--phraseValue---VS-k")
            else None
        )
        high_low_elem = current_section.select_one(
            ".CurrentConditions--tempHiLoValue--Og9IG"
        )
        if high_low_elem:
            temps = re.findall(r"\d+°", high_low_elem.get_text())
            current["high_low_today"] = {
                "high": temps[0].strip() if len(temps) > 0 else None,
                "low": temps[1].strip() if len(temps) > 1 else None,
            }
        details_container = soup.select_one(
            ".TodayDetailsCard--detailsContainer--jPhjU"
        )
        if details_container:
            detail_items = details_container.select(
                ".WeatherDetailsListItem--WeatherDetailsListItem--HLP3I"
            )
            for item in detail_items:
                label_element = item.select_one(
                    ".WeatherDetailsListItem--label--U\+Wrx"
                )
                value_element = item.select_one(
                    ".WeatherDetailsListItem--wxData--lW-7H"
                )
                if label_element and value_element:
                    label = label_element.get_text(strip=True)
                    value = value_element.get_text(strip=True)
                    if label == "Wind":
                        current["wind"] = {"speed": value.strip()}
                    elif label == "Humidity":
                        current["humidity"] = value.strip()
                    elif label == "Dew Point":
                        current["dew_point"] = value.strip()
                    elif label == "Pressure":
                        current["pressure"] = value.strip()
                    elif label == "UV Index":
                        current["uv_index"] = value.strip()
                    elif label == "Visibility":
                        current["visibility"] = value.strip()
                    elif label == "Moon Phase":
                        current["moon_phase"] = value.strip()
        sunrise_sunset_container = soup.select_one(
            ".TwcSunChart--sunriseSunsetContainer--iuUOj"
        )
        if sunrise_sunset_container:
            sunrise_value = sunrise_sunset_container.select_one(
                ".TwcSunChart--sunriseDateItem--Os-KL .TwcSunChart--dateValue--TzXBr"
            )
            sunset_value = sunrise_sunset_container.select_one(
                ".TwcSunChart--sunsetDateItem--y9wq2 .TwcSunChart--dateValue--TzXBr"
            )
            current["sunrise"] = (
                sunrise_value.get_text(strip=True) if sunrise_value else None
            )
            current["sunset"] = (
                sunset_value.get_text(strip=True) if sunset_value else None
            )
        weather_data["current_conditions"] = current

    hourly_section = soup.find("section", attrs={"data-testid": "HourlyWeatherModule"})
    if hourly_section:
        hourly_forecast_summary = []
        hourly_items = hourly_section.select(
            ".HourlyWeatherCard--TableWrapper--Tn1HM li.Column--column--gUiRn"
        )
        for item in hourly_items:
            hour_summary = {}
            hour_summary["time_label"] = (
                item.select_one(".Column--label--tMb5q").get_text(strip=True)
                if item.select_one(".Column--label--tMb5q")
                else None
            )
            hour_summary["temperature"] = (
                item.select_one(
                    '.Column--temp--XitCX span[data-testid="TemperatureValue"]'
                ).get_text(strip=True)
                if item.select_one(
                    '.Column--temp--XitCX span[data-testid="TemperatureValue"]'
                )
                else None
            )
            hour_summary["description"] = (
                item.select_one(".Column--icon--yAZ1r span").get_text(strip=True)
                if item.select_one(".Column--icon--yAZ1r span")
                else None
            )
            precip_elem = item.select_one(
                ".Column--columnPrecipWrapper--jjfnS .Column--precip--YkErk"
            )
            precip_text = precip_elem.get_text(strip=True) if precip_elem else None
            if precip_text:
                precip_text = re.sub(
                    r"Chance of \w+", "", precip_text, flags=re.IGNORECASE
                ).strip()
            hour_summary["precip_chance"] = precip_text if precip_text else None
            hourly_forecast_summary.append(hour_summary)
        weather_data["hourly_forecast_summary"] = hourly_forecast_summary

    daily_section = soup.find("section", attrs={"data-testid": "DailyWeatherModule"})
    if daily_section:
        daily_forecast_summary = []
        daily_items = daily_section.select(
            ".DailyWeatherCard--TableWrapper--HtB4k li.Column--column--gUiRn"
        )
        for item in daily_items:
            day_data = {}
            day_data["day_date"] = (
                item.select_one(".Column--label--tMb5q").get_text(strip=True)
                if item.select_one(".Column--label--tMb5q")
                else None
            )
            temp_elements = item.select('span[data-testid="TemperatureValue"]')
            day_data["high_temperature"] = (
                temp_elements[0].get_text(strip=True)
                if len(temp_elements) > 0
                else None
            )
            day_data["low_temperature"] = (
                temp_elements[1].get_text(strip=True)
                if len(temp_elements) > 1
                else None
            )
            day_data["description"] = (
                item.select_one(".Column--icon--yAZ1r span").get_text(strip=True)
                if item.select_one(".Column--icon--yAZ1r span")
                else None
            )
            precip_elem = item.select_one(
                ".Column--columnPrecipWrapper--jjfnS .Column--precip--YkErk"
            )
            precip_text = precip_elem.get_text(strip=True) if precip_elem else None
            if precip_text:
                precip_text = re.sub(
                    r"Chance of \w+", "", precip_text, flags=re.IGNORECASE
                ).strip()
            day_data["precip_chance"] = precip_text if precip_text else None
            daily_forecast_summary.append(day_data)
        weather_data["daily_forecast_summary"] = daily_forecast_summary

    aqi_section = soup.find("section", attrs={"data-testid": "AirQualityModule"})
    if aqi_section:
        air_quality = {}
        air_quality["aqi_value"] = (
            aqi_section.select_one(".DonutChart--innerValue--VRvST").get_text(
                strip=True
            )
            if aqi_section.select_one(".DonutChart--innerValue--VRvST")
            else None
        )
        air_quality["category"] = (
            aqi_section.select_one(".AirQualityText--severity--jiW\+F").get_text(
                strip=True
            )
            if aqi_section.select_one(".AirQualityText--severity--jiW\+F")
            else None
        )
        air_quality["description"] = (
            aqi_section.select_one(".AirQualityText--severityText--7Tout").get_text(
                strip=True
            )
            if aqi_section.select_one(".AirQualityText--severityText--7Tout")
            else None
        )
        air_quality["pollutants"] = []
        pollutant_list_container = aqi_section.select_one(
            ".AirQuality--allPollutantDials--EdhjT"
        )
        if pollutant_list_container:
            pollutant_items = pollutant_list_container.select(
                ".AirQuality--dial--nuMue"
            )
            for item in pollutant_items:
                pollutant = {}
                pollutant["name"] = (
                    item.select_one(".AirQuality--pollutantName--380Zs").get_text(
                        strip=True
                    )
                    if item.select_one(".AirQuality--pollutantName--380Zs")
                    else None
                )
                pollutant["category"] = (
                    item.select_one(".AirQuality--pollutantCategory--twV3l").get_text(
                        strip=True
                    )
                    if item.select_one(".AirQuality--pollutantCategory--twV3l")
                    else None
                )
                measurement_element = item.select_one(
                    ".AirQuality--pollutantMeasurement--ydwxe"
                )
                pollutant["measurement"] = (
                    measurement_element.get_text(strip=True)
                    if measurement_element
                    else None
                )
                if pollutant["measurement"]:
                    match = re.match(r"(\d+\.?\d*)\s*(.*)", pollutant["measurement"])
                    if match:
                        pollutant["value"] = match.group(1)
                        pollutant["unit"] = match.group(2)
                    else:
                        pollutant["value"] = pollutant["measurement"]
                air_quality["pollutants"].append(pollutant)
        weather_data["air_quality_summary"] = air_quality

    return weather_data


# ---------- main(playwright):


async def toggle_favorite(playwright):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        slow_mo=SLOW_MO,
        args=["--disable-geolocation", "--deny-permission-prompts"],
    )
    context = await browser.new_context(
        storage_state=COOKIES_FILE if COOKIES_FILE.exists() else None
    )
    page = await context.new_page()

    logging.info("Opening weather.com")
    await page.goto("https://weather.com/")

    banner_iframe = page.frame_locator("iframe[id^='sp_message_iframe']")
    accept_btn = banner_iframe.locator("button:has-text('Accept')")

    try:
        # Attempt to click the button, waiting up to 1000ms (1 second)
        logging.info("Waiting for and attempting to click the Accept banner...")
        await accept_btn.click(timeout=1000 * (0.5 + 0.5 * random()))
        logging.info("Successfully clicked the Accept banner.")

    except TimeoutError:
        logging.info("Privacy banner did not appear within 1 second.")

    except Exception as e:
        logging.error(f"An unexpected error occurred while clicking the banner: {e}")

    logging.info("Searching for %s via header bar", CITY)
    # ensure search visible
    if not await page.is_visible("#headerSearch_LocationSearch_input"):
        await page.click('button[aria-label="Search"], span[class*="searchIcon"]')
    await page.wait_for_selector("#headerSearch_LocationSearch_input")

    sleep(1 + 0.5 * random())
    await page.fill("#headerSearch_LocationSearch_input", "")  # clear any placeholder
    for char in CITY:
        await page.type("#headerSearch_LocationSearch_input", char, delay=100)

    suggestion_sel = 'button[id^="headerSearch_LocationSearch_listbox"], [data-testid="LocationSearchListItem"]'
    try:
        await page.wait_for_selector(suggestion_sel, timeout=5000)
        await page.click(suggestion_sel)
        logging.info("Clicked first suggestion for %s", CITY)
    except TimeoutError:
        logging.info("Submitting via Enter")
        await page.press("#headerSearch_LocationSearch_input", "Enter")

    await page.press("#headerSearch_LocationSearch_input", "Enter")
    await page.wait_for_selector(
        "#MainContent > div.DaybreakLargeScreen--gridWrapper--ZHESz > main",
        timeout=10000,
    )

    # Set up popup handler BEFORE extracting content
    async def handle_popup(popup):
        await popup.close()  # Immediately close any popups

    page.on("popup", handle_popup)

    # Or handle multiple popups if needed
    context.on("page", lambda new_page: new_page.close())

    raw_html = await page.content()
    print(extract_weather_info_from_html(raw_html))
    await context.storage_state(path=COOKIES_FILE)
    await browser.close()


async def _main():
    async with async_playwright() as p:
        await toggle_favorite(p)


if __name__ == "__main__":
    asyncio.run(_main())
