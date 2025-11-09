"""
API routers.
"""

from fastapi import APIRouter

from . import pricing, procedures, providers

api_router = APIRouter()
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(procedures.router, prefix="/procedures", tags=["procedures"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])

__all__ = ["api_router"]

