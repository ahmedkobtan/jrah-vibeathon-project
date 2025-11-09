"""
OpenRouter LLM Client
Uses OpenRouter API to access multiple LLM providers
"""

import os
import json
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class OpenRouterLLMClient:
    """
    OpenRouter LLM client for production use
    Provides access to multiple LLM providers through a single API
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "anthropic/claude-3.5-sonnet"
    ):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
            model: Model to use. Best options for this use case:
                - anthropic/claude-3.5-sonnet (recommended - best reasoning)
                - openai/gpt-4-turbo (excellent alternative)
                - google/gemini-pro-1.5 (good for structured tasks)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.call_count = 0
        
        if not self.api_key:
            logger.warning("No OpenRouter API key found. Using mock mode.")
            self.mock_mode = True
        else:
            self.mock_mode = False
            logger.info(f"OpenRouter client initialized with model: {self.model}")
    
    def complete(
        self, 
        prompt: str, 
        temperature: float = 0.1, 
        max_tokens: int = 1024
    ) -> str:
        """
        Get completion from OpenRouter
        
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/healthcare-transparency",
                "X-Title": "Healthcare Price Transparency Parser",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract response text
            response_text = result['choices'][0]['message']['content']
            
            logger.debug(f"LLM call #{self.call_count}: {len(response_text)} chars returned")
            logger.info(f"Model used: {result.get('model', self.model)}")
            
            return response_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            logger.warning("Falling back to heuristic response")
            return self._mock_response(prompt)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.warning("Falling back to heuristic response")
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """Fallback responses when API unavailable"""
        from .mock_llm import MockLLMClient
        return MockLLMClient().complete(prompt)
    
    def get_available_models(self) -> list:
        """
        Get list of available models from OpenRouter
        
        Returns:
            List of model dictionaries
        """
        if self.mock_mode:
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            
            response.raise_for_status()
            models = response.json()
            
            return models.get('data', [])
            
        except Exception as e:
            logger.error(f"Failed to fetch models: {e}")
            return []
