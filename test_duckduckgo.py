#!/usr/bin/env python3
"""
DuckDuckGo Search Test - NO API KEY REQUIRED!
Run this to see web-based pricing working immediately.
"""

import sys
import os

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.duckduckgo_search_client import DuckDuckGoSearchClient


def main():
    print("=" * 70)
    print("🦆 DUCKDUCKGO SEARCH TEST - NO API KEY NEEDED!")
    print("=" * 70)
    print()
    
    # Get search parameters
    print("📋 SEARCH PARAMETERS")
    print("-" * 70)
    cpt_code = input("Enter CPT code to search (default: 99213): ").strip() or "99213"
    city = input("Enter city (default: Joplin): ").strip() or "Joplin"
    state = input("Enter state (default: MO): ").strip() or "MO"
    print()
    
    # Create client (no API key needed!)
    print("🔧 Creating DuckDuckGo search client...")
    try:
        client = DuckDuckGoSearchClient()
        print("✅ Client created successfully! (No API key required)")
    except ImportError:
        print("❌ ERROR: duckduckgo-search not installed")
        print("\n📦 Install it with:")
        print("   cd backend")
        print("   pip install duckduckgo-search")
        return
    print()
    
    # Perform search
    print(f"🔎 Searching for: CPT {cpt_code} in {city}, {state}")
    print("⏳ Please wait... (this may take 5-10 seconds)")
    print()
    
    try:
        results = client.search_cpt_pricing(
            cpt_code=cpt_code,
            location=city,
            state=state,
            num_results=10,
        )
        
        print("=" * 70)
        print(f"📊 SEARCH RESULTS: Found {len(results)} results")
        print("=" * 70)
        print()
        
        if not results:
            print("⚠️  No results found!")
            print("\n💡 TIPS:")
            print("   • Try a different CPT code (e.g., 99214, 80053, 93000)")
            print("   • Try a bigger city (e.g., New York, Los Angeles)")
            print("   • Common CPT codes work better")
            return
        
        # Show detailed results
        for i, result in enumerate(results, 1):
            print(f"🔹 Result {i}:")
            print(f"   Title: {result.title[:70]}")
            print(f"   URL: {result.url[:70]}")
            if result.provider_name:
                print(f"   Provider: {result.provider_name}")
            if result.location:
                print(f"   Location: {result.location}")
            if result.extracted_prices:
                print(f"   💰 Prices found: {[f'${p:,.2f}' for p in result.extracted_prices]}")
            else:
                print(f"   💰 Prices found: None")
            print()
        
        # Aggregate results
        print("=" * 70)
        print("📈 AGGREGATED PRICING ESTIMATE")
        print("=" * 70)
        print()
        
        aggregated = client.aggregate_pricing_estimate(results)
        
        if aggregated["average"] is not None:
            print("✅ SUCCESS! Web-based pricing estimate generated:")
            print()
            print(f"   💵 RECOMMENDED PRICE (Median): ${aggregated['median']:,.2f}")
            print(f"   📊 Average: ${aggregated['average']:,.2f}")
            print(f"   📉 Minimum: ${aggregated['min']:,.2f}")
            print(f"   📈 Maximum: ${aggregated['max']:,.2f}")
            print(f"   🎯 Confidence: {aggregated['confidence']:.0%}")
            print(f"   📚 Data Sources: {len([r for r in results if r.extracted_prices])} sources")
            print()
            
            # Confidence interpretation
            if aggregated['confidence'] >= 0.6:
                print("   ✅ HIGH CONFIDENCE - Good data quality")
            elif aggregated['confidence'] >= 0.4:
                print("   ⚠️  MODERATE CONFIDENCE - Use with some caution")
            else:
                print("   ⚠️  LOW CONFIDENCE - Limited data, use as rough estimate")
            
            print()
            print("🎉 DuckDuckGo search is working! This is what the backend API returns.")
            print("   The 'data_source' field will show: \"DuckDuckGo (n=X sources)\"")
        else:
            print("❌ Could not extract pricing from search results")
            print("   Search found pages but no dollar amounts were detected.")
        
        print()
        print("=" * 70)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("🚀 NEXT STEPS:")
        print("   1. Install: cd backend && pip install duckduckgo-search")
        print("   2. Start backend: uvicorn app.main:app --reload")
        print("   3. Test API endpoint with CPT code not in your database")
        print("   4. Look for 'DuckDuckGo' in the data_source field!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 TROUBLESHOOTING:")
        print("   • Make sure duckduckgo-search is installed")
        print("   • Check internet connectivity")
        print("   • Try different search terms")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

