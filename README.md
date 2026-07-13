# TheTerminal

A multi-agent travel planner that helps customers plan a trip and find the best
flight deal. It takes a traveler's preferences, factors in the origin city's climate,
reasons about and recommends 3 destinations, finds the best fare per destination
(Tavily web search on airline sites in fast mode, or a live Google Flights scrape),
enriches each destination with live
weather + local trivia, and presents everything — with booking links and prices
in **SAR** — through a React web UI.

Built on **LangGraph + OpenAI** (GPT-4o for reasoning, GPT-4o-mini for the
lightweight sub-agents), **OpenWeatherMap** for climate, **Tavily** for fast
airline-site web search, and **Playwright** for live Google Flights scraping
(with a graceful estimated fallback when a source fails).

## Repository branches

| Branch | Purpose |
|--------|---------|
| **`main`** | Production stack — `agents/`, `smart-travel/api/`, and `smart-travel/frontend/` |
| **`dev`** | Development work — everything on `main` plus `notebooks/` for step-by-step agent exploration |

Clone and use `main` to run the full app. Switch to `dev` when working in Jupyter
notebooks or iterating on individual agents:

```bash
git checkout dev
```

## Architecture

TheTerminal is a single full-stack project:

| Layer | Path | Role |
|-------|------|------|
| **Backend** | `agents/` | LangGraph multi-agent pipeline |
| **API** | `smart-travel/api/` | FastAPI server that adapts the React UI contract to the LangGraph pipeline |
| **Frontend** | `smart-travel/frontend/` | React + Vite + Tailwind web UI |

```
TheTerminal/
├── .env.example                 # Template for repo-root .env
├── requirements.txt             # Python dependencies (root venv)
├── run_api.py                   # Start FastAPI from repo root
├── agents/                      # Multi-agent pipeline
│   ├── graph.py                 # LangGraph orchestration
│   ├── intake_agent.py          # Agent 1 — parse user input
│   ├── weather_agent.py         # Agent 2 — origin climate
│   ├── manager_agent.py         # Pick 3 destinations + final synthesis
│   ├── enrich_agent.py          # Destination weather, trivia, seasonal notes
│   ├── flight_agent.py          # Agent 3 — route by price_mode
│   ├── tavily_agent.py          # Fast mode — airline-domain web search
│   ├── playwright_agent.py      # Live mode — Google Flights scrape
│   ├── state.py                 # Shared TravelState types
│   ├── config.py                # LLM factory + env helpers
│   └── app.py                   # Gradio chatbot prototype (optional)
└── smart-travel/
    ├── api/
    │   ├── main.py              # FastAPI — GET /, POST /api/travel-agents
    │   ├── adapter.py           # TripRequest ↔ plan_trip() ↔ UI JSON
    │   ├── schemas.py           # Pydantic TripRequest (includes priceMode)
    │   └── _bootstrap.py        # Repo root on sys.path; loads .env
    └── frontend/                # React UI
```

On the **`dev`** branch only:

```
notebooks/                       # Per-agent demos + orchestrator (see below)
```

```
React UI (localhost:5173)
    │  POST /api/travel-agents  { fromCity, budget, …, priceMode }
    ▼
smart-travel/api/adapter.py
    │  trip_request_to_user_input() → plan_trip(price_mode=…)
    ▼
agents/graph.py  (LangGraph pipeline)
    │  intake → weather → manager → [enrich ∥ flights] → synthesis
    ▼
TravelState  →  adapter.state_to_ui_response()  →  JSON for the UI
```

The frontend sends trip requests to `POST /api/travel-agents`. The API adapter
composes a user message, runs `agents.graph.plan_trip`, and maps the resulting
`TravelState` back to the JSON shape the UI expects.

## Agents

| Agent | Module | Role |
|-------|--------|------|
| Agent 1 — Intake | `agents/intake_agent.py` | Parse free-form input into a structured `TravelRequest` (origin, budget, travelers, trip type, goal, + any extras). |
| Agent 2 — Weather | `agents/weather_agent.py` | Look up the origin city's climate via OpenWeatherMap and summarize it. |
| Manager | `agents/manager_agent.py` | Reason over intake + weather to pick 3 destinations; later synthesize the final plan. |
| Enrich | `agents/enrich_agent.py` | Add live destination weather + trivia + "what to expect this time of year" (the 3 destinations are enriched concurrently). |
| Agent 3 — Flights | `agents/flight_agent.py` | Compare four carriers and pick the best fare per destination. Routes to Tavily (`fast`) or Playwright (`live`); estimated fallback if the chosen source fails. |
| Tavily search | `agents/tavily_agent.py` | Fast mode — targeted web search on Saudia, Qatar Airways, Etihad, and Flynas domains; LLM extracts SAR fares. |
| Playwright scrape | `agents/playwright_agent.py` | Live mode — fill the Google Flights search form, read fare rows, return the cheapest in SAR. |
| Web UI | `smart-travel/frontend/` | React web app — conversational intake, dashboard, and plan presentation. |

