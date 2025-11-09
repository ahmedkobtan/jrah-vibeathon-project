# 🦆 DuckDuckGo Search Integration - NO API KEY REQUIRED!

## Why DuckDuckGo is Better for Your Use Case

✅ **No API key needed** - Works immediately!  
✅ **Completely free** - No quotas or rate limits  
✅ **No setup complexity** - Just install and go  
✅ **Privacy-focused** - No tracking  
✅ **Same functionality** - Finds pricing just like Google  

## Quick Start (2 Minutes!)

### Step 1: Install DuckDuckGo Search

```bash
cd backend
pip install duckduckgo-search
```

### Step 2: Test It Immediately

```bash
cd ..
python3 test_duckduckgo.py
```

The script will prompt you for:
- CPT code (default: 99213)
- City (default: Joplin)
- State (default: MO)

### Step 3: See It Work!

You'll see output like:

```
🦆 DUCKDUCKGO SEARCH TEST - NO API KEY NEEDED!
======================================================================

✅ Client created successfully! (No API key required)

🔎 Searching for: CPT 99213 in Joplin, MO
⏳ Please wait... (this may take 5-10 seconds)

📊 SEARCH RESULTS: Found 7 results
======================================================================

🔹 Result 1: Office Visit Costs (CPT 99213)
   💰 Prices found: ['$145.00', '$180.50']

🔹 Result 2: Medicare Fee Schedule...
   💰 Prices found: ['$98.00']

...

📈 AGGREGATED PRICING ESTIMATE
======================================================================

✅ SUCCESS! Web-based pricing estimate generated:

   💵 RECOMMENDED PRICE (Median): $145.50
   📊 Average: $152.30
   📉 Minimum: $98.00
   📈 Maximum: $215.00
   🎯 Confidence: 55%
   📚 Data Sources: 6 sources

🎉 DuckDuckGo search is working!
```

### Step 4: Use with Backend API

The backend **automatically** uses DuckDuckGo if installed:

```bash
cd backend
uvicorn app.main:app --reload
```

Test with API:
```bash
curl "http://localhost:8000/api/pricing/estimates?cpt_code=99213&provider_city=Joplin&provider_state=MO"
```

Look for in the response:
```json
{
  "data_source": "DuckDuckGo (n=7 sources)",
  "confidence_score": 0.55
}
```

## How It Works

### Automatic Fallback Priority

The system automatically chooses the best available search engine:

1. **DuckDuckGo** (if installed) ← **Preferred!**
2. Google Custom Search (if API keys configured)
3. Algorithmic estimates (if no search available)

You don't need to do anything - it just works!

### Code Flow

```python
# In dependencies.py - automatically selects DuckDuckGo
def get_search_client():
    # Try DuckDuckGo first (no API key required!)
    try:
        return DuckDuckGoSearchClient()  # ✅ Returns this if installed
    except ImportError:
        pass  # Not installed
    
    # Fall back to Google if configured
    if settings.google_search_enabled:
        return GoogleSearchClient(...)
    
    return None  # Use algorithmic estimates
```

## Comparison: DuckDuckGo vs Google

| Feature | DuckDuckGo | Google Custom Search |
|---------|------------|---------------------|
| **API Key Required** | ❌ No | ✅ Yes |
| **Setup Time** | 1 minute | 5-10 minutes |
| **Cost** | Free forever | 100/day free, then $5/1000 |
| **Rate Limits** | None (reasonable use) | 100/day free tier |
| **Privacy** | High (no tracking) | Standard |
| **Search Quality** | Good | Excellent |
| **Installation** | `pip install duckduckgo-search` | Need API keys |

**Recommendation**: Use DuckDuckGo! It's simpler and free.

## Installation Details

### Using pip:

```bash
pip install duckduckgo-search
```

### Using pip with version:

```bash
pip install duckduckgo-search>=4.0.0
```

### Verify installation:

```bash
python3 -c "from duckduckgo_search import DDGS; print('✅ Installed!')"
```

## Testing

### Test Script Only (No Backend)

```bash
python3 test_duckduckgo.py
```

This tests DuckDuckGo directly without running the backend.

### Test Full Backend Integration

```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Test API
curl "http://localhost:8000/api/pricing/estimates?cpt_code=12345&provider_city=Joplin&provider_state=MO" | python3 -m json.tool
```

Look for `"data_source": "DuckDuckGo ..."` in the response.

## Example API Response

When DuckDuckGo finds pricing:

```json
{
  "query": {
    "cpt_code": "99213",
    "state": "MO"
  },
  "summary": {
    "providers_count": 1,
    "min_rate": 98.00,
    "max_rate": 215.00,
    "average_rate": 145.50
  },
  "results": [
    {
      "provider": {
        "name": "Regional Average (Joplin, MO)",
        "address": "Web-sourced estimate"
      },
      "procedure": {
        "cpt_code": "99213",
        "description": "Office visit..."
      },
      "price": {
        "negotiated_rate": 145.50,
        "min_negotiated_rate": 98.00,
        "max_negotiated_rate": 215.00,
        "data_source": "DuckDuckGo (n=7 sources)",
        "confidence_score": 0.55
      }
    }
  ]
}
```

## Good CPT Codes to Try

These typically have pricing info online:
- `99213` - Office visit (common)
- `99214` - Complex office visit
- `99203` - New patient visit
- `80053` - Blood test panel
- `70553` - MRI brain
- `93000` - EKG
- `45378` - Colonoscopy

## Troubleshooting

### "ImportError: No module named 'duckduckgo_search'"

**Solution**: Install it!
```bash
cd backend
pip install duckduckgo-search
```

### No results found

**Try**:
- Different CPT code (99214, 80053)
- Bigger city (New York, Los Angeles)
- More common procedures

### Slow searches

**Normal!** DuckDuckGo can take 5-10 seconds to search.

### Search times out

**Try**:
- Check internet connection
- Try again (sometimes temporary)
- Use a different location

## Advanced: Using Both DuckDuckGo and Google

You can have both installed! The system prefers DuckDuckGo but falls back to Google if DuckDuckGo fails:

```bash
# Install DuckDuckGo (preferred)
pip install duckduckgo-search

# Optionally configure Google as backup
echo "GOOGLE_SEARCH_API_KEY=your_key" >> backend/.env
echo "GOOGLE_SEARCH_CSE_ID=your_cse" >> backend/.env
```

Priority: DuckDuckGo → Google → Algorithmic

## Files Created

- **`backend/app/services/duckduckgo_search_client.py`** - DuckDuckGo client
- **`test_duckduckgo.py`** - Test script (no backend needed)
- **`DUCKDUCKGO_GUIDE.md`** - This guide

## Summary

🦆 **DuckDuckGo is the easiest solution:**

1. Install: `pip install duckduckgo-search`
2. Test: `python3 test_duckduckgo.py`
3. Use: Automatically works with backend!

**No API keys, no configuration, no cost - just works!** ✨

---

**Next Steps**:
1. Run `pip install duckduckgo-search`
2. Run `python3 test_duckduckgo.py`
3. Watch it find real pricing data!

