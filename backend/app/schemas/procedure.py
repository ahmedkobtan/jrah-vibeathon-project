"""
Procedure response models.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProcedureSummary(BaseModel):
    """
    Summary details about a procedure.
    """

    cpt_code: str
    description: str
    category: Optional[str] = None
    medicare_rate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

