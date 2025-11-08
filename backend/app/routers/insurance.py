import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas import InsuranceMatchResponse, InsuranceSuggestionsResponse
from ..services.insurance import (
    InsuranceMatcher,
    SQLiteInsuranceMatcher,
    StubInsuranceMatcher,
)
from ..services.sqlite_repositories import SQLiteConfig

router = APIRouter(prefix="/insurance", tags=["insurance"])


@lru_cache(maxsize=1)
def _matcher_factory() -> InsuranceMatcher:
    db_path = Path(
        os.getenv(
            "TRANSPARENTCARE_DB_PATH",
            Path(__file__).resolve().parents[3] / "data" / "transparentcare.db",
        )
    )
    if db_path.exists():
        return SQLiteInsuranceMatcher(SQLiteConfig(db_path=db_path))
    return StubInsuranceMatcher()


async def get_matcher() -> InsuranceMatcher:
    return _matcher_factory()


@router.get("/match", response_model=InsuranceMatchResponse)
async def match_insurance(
    name: str = Query(..., description="User-supplied insurance name"),
    matcher: InsuranceMatcher = Depends(get_matcher),
) -> InsuranceMatchResponse:
    match = await matcher.match(name)
    if match is None:
        raise HTTPException(status_code=404, detail="No matching insurance plan found")
    return InsuranceMatchResponse(**match.__dict__)


@router.get("/suggest", response_model=InsuranceSuggestionsResponse)
async def suggest_insurance(
    prefix: str = Query(..., min_length=2, description="Prefix to search"),
    matcher: InsuranceMatcher = Depends(get_matcher),
) -> InsuranceSuggestionsResponse:
    matches = await matcher.suggest(prefix)
    return InsuranceSuggestionsResponse(matches=[InsuranceMatchResponse(**m.__dict__) for m in matches])
