"""
Query Understanding Agent (LLM #1) - Real-time
Parses natural language queries and maps them to structured data for database lookup
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from database.schema import Procedure


class QueryUnderstandingAgent:
    """
    Real-time LLM agent that interprets user queries about healthcare costs
    """
    
    def __init__(self, llm_client, db_session: Session):
        """
        Initialize the query understanding agent
        
        Args:
            llm_client: LLM client (OpenRouterLLM or MockLLM)
            db_session: Database session for CPT code lookups
        """
        self.llm = llm_client
        self.db_session = db_session
        
    def parse_query(self, user_query: str) -> Dict:
        """
        Parse natural language into structured query
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            {
                "procedure_name": str,  # e.g., "MRI knee"
                "cpt_codes": list,  # e.g., ["73721"]
                "insurance_carrier": str or None,  # e.g., "Blue Cross Blue Shield"
                "plan_type": str or None,  # e.g., "PPO"
                "location": str or None,  # e.g., "64801" or "Joplin"
                "intent": str,  # "cost_estimate", "compare_providers", "find_cheapest"
                "confidence": float  # 0-1 score
            }
        """
        
        # Step 1: LLM extracts structured intent
        structured_data = self._extract_intent(user_query)
        
        # Step 2: Map procedure to CPT code using database
        cpt_codes, matching_procedures = self._map_procedure_to_cpt(
            structured_data.get("procedure_name", "")
        )
        
        # Step 3: Calculate confidence score
        confidence = self._calculate_confidence(structured_data, cpt_codes)
        
        return {
            **structured_data,
            "cpt_codes": cpt_codes,
            "matched_procedures": matching_procedures,
            "confidence": confidence
        }
    
    def _extract_intent(self, user_query: str) -> Dict:
        """
        Use LLM to extract structured intent from natural language
        """
        prompt = f"""Extract healthcare cost query details from user input.

User query: "{user_query}"

Return ONLY a valid JSON object with these fields:
- procedure_name: medical procedure mentioned (e.g., "MRI knee", "CT scan brain")
- insurance_carrier: insurance company if mentioned (e.g., "Blue Cross", "Aetna", "Medicare")
- plan_type: PPO/HMO/EPO/POS if mentioned
- location: ZIP code or city if mentioned (e.g., "64801", "Joplin")
- intent: what user wants - one of: "cost_estimate", "compare_providers", "find_cheapest"

Rules:
- Be precise. If something isn't clearly mentioned, use null
- For procedure_name, extract the medical procedure even if described colloquially
- Return ONLY the JSON, no other text

Example responses:
{{"procedure_name": "MRI knee", "insurance_carrier": "Blue Cross", "plan_type": "PPO", "location": "Joplin", "intent": "cost_estimate"}}
{{"procedure_name": "CT scan", "insurance_carrier": null, "plan_type": null, "location": "64801", "intent": "find_cheapest"}}
"""
        
        response = self.llm.complete(prompt, temperature=0.1)
        
        # Parse JSON response
        try:
            # Clean response - sometimes LLM adds markdown
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
            
            structured_data = json.loads(clean_response)
            return structured_data
        except json.JSONDecodeError as e:
            # Fallback: return basic structure
            return {
                "procedure_name": user_query,
                "insurance_carrier": None,
                "plan_type": None,
                "location": None,
                "intent": "cost_estimate"
            }
    
    def _map_procedure_to_cpt(self, procedure_name: str) -> Tuple[List[str], List[Dict]]:
        """
        Map procedure description to CPT codes using database + LLM
        
        Returns:
            Tuple of (cpt_codes, matched_procedures)
        """
        if not procedure_name:
            return [], []
        
        # Step 1: Try database search first (fast)
        db_matches = self._search_procedures_in_db(procedure_name)
        
        if db_matches:
            cpt_codes = [match["cpt_code"] for match in db_matches[:3]]
            return cpt_codes, db_matches[:3]
        
        # Step 2: Use LLM to find CPT codes + then validate against DB
        llm_suggested_cpts = self._llm_suggest_cpt_codes(procedure_name)
        
        if llm_suggested_cpts:
            # Validate these CPT codes exist in our database
            validated_matches = []
            for cpt in llm_suggested_cpts:
                proc = self.db_session.query(Procedure).filter(
                    Procedure.cpt_code == cpt
                ).first()
                if proc:
                    validated_matches.append({
                        "cpt_code": proc.cpt_code,
                        "description": proc.description,
                        "match_score": 0.8  # LLM suggested match
                    })
            
            if validated_matches:
                cpt_codes = [m["cpt_code"] for m in validated_matches]
                return cpt_codes, validated_matches
        
        # Step 3: Fallback - use LLM to search descriptions
        return self._llm_semantic_search(procedure_name)
    
    def _search_procedures_in_db(self, procedure_name: str) -> List[Dict]:
        """
        Search for procedures in database using fuzzy text matching
        """
        search_term = f"%{procedure_name}%"
        
        # Search in description
        procedures = self.db_session.query(Procedure).filter(
            Procedure.description.ilike(search_term)
        ).limit(10).all()
        
        matches = []
        for proc in procedures:
            # Simple matching score based on keyword overlap
            score = self._calculate_text_similarity(
                procedure_name.lower(),
                proc.description.lower()
            )
            matches.append({
                "cpt_code": proc.cpt_code,
                "description": proc.description,
                "match_score": score
            })
        
        # Sort by score
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches
    
    def _calculate_text_similarity(self, query: str, text: str) -> float:
        """
        Simple keyword-based similarity score
        """
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        if not query_words:
            return 0.0
        
        # Calculate overlap
        overlap = query_words.intersection(text_words)
        score = len(overlap) / len(query_words)
        
        # Bonus for exact phrase match
        if query.lower() in text.lower():
            score = min(1.0, score + 0.3)
        
        return score
    
    def _llm_suggest_cpt_codes(self, procedure_name: str) -> List[str]:
        """
        Ask LLM to suggest CPT codes for a procedure
        """
        prompt = f"""What are the most common CPT codes for this medical procedure: "{procedure_name}"?

