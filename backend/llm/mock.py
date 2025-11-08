from __future__ import annotations

import asyncio
from typing import Any, Dict

from .base import LLMClient


class MockLLMClient(LLMClient):
    """Deterministic LLM stub for offline demos and tests."""

    def __init__(self, responses: Dict[str, Dict[str, Any]] | None = None) -> None:
        self._responses = responses or {}

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        await asyncio.sleep(0)
        payload = self._responses.get(prompt)
        if payload is None:
            # naive default response to keep flow running
            return "{\"procedure\":\"\",\"cpt_code\":\"\",\"insurance\":\"\",\"location\":\"\",\"confidence\":0.0}"
        import json

        return json.dumps(payload)
