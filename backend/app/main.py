"""main.py - the OOS Sales Opportunity Command Center API.

Architecture: React (frontend, not yet built) -> FastAPI (this app) ->
service layer -> repository layer -> SQLite. The one exception is the AI
Assistant route, which calls the existing Azure AI Foundry Agent thin
client instead of the database - see services/foundry_service.py.

No secrets live in this file or anywhere reachable by the frontend; the
Foundry client's credentials are read from environment variables by
foundry_service's underlying agent_api_demo/call_agent_api.py module."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import get_connection, init_schema
from .routers import overview, opportunities, sales_team, outreach, assistant, refresh

app = FastAPI(title="OOS Sales Opportunity Command Center API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(opportunities.router)
app.include_router(sales_team.router)
app.include_router(outreach.router)
app.include_router(assistant.router)
app.include_router(refresh.router)


@app.on_event("startup")
def startup():
    conn = get_connection()
    init_schema(conn)


@app.get("/api/health")
def health():
    return {"status": "ok"}
