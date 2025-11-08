from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    """Parameters required to retrieve pricing estimates."""

    cpt_code: str = Field(..., description="Target CPT code for procedure")
    insurance: str = Field(..., description="Insurance carrier or plan name")
    zip: str = Field(..., description="User postal code")
    radius: int = Field(50, description="Search radius in miles")
    include_out_of_network: bool = Field(
        True, description="Whether to include out-of-network facilities"
    )


class FacilityEstimate(BaseModel):
    facility: str
    distance_miles: Optional[float] = None
    services: List["ServiceEstimate"] = Field(
        default_factory=list,
        description="Per-service estimates for this facility",
    )
    source: Optional[str] = Field(
        None, description="Price provenance identifier (hospital_mrf, etc.)"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence level in the price estimate",
    )
    coverage_percent: Optional[float] = Field(
        None,
        description="Estimated coverage percentage applied to patient responsibility",
    )


class StateEstimates(BaseModel):
    state: str
    facilities: List[FacilityEstimate]


class EstimateResponse(BaseModel):
    results: Dict[str, List[FacilityEstimate]] = Field(
        default_factory=dict,
        description="Mapping of state to facility estimates",
    )


class ServiceEstimate(BaseModel):
    cpt_code: str = Field(..., description="CPT code for the quoted service")
    negotiated_rate: float = Field(
        ..., description="Negotiated rate between provider and payer"
    )
    patient_responsibility: Optional[float] = Field(
        None,
        description="Estimated out-of-pocket amount for the patient",
    )
