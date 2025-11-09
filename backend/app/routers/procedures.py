"""
Procedure-related API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import ProcedureSummary
from database import Procedure

router = APIRouter()


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

    procedures = query.order_by(Procedure.cpt_code.asc()).limit(limit).all()
    return [ProcedureSummary.model_validate(procedure) for procedure in procedures]


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
