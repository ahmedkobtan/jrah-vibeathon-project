"""
Tests for Query Understanding Agent with web search fallback
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents.query_understanding_agent import QueryUnderstandingAgent
from database.schema import Procedure


# Mock database session
@pytest.fixture
def mock_db():
    """Create a mock database session"""
    return Mock()


# Mock LLM client
@pytest.fixture
def mock_llm():
    """Create a mock LLM client"""
    llm = Mock()
    llm.complete = Mock(return_value='["12345", "67890"]')
    return llm


# Mock procedures in database
@pytest.fixture
def mock_procedures():
    """Create mock procedure objects"""
    proc1 = Mock(spec=Procedure)
    proc1.cpt_code = "70553"
    proc1.description = "MRI, Brain with and without Contrast"
    proc1.category = "Radiology"
    proc1.medicare_rate = 1800.0
    
    proc2 = Mock(spec=Procedure)
    proc2.cpt_code = "73721"
    proc2.description = "MRI, Lower Extremity without Contrast"
    proc2.category = "Radiology"
    proc2.medicare_rate = 1400.0
    
    return [proc1, proc2]


class TestQueryUnderstandingAgent:
    """Test suite for Query Understanding Agent"""
    
    def test_database_search_with_results(self, mock_db, mock_llm, mock_procedures):
        """Test that database search returns results when procedures exist"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = mock_procedures
        mock_db.query.return_value = mock_query
        
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Execute
        results = agent.search_procedures("MRI", limit=5)
        
        # Assert
        assert len(results) > 0
        assert all("cpt_code" in r for r in results)
        assert all("description" in r for r in results)
        assert all("match_score" in r for r in results)
    
    def test_database_search_empty_results(self, mock_db, mock_llm):
        """Test behavior when database has no matching procedures"""
        # Setup - empty database
        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Execute
        results = agent.search_procedures("rare procedure xyz", limit=5)
        
        # Assert - should still return something (from LLM or web search)
        # Even if empty, should not raise error
        assert isinstance(results, list)
    
    def test_llm_enhanced_search(self, mock_db, mock_llm, mock_procedures):
        """Test that LLM enhancement works"""
        # Setup
        mock_query = Mock()
        # First call (sample procedures)
        mock_query.limit.return_value.all.return_value = mock_procedures
        # Second call (filter by CPT code)
        mock_filter_query = Mock()
        mock_filter_query.first.return_value = mock_procedures[0]
        mock_query.filter.return_value = mock_filter_query
        
        mock_db.query.return_value = mock_query
        
        # Mock LLM to return valid CPT codes
        mock_llm.complete.return_value = '["70553"]'
        
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Execute
        results = agent._llm_enhanced_search("brain MRI", limit=5)
        
        # Assert
        assert len(results) > 0
        assert results[0]["cpt_code"] == "70553"
    
    def test_cpt_code_parsing(self, mock_db, mock_llm):
        """Test CPT code extraction from LLM responses"""
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Test with clean JSON
        result = agent._parse_cpt_codes('["12345", "67890"]')
        assert result == ["12345", "67890"]
        
        # Test with markdown code block
        result = agent._parse_cpt_codes('```json\n["12345"]\n```')
        assert result == ["12345"]
        
        # Test with invalid codes (should filter out non-5-digit)
        result = agent._parse_cpt_codes('["123", "12345"]')
        assert result == ["12345"]
        
        # Test that only digits are accepted (no letters)
        result = agent._parse_cpt_codes('["12345", "abcde", "1234a"]')
        assert result == ["12345"]
    
    def test_match_score_calculation(self, mock_db, mock_llm):
        """Test similarity scoring between query and description"""
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Exact match
        score = agent._calculate_match_score("MRI", "MRI Brain")
        assert score == 1.0
        
        # Partial match
        score = agent._calculate_match_score("knee surgery", "Knee Arthroscopy Surgery")
        assert score > 0.5
        
        # No match
        score = agent._calculate_match_score("MRI", "Colonoscopy")
        assert score < 0.5
    
    @patch('agents.query_understanding_agent.DUCKDUCKGO_AVAILABLE', True)
    @patch('duckduckgo_search.DDGS')
    def test_web_search_fallback(self, mock_ddgs, mock_db, mock_llm):
        """Test web search fallback when database is empty"""
        # Setup empty database
        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = []
        mock_query.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # Mock web search results
        mock_search_instance = MagicMock()
        mock_search_instance.text.return_value = [
            {
                "title": "CPT Code 99213 Office Visit",
                "body": "CPT 99213 is for office visits. Cost ranges from $100-$200.",
                "href": "https://example.com/cpt-99213"
            },
            {
                "title": "Understanding CPT Code 99214",  
                "body": "CPT code 99214 is another common code for 99214 office visits.",
                "href": "https://example.com/cpt-99214"
            }
        ]
        mock_search_instance.__enter__.return_value = mock_search_instance
        mock_search_instance.__exit__.return_value = None
        mock_ddgs.return_value = mock_search_instance
        
        # Mock LLM validation response
        mock_llm.complete.return_value = '''[
            {"cpt_code": "99213", "description": "Office Visit Level 3"},
            {"cpt_code": "99214", "description": "Office Visit Level 4"}
        ]'''
        
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Execute
        results = agent._web_search_fallback("office visit", limit=5)
        
        # Assert
        assert len(results) > 0
        # Should extract CPT codes from web search
        cpt_codes = [r["cpt_code"] for r in results]
        assert any(code in ["99213", "99214"] for code in cpt_codes)
    
    def test_cpt_validation_with_llm(self, mock_db, mock_llm):
        """Test LLM validation of CPT codes found on web"""
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Mock LLM response
        mock_llm.complete.return_value = '''[
            {"cpt_code": "12345", "description": "Test Procedure A"},
            {"cpt_code": "67890", "description": "Test Procedure B"}
        ]'''
        
        # Execute
        result = agent._validate_cpts_with_llm(
            "test query",
            ["12345", "67890", "99999"],
            ["Context snippet 1", "Context snippet 2"]
        )
        
        # Assert
        assert len(result) == 2
        assert result[0] == ("12345", "Test Procedure A")
        assert result[1] == ("67890", "Test Procedure B")
    
    def test_merge_results_deduplication(self, mock_db, mock_llm):
        """Test that merge properly deduplicates results"""
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        db_results = [
            {"cpt_code": "12345", "description": "Test A", "match_score": 0.9},
            {"cpt_code": "67890", "description": "Test B", "match_score": 0.8}
        ]
        
        llm_results = [
            {"cpt_code": "12345", "description": "Test A Duplicate", "match_score": 0.7},
            {"cpt_code": "11111", "description": "Test C", "match_score": 0.6}
        ]
        
        # Execute
        merged = agent._merge_results(db_results, llm_results, limit=10)
        
        # Assert
        assert len(merged) == 3  # Not 4, because 12345 is deduplicated
        cpt_codes = [r["cpt_code"] for r in merged]
        assert cpt_codes == ["12345", "67890", "11111"]
    
    def test_integration_search_with_fallback_chain(self, mock_db, mock_llm):
        """Test the full search chain: DB -> LLM -> Web"""
        # Setup - empty initial database search
        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = []
        mock_query.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # Mock LLM returns
        mock_llm.complete.return_value = '[]'  # No LLM results either
        
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Execute
        results = agent.search_procedures("extremely rare procedure", limit=5)
        
        # Assert - should not crash, returns list (possibly empty)
        assert isinstance(results, list)
    
    def test_error_handling_in_web_search(self, mock_db, mock_llm):
        """Test that web search errors are handled gracefully"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Force an error by mocking DDGS to raise exception
        with patch('duckduckgo_search.DDGS', side_effect=Exception("Network error")):
            # Execute
            results = agent._web_search_fallback("test query", limit=5)
            
            # Assert - should return empty list, not crash
            assert results == []


def test_import_fallback_when_duckduckgo_unavailable():
    """Test that agent still works when duckduckgo-search is not installed"""
    with patch('agents.query_understanding_agent.DUCKDUCKGO_AVAILABLE', False):
        # Should be able to import and create agent
        from agents.query_understanding_agent import QueryUnderstandingAgent
        
        mock_llm = Mock()
        mock_db = Mock()
        
        agent = QueryUnderstandingAgent(mock_llm, mock_db)
        
        # Web search should be skipped
        assert agent is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
