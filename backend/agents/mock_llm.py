"""
Mock LLM Client for testing without actual LLM API calls
"""

import json
from typing import Dict, Any


class MockLLMClient:
    """
    Mock LLM client that provides deterministic responses
    Useful for testing without API costs
    """
    
    def __init__(self):
        """Initialize mock client"""
        self.call_count = 0
    
    def complete(self, prompt: str, temperature: float = 0.1) -> str:
        """
        Mock completion that returns reasonable responses
        
        Args:
            prompt: The prompt text
            temperature: Temperature parameter (ignored in mock)
            
        Returns:
            Mocked response string
        """
        self.call_count += 1
        
        # Detect what type of request this is
        if "hospital price transparency file" in prompt and "map" in prompt.lower():
            # Schema inference request
            return self._mock_schema_inference(prompt)
        elif "CPT" in prompt and "code" in prompt:
            # CPT extraction request
            return self._mock_cpt_extraction(prompt)
        elif "insurance payer name" in prompt.lower():
            # Payer normalization request
            return self._mock_payer_normalization(prompt)
        else:
            return "Mock LLM response"
    
    def _mock_schema_inference(self, prompt: str) -> str:
        """Mock schema inference response"""
        # Return a standard schema mapping
        schema = {
            "provider_name": "hospital_name",
            "provider_npi": "npi",
            "cpt_code": "code",
            "procedure_description": "description",
            "payer_name": "payer",
            "negotiated_rate": "rate",
            "standard_charge": "gross_charge"
        }
        return json.dumps(schema)
    
    def _mock_cpt_extraction(self, prompt: str) -> str:
        """Mock CPT code extraction"""
        # Try to extract from the prompt
        import re
        match = re.search(r'\b\d{5}\b', prompt)
        if match:
            return match.group(0)
        return "null"
    
    def _mock_payer_normalization(self, prompt: str) -> str:
        """Mock payer name normalization"""
        # Simple normalization
        if "blue cross" in prompt.lower() or "bcbs" in prompt.lower():
            return "Blue Cross Blue Shield"
        elif "united" in prompt.lower():
            return "UnitedHealthcare"
        elif "aetna" in prompt.lower():
            return "Aetna"
        else:
            # Return first capitalized word as carrier name
            words = prompt.split()
            for word in words:
                if word and word[0].isupper() and len(word) > 3:
                    return word
        return "Unknown Carrier"
