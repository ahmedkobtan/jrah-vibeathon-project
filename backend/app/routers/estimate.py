import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends

from ..schemas import EstimateRequest, EstimateResponse
from ..services.estimator import (
    CostEstimator,
    StubPricingRepository,
    StubProviderRepository,
)
from ..services.insurance import SQLiteInsuranceMatcher, StubInsuranceMatcher
from ..services.sqlite_repositories import (
    SQLiteConfig,
    SQLitePricingRepository,
    SQLiteProviderRepository,
)

router = APIRouter(prefix="", tags=["estimate"])


@lru_cache(maxsize=1)
def _estimator_factory() -> CostEstimator:
    db_path = Path(
        os.getenv(
            "TRANSPARENTCARE_DB_PATH",
            Path(__file__).resolve().parents[3] / "data" / "transparentcare.db",
        )
    )
    if db_path.exists():
        config = SQLiteConfig(db_path=db_path)
        return CostEstimator(
            SQLiteProviderRepository(config),
            SQLitePricingRepository(config),
            SQLiteInsuranceMatcher(config),
        )
    return CostEstimator(
        StubProviderRepository(),
        StubPricingRepository(),
        StubInsuranceMatcher(),
    )


async def get_estimator() -> CostEstimator:
    return _estimator_factory()


@router.get("/estimate", response_model=EstimateResponse)
async def estimate_cost(
    request: EstimateRequest = Depends(),
    estimator: CostEstimator = Depends(get_estimator),
) -> EstimateResponse:
    """Return price estimates grouped by state and facility."""

    return await estimator.estimate(request)
