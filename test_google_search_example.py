"""
Example script demonstrating Google Search integration for healthcare pricing.

This script shows how to use the GoogleSearchClient directly for testing.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.google_search_client import GoogleSearchClient


def test_google_search():
    """Test the Google Search client with example CPT code."""
    
    # Get credentials from environment
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cse_id = os.getenv("GOOGLE_SEARCH_CSE_ID")
    
    if not api_key or not cse_id:
        print("❌ Google Search API credentials not configured.")
        print("\nTo test this feature:")
        print("1. Set GOOGLE_SEARCH_API_KEY environment variable")
        print("2. Set GOOGLE_SEARCH_CSE_ID environment variable")
        print("\nOr create a .env file in the backend/ directory.")
        return
    
    print("✅ Google Search API credentials found!")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   CSE ID: {cse_id[:10]}...")
    print()
    
    # Create client
    client = GoogleSearchClient(
        api_key=api_key,
        cse_id=cse_id,
    )
    
    # Test search
    print("🔍 Searching for CPT code 99213 pricing in Joplin, MO...")
    print()
    
    try:
        results = client.search_cpt_pricing(
            cpt_code="99213",
            location="Joplin",
            state="MO",
            num_results=10,
        )
        
        print(f"📊 Found {len(results)} search results\n")
        
        if not results:
            print("⚠️  No results found. Try:")
            print("   - Different location")
            print("   - Different CPT code")
            print("   - Check Custom Search Engine configuration")
            return
        
        # Display results
        for i, result in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Title: {result.title[:60]}...")
            print(f"  URL: {result.url}")
            print(f"  Provider: {result.provider_name or 'Unknown'}")
            print(f"  Location: {result.location or 'Unknown'}")
            print(f"  Prices found: {result.extracted_prices}")
            print()
        
        # Aggregate pricing
        print("=" * 70)
        print("📈 AGGREGATED PRICING ESTIMATE")
        print("=" * 70)
        
        aggregated = client.aggregate_pricing_estimate(results)
        
        if aggregated["average"] is not None:
            print(f"\n💰 Price Estimate:")
            print(f"   Median (recommended): ${aggregated['median']:,.2f}")
            print(f"   Average: ${aggregated['average']:,.2f}")
            print(f"   Range: ${aggregated['min']:,.2f} - ${aggregated['max']:,.2f}")
            print(f"   Confidence: {aggregated['confidence']:.0%}")
            print(f"   Data sources: {len(results)}")
            
            if aggregated['confidence'] < 0.4:
                print("\n⚠️  Low confidence - use with caution")
            elif aggregated['confidence'] > 0.6:
                print("\n✅ Good confidence - relatively reliable estimate")
            else:
                print("\n ℹ️  Moderate confidence - reasonable estimate")
        else:
            print("\n❌ Could not extract pricing information from search results")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPossible issues:")
        print("- Invalid API credentials")
        print("- API quota exceeded (free tier: 100/day)")
        print("- Network connectivity")
        print("- Custom Search Engine not configured correctly")


def show_integration_info():
    """Show information about the integration."""
    print("=" * 70)
    print("🔎 GOOGLE SEARCH INTEGRATION FOR HEALTHCARE PRICING")
    print("=" * 70)
    print()
    print("This feature adds web-based price discovery to your backend.")
    print()
    print("📋 Pricing Lookup Strategy:")
    print("   1. Database (actual negotiated rates)")
    print("   2. NPI Registry + algorithmic estimates")
    print("   3. Google Search (web-sourced prices) ⭐ NEW")
    print("   4. Pure algorithmic fallback")
    print()
    print("🔧 Setup:")
    print("   1. Get API key: https://console.developers.google.com/")
    print("   2. Create CSE: https://programmablesearchengine.google.com/")
    print("   3. Set environment variables in backend/.env")
    print()
    print("📖 Full documentation: GOOGLE_SEARCH_INTEGRATION.md")
    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    show_integration_info()
    test_google_search()