Return ONLY a JSON array of CPT codes (5-digit codes or 5-character alphanumeric HCPCS codes).
Return up to 3 codes.
Be precise - only suggest codes that actually exist.

Format: ["12345", "67890", "A1234"]

If you're not sure, return an empty array: []
"""
        
        response = self.llm.complete(prompt, temperature=0)
        
        try:
            # Clean response
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:].strip()
            
            codes = json.loads(clean_response)
            
            # Validate format (5 digits or 5 alphanumeric)
            valid_codes = []
            for code in codes:
                if isinstance(code, str) and len(code) == 5:
                    valid_codes.append(code)
            
            return valid_codes
        except:
            return []
    
    def _llm_semantic_search(self, procedure_name: str) -> Tuple[List[str], List[Dict]]:
        """
        Use LLM to semantically match procedure to database entries
        """
        # Get sample procedures from database
        sample_procedures = self.db_session.query(Procedure).limit(100).all()
        
        # Build a list of descriptions
        procedure_list = []
        for i, proc in enumerate(sample_procedures):
            procedure_list.append(f"{proc.cpt_code}: {proc.description}")
            if i >= 50:  # Limit to avoid token limits
                break
        
        procedures_text = "\n".join(procedure_list[:30])
        
        prompt = f"""Given this query: "{procedure_name}"

Find the best matching procedure(s) from this list:
{procedures_text}

Return ONLY a JSON array of CPT codes that best match the query.
Return up to 3 best matches.
Format: ["12345", "67890"]

If no good match, return empty array: []
"""
        
        response = self.llm.complete(prompt, temperature=0)
        
        try:
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:].strip()
            
            codes = json.loads(clean_response)
            
            # Get full details for these codes
            matches = []
            for cpt in codes:
                proc = self.db_session.query(Procedure).filter(
                    Procedure.cpt_code == cpt
                ).first()
                if proc:
                    matches.append({
                        "cpt_code": proc.cpt_code,
                        "description": proc.description,
                        "match_score": 0.7
                    })
            
            cpt_codes = [m["cpt_code"] for m in matches]
            return cpt_codes, matches
        except:
            return [], []
    
    def _calculate_confidence(self, structured_data: Dict, cpt_codes: List[str]) -> float:
        """
        Calculate confidence score for the parsed query
        """
        confidence = 0.5  # Base confidence
        
        # Boost for having procedure name
        if structured_data.get("procedure_name"):
            confidence += 0.2
        
        # Boost for finding CPT codes
        if cpt_codes:
            confidence += 0.2
        
        # Boost for having insurance info
        if structured_data.get("insurance_carrier"):
            confidence += 0.05
        
        # Boost for having location
        if structured_data.get("location"):
            confidence += 0.05
        
        return min(1.0, confidence)
