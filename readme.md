# 🌤️ Weather Agent Assistant

A conversational AI agent that processes natural language weather queries using live data scraped from weather.com, with integrated user account management and calendar utilities.

## ✨ Core Features

- **🤖 Conversational Interface**: Natural language processing for weather queries ("Is it sunny in London?", "Add Paris to my favorites")
- **🌐 Live Weather Scraping**: Real-time data extraction from weather.com using robust browser automation
- **👤 Authenticated Account Management**: Login and manage favorite locations on weather.com
- **📅 Calendar Integration**: Mock Google Calendar utilities demonstrating multi-tool agent capabilities
- **💬 Persistent Chat Sessions**: Maintains conversation context and authentication state across interactions

## 🏗️ Architecture & Design Philosophy

### Technology Stack Selection

**Backend: FastAPI + Python 3.11+**

- Chosen for native async support, enabling concurrent scraping operations
- Automatic OpenAPI documentation generation for seamless frontend integration
- Pydantic models ensure type safety and data validation throughout the system

**Web Scraping: Playwright**

- Superior to traditional HTTP libraries for dynamic content extraction
- Bypasses anti-bot detection mechanisms through realistic browser automation
- Handles JavaScript-heavy pages and complex user interactions (login flows, favorites)

**AI/LLM: Google Gemini**

- Cost-effective solution compared to OpenAI alternatives
- Strong natural language understanding for intent classification
- Fast response times critical for conversational UX

**Frontend: Streamlit**

- Rapid prototyping tool that accelerated development iteration
- Excellent for technical demonstrations and debugging complex workflows
- Two-column design separates direct API testing from conversational interface

### Session Management Architecture

**Critical Design Decision**: Persistent browser contexts per user session

- Each user gets an isolated Playwright browser context stored server-side
- Authentication state persists across API calls without re-login overhead
- Enables seamless transition between weather queries and account management
- Essential for smooth conversational experience where users expect context retention

## 🛠️ Development Approach

### Phase 1: Foundation & Architecture (Day 1)

- Designed FastAPI backend with modular structure (`api/`, `core/`, `models/`)
- Implemented core routing and session management infrastructure
- Created Pydantic models for type-safe request/response handling
- Integrated Google Gemini for natural language processing
- Built Streamlit interface for rapid testing and iteration

### Phase 2: Scraping Research & Prototyping (Day 2)

- Developed standalone scripts in `scripts/` directory for faster iteration cycles
- `test_weather_scraper.py`: Refined weather.com data extraction techniques
- `test_login_and_favorite.py`: Solved authentication and favorites management challenges
- Discovered optimal selectors and timing patterns through isolated testing
- This script-first approach prevented coupling scraping complexity with API development

### Phase 3: Integration & Polish (Day 3)

- Seamlessly integrated proven scraping techniques into the main API
- Implemented robust error handling and fallback mechanisms
- Added comprehensive session management with automatic cleanup
- Polished user experience with context-aware conversation handling
- Applied code quality tools (ruff, black, pylint) for production readiness

## 🎯 Key Product Decisions

### User Experience Priorities

1. **Zero-Friction Onboarding**: Demo credentials pre-filled for immediate testing
2. **Dual Interface Strategy**: Technical users can test APIs directly; end users enjoy conversational flow
3. **Context Preservation**: Chat history and authentication state persist throughout sessions
4. **Progressive Feature Discovery**: Users naturally discover capabilities through conversation

### Technical Trade-offs

1. **Session-Based Authentication vs. Token-Based**: Chose sessions for simplified user experience and browser context persistence
2. **Real-time Scraping vs. Cached APIs**: Prioritized live data accuracy over response speed
3. **Monolithic vs. Microservices**: Single FastAPI app reduces complexity for demo/prototype phase
4. **Mock Calendar vs. Real Integration**: Focused on demonstrating agent architecture over production calendar setup

### Scalability Considerations

- **Caching Strategy**: 10-minute weather data cache reduces redundant scraping
- **Resource Management**: Automatic browser context cleanup prevents memory leaks
- **Rate Limiting Ready**: Architecture supports future rate limiting implementation
- **Fallback Mechanisms**: OpenWeather API backup when scraping fails

## 🚀 Quick Start

### Prerequisites

```bash
git clone <repository-url>
cd "Technical Test"
pip install -r requirements.txt
playwright install  # Downloads browser binaries
```

### Environment Setup

Create `.env` file in project root:

```bash
# Required
GOOGLE_API_KEY="your_gemini_api_key"

# Optional fallback
OPENWEATHER_API_KEY="your_openweather_key"
```

### Running the Application

```bash
# Terminal 1: Start Backend
uvicorn app.main:app --reload

# Terminal 2: Start Frontend  
streamlit run frontend/streamlit_app.py
```

- **API Documentation**: <http://localhost:8000/docs>
- **Web Interface**: <http://localhost:8501>

## 🧪 Testing & Demo

### Automated Testing

```bash
# Integration test with demo credentials
python scripts/test_login_and_favorite.py

# Weather scraping validation  
python scripts/test_weather_scraper.py
```

### Demo Flow

1. **Authentication**: Use pre-filled demo credentials or your own weather.com account
2. **Weather Queries**: "What's the weather in Tokyo?", "Is it raining in London?"
3. **Account Management**: "Add Berlin to my favorites", "Show me my favorite cities"
4. **Context Retention**: Follow-up questions like "What about tomorrow?" reference previous city

## 📁 Project Structure

```bash
├── app/                    # Core FastAPI application
│   ├── api/               # API route handlers
│   ├── core/              # Business logic & external clients
│   │   ├── scrapers/      # Playwright-based web scraping
│   │   └── auth/          # Credential management
│   ├── models/            # Pydantic data models
│   └── middleware/        # Custom FastAPI middleware
├── frontend/              # Streamlit demonstration interface
├── scripts/               # Standalone development/testing scripts
├── docs/                  # Technical documentation
└── data/                  # Persistent data storage
```

## 🔮 Future Enhancements

- **Better Scrapping**: Faster, retry logic, scrapping the whole city page
- **Advanced Caching**: Redis integration for distributed session management
- **Monitoring**: Add logging, metrics, and health check endpoints
- **Multi-LLM Support**: Add fallback providers for improved reliability  

