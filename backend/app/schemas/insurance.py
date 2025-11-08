from typing import List, Optional

from pydantic import BaseModel, Field


class InsuranceMatchResponse(BaseModel):
    plan_id: str = Field(..., description="Canonical plan identifier")
    payer_name: str = Field(..., description="Standardized payer name")
    network_id: Optional[str] = Field(
        None, description="Network identifier used for provider eligibility"
    )
    coverage_percent: Optional[float] = Field(
        None,
        description="Estimated coverage percentage expressed 0-1",
    )
    deductible: Optional[float] = Field(
        None, description="Illustrative deductible amount in dollars"
    )
    match_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the match"
    )


class InsuranceSuggestionsResponse(BaseModel):
    matches: List[InsuranceMatchResponse] = Field(
        default_factory=list,
        description="Top matching plans for the provided prefix",
    )
