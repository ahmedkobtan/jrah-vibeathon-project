# Healthcare Price Transparency Platform - Complete Architecture

## 🎯 Executive Summary

**Problem**: Patients cannot easily find out what medical procedures will cost with their specific insurance before receiving care. The same MRI might cost $400 or $4,000 depending on insurance and provider.

**Solution**: An embedded widget using LLM agents to:
1. Parse diverse hospital price transparency files (backend batch processing)
2. Understand natural language user queries in real-time
3. Match insurance plans intelligently
4. Display accurate cost estimates across nearby providers

**Hackathon Requirement**: Must demonstrate LLM/AI agent capabilities as core innovation.

---

## 📋 System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMBEDDED WIDGET (Frontend)                    │
│  User types: "How much for knee MRI with Blue Cross?"          │
│  Widget shows: Top 3 facilities, costs, insurance breakdown     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Real-time API calls
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API GATEWAY (FastAPI)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  QUERY UNDERSTANDING AGENT (LLM #1) - Real-time      │     │
│  │  • Parse natural language query                       │     │
│  │  • Extract: procedure, insurance, location           │     │
│  │  • Map to: CPT code, network ID, ZIP                │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  INSURANCE MATCHING LOGIC                             │     │
│  │  • Fuzzy match insurance plan name                   │     │
│  │  • Query CMS/Healthcare.gov APIs                     │     │
│  │  • Determine network, deductible, coinsurance        │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  COST ESTIMATOR                                       │     │
│  │  • Query database for negotiated rates               │     │
│  │  • Calculate patient responsibility                  │     │
│  │  • Rank providers by total out-of-pocket            │     │
│  └──────────────────────────────────────────────────────┘     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATABASE (PostgreSQL/SQLite)                   │
│                                                                  │
│  Tables:                                                         │
│  • providers (hospitals, clinics)                               │
│  • procedures (CPT codes, descriptions)                         │
│  • price_transparency (negotiated rates by provider+payer)      │
│  • insurance_plans (carriers, networks, coverage details)       │
│  • medicare_baseline (CMS fee schedules)                        │
│                                                                  │
│  Updated by: Backend Data Pipeline                              │
└──────────────────────┬──────────────────────────────────────────┘
                       ▲
                       │ Periodic updates (nightly/weekly)
                       │
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND DATA PIPELINE (Batch Processing)            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  FILE DISCOVERY AGENT                                 │     │
│  │  • Find hospital transparency files                   │     │
│  │  • Download from known URLs                          │     │
│  │  • Queue for processing                              │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  ADAPTIVE PARSING AGENT (LLM #2) - Batch             │     │
│  │  • Inspect file format (JSON/CSV/XML)                │     │
│  │  • Identify schema and field mappings                │     │
│  │  • Extract: CPT, payer, negotiated rate             │     │
│  │  • Normalize to standard schema                      │     │
│  │  • Handle missing/malformed data                     │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  DATA QUALITY & VALIDATION                            │     │
│  │  • Check for outliers                                │     │
│  │  • Compare to Medicare baseline                     │     │
│  │  • Flag suspicious data                             │     │
│  │  • Generate confidence scores                       │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  DATABASE LOADER                                      │     │
│  │  • Insert/update records                             │     │
│  │  • Maintain version history                         │     │
│  │  • Update indexes                                   │     │
│  └──────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                       ▲
                       │ Data sources
                       │
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                         │
│                                                                  │
│  • Hospital Price Transparency Files (CMS-mandated)             │
│  • CMS Marketplace API (insurance plans, benefits)              │
│  • Healthcare.gov API (coverage, eligibility)                   │
│  • Medicare Fee Schedules (baseline pricing)                    │
│  • Optional: Serif Health API (enhanced negotiated rates)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 LLM Agent Architecture (Detailed)

### Agent #1: Query Understanding Agent (Real-time)

**Purpose**: Transform natural language user queries into structured data for database lookup.

**Input Examples**:
- "knee MRI with Blue Cross PPO in Joplin"
- "How much does a CT scan cost with Medicare?"
- "cheapest colonoscopy near 64801"

**LLM Processing Flow**:

```python
class QueryUnderstandingAgent:
    """
    Real-time LLM agent that interprets user queries
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.procedure_db = load_cpt_codes()
        
    def parse_query(self, user_query: str) -> dict:
        """
        Parse natural language into structured query
        
        Returns:
            {
                "procedure": str,  # e.g., "MRI knee"
                "cpt_codes": list,  # e.g., ["73721"]
                "insurance_carrier": str,  # e.g., "Blue Cross Blue Shield"
                "plan_type": str,  # e.g., "PPO"
                "location": str,  # e.g., "64801"
                "confidence": float  # 0-1 score
            }
        """
        
        # Step 1: LLM extracts structured intent
        prompt = f"""
        Extract healthcare cost query details from user input.
        
        User query: "{user_query}"
        
        Return JSON with:
        - procedure_name: medical procedure mentioned
        - insurance_carrier: insurance company (if mentioned)
        - plan_type: PPO/HMO/EPO/etc (if mentioned)
        - location: ZIP code or city (if mentioned)
        - intent: what user wants ("cost_estimate", "compare_providers", "find_cheapest")
        
        Be precise. If something isn't mentioned, use null.
        """
        
        structured_data = self.llm.complete(prompt)
        
        # Step 2: Map procedure to CPT code
        cpt_codes = self.map_procedure_to_cpt(
            structured_data["procedure_name"]
        )
        
        # Step 3: Validate and enrich
        return {
            **structured_data,
            "cpt_codes": cpt_codes,
            "confidence": self.calculate_confidence(structured_data)
        }
    
    def map_procedure_to_cpt(self, procedure: str) -> list:
        """
        Use semantic search + LLM to find matching CPT codes
        """
        # First: Try exact/fuzzy match in procedure DB
        matches = self.procedure_db.search(procedure)
        
        if matches:
            return [m["cpt_code"] for m in matches[:3]]
        
        # Fallback: Ask LLM for CPT codes
        prompt = f"""
        What are the most common CPT codes for: "{procedure}"?
        Return up to 3 CPT codes.
        Format: ["12345", "67890"]
        """
        return self.llm.complete(prompt)
```

**Technology Stack**:
- **LLM**: OpenAI GPT-4 or Anthropic Claude (via API)
- **Fallback**: Local embedding model for semantic search
- **Caching**: Redis for common queries
- **Latency Target**: < 1 second for real-time response

**Prompt Engineering Strategy**:
```
System Prompt:
"You are a healthcare billing assistant that extracts structured information 
from patient queries about medical costs. Be precise and conservative - only 
extract information that is clearly stated. Return valid JSON."

Few-shot Examples:
1. "knee surgery with BCBS" → {"procedure": "knee arthroscopy", "cpt": ["29881"], ...}
2. "MRI brain Medicare" → {"procedure": "MRI brain", "cpt": ["70553"], ...}
3. "cheapest CT scan 64801" → {"procedure": "CT scan", "location": "64801", ...}
```

---

### Agent #2: Adaptive Parsing Agent (Batch Processing)

**Purpose**: Parse hospital price transparency files despite varying formats, schemas, and quality issues.

**Challenge**: Hospital files vary dramatically:
- Formats: JSON, CSV, XML, nested ZIP files
- Schemas: Different field names ("gross_charge" vs "standard_charge" vs "negotiated_rate")
- Structures: Flat vs nested, single vs multiple payers per row
- Quality: Missing data, encoding issues, inconsistent CPT codes

**LLM Processing Flow**:

```python
class AdaptiveParsingAgent:
    """
    Batch LLM agent that adapts to any hospital file format
    """
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.schema_cache = {}  # Cache learned schemas
        
    def parse_hospital_file(self, file_path: str) -> list:
        """
        Parse any hospital price transparency file
        
        Returns: List of standardized price records
        """
        
        # Step 1: Detect format
        file_format = self.detect_format(file_path)
        
        # Step 2: Load sample of data
        sample = self.load_sample(file_path, file_format, n_rows=20)
        
        # Step 3: LLM infers schema
        schema_mapping = self.infer_schema(sample, file_path)
        
        # Step 4: Parse full file using inferred schema
        all_records = []
        for chunk in self.chunk_file(file_path, file_format):
            records = self.extract_records(chunk, schema_mapping)
            all_records.extend(records)
        
        # Step 5: Validate and normalize
        return self.normalize_records(all_records)
    
    def infer_schema(self, sample_data: dict, file_path: str) -> dict:
        """
        Use LLM to map file schema to standard schema
        """
        
        # Check cache first
        file_hash = hash_file(file_path)
        if file_hash in self.schema_cache:
            return self.schema_cache[file_hash]
        
        # Ask LLM to analyze schema
        prompt = f"""
        Analyze this sample of a hospital price transparency file and map 
        the fields to our standard schema.
        
        Sample data (first 3 records):
        {json.dumps(sample_data[:3], indent=2)}
        
        Standard schema fields we need:
        - provider_name: Hospital/facility name
        - provider_npi: National Provider Identifier
        - cpt_code: Procedure code (CPT/HCPCS)
        - procedure_description: Human-readable procedure name
        - payer_name: Insurance carrier
        - negotiated_rate: Rate negotiated with insurance
        - standard_charge: List/gross price
        
        Return JSON mapping:
        {{
            "provider_name": "field_name_in_file",
            "cpt_code": "field_name_in_file",
            ...
        }}
        
        If a field doesn't exist, use null.
        Explain any ambiguities in "notes" field.
        """
        
        mapping = self.llm.complete(prompt, temperature=0.1)
        
        # Cache for future use
        self.schema_cache[file_hash] = mapping
        return mapping
    
    def extract_records(self, chunk: list, schema_mapping: dict) -> list:
        """
        Extract records using LLM-inferred schema
        
        Handles edge cases:
        - Nested JSON structures
        - Multiple payers per row
        - Free-text descriptions needing CPT extraction
        """
        
        records = []
        
        for row in chunk:
            try:
                record = {}
                
                # Map fields using schema
                for std_field, file_field in schema_mapping.items():
                    if file_field:
                        record[std_field] = self.extract_field(
                            row, file_field
                        )
                
                # Special handling: Extract CPT from free text
                if not record.get("cpt_code") and record.get("procedure_description"):
                    record["cpt_code"] = self.extract_cpt_from_text(
                        record["procedure_description"]
                    )
                
                # Normalize payer name
                if record.get("payer_name"):
                    record["payer_name"] = self.normalize_payer_name(
                        record["payer_name"]
                    )
                
                records.append(record)
                
            except Exception as e:
                # Log error but continue processing
                logger.error(f"Failed to parse row: {e}")
                continue
        
        return records
    
    def extract_cpt_from_text(self, description: str) -> str:
        """
        Use LLM to extract CPT code from free-text description
        """
        prompt = f"""
        Extract the CPT or HCPCS code from this procedure description.
        
        Description: "{description}"
        
        Return only the code (5 digits, or 5 char alphanumeric for HCPCS).
        If no code found, return null.
        """
        return self.llm.complete(prompt, temperature=0)
    
    def normalize_payer_name(self, payer: str) -> str:
        """
        Standardize insurance carrier names
        
        Examples:
        - "BCBS Missouri" → "Blue Cross Blue Shield of Missouri"
        - "United HealthCare" → "UnitedHealthcare"
        - "Aetna Inc" → "Aetna"
        """
        prompt = f"""
        Standardize this insurance payer name: "{payer}"
        
        Rules:
        - Use official company name
        - Include state if mentioned
        - Remove legal suffixes (Inc, LLC, etc.)
        
        Return only the standardized name.
        """
        return self.llm.complete(prompt, temperature=0)
```

**Technology Stack**:
- **LLM**: GPT-4 for schema inference (high reasoning capability needed)
- **Batch Processing**: Python with multiprocessing
- **Scheduling**: Airflow or simple cron jobs
- **Storage**: Raw files in S3/local storage, parsed data in PostgreSQL
- **Error Handling**: Dead letter queue for failed files

**Performance Optimization**:
1. **Schema Caching**: Once a hospital's schema is learned, cache it
2. **Batch LLM Calls**: Group multiple schema inferences into one API call
3. **Parallel Processing**: Process multiple files simultaneously
4. **Incremental Updates**: Only re-parse files that have changed

---

## 💾 Database Schema

```sql
-- Providers (hospitals, clinics, facilities)
CREATE TABLE providers (
    id SERIAL PRIMARY KEY,
    npi VARCHAR(10) UNIQUE,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    phone VARCHAR(20),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Medical procedures (CPT/HCPCS codes)
CREATE TABLE procedures (
    cpt_code VARCHAR(10) PRIMARY KEY,
    description TEXT NOT NULL,
    category VARCHAR(100),
    medicare_rate DECIMAL(10, 2),  -- Baseline from CMS
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insurance plans and carriers
CREATE TABLE insurance_plans (
    id SERIAL PRIMARY KEY,
    carrier VARCHAR(255) NOT NULL,
    plan_name VARCHAR(255),
    plan_type VARCHAR(50),  -- PPO, HMO, EPO, POS
    network_id VARCHAR(100),
    state VARCHAR(2),
    deductible_individual DECIMAL(10, 2),
    deductible_family DECIMAL(10, 2),
    coinsurance_rate DECIMAL(5, 4),  -- e.g., 0.20 for 20%
    copay_specialist DECIMAL(10, 2),
    out_of_pocket_max DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Price transparency data (core table)
CREATE TABLE price_transparency (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER REFERENCES providers(id),
    cpt_code VARCHAR(10) REFERENCES procedures(cpt_code),
    payer_name VARCHAR(255),  -- Raw payer name from file
    insurance_plan_id INTEGER REFERENCES insurance_plans(id),  -- Mapped plan
    
    -- Pricing data
    negotiated_rate DECIMAL(10, 2),
    min_negotiated_rate DECIMAL(10, 2),
    max_negotiated_rate DECIMAL(10, 2),
    standard_charge DECIMAL(10, 2),  -- List/gross price
    cash_price DECIMAL(10, 2),
    
    -- Metadata
    in_network BOOLEAN DEFAULT TRUE,
    data_source VARCHAR(255),  -- URL of transparency file
    confidence_score DECIMAL(3, 2),  -- 0-1 score from parsing agent
    last_updated DATE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Composite index for fast lookups
    INDEX idx_lookup (provider_id, cpt_code, insurance_plan_id),
    INDEX idx_payer (payer_name),
    INDEX idx_cpt (cpt_code)
);

-- File processing log
CREATE TABLE file_processing_log (
    id SERIAL PRIMARY KEY,
    file_url VARCHAR(255),
    file_hash VARCHAR(64),
    provider_id INTEGER REFERENCES providers(id),
    status VARCHAR(50),  -- pending, processing, completed, failed
    records_parsed INTEGER,
    errors TEXT,
    processing_time_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- User queries (for analytics and caching)
CREATE TABLE query_log (
    id SERIAL PRIMARY KEY,
    user_query TEXT,
    parsed_intent JSONB,
    cpt_codes VARCHAR(50)[],
    location VARCHAR(10),
    insurance_carrier VARCHAR(255),
    results_returned INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔄 Data Flow Diagrams

### Real-Time Query Flow

```
User → Widget → API
           ↓
    [Query Understanding Agent (LLM)]
           ↓
    Extract: procedure, insurance, ZIP
           ↓
    Map: procedure → CPT codes
    Map: insurance → network ID
           ↓
    [Database Query]
           ↓
    SELECT negotiated_rate 
    FROM price_transparency
    WHERE cpt_code IN (...)
      AND insurance_plan_id = ...
      AND provider.zip NEAR ...
           ↓
    [Cost Calculator]
           ↓
    Calculate patient responsibility:
    - Apply deductible
    - Apply coinsurance
    - Add copay
           ↓
    [Rank & Filter Results]
           ↓
    Sort by total out-of-pocket cost
    Filter by distance, in-network
           ↓
    Widget displays top 5 providers
```

### Batch File Processing Flow

```
Scheduler triggers job (nightly)
           ↓
    [File Discovery]
    - Check known hospital URLs
    - Download new/updated files
           ↓
    For each file:
           ↓
    [Format Detection]
    - CSV, JSON, XML, ZIP?
           ↓
    [Adaptive Parsing Agent (LLM)]
    - Load sample (20 rows)
    - Infer schema mapping
    - Cache schema for this provider
           ↓
    [Chunk Processing]
    - Process file in 1000-row chunks
    - Extract records using schema
    - Handle errors gracefully
           ↓
    [Data Validation]
    - Check for outliers (vs Medicare baseline)
    - Calculate confidence scores
    - Flag suspicious data
           ↓
    [Database Upsert]
    - Insert new records
    - Update existing records
    - Mark old data as stale
           ↓
    [Update Indexes]
           ↓
    Log completion status
```

---

## 🛠️ Technology Stack

### Frontend (Embedded Widget)
```javascript
// React + TypeScript
- React 18
- TypeScript
- Tailwind CSS (styling)
- Axios (API calls)
- React Query (caching)
- Leaflet (maps, optional)

// Build & Deploy
- Vite (fast build)
- ESBuild (bundler)
- Deployed as: <script> tag or iframe
```

### Backend API (Real-time)
```python
# FastAPI + Python 3.11
- FastAPI (REST API)
- Pydantic (data validation)
- SQLAlchemy (ORM)
- Redis (caching)
- OpenAI/Anthropic SDK (LLM calls)

# Deployment
- Docker containers
- Railway / Render / Fly.io
- Auto-scaling enabled
```

### Batch Processing Pipeline
```python
# Python 3.11
- Pandas (data manipulation)
- Requests (file downloads)
- OpenAI SDK (parsing agent)
- Multiprocessing (parallel processing)
- Schedule or APScheduler (job scheduling)

# For production:
- Apache Airflow (workflow orchestration)
- Celery (task queue)
```

### Database
```sql
# Development
- SQLite (fast prototyping)

# Production
- PostgreSQL 15+
- PostGIS extension (geospatial queries)
- Connection pooling with PgBouncer
```

### LLM Services
```
Primary: OpenAI GPT-4-turbo
- Query understanding (real-time)
- Schema inference (batch)
- Entity extraction

Fallback: Anthropic Claude 3
- Same prompts, different model
- Use if OpenAI rate limited

Cost optimization:
- Cache common queries (Redis)
- Use GPT-3.5 for simple tasks
- Batch multiple LLM calls when possible
```

---

## ⚡ Performance Requirements

### Real-Time API
- **Latency**: < 2 seconds end-to-end
  - LLM query understanding: < 800ms
  - Database query: < 200ms
  - Cost calculation: < 100ms
  - Response formatting: < 50ms
  - Network overhead: < 850ms

- **Throughput**: 100 requests/second
- **Availability**: 99.9% uptime

### Batch Processing
- **Processing Speed**: 1,000 rows/second per worker
- **Concurrency**: 4-8 parallel file parsers
- **LLM Efficiency**: Batch schema inferences, cache aggressively
- **Schedule**: Run nightly (2am - 6am)

---

##  Security & Compliance

### Data Privacy
- **No PHI**: Widget does NOT collect:
  - Patient names
  - Medical record numbers
  - Specific diagnoses
  - Treatment history

- **Collected Data** (non-PHI):
  - Insurance carrier (type only, no member ID)
  - Procedure type (generic CPT code)
  - ZIP code (location only)

### HIPAA Compliance
- **Current Status**: Not HIPAA-regulated (no PHI)
- **Future**: If integrating with EHR systems:
  - Sign BAA with healthcare partners
  - Encrypt data at rest and in transit
  - Implement audit logs
  - Add access controls

### API Security
```python
# Rate limiting
- 100 requests per minute per IP
- 1000 requests per day per API key

# Authentication (future)
- API keys for hospital partners
- JWT tokens for widget authentication

# Data sanitization
- Input validation on all parameters
- SQL injection prevention (SQLAlchemy)
- XSS prevention (sanitize user input)
```

---

## 📊 Hackathon Demo Plan (24-Hour Build)

### Hour 0-4: Foundation
**Data Scientist**:
- Download 2-3 Joplin hospital transparency files
- Download CMS Medicare fee schedule
- Manually inspect file formats and schemas

**ML Engineer**:
- Set up FastAPI project structure
- Configure OpenAI API
- Create database schema (SQLite)
- Set up React widget skeleton

### Hour 4-8: Core LLM Agents
**Data Scientist**:
- Implement Query Understanding Agent
- Create test cases for natural language queries
- Build procedure → CPT mapping logic

**ML Engineer**:
- Implement Adaptive Parsing Agent
- Test on 2-3 different hospital file formats
- Build schema inference prompts

### Hour 8-12: Data Pipeline
**Both**:
- Parse hospital files → database
- Seed database with 50-100 procedures
- Add 5-10 Joplin providers
- Validate data quality

### Hour 12-16: Widget & API Integration
**ML Engineer**:
- Complete React widget UI
- Wire up API calls
- Add loading states, error handling

**Data Scientist**:
- Build cost calculation engine
- Test insurance deductible/coinsurance logic
- Create demo scenarios

### Hour 16-20: Polish & Demo Prep
**Both**:
- End-to-end testing
- Create pitch deck
- Record demo video (backup)
- Prepare 3-5 demo scenarios

### Hour 20-24: Rehearsal & Sleep
- Practice demo (10 times)
- Fix critical bugs only
- Get REST before presentation

---

## 🎬 Demo Script (3 Minutes)

### Setup
- Mock hospital website with embedded widget
- Pre-seed database with real Joplin data
- Have 3 demo scenarios ready

### Act 1: Problem (30 seconds)
> "Meet Sarah. She needs an MRI for her knee. Her doctor says it'll cost 
> 'between $400 and $4,000 depending on your insurance.'
>
> Sarah has Blue Cross PPO. Will she pay $400 or $4,000? She has no way to know.
>
> This happens millions of times per day. It's why medical debt is $220 billion."

### Act 2: Solution Demo (90 seconds)
> "This is our widget - it embeds in any hospital website.
>
> Watch Sarah use it...
>
> [Type]: 'knee MRI with Blue Cross PPO in Joplin'
>
> Our LLM agent understands she needs:
> - CPT code 73721 (Knee MRI)
> - Blue Cross Blue Shield Missouri PPO
> - Providers near 64801
>
> [Results appear in 1.5 seconds]
>
> Freeman Health: YOU PAY $385
> - Base Price: $1,850
> - Insurance negotiated: $1,250
> - Your deductible: $200 remaining
> - Your coinsurance (20%): $185
>
> Mercy Hospital: YOU PAY $470
> - Base Price: $2,100
> ...
>
> Cox Health: YOU PAY $550
> - Base Price: $2,400
> ...
>
> Sarah saves $165 by choosing Freeman. More importantly, she KNOWS the cost 
> before scheduling. No surprises.
>
> [Show 'How we calculated' popup]
>
> Behind the scenes: Our adaptive parsing agent processed 50MB+ of hospital 
> price transparency files, each with different formats. The LLM figured out 
> their schemas automatically - no manual coding needed."

### Act 3: Impact & Technology (40 seconds)
> "The innovation: **Two LLM agents working together**
>
> 1. Backend Agent (batch): Adaptively parses ANY hospital file format
>    - Handles CSV, JSON, XML automatically
>    - Learns each hospital's unique schema
>    - Normalizes to our database
>
> 2. Frontend Agent (real-time): Understands patient queries
>    - 'knee MRI' → CPT 73721
>    - 'Blue Cross PPO' → network ID
>    - Natural language, no forms
>
> Data sources: 100% public
> - CMS-mandated hospital files
> - Medicare fee schedules
> - Healthcare.gov APIs
>
> Impact:
> - Patient time: 2 hours → 30 seconds (240x faster)
> - Surprise bills: -60%
> - Hospital billing calls:
