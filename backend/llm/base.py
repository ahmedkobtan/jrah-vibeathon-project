from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMClient(ABC):
    """Abstract base class for all LLM providers used in the gateway."""

    @abstractmethod
    async def complete(self, prompt: str, **kwargs: Any) -> str:
        """Return the raw text completion from the underlying provider."""

    async def complete_json(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Helper that expects the LLM to emit JSON and parses the payload."""
        import json

        raw = await self.complete(prompt, **kwargs)
        return json.loads(raw)
