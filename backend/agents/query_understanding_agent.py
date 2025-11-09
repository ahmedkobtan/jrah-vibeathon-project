"""
Query Understanding Agent - Real-time natural language to CPT code mapping
"""

import json
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from database.schema import Procedure


class QueryUnderstandingAgent:
    """
    Interprets natural language procedure queries and maps to CPT codes
    using LLM + database search
    """
    
    def __init__(self, llm_client, db_session: Session):
        self.llm = llm_client
        self.db = db_session
        
    def search_procedures(self, user_query: str, limit: int = 10) -> List[Dict]:
        """
        Main entry point: Search for procedures using natural language
        
        Args:
            user_query: Natural language query (e.g., "knee MRI", "x-ray chest")
            limit: Max results to return
            
        Returns:
            List of dicts with cpt_code, description, match_score
        """
        # Step 1: Database fuzzy search (fast, most common case)
        db_matches = self._database_search(user_query, limit)
        
        if db_matches and len(db_matches) >= 3:
            # Good matches found, return them
            return db_matches[:limit]
        
        # Step 2: LLM-enhanced search for better understanding
        llm_enhanced = self._llm_enhanced_search(user_query, limit)
        
        # Combine and deduplicate
        combined = self._merge_results(db_matches, llm_enhanced, limit)
        
        return combined[:limit]
    
    def _database_search(self, query: str, limit: int) -> List[Dict]:
        """Fast database fuzzy text search"""
        search_term = f"%{query}%"
        
        procedures = self.db.query(Procedure).filter(
            Procedure.description.ilike(search_term)
        ).limit(limit * 2).all()  # Get extra for scoring
        
        matches = []
        for proc in procedures:
            score = self._calculate_match_score(query, proc.description)
            matches.append({
                "cpt_code": proc.cpt_code,
                "description": proc.description,
                "category": proc.category,
                "medicare_rate": proc.medicare_rate,
                "match_score": score
            })
        
        # Sort by score
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches
    
    def _llm_enhanced_search(self, query: str, limit: int) -> List[Dict]:
        """Use LLM to understand query and suggest CPT codes"""
        try:
            # Get sample procedures for context
            sample_procs = self.db.query(Procedure).limit(50).all()
            proc_context = "\n".join([
                f"{p.cpt_code}: {p.description[:80]}"
                for p in sample_procs[:30]
            ])
            
            prompt = f"""You are a medical coding assistant. Given a user's natural language query about a medical procedure, find the most relevant CPT codes from the database.

User query: "{query}"

Sample procedures in database:
{proc_context}

Task: Return ONLY a JSON array of CPT codes (up to 5) that best match this query. Be precise.

Format: ["12345", "67890", "11111"]

If unsure, return fewer codes rather than guessing.
"""
            
            response = self.llm.complete(prompt, temperature=0.1)
            
            # Parse LLM response
            cpt_codes = self._parse_cpt_codes(response)
            
            # Fetch full details for these CPT codes
            matches = []
            for cpt in cpt_codes:
                proc = self.db.query(Procedure).filter(
                    Procedure.cpt_code == cpt
                ).first()
                if proc:
                    matches.append({
                        "cpt_code": proc.cpt_code,
                        "description": proc.description,
                        "category": proc.category,
                        "medicare_rate": proc.medicare_rate,
                        "match_score": 0.8  # LLM suggested
                    })
            
            return matches
            
        except Exception as e:
            print(f"LLM search error: {e}")
            return []
    
    def _parse_cpt_codes(self, llm_response: str) -> List[str]:
        """Extract CPT codes from LLM response"""
        try:
            # Clean response
            response = llm_response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()
            
            codes = json.loads(response)
            
            # Validate format
            valid_codes = []
            for code in codes:
                if isinstance(code, str) and len(code) == 5:
                    valid_codes.append(code)
            
            return valid_codes
        except:
            return []
    
    def _calculate_match_score(self, query: str, description: str) -> float:
        """Calculate similarity score between query and description"""
        query_lower = query.lower()
        desc_lower = description.lower()
        
        # Exact phrase match
        if query_lower in desc_lower:
            return 1.0
        
        # Word overlap
        query_words = set(query_lower.split())
        desc_words = set(desc_lower.split())
        
        if not query_words:
            return 0.0
        
        overlap = query_words.intersection(desc_words)
        score = len(overlap) / len(query_words)
        
        # Boost for word order matching
        if all(word in desc_lower for word in query_words):
            score += 0.2
        
        return min(1.0, score)
    
    def _merge_results(self, db_results: List[Dict], llm_results: List[Dict], limit: int) -> List[Dict]:
        """Combine and deduplicate results"""
        seen_cpts = set()
        merged = []
        
        # Add DB results first (usually more accurate)
        for result in db_results:
            if result["cpt_code"] not in seen_cpts:
                seen_cpts.add(result["cpt_code"])
                merged.append(result)
        
        # Add LLM results that aren't duplicates
        for result in llm_results:
            if result["cpt_code"] not in seen_cpts:
                seen_cpts.add(result["cpt_code"])
                merged.append(result)
        
        return merged[:limit]
