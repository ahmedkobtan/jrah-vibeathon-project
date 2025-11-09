"""
Integration tests for Query Understanding Agent with real OpenRouter LLM
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agents.query_understanding_agent import QueryUnderstandingAgent
from agents.openrouter_llm import OpenRouterLLMClient
from database.schema import Base, Procedure


@pytest.fixture(scope="module")
def test_db():
    """Create a test database with sample procedures"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add sample procedures
    sample_procedures = [
        Procedure(cpt_code="70553", description="MRI, Brain with and without Contrast", category="Radiology", medicare_rate=1800.0),
        Procedure(cpt_code="73721", description="MRI, Lower Extremity without Contrast", category="Radiology", medicare_rate=1400.0),
        Procedure(cpt_code="45378", description="Colonoscopy", category="Gastroenterology", medicare_rate=3200.0),
        Procedure(cpt_code="29881", description="Knee Arthroscopy", category="Orthopedic Surgery", medicare_rate=4500.0),
    ]
    
    for proc in sample_procedures:
        session.add(proc)
    session.commit()
    
    yield session
    
    session.close()


@pytest.fixture(scope="module")
def real_llm():
    """Create real OpenRouter LLM client"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return OpenRouterLLMClient(api_key=api_key)


@pytest.fixture
def query_agent(real_llm, test_db):
    """Create Query Understanding Agent with real LLM"""
    return QueryUnderstandingAgent(real_llm, test_db)


class TestQueryUnderstandingAgentIntegration:
    """Integration tests with real OpenRouter LLM"""
    
    def test_search_existing_procedure_mri(self, query_agent):
        """Test searching for MRI procedures that exist in database"""
        results = query_agent.search_procedures("MRI brain", limit=5)
        
        assert len(results) > 0
        assert any("70553" in r["cpt_code"] for r in results)
        assert any("brain" in r["description"].lower() for r in results)
    
    def test_search_existing_procedure_colonoscopy(self, query_agent):
        """Test searching for colonoscopy that exists in database"""
        results = query_agent.search_procedures("colonoscopy", limit=5)
        
        assert len(results) > 0
        assert any("45378" in r["cpt_code"] for r in results)
        assert any("colonoscopy" in r["description"].lower() for r in results)
    
    def test_search_with_natural_language(self, query_agent):
        """Test natural language query understanding"""
        results = query_agent.search_procedures("knee surgery", limit=5)
        
        assert len(results) > 0
        # Should find knee arthroscopy
        assert any("knee" in r["description"].lower() for r in results)
    
    @pytest.mark.slow
    def test_web_search_fallback_rare_procedure(self, query_agent):
        """Test web search fallback for procedure not in database"""
        # This procedure likely won't be in our test database
        results = query_agent.search_procedures("cardiac stress test", limit=5)
        
        # Should return something (either from database similar matches or web search)
        assert isinstance(results, list)
        # If web search worked, should have results
        if len(results) > 0:
            assert all("cpt_code" in r for r in results)
            assert all("description" in r for r in results)
    
    def test_database_prioritized_over_web(self, query_agent):
        """Test that database results are prioritized over web search"""
        results = query_agent.search_procedures("MRI", limit=5)
        
        # Should get database results fast
        assert len(results) >= 2  # We have 2 MRI procedures in test database
        # Check that database results came first
        assert any("70553" in r["cpt_code"] or "73721" in r["cpt_code"] for r in results[:2])
    
    def test_match_score_calculation(self, query_agent):
        """Test that match scores are calculated correctly"""
        results = query_agent.search_procedures("MRI brain", limit=5)
        
        if len(results) > 0:
            # All results should have match scores
            assert all("match_score" in r for r in results)
            # Scores should be between 0 and 1
            assert all(0 <= r["match_score"] <= 1.0 for r in results)
            # Results should be sorted by match score (descending)
            scores = [r["match_score"] for r in results]
            assert scores == sorted(scores, reverse=True)
    
    def test_llm_enhanced_search(self, query_agent):
        """Test LLM enhancement provides relevant results"""
        results = query_agent.search_procedures("arthroscopic knee procedure", limit=5)
        
        # Should find knee arthroscopy using LLM understanding
        assert len(results) > 0
        # LLM should understand this refers to knee procedures
        knee_procedures = [r for r in results if "knee" in r["description"].lower()]
        assert len(knee_procedures) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
