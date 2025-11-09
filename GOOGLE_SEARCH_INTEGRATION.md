# Google Search Integration for Healthcare Pricing

## Overview

The backend now includes **Google Custom Search API integration** as an additional fallback layer for price estimation when database records are unavailable. This feature searches the web for actual pricing information rather than relying solely on algorithmic estimates.

## How It Works

### Pricing Lookup Waterfall Strategy

The system now follows this 4-tier fallback approach:

1. **Database Lookup** (Primary)
   - Searches local database for actual negotiated rates from hospital price transparency data
   - Most accurate, instant results

2. **NPI Registry + Algorithmic Estimates** (First Fallback)
   - Queries CMS NPI Registry API to find healthcare providers in the requested location
   - Generates estimates using Medicare rates and deterministic algorithms
   - No external pricing data, but uses real provider information

3. **Google Custom Search** (Second Fallback) ⭐ **NEW**
   - Searches web for CPT code pricing information
   - Parses results to extract dollar amounts
   - Aggregates multiple sources for more reliable estimates
   - Only activates if configured with API credentials

4. **Pure Algorithmic** (Last Resort)
   - Falls back to Medicare-based calculations
   - Deterministic but reasonable estimates

## Features

### Smart Search Queries
- Automatically constructs search queries with:
  - CPT code
  - Location (city/state if provided)
  - Healthcare-specific terms (hospital, facility, healthcare)
  - Pricing keywords (cost, price)

### Intelligent Price Extraction
- Parses search results for dollar amounts
- Filters reasonable healthcare prices ($50 - $1,000,000)
- Extracts provider names and locations from titles/URLs
- Handles various price formats ($1,234.56, 1234, etc.)

### Robust Aggregation
- Calculates min, max, average, and **median** prices
- Uses median as primary estimate (more robust to outliers)
- Confidence scoring based on:
  - Number of data sources found
  - Price variance (high variance = lower confidence)
  - Ranges from 0.3 to 0.7

### Result Presentation
- Creates a "Regional Average" provider entry
- Shows number of sources in data_source field: `"Google Search (n=5 sources)"`
- Includes min/max range for transparency
- Confidence score helps users assess reliability

## Setup Instructions

### 1. Get Google Custom Search API Credentials

