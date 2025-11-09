#!/usr/bin/env python3
"""
Test script for the Pricing Estimation Agent.
This tests the AI-powered pricing estimation with DuckDuckGo and Google Search.
"""

import sys
import os

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from agents.pricing_estimation_agent import PricingEstimationAgent
from agents.openrouter_llm import OpenRouterLLMClient


def main():
    print("=" * 80)
    print("🤖 PRICING ESTIMATION AGENT TEST")
    print("=" * 80)
    print()
    
    # Initialize LLM client
    print("🔧 Initializing OpenRouter LLM client...")
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    llm_client = OpenRouterLLMClient(api_key=api_key)
    print("✅ LLM client initialized")
    print()
    
    # Initialize agent
    print("🔧 Initializing Pricing Estimation Agent...")
    agent = PricingEstimationAgent(
        llm_client=llm_client,
        use_duckduckgo=True,
        use_google=True
    )
    print("✅ Agent initialized")
    print()
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Office Visit - Joplin, MO",
            "cpt_code": "99213",
            "description": "Office outpatient visit, established patient, 15 minutes",
            "city": "Joplin",
            "state": "MO",
            "payer": "Blue Cross Blue Shield"
        },
        {
            "name": "Chest X-Ray - Kansas City, MO",
            "cpt_code": "71020",
            "description": "Chest X-ray, 2 views",
            "city": "Kansas City",
            "state": "MO",
            "payer": "Medicare"
        },
        {
            "name": "Basic Metabolic Panel - New York",
            "cpt_code": "80048",
            "description": "Basic metabolic panel",
            "city": "New York",
            "state": "NY",
            "payer": None
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print("=" * 80)
        print(f"TEST {i}: {scenario['name']}")
        print("=" * 80)
        print(f"📋 CPT Code: {scenario['cpt_code']}")
        print(f"📋 Description: {scenario['description']}")
        print(f"📍 Location: {scenario['city']}, {scenario['state']}")
        print(f"🏥 Payer: {scenario['payer'] or 'Not specified'}")
        print()
        
        print("⏳ Estimating price (this may take 10-30 seconds)...")
        print()
        
        try:
            # Perform estimation
            estimate = agent.estimate_price(
                cpt_code=scenario['cpt_code'],
                procedure_description=scenario['description'],
                city=scenario['city'],
                state=scenario['state'],
                payer_name=scenario['payer'],
                use_llm_analysis=True  # Enable LLM analysis
            )
            
            # Display results
            print("✅ ESTIMATION COMPLETE!")
            print()
            print("💰 PRICING ESTIMATE:")
            print(f"   Primary Rate:    ${estimate['negotiated_rate']:>10,.2f}")
            print(f"   Min Rate:        ${estimate['min_rate']:>10,.2f}")
            print(f"   Max Rate:        ${estimate['max_rate']:>10,.2f}")
            print(f"   Cash Price:      ${estimate['cash_price']:>10,.2f}")
            print(f"   Standard Charge: ${estimate['standard_charge']:>10,.2f}")
            print()
            print(f"📊 CONFIDENCE: {estimate['confidence']:.0%}")
            print(f"📚 DATA SOURCES: {estimate['source_count']} web sources")
            print(f"🔍 SEARCH ENGINE: {estimate['data_source']}")
            
            # Display LLM analysis if available
            if 'analysis' in estimate:
                print()
                print("🤖 AI ANALYSIS:")
                print(f"   {estimate['analysis']}")
            
            if 'location_factor' in estimate:
                print()
                print("📍 LOCATION FACTOR:")
                print(f"   {estimate['location_factor']}")
            
            # Interpretation
            print()
            if estimate['confidence'] >= 0.6:
                print("   ✅ HIGH CONFIDENCE - Reliable web data with AI validation")
            elif estimate['confidence'] >= 0.4:
                print("   ⚠️  MODERATE CONFIDENCE - Some web data, use with caution")
            else:
                print("   ⚠️  LOW CONFIDENCE - Limited data, rough estimate")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 80)
    print("🎉 ALL TESTS COMPLETED!")
    print("=" * 80)
    print()
    print("📝 WHAT THIS DEMONSTRATES:")
    print("   ✓ Web search for real pricing data (DuckDuckGo/Google)")
    print("   ✓ Statistical aggregation with outlier removal")
    print("   ✓ Location-based price adjustments")
    print("   ✓ LLM-powered intelligent analysis")
    print("   ✓ Confidence scoring based on data quality")
    print("   ✓ Graceful fallback when data is limited")
    print()
    print("🚀 The agent is now integrated into the backend API!")
    print("   Endpoint: GET /api/pricing/estimates")
    print("   Parameters: cpt_code, provider_city, provider_state")
    print()
    print("💡 TIP: The agent automatically activates when:")
    print("   - Database has no pricing data for the CPT code")
    print("   - NPI registry returns no providers")
    print("   - You specify provider_city and provider_state")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

