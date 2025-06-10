"""A Streamlit web frontend for demonstrating the Weather Agent API."""

import streamlit as st
import requests

# --- Page and API Configuration ---
st.set_page_config(page_title="Weather Agent Demo", page_icon="🤖", layout="wide")
API_BASE = "http://localhost:8000"
DEMO_CREDS = {
    "email": "weather.protract723@passinbox.com",
    "password": "74mXnpt^8x9Z1bm&FjXc",
}


def get_api_session():
    """Gets the requests.Session object from streamlit's session state."""
    if "api_session" not in st.session_state:
        st.session_state.api_session = requests.Session()
    return st.session_state.api_session


# --- Main App ---
st.title("🤖 Weather Agent Demo")
st.caption("A demo showcasing API tools and a conversational agent that uses them.")

# --- API Health Check ---
try:
    health_response = get_api_session().get(f"{API_BASE}/health", timeout=3)
    if (
        health_response.status_code != 200
        or health_response.json().get("status") != "healthy"
    ):
        st.error(
            "API is not running or is unhealthy. Please start the backend server.",
            icon="🚨",
        )
        st.stop()
except requests.exceptions.ConnectionError:
    st.error(
        "Could not connect to the API. Please ensure the backend server is running.",
        icon="🚨",
    )
    st.stop()

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "auth_status" not in st.session_state:
    st.session_state.auth_status = {"authenticated": False}

# --- Define the two main columns ---
col1, col2 = st.columns(2)

# ==============================================================================
# === LEFT COLUMN: DIRECT API TOOL TESTING =====================================
# ==============================================================================
with col1:
    st.header("🛠️ API Tools")
    st.markdown("Directly test the raw API endpoints.")

    # --- Authentication Status ---
    with st.container(border=True):
        st.subheader("Authentication")
        button_col, status_col = st.columns([1, 2])

        def refresh_auth_status():
            """Refreshes the authentication status from the API."""
            try:
                response = get_api_session().get(f"{API_BASE}/auth/status")
                if response.status_code == 200:
                    st.session_state.auth_status = response.json()
                else:
                    st.session_state.auth_status = {
                        "authenticated": False,
                        "error": "Failed to get status",
                    }
            except Exception as e:
                st.session_state.auth_status = {"authenticated": False, "error": str(e)}

        if button_col.button("Refresh Auth Status", use_container_width=True):
            refresh_auth_status()

        status = st.session_state.auth_status
        if status.get("authenticated"):
            status_col.success(
                f"Authenticated as: {status.get('email', 'N/A')}", icon="✅"
            )
        else:
            status_col.warning("Not Authenticated", icon="❌")

        demo_creds = DEMO_CREDS
        email = st.text_input(
            "Email", value=demo_creds["email"], disabled=status.get("authenticated")
        )
        password = st.text_input(
            "Password",
            type="password",
            value=demo_creds["password"],
            disabled=status.get("authenticated"),
        )

        # Login and Logout buttons
        login_col, logout_col = st.columns(2)
        with login_col:
            if st.button(
                "Login", use_container_width=True, disabled=status.get("authenticated")
            ):
                with st.spinner("Logging in... This may take 15-25 seconds."):
                    try:
                        login_payload = {"email": email, "password": password}
                        # Call the main /login endpoint
                        response = get_api_session().post(
                            f"{API_BASE}/auth/login", json=login_payload, timeout=60
                        )

                        if response.status_code == 200 and response.json().get(
                            "success"
                        ):
                            st.toast("Login successful!", icon="🎉")
                        else:
                            st.error(
                                f"Login failed: {response.json().get('message', 'Unknown error')}"
                            )
                    except Exception as e:
                        st.error(f"Error during login: {e}")
                refresh_auth_status()
                st.rerun()

        with logout_col:
            if st.button(
                "Logout",
                type="primary",
                use_container_width=True,
                disabled=not status.get("authenticated"),
            ):
                get_api_session().post(f"{API_BASE}/auth/logout")
                st.toast("Logout successful!")
                refresh_auth_status()
                st.rerun()

    # --- Favorites Management ---
    with st.container(border=True):
        st.subheader("Favorites Management")

        if not status.get("authenticated"):
            st.info("Login to manage favorites.")
        else:
            # List Favorites
            if st.button("List My Favorites"):
                with st.spinner("Fetching favorites..."):
                    response = get_api_session().get(
                        f"{API_BASE}/favorites/", timeout=30
                    )
                    if response.status_code == 200:
                        st.write(response.json())
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")

            # Add/Remove Favorites
            fav_city = st.text_input("City to Add/Remove", placeholder="e.g., Tokyo")
            add_col, rem_col = st.columns(2)
            with add_col:
                if st.button(
                    "Add Favorite", use_container_width=True, disabled=not fav_city
                ):
                    with st.spinner(f"Adding {fav_city}..."):
                        response = get_api_session().post(
                            f"{API_BASE}/favorites/add",
                            json={"city": fav_city},
                            timeout=30,
                        )
                        if response.status_code == 200:
                            st.success(response.json().get("message"))
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
            with rem_col:
                if st.button(
                    "Remove Favorite", use_container_width=True, disabled=not fav_city
                ):
                    with st.spinner(f"Removing {fav_city}..."):
                        response = get_api_session().post(
                            f"{API_BASE}/favorites/remove",
                            json={"city": fav_city},
                            timeout=30,
                        )
                        if response.status_code == 200:
                            st.info(response.json().get("message"))
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")

    # --- Direct Weather Check ---
    with st.container(border=True):
        st.subheader("Direct Weather Query")
        weather_city = st.text_input("City for Weather", placeholder="e.g., Berlin")
        if st.button("Get Weather Data", disabled=not weather_city):
            with st.spinner(f"Getting weather for {weather_city}..."):
                # This endpoint doesn't require auth, but using the session is fine
                response = get_api_session().get(
                    f"{API_BASE}/weather/city/{weather_city}", timeout=30
                )
                if response.status_code == 200:
                    st.write(response.json())
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")


# ==============================================================================
# === RIGHT COLUMN: CONVERSATIONAL AGENT =======================================
# ==============================================================================
with col2:
    st.header("💬 Conversational Agent")
    st.markdown("Chat with the agent that uses the API tools.")

    # Chat message display container
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "action" in message and message["action"]:
                    st.caption(f"Action: `{message['action']}`")

    # Chat input
    if prompt := st.chat_input("Ask about weather or favorites..."):
        # Add and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # Get and display assistant response
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("🧠 Thinking..."):
                    # The chat API is now fully managed by the backend session
                    response = get_api_session().post(
                        f"{API_BASE}/chat/", json={"message": prompt}, timeout=60
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        response_text = response_data.get(
                            "response", "I received an empty response."
                        )
                        action_taken = response_data.get("action_taken")

                        st.markdown(response_text)
                        if action_taken:
                            st.caption(f"Action: `{action_taken}`")

                        # Append full assistant message to history
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": response_text,
                                "action": action_taken,
                            }
                        )
                    else:
                        error_msg = (
                            f"API Error: {response.status_code} - {response.text}"
                        )
                        st.error(error_msg)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": error_msg}
                        )

        # Force a rerun to anchor the input box at the bottom after a new message
        st.rerun()
