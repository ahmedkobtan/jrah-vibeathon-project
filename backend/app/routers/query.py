from fastapi import APIRouter

from ..schemas import QueryParseResponse, QueryRequest
from ..services.query_parser import QueryParser

router = APIRouter(prefix="", tags=["query"])

_parser = QueryParser()


@router.post("/parse-query", response_model=QueryParseResponse)
async def parse_query(payload: QueryRequest) -> QueryParseResponse:
    """Parse a natural language healthcare price query into structured fields."""

    return await _parser.parse(payload.query)
