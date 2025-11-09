"""
FastAPI Application - Healthcare Price Transparency API Gateway
Includes Query Understanding Agent endpoint
"""

import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from app.schemas.query import QueryRequest, QueryResponse, HealthCheckResponse, ProcedureMatch, ProviderPrice, PriceQueryResponse
from agents.query_understanding_agent import QueryUnderstandingAgent
from agents.openrouter_llm import OpenRouterLLM
from agents.mock_llm import MockLLM
from database.connection import get_db_manager
from database.schema import PriceTransparency, Provider, Procedure
from sqlalchemy import func

# Initialize FastAPI app
app = FastAPI(
    title="Healthcare Price Transparency API",
    description="API Gateway with Query Understanding Agent for healthcare cost queries",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database manager
db_manager = get_db_manager()

# Initialize LLM client
def get_llm_client():
    """Get LLM client (OpenRouter or Mock)"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if api_key:
        return OpenRouterLLM(api_key=api_key)
    else:
        print("⚠️  No OPENROUTER_API_KEY found, using MockLLM for development")
        return MockLLM()

llm_client = get_llm_client()


# Dependency to get database session
def get_db():
    """Dependency for database session"""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "message": "Healthcare Price Transparency API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "parse_query": "/api/query/parse",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_connected = True
    except:
        db_connected = False
    
    # Check LLM availability
    llm_available = llm_client is not None
    
    status = "healthy" if (db_connected and llm_available) else "degraded"
    
    return HealthCheckResponse(
        status=status,
        database_connected=db_connected,
        llm_available=llm_available
    )


@app.post("/api/query/parse", response_model=QueryResponse)
async def parse_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Parse natural language query using Query Understanding Agent
    
    This endpoint:
    1. Extracts procedure, insurance, and location from natural language
    2. Maps procedure to CPT codes using database + LLM
    3. Returns structured data for cost estimation
    
    Example queries:
    - "How much for a knee MRI with Blue Cross PPO in Joplin?"
    - "What's the cost of a CT scan with Medicare?"
    - "Find cheapest colonoscopy near 64801"
    """
    try:
        # Initialize Query Understanding Agent
        agent = QueryUnderstandingAgent(llm_client, db)
        
        # Parse the query
        result = agent.parse_query(request.query)
        
        # Convert matched_procedures to ProcedureMatch objects
        matched_procedures = [
            ProcedureMatch(**proc) for proc in result.get("matched_procedures", [])
        ]
        
        # Build response
        response = QueryResponse(
            user_query=request.query,
            procedure_name=result.get("procedure_name"),
            cpt_codes=result.get("cpt_codes", []),
            matched_procedures=matched_procedures,
            insurance_carrier=result.get("insurance_carrier"),
            plan_type=result.get("plan_type"),
            location=result.get("location"),
            intent=result.get("intent", "cost_estimate"),
            confidence=result.get("confidence", 0.5)
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing query: {str(e)}"
        )


@app.post("/api/query/prices", response_model=PriceQueryResponse)
async def get_prices(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Get actual prices from database for the query
    
    This endpoint:
    1. Parses the query using the Query Understanding Agent
    2. Retrieves REAL pricing data from the database
    3. Returns query understanding + actual prices
    """
    try:
        # Initialize Query Understanding Agent
        agent = QueryUnderstandingAgent(llm_client, db)
        
        # Parse the query
        result = agent.parse_query(request.query)
        
        # Convert matched_procedures to ProcedureMatch objects
        matched_procedures = [
            ProcedureMatch(**proc) for proc in result.get("matched_procedures", [])
        ]
        
        # Build query understanding response
        query_understanding = QueryResponse(
            user_query=request.query,
            procedure_name=result.get("procedure_name"),
            cpt_codes=result.get("cpt_codes", []),
            matched_procedures=matched_procedures,
            insurance_carrier=result.get("insurance_carrier"),
            plan_type=result.get("plan_type"),
            location=result.get("location"),
            intent=result.get("intent", "cost_estimate"),
            confidence=result.get("confidence", 0.5)
        )
        
        # Get actual prices from database - calculate averages per CPT code
        prices = []
        cpt_codes = result.get("cpt_codes", [])
        
        if cpt_codes:
            # Query and calculate average prices per CPT code
            for cpt_code in cpt_codes:
                # Get average negotiated rate and standard charge per CPT code
                avg_prices = db.query(
                    PriceTransparency.cpt_code,
                    Procedure.description,
                    func.avg(PriceTransparency.negotiated_rate).label('avg_negotiated'),
                    func.avg(PriceTransparency.standard_charge).label('avg_standard'),
                    func.min(PriceTransparency.negotiated_rate).label('min_negotiated'),
                    func.max(PriceTransparency.negotiated_rate).label('max_negotiated'),
                    func.count(PriceTransparency.id).label('record_count')
                ).join(
                    Procedure, PriceTransparency.cpt_code == Procedure.cpt_code
                ).filter(
                    PriceTransparency.cpt_code == cpt_code,
                    PriceTransparency.negotiated_rate.isnot(None)
                ).group_by(
                    PriceTransparency.cpt_code,
                    Procedure.description
                ).first()
                
                if avg_prices:
                    # Only show range if min != max
                    payer_info = None
                    if avg_prices[4] and avg_prices[5]:
                        if avg_prices[4] == avg_prices[5]:
                            payer_info = None  # Don't show range when min == max
                        else:
                            payer_info = f"Range: ${avg_prices[4]:.2f} - ${avg_prices[5]:.2f}"
                    
                    prices.append(ProviderPrice(
                        provider_name=f"Average across {avg_prices[6]} providers",
                        cpt_code=avg_prices[0],
                        procedure_description=avg_prices[1],
                        payer_name=payer_info,
                        negotiated_rate=float(avg_prices[2]) if avg_prices[2] else None,
                        standard_charge=float(avg_prices[3]) if avg_prices[3] else None
                    ))
        
        return PriceQueryResponse(
            query_understanding=query_understanding,
            prices=prices,
            total_results=len(prices)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting prices: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
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
