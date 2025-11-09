"""
Pydantic schemas for query understanding API
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class QueryRequest(BaseModel):
    """Request model for query understanding"""
    query: str = Field(..., description="Natural language query from user", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "How much for a knee MRI with Blue Cross PPO in Joplin?"
            }
        }


class ProcedureMatch(BaseModel):
    """A matched procedure with CPT code"""
    cpt_code: str = Field(..., description="CPT or HCPCS code")
    description: str = Field(..., description="Procedure description")
    match_score: float = Field(..., description="Match confidence (0-1)")


class QueryResponse(BaseModel):
    """Response model for parsed query"""
    user_query: str = Field(..., description="Original user query")
    procedure_name: Optional[str] = Field(None, description="Extracted procedure name")
    cpt_codes: List[str] = Field(default_factory=list, description="Matched CPT codes")
    matched_procedures: List[ProcedureMatch] = Field(
        default_factory=list,
        description="Detailed information about matched procedures"
    )
    insurance_carrier: Optional[str] = Field(None, description="Extracted insurance carrier")
    plan_type: Optional[str] = Field(None, description="Insurance plan type (PPO/HMO/etc)")
    location: Optional[str] = Field(None, description="Extracted location (ZIP or city)")
    intent: str = Field(..., description="User intent (cost_estimate/compare_providers/find_cheapest)")
    confidence: float = Field(..., description="Overall confidence score (0-1)", ge=0, le=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "How much for a knee MRI with Blue Cross PPO in Joplin?",
                "procedure_name": "MRI knee",
                "cpt_codes": ["73721", "73722"],
                "matched_procedures": [
                    {
                        "cpt_code": "73721",
                        "description": "MRI ARTHROGRAM KNEE",
                        "match_score": 0.95
                    }
                ],
                "insurance_carrier": "Blue Cross",
                "plan_type": "PPO",
                "location": "Joplin",
                "intent": "cost_estimate",
                "confidence": 0.95
            }
        }


class ProviderPrice(BaseModel):
    """Price information from database"""
    provider_name: str
    cpt_code: str
    procedure_description: str
    payer_name: Optional[str] = None
    negotiated_rate: Optional[float] = None
    standard_charge: Optional[float] = None


class PriceQueryResponse(BaseModel):
    """Response with query understanding and actual prices"""
    query_understanding: QueryResponse
    prices: List[ProviderPrice]
    total_results: int


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    database_connected: bool = Field(..., description="Database connection status")
    llm_available: bool = Field(..., description="LLM service availability")