The orchestration that wires the backend agents together lives in `agents/graph.py`.

## Pipeline

```
intake -> weather -> manager_destinations -> [enrich || flights] -> manager_synthesis
```

After the manager picks destinations, `enrich` and `flights` run as concurrent
branches and rejoin at the final synthesis step, which keeps responses fast.

## Setup

From the repo root:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium   # required for priceMode: live

cp .env.example .env          # fill in keys (see below)
```

### Environment variables

All keys live in the **repo root** `.env`:

| Variable | Required for | Notes |
|----------|--------------|-------|
| `OPENAI_API_KEY` | All AI steps | Required |
| `OPENWEATHER_API_KEY` | Weather + enrich | [Free tier](https://home.openweathermap.org/api_keys) |
| `TAVILY_API_KEY` | `priceMode: fast` | [Tavily](https://tavily.com/) — searches Saudia, Qatar, Etihad, Flynas |
| `USE_LIVE_FLIGHTS` | API clients without `priceMode` | `true` → live, `false` → fast; UI choice overrides |
| `OPENAI_MODEL` | Optional | Default `gpt-4o` |
| `OPENAI_FAST_MODEL` | Optional | Default `gpt-4o-mini` |

### Flight price modes (UI + API)

After entering trip details, the chat offers two buttons:

| `priceMode` | Backend | Typical time |
|-------------|---------|--------------|
| `fast` (default) | Tavily web search on airline sites only | ~1 min |
| `live` | Playwright Google Flights scrape only | ~2–3 min |

API request field on `POST /api/travel-agents`:

```json
{
  "fromCity": "Riyadh",
  "budget": "8000 SAR",
  "duration": "7 days",
  "purpose": "family vacation",
  "travelers": "2 adults",
  "date": "2026-07-15",
  "priceMode": "fast"
}
```

Live mode requires `playwright install chromium`. Fast mode requires `TAVILY_API_KEY`.
If the chosen source fails, the backend falls back to **estimated** fares (labeled
`(estimated)` in the UI). Always confirm prices on the airline site before booking.

## Run

**Full app** — two terminals from the repo root:

```bash
# Terminal 1 — API (auto-reloads api/ + agents/)
python run_api.py

# Terminal 2 — React UI
cd smart-travel/frontend
npm install
npm run dev
```

| Service | URL |
|---------|-----|
| API | http://127.0.0.1:8000 |
| UI | http://localhost:5173 |

Use the **Vite dev server** for the app. The API URL alone returns JSON, not the
React interface.

Alternative API start:

```bash
python -m uvicorn api.main:app --reload --app-dir smart-travel --reload-dir smart-travel/api --reload-dir agents
```

## Development (`dev` branch)

Check out `dev` for notebook-based exploration and the Gradio prototype.

**Notebooks** — open `notebooks/06_orchestrator.ipynb` to run the whole agent
pipeline step by step:

| Notebook | Topic |
|----------|-------|
| `01_intake_agent.ipynb` | Intake agent |
| `02_weather_agent.ipynb` | Weather agent |
| `03_manager_destinations.ipynb` | Destination picking |
| `04_flight_agent.ipynb` | Flight pricing (Tavily + Playwright) |
| `05_gradio_app.ipynb` | Gradio chatbot prototype |
| `06_orchestrator.ipynb` | End-to-end pipeline |

**Gradio prototype** — quick chatbot UI wired directly to the LangGraph pipeline,
useful for testing agents without the React frontend:

```bash
python -m agents.app
```

## Notes

- **Flight prices — user choice.** The UI lets users pick **Web search (Tavily)** (`priceMode: fast`) or **Live Google Flights (Playwright)** (`priceMode: live`). Each mode uses a single source; estimated fares are used only if that source fails.
- **Conversational intake.** The UI collects trip details step by step (with a hint that more detail improves results), then asks for a price search mode before running the pipeline.
- **Speed.** Fast mode uses Tavily only (~1 min). Live mode uses Playwright only (~2–3 min). Set `USE_LIVE_FLIGHTS=false` in `.env` only as a server default for non-UI clients.
- **Out of scope (for now):** real booking/payment, authentication, persistence,
  and deployment.

## Related docs

- [`smart-travel/README.md`](smart-travel/README.md) — API reference, UI flow, frontend stack, troubleshooting
- [`agents/graph.py`](agents/graph.py) — LangGraph orchestration
- [`agents/flight_agent.py`](agents/flight_agent.py) — Tavily vs Playwright by `price_mode`
- [`agents/tavily_agent.py`](agents/tavily_agent.py) — airline-domain web search
- [`agents/playwright_agent.py`](agents/playwright_agent.py) — Google Flights scrape
