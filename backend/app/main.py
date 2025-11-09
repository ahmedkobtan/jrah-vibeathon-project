"""
FastAPI main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import pricing, procedures, providers

app = FastAPI(
    title="Healthcare Price Transparency API",
    description="API for accessing healthcare pricing data and provider information",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pricing.router, prefix="/api/pricing", tags=["pricing"])
app.include_router(procedures.router, prefix="/api/procedures", tags=["procedures"])
app.include_router(providers.router, prefix="/api/providers", tags=["providers"])


@app.get("/")
def read_root():
    """
    Health check endpoint.
    """
    return {"status": "ok", "service": "Healthcare Price Transparency API"}


@app.get("/health")
def health_check():
    """
    Detailed health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "Healthcare Price Transparency API",
        "version": "1.0.0",
    }
