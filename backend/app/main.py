"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import api_router
from database.connection import init_database

app = FastAPI(
    title="Healthcare Price Transparency API",
    version="0.1.0",
    description=(
        "Exposes provider, procedure, and price transparency data for the "
        "Vibeathon frontend widget."
    ),
)

# Configure permissive CORS for local development and embedding scenarios.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """
    Ensure database tables exist before serving requests.
    """
    init_database()


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """
    Lightweight health check endpoint.
    """
    return {"status": "ok"}


# Mount API router under /api namespace.
app.include_router(api_router, prefix="/api")

