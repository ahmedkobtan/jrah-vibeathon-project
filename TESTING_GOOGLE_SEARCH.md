# 🚀 Quick Guide: Testing Google Search Feature

## Step-by-Step Instructions to See It Working

### Step 1: Get Google API Credentials (5 minutes)

#### Get API Key
1. Go to: https://console.developers.google.com/apis/credentials
2. Create a new project (or select existing)
3. Click "**+ CREATE CREDENTIALS**" → "**API Key**"
4. **Enable Custom Search API**:
   - Go to: https://console.developers.google.com/apis/library
   - Search for "Custom Search API"
   - Click and press "**ENABLE**"
5. Copy your API key (looks like: `AIzaSyAbc123...`)

#### Create Custom Search Engine
1. Go to: https://programmablesearchengine.google.com/
2. Click "**Add**" or "**Get Started**"
3. Configure:
   - **Name**: Healthcare Pricing Search
   - **What to search**: Select "**Search the entire web**"
   - (Optionally add specific sites like fairhealthconsumer.org)
4. Click "**Create**"
5. Copy your **Search engine ID** (looks like: `abc123def456...`)

### Step 2: Run the Test Script

#### Option A: Interactive Test (Recommended)
```bash
cd /Users/j0c0p72/Projects/jaechoi/jrah-vibeathon-project

python3 quick_test_google_search.py
```

The script will ask you for:
- API Key (paste it)
- CSE ID (paste it)
- CPT code to search (default: 99213)
- City (default: Joplin)
- State (default: MO)

#### Option B: Using Environment Variables
```bash
cd /Users/j0c0p72/Projects/jaechoi/jrah-vibeathon-project

export GOOGLE_SEARCH_API_KEY='your_api_key_here'
export GOOGLE_SEARCH_CSE_ID='your_cse_id_here'

python3 quick_test_google_search.py
```

### Step 3: Test with the Full Backend API

Once you see the test script working, test the actual API:

#### 1. Add credentials to .env file
```bash
cd backend
echo "GOOGLE_SEARCH_API_KEY=your_key_here" >> .env
echo "GOOGLE_SEARCH_CSE_ID=your_cse_id_here" >> .env
```

#### 2. Start the backend
```bash
# In backend directory
uvicorn app.main:app --reload
```

#### 3. Test with a CPT code that's NOT in your database

```bash
# This should trigger Google Search fallback
curl -X GET "http://localhost:8000/api/pricing/estimates?cpt_code=12345&provider_city=Joplin&provider_state=MO" | python3 -m json.tool
```

Look for in the response:
```json
{
  "data_source": "Google Search (n=7 sources)",
  "confidence_score": 0.55
}
```

### Expected Output Examples

#### ✅ Successful Test
```
🔍 GOOGLE SEARCH TEST FOR HEALTHCARE PRICING
======================================================================

✅ Using API Key: AIzaSyAbc123...
✅ Using CSE ID: abc123def456...

🔎 Searching for: CPT 99213 in Joplin, MO
⏳ Please wait... (this may take a few seconds)

======================================================================
📊 SEARCH RESULTS: Found 8 results
======================================================================

🔹 Result 1:
   Title: Office Visit Cost (CPT 99213) - Healthcare Bluebook
   URL: https://healthcarebluebook.com/...
   💰 Prices found: ['$145.00', '$180.50']

🔹 Result 2:
   Title: CPT 99213 - Medicare Fee Schedule
   URL: https://www.cms.gov/...
   💰 Prices found: ['$98.00']

...

======================================================================
📈 AGGREGATED PRICING ESTIMATE
======================================================================

✅ SUCCESS! Web-based pricing estimate generated:

   💵 RECOMMENDED PRICE (Median): $145.50
   📊 Average: $152.30
   📉 Minimum: $98.00
   📈 Maximum: $215.00
   🎯 Confidence: 55%
   📚 Data Sources: 7 sources

   ⚠️  MODERATE CONFIDENCE - Use with some caution

🎉 This is what the backend API would return for this CPT code!
   The 'Google Search' fallback layer is working correctly.
```

#### ⚠️ No Results
```
📊 SEARCH RESULTS: Found 0 results

⚠️  No results found!

💡 TROUBLESHOOTING:
   • Try a different CPT code (e.g., 99214, 70553, 80053)
   • Try a different location (e.g., New York, NY)
   • Check your Custom Search Engine settings:
     - Make sure 'Search the entire web' is enabled
```

### Troubleshooting

#### "ValueError: Google Custom Search API key and CSE ID are required"
- Make sure you entered both credentials
- Check for typos
- Try setting environment variables

#### "HTTPError 403: Forbidden"
- API key is invalid or not enabled
- Go back and enable "Custom Search API" in Google Console
- Create a new API key if needed

#### "HTTPError 429: Too Many Requests"
- You've exceeded the free quota (100/day)
- Wait 24 hours or upgrade to paid tier
- Each test = 1 query

#### No prices extracted (empty arrays)
- Google found pages but they don't contain prices
- Try different CPT codes (common ones work better)
- Try broader locations (e.g., "New York" instead of small towns)

#### Custom Search Engine returns irrelevant results
- Edit your CSE at: https://programmablesearchengine.google.com/
- Make sure "Search the entire web" is enabled
- Optionally add healthcare sites to prioritize

### Quick CPT Codes to Try

These commonly have pricing information online:
- `99213` - Office visit (established patient)
- `99214` - Office visit (complex)
- `99203` - New patient visit
- `80053` - Comprehensive metabolic panel
- `70553` - MRI brain
- `93000` - EKG
- `45378` - Colonoscopy

### Viewing Backend Logs

To see when Google Search is triggered:

```bash
# In backend directory
uvicorn app.main:app --reload --log-level debug
```

Watch for fallback logic in action!

### Need More Help?

1. **Test script not working?** 
   - Check Python path: `python3 --version` (needs 3.9+)
   - Install dependencies: `cd backend && pip install -r requirements.txt`

2. **API issues?**
   - Check Google Cloud Console for API status
   - Verify billing is set up (free tier requires billing info)
   - Check API quotas/limits

3. **Still stuck?**
   - Read full docs: `GOOGLE_SEARCH_INTEGRATION.md`
   - Check error messages carefully
   - Test with simple CPT codes first (99213, 99214)

---

## Summary

1. ✅ Get credentials from Google (API Key + CSE ID)
2. ✅ Run `python3 quick_test_google_search.py`
3. ✅ Enter credentials and search parameters
4. ✅ See web-based pricing in action!
5. ✅ Add to `.env` for full backend integration

**The test script will show you exactly what the Google Search feature finds!** 🎉

