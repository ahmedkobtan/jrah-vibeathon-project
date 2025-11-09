"""
Procedure-related response models.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProcedureSummary(BaseModel):
    """
    Summary information about a medical procedure.
    """

    cpt_code: str
    description: Optional[str] = None
    category: Optional[str] = None
    medicare_rate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
