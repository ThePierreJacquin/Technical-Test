# Frontend Interface Documentation

This directory contains the Streamlit web interface for the Weather Agent. It serves as an interactive demonstration panel for the backend API.

## 🛠️ Technology

The frontend is built entirely with **[Streamlit](https://streamlit.io/)**, a Python framework for creating data applications and interactive UIs with simple Python scripts.

## ⚙️ How It Works

The interface is designed with two distinct columns to showcase the backend's capabilities in different ways.

### Session Management

To maintain a consistent session with the stateful backend, the app uses a `requests.Session` object.

- This session object is initialized once and stored in `st.session_state`.
- The `requests.Session` object automatically handles the `weather_session_id` cookie set by the FastAPI backend, ensuring that all subsequent API calls from the frontend belong to the same user session.
- This allows the user to log in once and have their authenticated state (including their unique browser context on the server) persist for all subsequent actions.

### API Connection

The frontend communicates with the backend via HTTP requests. The base URL of the API is defined as a constant at the top of `streamlit_app.py`:

```python
API_BASE = "http://localhost:8000"
```

All API calls use this base URL to construct the full endpoint path.

## ✨ UI Components

1. Left Column: API Tools
    - This column provides a direct, raw interface to the backend API endpoints.
    - Its purpose is to allow for clear, isolated testing of each tool (Authentication, Favorites, Weather) without the complexity of the conversational agent.
    - Each button in this column maps directly to a specific API call.
2. Right Column: Conversational Agent
    - This is the primary user-facing component.
    - It interacts exclusively with the /chat/ endpoint on the backend.
    - The agent on the backend is responsible for understanding the user's message, classifying the intent, and calling the appropriate tools itself. This column demonstrates the final, integrated product.

## 🚀 Running the Frontend

To run the Streamlit interface, you must have the backend API running first.

```bash
# Ensure the FastAPI server is running in another terminal

# From the project root directory, run:
streamlit run frontend/streamlit_app.py
Use code with caution.
```

The interface will open in your browser, typically at <http://localhost:8501>.