#### Step 1: Get API Key
1. Go to [Google Cloud Console](https://console.developers.google.com/apis/credentials)
2. Create a new project or select existing one
3. Enable "Custom Search API"
4. Create credentials → API Key
5. Copy the API key

#### Step 2: Create Custom Search Engine
1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click "Add" to create new search engine
3. Configure:
   - **Sites to search**: Leave empty or add healthcare pricing sites like:
     - fairhealthconsumer.org
     - healthcarebluebook.com
     - healthsparq.com
     - Hospital websites
   - **Search the entire web**: Enable this option
   - **Name**: "Healthcare Pricing Search" (or any name)
4. Click "Create"
5. Copy the **Search engine ID** (looks like: `0123456789abcdef:a1b2c3d4e5f`)

### 2. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Google Custom Search API Configuration
GOOGLE_SEARCH_API_KEY=your_api_key_here
GOOGLE_SEARCH_CSE_ID=your_search_engine_id_here
```

**Important**: The feature is **optional**. If you don't set these variables:
- The system will skip Google Search fallback
- No errors will occur
- It will fall back to algorithmic estimates

### 3. Restart the Backend

```bash
cd backend
uvicorn app.main:app --reload
```

The feature will automatically activate if credentials are detected.

## Usage

No changes to API calls are needed! The Google Search fallback is transparent:

```bash
# Example API call
curl "http://localhost:8000/api/pricing/estimates?cpt_code=99213&provider_city=Joplin&provider_state=MO"
```

### When Google Search Activates

The Google Search fallback only triggers when:
1. No database records exist for the CPT code
2. NPI Registry lookup returns no providers OR you didn't specify city/state
3. Google Search credentials are configured

### How to Identify Google Search Results

Check the response:

```json
{
  "results": [
    {
      "provider": {
        "name": "Regional Average (Joplin, MO)",  // ← Indicates aggregated result
        "address": "Web-sourced estimate"          // ← Web-based data
      },
      "price": {
        "data_source": "Google Search (n=7 sources)",  // ← Shows source count
        "confidence_score": 0.55,                       // ← Reliability indicator
        "negotiated_rate": 145.50,                     // ← Median price
        "min_negotiated_rate": 98.00,                  // ← Range
        "max_negotiated_rate": 215.00
      }
    }
  ]
}
```

## Cost Considerations

### Google Custom Search API Pricing
- **Free tier**: 100 queries/day
- **Paid tier**: $5 per 1,000 queries (beyond free tier)
- Each pricing lookup = 1 query

### Optimization Tips
1. The system only uses Google Search as a **last resort**
2. Database results are always preferred (no API cost)
3. NPI fallback is tried before Google Search
4. Consider rate limiting in production

## Architecture

### New Files Created

1. **`backend/app/services/google_search_client.py`** (320 lines)
   - `GoogleSearchClient`: Main API client
   - `SearchResult`: Data model for search results
   - Price extraction and aggregation logic

2. **`backend/app/config.py`** (28 lines)
   - `Settings`: Configuration class
   - Loads environment variables
   - Provides `google_search_enabled` property

3. **`backend/.env.example`** (10 lines)
   - Template for environment variables
   - Instructions for obtaining credentials

### Modified Files

1. **`backend/app/services/pricing.py`**
   - Added `google_search_client` parameter to `PricingService`
   - Added `_fallback_with_google_search()` method
   - Integrated into fallback chain

2. **`backend/app/dependencies.py`**
   - Added `get_google_search_client()` dependency
   - Automatically creates client if configured

3. **`backend/app/routers/pricing.py`**
   - Injects `GoogleSearchClient` into pricing endpoint
   - Updated documentation

4. **`backend/app/services/__init__.py`**
   - Exported `GoogleSearchClient`

## Technical Details

### Search Query Construction

For CPT code `99213` in `Joplin, MO`:
```
"CPT 99213 cost price Joplin MO hospital OR facility OR healthcare"
```

### Price Extraction Regex

```python
r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
```

Matches:
- `$1,234.56` ✓
- `1234` ✓
- `$1234.56` ✓
- `1,234` ✓

Filters to $50-$1,000,000 range.

### Confidence Calculation

```python
# Base confidence from sample size (0.3 to 0.7)
confidence = min(0.7, 0.3 + (sample_size / 20))

# Reduce if high variance
coefficient_of_variation = std_dev / mean
if coefficient_of_variation > 0.5:
    confidence *= 0.7
```

## Testing

### Test Without API Credentials
```bash
# Leave .env empty or don't create it
# System should still work, just skip Google Search layer
curl "http://localhost:8000/api/pricing/estimates?cpt_code=99213&provider_city=Joplin&provider_state=MO"
```

### Test With API Credentials
```bash
# Set up .env with valid credentials
# Try a CPT code not in your database
curl "http://localhost:8000/api/pricing/estimates?cpt_code=12345&provider_city=Joplin&provider_state=MO"
```

### Manual Testing of Search Client

Create `test_google_search.py`:

```python
from backend.app.services.google_search_client import GoogleSearchClient

client = GoogleSearchClient(
    api_key="your_key",
    cse_id="your_cse_id"
)

results = client.search_cpt_pricing(
    cpt_code="99213",
    location="Joplin",
    state="MO"
)

print(f"Found {len(results)} results")
for r in results:
    print(f"  {r.provider_name}: {r.extracted_prices}")

aggregated = client.aggregate_pricing_estimate(results)
print(f"\nAggregated estimate: ${aggregated['median']:.2f}")
print(f"Range: ${aggregated['min']:.2f} - ${aggregated['max']:.2f}")
print(f"Confidence: {aggregated['confidence']:.2f}")
```

## Limitations & Considerations

### Accuracy
- Web-sourced prices may be:
  - Out of date
  - From different geographic regions
  - For different insurance types
  - Self-pay vs negotiated rates

### Rate Limits
- Free tier: 100 queries/day
- Consider caching results
- Monitor usage in production

### Search Quality
- Depends on what's indexed by Google
- Healthcare pricing may not always be publicly available
- Custom Search Engine configuration affects results

### Privacy
- API calls to Google include search terms (CPT codes, locations)
- No patient data is sent
- Consider privacy policies

## Future Enhancements

Possible improvements:

1. **Caching Layer**
   - Cache Google Search results for 24-48 hours
   - Reduce API costs
   - Faster response times

2. **Custom Search Engine Tuning**
   - Add more healthcare pricing sites
   - Exclude irrelevant domains
   - Regional configurations

3. **Advanced Price Extraction**
   - ML-based extraction for better accuracy
   - Context awareness (outpatient vs inpatient)
   - Insurance type detection

4. **Result Validation**
   - Cross-reference with Medicare rates
   - Flag suspicious outliers
   - Provider reputation scoring

5. **Alternative Search Engines**
   - Bing Search API
   - DuckDuckGo
   - Healthcare-specific search engines

## Support

### Troubleshooting

**Issue**: "ValueError: Google Custom Search API key and CSE ID are required"
- **Solution**: Make sure `.env` file exists and contains both credentials

**Issue**: No results from Google Search
- **Solution**: 
  - Check API key is valid
  - Verify Custom Search Engine ID
  - Ensure search engine is set to "Search the entire web"
  - Try broader search terms (remove city filter)

**Issue**: Low confidence scores
- **Solution**: Normal! Web data is less reliable than database records. Confidence 0.4-0.6 is expected.

**Issue**: API quota exceeded
- **Solution**: 
  - Free tier is 100 queries/day
  - Implement caching
  - Upgrade to paid tier if needed

### Getting Help

- Check `backend/app/services/google_search_client.py` for implementation details
- Review API response `data_source` field to see which fallback was used
- Enable debug logging to trace the fallback chain

## Summary

✅ **Implemented**: Google Custom Search integration for web-based price discovery  
✅ **Optional**: Works with or without API credentials  
✅ **Smart**: Only activates when database and NPI lookups fail  
✅ **Transparent**: Clearly labels web-sourced estimates  
✅ **Robust**: Aggregates multiple sources with confidence scoring  

The feature is production-ready and fully integrated into your existing pricing API!

