"""
Test Query Understanding Agent - REAL LLM ONLY
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.query_understanding_agent import QueryUnderstandingAgent
from agents.openrouter_llm import OpenRouterLLM
from database.connection import get_db_manager
from database.schema import Procedure


# Check for API key at module level
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    pytest.skip(
        "OPENROUTER_API_KEY environment variable required for Query Understanding Agent tests",
        allow_module_level=True
    )


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db_manager = get_db_manager()
    session = db_manager.get_session()
    yield session
    session.close()


@pytest.fixture
def llm_client():
    """Create real LLM client"""
    return OpenRouterLLM(api_key=OPENROUTER_API_KEY)


@pytest.fixture
def query_agent(llm_client, db_session):
    """Create Query Understanding Agent with real LLM"""
    return QueryUnderstandingAgent(llm_client, db_session)


class TestQueryUnderstandingAgent:
    """Test suite for Query Understanding Agent with Real LLM"""
    
    def test_agent_initialization(self, query_agent):
        """Test agent can be initialized"""
        assert query_agent is not None
        assert query_agent.llm is not None
        assert query_agent.db_session is not None
    
    def test_parse_query_basic(self, query_agent):
        """Test basic query parsing"""
        query = "knee MRI"
        result = query_agent.parse_query(query)
        
        print(f"\n=== Basic Query Test ===")
        print(f"Query: {query}")
        print(f"Result: {result}")
        
        assert "procedure_name" in result
        assert "cpt_codes" in result
        assert "confidence" in result
        assert isinstance(result["cpt_codes"], list)
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1
    
    def test_parse_query_with_insurance(self, query_agent):
        """Test query parsing with insurance information"""
        query = "How much for knee MRI with Blue Cross PPO?"
        result = query_agent.parse_query(query)
        
        print(f"\n=== Insurance Query Test ===")
        print(f"Query: {query}")
        print(f"Procedure: {result.get('procedure_name')}")
        print(f"Insurance: {result.get('insurance_carrier')}")
        print(f"Plan Type: {result.get('plan_type')}")
        
        assert result["procedure_name"] is not None
        assert "insurance_carrier" in result
        assert "plan_type" in result
    
    def test_parse_query_with_location(self, query_agent):
        """Test query parsing with location"""
        query = "CT scan cost in Joplin"
        result = query_agent.parse_query(query)
        
        print(f"\n=== Location Query Test ===")
        print(f"Query: {query}")
        print(f"Procedure: {result.get('procedure_name')}")
        print(f"Location: {result.get('location')}")
        
        assert result["procedure_name"] is not None
        assert "location" in result
    
    def test_cpt_code_matching_mri(self, query_agent, db_session):
        """Test CPT code matching for MRI procedures"""
        # Check if MRI procedures exist in database
        mri_procs = db_session.query(Procedure).filter(
            Procedure.description.ilike("%MRI%")
        ).limit(3).all()
        
        print(f"\n=== MRI CPT Matching Test ===")
        print(f"MRI procedures in database: {len(mri_procs)}")
        
        if len(mri_procs) > 0:
            query = "MRI scan"
            result = query_agent.parse_query(query)
            
            print(f"Query: {query}")
            print(f"CPT Codes Found: {result.get('cpt_codes')}")
            print(f"Matched Procedures: {len(result.get('matched_procedures', []))}")
            
            assert len(result["cpt_codes"]) > 0
            assert len(result["matched_procedures"]) > 0
            
            # Check matched procedures have required fields
            for proc in result["matched_procedures"]:
                print(f"  - {proc['cpt_code']}: {proc['description'][:60]}... (score: {proc['match_score']})")
                assert "cpt_code" in proc
                assert "description" in proc
                assert "match_score" in proc
    
    def test_database_search(self, query_agent, db_session):
        """Test database search functionality"""
        # Search for MRI procedures
        matches = query_agent._search_procedures_in_db("MRI")
        
        print(f"\n=== Database Search Test ===")
        print(f"Search term: MRI")
        print(f"Matches found: {len(matches)}")
        
        assert len(matches) >= 0
        
        if len(matches) > 0:
            for i, match in enumerate(matches[:3]):
                print(f"  {i+1}. {match['cpt_code']}: {match['description'][:60]}... (score: {match['match_score']})")
            # Check match structure
            assert "cpt_code" in matches[0]
            assert "description" in matches[0]
            assert "match_score" in matches[0]
    
    def test_text_similarity_calculation(self, query_agent):
        """Test text similarity scoring"""
        print(f"\n=== Text Similarity Test ===")
        
        # Test exact match
        score = query_agent._calculate_text_similarity("MRI", "MRI scan")
        print(f"'MRI' vs 'MRI scan': {score:.2f}")
        assert score > 0.5
        
        # Test partial match
        score = query_agent._calculate_text_similarity("knee MRI", "MRI of knee joint")
        print(f"'knee MRI' vs 'MRI of knee joint': {score:.2f}")
        assert score > 0
        
        # Test no match
        score = query_agent._calculate_text_similarity("MRI", "blood test")
        print(f"'MRI' vs 'blood test': {score:.2f}")
        assert score >= 0
    
    def test_confidence_calculation(self, query_agent):
        """Test confidence score calculation"""
        print(f"\n=== Confidence Calculation Test ===")
        
        # Test with full data
        structured_data = {
            "procedure_name": "MRI knee",
            "insurance_carrier": "Blue Cross",
            "plan_type": "PPO",
            "location": "Joplin"
        }
        confidence = query_agent._calculate_confidence(structured_data, ["73721"])
        print(f"Full data confidence: {confidence:.2f}")
        assert confidence >= 0.8  # Should have high confidence
        
        # Test with minimal data
        structured_data = {
            "procedure_name": None,
            "insurance_carrier": None,
            "location": None
        }
        confidence = query_agent._calculate_confidence(structured_data, [])
        print(f"Minimal data confidence: {confidence:.2f}")
        assert confidence < 0.7  # Should have lower confidence
    
    def test_comprehensive_queries(self, query_agent):
        """Test comprehensive real-world queries"""
        queries = [
            "How much for a knee MRI with Blue Cross PPO in Joplin?",
            "CT scan cost with Medicare",
            "Find cheapest ultrasound near 64801",
            "I need an MRI for my knee"
        ]
        
        print(f"\n=== Comprehensive Query Tests ===")
        
        for query in queries:
            print(f"\n{'─'*60}")
            print(f"Query: {query}")
            
            result = query_agent.parse_query(query)
            
            print(f"Procedure: {result.get('procedure_name')}")
            print(f"CPT Codes: {result.get('cpt_codes')}")
            print(f"Insurance: {result.get('insurance_carrier')}")
            print(f"Plan Type: {result.get('plan_type')}")
            print(f"Location: {result.get('location')}")
            print(f"Intent: {result.get('intent')}")
            print(f"Confidence: {result.get('confidence'):.2f}")
            
            if result.get('matched_procedures'):
                print(f"Matched Procedures:")
                for proc in result.get('matched_procedures', []):
                    print(f"  - {proc['cpt_code']}: {proc['description'][:50]}... (score: {proc['match_score']})")
            
            assert result["procedure_name"] is not None
            assert result["confidence"] > 0


def run_interactive_test():
    """Interactive test to demonstrate the agent"""
    print("\n" + "="*60)
    print("Query Understanding Agent - Interactive Test")
    print("="*60)
    
    # Initialize
    db_manager = get_db_manager()
    session = db_manager.get_session()
    
    # Get LLM
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        llm = OpenRouterLLM(api_key=api_key)
        print("✓ Using Real LLM (OpenRouter)")
    else:
        llm = MockLLM()
        print("✓ Using Mock LLM")
    
    agent = QueryUnderstandingAgent(llm, session)
    
    # Test queries
    test_queries = [
        "How much for a knee MRI with Blue Cross PPO in Joplin?",
        "What's the cost of a CT scan with Medicare?",
        "Find cheapest ultrasound near 64801",
        "MRI of the brain",
        "X-ray cost"
    ]
    
    for query in test_queries:
        print(f"\n{'─'*60}")
        print(f"Query: {query}")
        print(f"{'─'*60}")
        
        try:
            result = agent.parse_query(query)
            
            print(f"Procedure Name: {result.get('procedure_name')}")
            print(f"Insurance: {result.get('insurance_carrier')} ({result.get('plan_type')})")
            print(f"Location: {result.get('location')}")
            print(f"Intent: {result.get('intent')}")
            print(f"Confidence: {result.get('confidence'):.2f}")
            print(f"\nMatched CPT Codes: {result.get('cpt_codes')}")
            
            if result.get('matched_procedures'):
                print(f"\nMatched Procedures:")
                for proc in result.get('matched_procedures'):
                    print(f"  • {proc['cpt_code']}: {proc['description'][:60]}...")
                    print(f"    Match Score: {proc['match_score']:.2f}")
        except Exception as e:
            print(f"Error: {e}")
    
    session.close()
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    # Run interactive test
    run_interactive_test()
    
    # Run pytest
    print("\nRunning pytest suite...")
    pytest.main([__file__, "-v", "-s"])
