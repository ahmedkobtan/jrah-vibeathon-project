"""
Test both DuckDuckGo (ddgs) and Google search APIs
"""
import time
import re

print("=" * 60)
print("TESTING GOOGLE SEARCH")
print("=" * 60)

query = "dental CPT code"
try:
    from googlesearch import search
    
    print(f"\nSearching Google for: '{query}'\n")
    
    results = []
    for url in search(query, num_results=10, lang='en'):
        results.append(url)
        print(f"✅ Found: {url}")
        time.sleep(0.2)  # Be polite
        
        if len(results) >= 5:
            break
    
    if results:
        print(f"\n✅ Google search SUCCESS: Found {len(results)} results")
        
        # Try extracting CPT codes with regex
        cpt_codes = set()
        for url in results:
            codes = re.findall(r'\b(\d{5})\b', url)
            cpt_codes.update(codes)
        
        if cpt_codes:
            print(f"✅ Regex extracted CPT codes: {list(cpt_codes)}")
        else:
            print("⚠️  No CPT codes found in URLs via regex")
            print("   → Would use LLM to extract from page content")
    else:
        print("❌ Google search returned no results")
        
except Exception as e:
    print(f"❌ Google search error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTING DUCKDUCKGO SEARCH (NEW DDGS)")
print("=" * 60)

try:
    from ddgs import DDGS
    
    print(f"\nSearching DuckDuckGo for: '{query}'\n")
    
    ddgs = DDGS()
    results = ddgs.text(query, max_results=10)
    
    if results:
        results_list = list(results)
        print(f"✅ DuckDuckGo search SUCCESS: Found {len(results_list)} results\n")
        
        for i, item in enumerate(results_list[:3], 1):
            print(f"Result {i}:")
            print(f"  Title: {item.get('title', 'No title')}")
            print(f"  URL: {item.get('href', 'No URL')}")
            print(f"  Snippet: {item.get('body', 'No snippet')[:100]}...\n")
        
        # Try extracting CPT codes with regex
        cpt_codes = set()
        all_text = ""
        for item in results_list:
            title = item.get('title', '')
            body = item.get('body', '')
            text = f"{title} {body}"
            all_text += text + " "
            codes = re.findall(r'\b(\d{5})\b', text)
            cpt_codes.update(codes)
        
        if cpt_codes:
            print(f"✅ Regex extracted CPT codes: {list(cpt_codes)}")
        else:
            print("⚠️  No CPT codes found via regex")
            print("   → Would use LLM to process search snippets")
            print(f"   Sample text: {all_text[:200]}...")
    else:
        print("❌ DuckDuckGo returned no results")
        
except Exception as e:
    print(f"❌ DuckDuckGo error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
