#!/usr/bin/env python3
"""
Quick verification that the Pricing Estimation Agent is properly integrated.
"""

import sys
import os

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from agents.pricing_estimation_agent import PricingEstimationAgent
        print("  ✅ PricingEstimationAgent imported")
    except ImportError as e:
        print(f"  ❌ Failed to import PricingEstimationAgent: {e}")
        return False
    
    try:
        from agents.openrouter_llm import OpenRouterLLMClient
        print("  ✅ OpenRouterLLMClient imported")
    except ImportError as e:
        print(f"  ❌ Failed to import OpenRouterLLMClient: {e}")
        return False
    
    try:
        from app.services.pricing import PricingService
        print("  ✅ PricingService imported")
    except ImportError as e:
        print(f"  ❌ Failed to import PricingService: {e}")
        return False
    
    try:
        from app.services.duckduckgo_search_client import DuckDuckGoSearchClient
        print("  ✅ DuckDuckGoSearchClient imported")
    except ImportError as e:
        print(f"  ⚠️  DuckDuckGo not available (install: pip install duckduckgo-search)")
    
    return True

def test_agent_creation():
    """Test that the agent can be created."""
    print("\nTesting agent creation...")
    
    try:
        from agents.pricing_estimation_agent import PricingEstimationAgent
        from agents.openrouter_llm import OpenRouterLLMClient
        
        llm_client = OpenRouterLLMClient()
        agent = PricingEstimationAgent(llm_client=llm_client, use_duckduckgo=True)
        print("  ✅ Agent created successfully")
        
        # Check search client
        if agent.search_client:
            print(f"  ✅ Search client available: {type(agent.search_client).__name__}")
        else:
            print("  ⚠️  No search client (install duckduckgo-search or configure Google)")
        
        return True
    except Exception as e:
        print(f"  ❌ Failed to create agent: {e}")
        return False

def test_pricing_service_integration():
    """Test that PricingService can use the agent."""
    print("\nTesting PricingService integration...")
    
    try:
        from app.services.pricing import PricingService, AGENT_AVAILABLE
        
        if AGENT_AVAILABLE:
            print("  ✅ Agent integration available in PricingService")
        else:
            print("  ❌ Agent not available in PricingService")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Failed to test integration: {e}")
        return False

def main():
    print("=" * 70)
    print("🔍 PRICING ESTIMATION AGENT - INTEGRATION VERIFICATION")
    print("=" * 70)
    print()
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test agent creation
    results.append(("Agent Creation", test_agent_creation()))
    
    # Test integration
    results.append(("PricingService Integration", test_pricing_service_integration()))
    
    # Summary
    print()
    print("=" * 70)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print()
    
    if all(passed for _, passed in results):
        print("🎉 ALL TESTS PASSED!")
        print()
        print("✅ The Pricing Estimation Agent is properly integrated!")
        print()
        print("Next steps:")
        print("  1. Run: python3 test_pricing_agent.py")
        print("  2. Start backend: cd backend && uvicorn app.main:app --reload")
        print("  3. Test API: curl 'http://localhost:8000/api/pricing/estimates?cpt_code=99213&provider_city=Joplin&provider_state=MO'")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print()
        print("Common fixes:")
        print("  - Install DuckDuckGo: pip install duckduckgo-search")
        print("  - Check that backend/ directory exists")
        print("  - Verify Python path is correct")
        return 1

if __name__ == "__main__":
    sys.exit(main())

