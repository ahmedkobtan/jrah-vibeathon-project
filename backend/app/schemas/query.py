from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming payload from widget for natural-language parsing."""

    query: str = Field(..., description="Natural language cost question from the user")


class QueryParseResponse(BaseModel):
    """Structured interpretation returned by the Query Understanding agent."""

    procedure: str = Field("", description="Normalized procedure name")
    cpt_code: str = Field("", description="Primary CPT code if identified")
    insurance: str = Field("", description="Standardized insurance carrier or plan name")
    location: str = Field("", description="ZIP code or state extracted from the query")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Model confidence that the parsing is correct",
    )
