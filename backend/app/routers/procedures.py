"""
Procedure-related endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas import ProcedureSummary
from database import Procedure

router = APIRouter()


@router.get("/", response_model=List[ProcedureSummary])
def list_procedures(
    q: Optional[str] = Query(None, description="Search term for CPT code or description"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[ProcedureSummary]:
    """
    List procedures, optionally filtered by a search term.
    """
    query = db.query(Procedure)

    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            or_(
                Procedure.cpt_code.ilike(like_pattern),
                Procedure.description.ilike(like_pattern),
            )
        )

    procedures = query.order_by(Procedure.cpt_code.asc()).limit(limit).all()
    return [ProcedureSummary.model_validate(proc) for proc in procedures]


@router.get("/{cpt_code}", response_model=ProcedureSummary)
def get_procedure(
    cpt_code: str,
    db: Session = Depends(get_db),
) -> ProcedureSummary:
    """
    Retrieve a single procedure by CPT code.
    """
    procedure = (
        db.query(Procedure)
        .filter(Procedure.cpt_code == cpt_code)
        .first()
    )

    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")

    return ProcedureSummary.model_validate(procedure)

