#!/usr/bin/env python3
"""
Quick test script for Google Search integration.
Run this to see Google Search working with healthcare pricing.
"""

import sys
import os

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.google_search_client import GoogleSearchClient


def main():
    print("=" * 70)
    print("🔍 GOOGLE SEARCH TEST FOR HEALTHCARE PRICING")
    print("=" * 70)
    print()
    
    # Get credentials
    api_key = input("Enter your Google API Key (or press Enter to use env var): ").strip()
    if not api_key:
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    
    cse_id = input("Enter your Custom Search Engine ID (or press Enter to use env var): ").strip()
    if not cse_id:
        cse_id = os.getenv("GOOGLE_SEARCH_CSE_ID")
    
    if not api_key or not cse_id:
        print("\n❌ ERROR: Missing credentials!")
        print("\n📋 TO GET CREDENTIALS:")
        print("   1. API Key: https://console.developers.google.com/apis/credentials")
        print("   2. CSE ID: https://programmablesearchengine.google.com/")
        print("\n💡 TIP: Set environment variables:")
        print("   export GOOGLE_SEARCH_API_KEY='your-key'")
        print("   export GOOGLE_SEARCH_CSE_ID='your-cse-id'")
        return
    
    print(f"\n✅ Using API Key: {api_key[:15]}...")
    print(f"✅ Using CSE ID: {cse_id[:15]}...")
    print()
    
    # Get search parameters
    print("📋 SEARCH PARAMETERS")
    print("-" * 70)
    cpt_code = input("Enter CPT code to search (default: 99213): ").strip() or "99213"
    city = input("Enter city (default: Joplin): ").strip() or "Joplin"
    state = input("Enter state (default: MO): ").strip() or "MO"
    print()
    
    # Create client
    print("🔧 Creating Google Search client...")
    client = GoogleSearchClient(api_key=api_key, cse_id=cse_id)
    print("✅ Client created!")
    print()
    
    # Perform search
    print(f"🔎 Searching for: CPT {cpt_code} in {city}, {state}")
    print("⏳ Please wait... (this may take a few seconds)")
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
            print("\n💡 TROUBLESHOOTING:")
            print("   • Try a different CPT code (e.g., 99214, 70553, 80053)")
            print("   • Try a different location (e.g., New York, NY)")
            print("   • Check your Custom Search Engine settings:")
            print("     - Make sure 'Search the entire web' is enabled")
            print("     - Remove site restrictions if any")
            return
        
        # Show detailed results
        for i, result in enumerate(results, 1):
            print(f"🔹 Result {i}:")
            print(f"   Title: {result.title[:70]}")
            print(f"   URL: {result.url}")
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
            print("🎉 This is what the backend API would return for this CPT code!")
            print("   The 'Google Search' fallback layer is working correctly.")
        else:
            print("❌ Could not extract pricing from search results")
            print("   Search found pages but no dollar amounts were detected.")
        
        print()
        print("=" * 70)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 COMMON ISSUES:")
        print("   • Invalid API credentials")
        print("   • API quota exceeded (free tier: 100/day)")
        print("   • Custom Search Engine not configured")
        print("   • Network connectivity issues")
        print("\n📖 See GOOGLE_SEARCH_INTEGRATION.md for troubleshooting")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

