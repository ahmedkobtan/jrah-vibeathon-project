"""
Anthropic Claude LLM Client
Production-ready LLM integration
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AnthropicLLMClient:
    """
    Anthropic Claude LLM client for production use
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307"):
        """
        Initialize Anthropic client
        
        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            model: Model to use (claude-3-haiku, claude-3-sonnet, claude-3-opus)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        self.call_count = 0
        
        if not self.api_key:
            logger.warning("No Anthropic API key found. Using mock mode.")
            self.mock_mode = True
        else:
            self.mock_mode = False
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"Anthropic client initialized with model: {self.model}")
            except ImportError:
                logger.error("anthropic package not installed. Run: pip install anthropic")
                self.mock_mode = True
    
    def complete(self, prompt: str, temperature: float = 0.1, max_tokens: int = 1024) -> str:
        """
        Get completion from Claude
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response string
        """
        self.call_count += 1
        
        if self.mock_mode:
            logger.warning("Running in mock mode - using fallback responses")
            return self._mock_response(prompt)
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response = message.content[0].text
            logger.debug(f"LLM call #{self.call_count}: {len(response)} chars returned")
            return response
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            logger.warning("Falling back to heuristic response")
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """Fallback responses when API unavailable"""
        # Import mock LLM for fallback
        from .mock_llm import MockLLMClient
        return MockLLMClient().complete(prompt)
