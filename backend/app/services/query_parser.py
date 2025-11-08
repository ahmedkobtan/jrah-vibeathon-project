from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..schemas.query import QueryParseResponse
from ...llm import LLMClient, MockLLMClient


DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "query_understanding_v1.txt"
ZIP_PATTERN = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


@dataclass
class QueryParserConfig:
    prompt_path: Path = DEFAULT_PROMPT_PATH


class QueryParser:
    """Encapsulates LLM-powered query understanding with deterministic fallback."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: QueryParserConfig = QueryParserConfig(),
    ) -> None:
        self._llm = llm_client or MockLLMClient()
        self._prompt = config.prompt_path.read_text(encoding="utf-8")

    async def parse(self, query: str) -> QueryParseResponse:
        if not query:
            return QueryParseResponse()

        prompt = f"{self._prompt}\nInput: \"{query}\""
        try:
            payload = await self._llm.complete_json(prompt)
        except Exception:
            payload = self._fallback(query)

        payload.setdefault("confidence", 0.0)
        return QueryParseResponse(**payload)

    def _fallback(self, query: str) -> Dict[str, Any]:
        """Very small rule-based backup when LLM is unavailable."""

        data: Dict[str, Any] = {
            "procedure": query,
            "cpt_code": "",
            "insurance": "",
            "location": "",
            "confidence": 0.1,
        }

        zip_match = ZIP_PATTERN.search(query)
        if zip_match:
            data["location"] = zip_match.group(1)
            data["confidence"] = 0.2

        return data
