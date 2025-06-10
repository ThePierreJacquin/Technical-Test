# API Backend Documentation

This directory contains the complete FastAPI backend for the Weather Agent Assistant. It handles all business logic, external API calls, web scraping, and data management.

## 🏗️ Architecture & Request Flow

The API is built on a modular, asynchronous architecture. A typical request follows this flow:

1. **HTTP Request**: A client (like the Streamlit frontend) sends a request to an endpoint (e.g., `POST /chat/`).
2. **Middleware**: The `SessionMiddleware` intercepts the request, retrieving an existing session ID from the request cookie or creating a new one. This ID is attached to the request state.
3. **API Router**: The request is routed to the corresponding endpoint function in the `app/api/` directory (e.g., `chat()` in `app/api/chat.py`).
4. **Core Logic**: The endpoint function calls business logic modules located in `app/core/`. This is where the main work happens.
    - `SessionManager` is used to retrieve the user's specific browser context.
    - `GeminiClient` may be called to classify intent.
    - `AccountManager` or `WeatherScraper` may be used to perform actions via Playwright.
5. **Data Validation**: Pydantic models from `app/models/` are used to validate incoming request data and serialize outgoing responses, ensuring type safety.
6. **HTTP Response**: The endpoint returns a Pydantic model, which FastAPI automatically converts to a JSON response.

## 🧩 Key Modules

- **`api/`**: Contains all the API routers and endpoints. Each file corresponds to a feature set (e.g., `auth.py`, `weather.py`). This is the "controller" layer.
- **`core/`**: The "brains" of the application. It contains the core business logic and clients for external services.
  - `llm_client.py`: Manages all interactions with the Google Gemini API.
  - `session_manager.py`: A critical singleton that manages user-specific browser contexts, enabling multi-user support and authentication persistence.
  - `weather_api.py`: The primary client for fetching weather data, orchestrating the scraper and cache.
  - **`scrapers/`**: Contains the Playwright-based web scrapers.
    - `playwright_manager.py`: A singleton that manages the global Playwright browser instance.
    - `account_manager.py`: Handles all user account interactions on `weather.com` (login, favorites).
    - `weather_scraper.py`: Handles searching for cities and scraping weather data.
  - **`auth/`**: Manages credential storage.
    - `credential_manager.py`: A simplified, encrypted credential store.
- **`models/`**: Contains all Pydantic models for request/response validation.
- **`middleware/`**: Custom FastAPI middleware, currently used for session handling.
- **`config.py`**: Centralized configuration management using Pydantic's `BaseSettings`.

## 🔧 Configuration

The API is configured via environment variables loaded from a `.env` file in the project root.

- `GOOGLE_API_KEY` (Required): Your API key for Google Gemini.
- `OPENWEATHER_API_KEY` (Optional): Your API key for OpenWeatherMap, used as a fallback.

## 🚀 Running the API

To run the API server independently:

```bash
# Ensure you are in the project's root directory
uvicorn app.main:app --reload
Use code with caution.
```

The API documentation will be available at <http://localhost:8000/docs>.

## 🧪 Testing

The test.py file in the root directory provides a simple integration test for the authentication and favorites flow. Ensure the API server is running before executing it:

```bash
python test.py
```
