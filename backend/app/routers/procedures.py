"""
Procedure-related API endpoints.
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import ProcedureSummary
from database import Procedure
from agents.query_understanding_agent import QueryUnderstandingAgent
from agents.openrouter_llm import OpenRouterLLMClient

router = APIRouter()


def get_llm_client():
    """Get LLM client for Query Understanding Agent"""
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    return OpenRouterLLMClient(api_key=api_key)


@router.get("/", response_model=List[ProcedureSummary])
def list_procedures(
    q: Optional[str] = Query(None, description="Search query for CPT code or description"),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of procedures to return"),
    db: Session = Depends(get_db),
) -> List[ProcedureSummary]:
    """
    Return all procedures, optionally filtered by search query.
    Prioritizes actual medical procedures (5-digit CPT codes) over medications (NDC codes).
    """
    query = db.query(Procedure)

    if q:
        # Search in both CPT code and description
        search_pattern = f"%{q}%"
        query = query.filter(
            (Procedure.cpt_code.ilike(search_pattern)) | 
            (Procedure.description.ilike(search_pattern))
        )
    else:
        # When no search query, only show actual medical procedures (5-digit CPT codes)
        # Filter out medications (NDC codes which are 11+ digits)
        # Use GLOB for pattern matching in SQLite
        query = query.filter(
            Procedure.cpt_code.op('GLOB')('[0-9][0-9][0-9][0-9][0-9]')
        )

    # Prioritize procedures with categories (common procedures) first, then by CPT code
    from sqlalchemy import case
    procedures = query.order_by(
        case(
            (Procedure.category.isnot(None), 0),
            else_=1
        ),
        Procedure.cpt_code.asc()
    ).limit(limit).all()
    return [ProcedureSummary.model_validate(procedure) for procedure in procedures]


@router.get("/smart-search", response_model=List[ProcedureSummary])
def smart_search_procedures(
    q: str = Query(..., description="Natural language query (e.g., 'knee MRI', 'chest x-ray')"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db),
) -> List[ProcedureSummary]:
    """
    AI-powered procedure search using Query Understanding Agent.
    
    Uses LLM to understand natural language and match to procedure descriptions in database.
    Examples:
    - "knee MRI" → finds MRI procedures for knee
    - "chest x-ray" → finds chest x-ray procedures  
    - "colonoscopy" → finds colonoscopy procedures
    """
    try:
        llm_client = get_llm_client()
        agent = QueryUnderstandingAgent(llm_client, db)
        
        # Use agent to search
        results = agent.search_procedures(q, limit)
        
        # Convert to ProcedureSummary format
        procedures = []
        for result in results:
            # First try to get from database
            proc = db.query(Procedure).filter(
                Procedure.cpt_code == result["cpt_code"]
            ).first()
            
            if proc:
                # Procedure exists in database
                procedures.append(ProcedureSummary.model_validate(proc))
            else:
                # Procedure from web search - create summary directly from result
                procedures.append(ProcedureSummary(
                    cpt_code=result["cpt_code"],
                    description=result["description"],
                    category=result.get("category", "Web Search Result"),
                    medicare_rate=result.get("medicare_rate")
                ))
        
        return procedures
        
    except Exception as e:
        print(f"Smart search error: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to regular search on error
        return list_procedures(q=q, limit=limit, db=db)


@router.get("/{cpt_code}", response_model=ProcedureSummary)
def get_procedure(
    cpt_code: str,
    db: Session = Depends(get_db),
) -> ProcedureSummary:
    """
    Retrieve a single procedure by CPT code.
    """
    from fastapi import HTTPException
    
    procedure = db.query(Procedure).filter(Procedure.cpt_code == cpt_code).first()

    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")

    return ProcedureSummary.model_validate(procedure)
