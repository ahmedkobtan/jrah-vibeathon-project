"""
Query Understanding Agent - Real-time natural language to CPT code mapping
"""

import json
import re
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from database.schema import Procedure

try:
    from app.services.duckduckgo_search_client import DuckDuckGoSearchClient
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False


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
        
        # Step 3: If still no good results, try web search as fallback
        if len(combined) < 2 and DUCKDUCKGO_AVAILABLE:
            web_results = self._web_search_fallback(user_query, limit)
            combined = self._merge_results(combined, web_results, limit)
        
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
            
            # Validate format - must be 5-digit numeric string
            valid_codes = []
            for code in codes:
                if isinstance(code, str) and len(code) == 5 and code.isdigit():
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
    
    def _web_search_fallback(self, query: str, limit: int) -> List[Dict]:
        """
        Use web search to find CPT codes when database is empty.
        Tries DuckDuckGo first, then Google search as fallback.
        """
        # Try DuckDuckGo first
        results = self._duckduckgo_search(query, limit)
        
        # If DuckDuckGo returns nothing, try Google search
        if not results:
            print("DuckDuckGo returned no results, trying Google search fallback...")
            results = self._google_search(query, limit)
        
        return results
    
    def _duckduckgo_search(self, query: str, limit: int) -> List[Dict]:
        """
        Use DuckDuckGo web search to find CPT codes.
        """
        try:
            # Initialize DuckDuckGo client
            ddg_client = DuckDuckGoSearchClient()
            
            # Search for CPT code information
            search_query = f"{query} CPT code medical procedure"
            
            # Use text search to find CPT code info
            from duckduckgo_search import DDGS
            
            results = []
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    keywords=search_query,
                    region='wt-wt',
                    safesearch='moderate',
                    max_results=10
                )
                
                if search_results:
                    search_results = list(search_results)
                else:
                    search_results = []
            
            # Extract CPT codes from search results
            cpt_codes_found = set()
            text_snippets = []
            
            for result in search_results:
                title = result.get("title", "")
                snippet = result.get("body", "")
                text = f"{title} {snippet}"
                text_snippets.append(text)
                
                # Extract 5-digit codes that might be CPT codes
                potential_cpts = re.findall(r'\b(\d{5})\b', text)
                for code in potential_cpts:
                    cpt_codes_found.add(code)
            
            # Use LLM to validate and rank the found CPT codes
            if cpt_codes_found:
                cpt_list = list(cpt_codes_found)[:limit]
                
                try:
                    # Try LLM validation
                    validated_cpts = self._validate_cpts_with_llm(
                        query, 
                        cpt_list, 
                        text_snippets[:5]
                    )
                except Exception as e:
                    print(f"LLM validation failed, using basic descriptions: {e}")
                    # Fallback: create basic descriptions from query
                    validated_cpts = [(code, f"{query.title()} (CPT {code})") for code in cpt_list[:limit]]
                
                # Create results for validated CPT codes
                for cpt_code, description in validated_cpts[:limit]:
                    # Check if code exists in database
                    proc = self.db.query(Procedure).filter(
                        Procedure.cpt_code == cpt_code
                    ).first()
                    
                    if proc:
                        results.append({
                            "cpt_code": proc.cpt_code,
                            "description": proc.description,
                            "category": proc.category,
                            "medicare_rate": proc.medicare_rate,
                            "match_score": 0.6  # Web search result
                        })
                    else:
                        # CPT code not in our database, use LLM-provided description
                        results.append({
                            "cpt_code": cpt_code,
                            "description": description,
                            "category": "Web Search Result",
                            "medicare_rate": None,
                            "match_score": 0.5  # Lower score for external data
                        })
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return []
    
    def _google_search(self, query: str, limit: int) -> List[Dict]:
        """
        Use Google search to find CPT codes (fallback when DuckDuckGo fails).
        """
        try:
            from googlesearch import search
            import time
            
            search_query = f"{query} CPT code medical procedure"
            
            # Collect search results
            urls_and_snippets = []
            for url in search(search_query, num_results=10, lang='en'):
                urls_and_snippets.append(url)
                time.sleep(0.1)  # Be polite to avoid blocks
            
            # Extract CPT codes from URLs and perform targeted searches
            cpt_codes_found = set()
            text_snippets = []
            
            # Search each result URL text for CPT codes
            for url in urls_and_snippets[:10]:
                text_snippets.append(url)
                # Extract 5-digit codes from URLs
                potential_cpts = re.findall(r'\b(\d{5})\b', url)
                for code in potential_cpts:
                    cpt_codes_found.add(code)
            
            # If no codes found in URLs, do additional web searches
            if not cpt_codes_found:
                # Try more specific searches
                specific_queries = [
                    f"{query} procedure code",
                    f"CPT code for {query}",
                ]
                
                for specific_query in specific_queries:
                    try:
                        for url in search(specific_query, num_results=5, lang='en'):
                            # Extract codes from URL
                            codes = re.findall(r'\b(\d{5})\b', url)
                            cpt_codes_found.update(codes)
                            time.sleep(0.1)
                        
                        if cpt_codes_found:
                            break
                    except:
                        continue
            
            results = []
            
            # Validate and create results
            if cpt_codes_found:
                cpt_list = list(cpt_codes_found)[:limit]
                
                try:
                    # Try LLM validation
                    validated_cpts = self._validate_cpts_with_llm(
                        query,
                        cpt_list,
                        text_snippets[:5]
                    )
                except Exception as e:
                    print(f"LLM validation failed, using basic descriptions: {e}")
                    # Fallback: create basic descriptions from query
                    validated_cpts = [(code, f"{query.title()} (CPT {code})") for code in cpt_list[:limit]]
                
                # Create results for validated CPT codes
                for cpt_code, description in validated_cpts[:limit]:
                    # Check if code exists in database
                    proc = self.db.query(Procedure).filter(
                        Procedure.cpt_code == cpt_code
                    ).first()
                    
                    if proc:
                        results.append({
                            "cpt_code": proc.cpt_code,
                            "description": proc.description,
                            "category": proc.category,
                            "medicare_rate": proc.medicare_rate,
                            "match_score": 0.6  # Google search result
                        })
                    else:
                        # CPT code not in our database
                        results.append({
                            "cpt_code": cpt_code,
                            "description": description,
                            "category": "Web Search Result (Google)",
                            "medicare_rate": None,
                            "match_score": 0.5  # Lower score for external data
                        })
            
            print(f"Google search found {len(results)} CPT code results")
            return results
            
        except Exception as e:
            print(f"Google search error: {e}")
            return []
    
    def _validate_cpts_with_llm(
        self, 
        query: str, 
        cpt_codes: List[str], 
        context_snippets: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Use LLM to validate CPT codes found on the web and provide descriptions.
        
        Returns:
            List of tuples (cpt_code, description)
        """
        try:
            context = "\n".join(context_snippets[:3])
            
            prompt = f"""You are a medical coding expert. A user searched for: "{query}"

We found these potential CPT codes from web search: {cpt_codes}

Context from search results:
{context}

Task: Identify which CPT codes are most relevant for "{query}" and provide a brief description for each.

Return ONLY a JSON array of objects with this format:
[
  {{"cpt_code": "12345", "description": "Brief procedure description"}},
  {{"cpt_code": "67890", "description": "Another procedure description"}}
]

Only include CPT codes that are truly relevant. Maximum 3 codes.
"""
            
            response = self.llm.complete(prompt, temperature=0.2)
            
            # Parse response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()
            
            parsed = json.loads(response)
            
            # Extract (code, description) tuples
            result = []
            for item in parsed:
                if isinstance(item, dict) and "cpt_code" in item and "description" in item:
                    code = str(item["cpt_code"])
                    desc = str(item["description"])
                    if len(code) == 5 and code.isdigit():
                        result.append((code, desc))
            
            return result
            
        except Exception as e:
            print(f"LLM validation error: {e}")
            # Return first few codes with generic descriptions as fallback
            return [(code, f"Procedure related to {query}") for code in cpt_codes[:3]]
    
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
