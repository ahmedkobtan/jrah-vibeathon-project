"""
Main Pipeline Script
Demonstrates complete workflow: Parse → Validate → Load
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

from database.connection import init_database, get_db_manager
from agents.adaptive_parser import AdaptiveParsingAgent
from agents.openrouter_llm import OpenRouterLLMClient
from loaders.database_loader import DatabaseLoader
from validation.data_validator import DataValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_seed_data():
    """Load seed data from JSON files"""
    data_dir = Path(__file__).parent / 'data' / 'seeds'
    
    # Load providers
    with open(data_dir / 'joplin_providers.json') as f:
        providers = json.load(f)
    
    # Load procedures
    with open(data_dir / 'common_procedures.json') as f:
        procedures = json.load(f)
    
    return providers, procedures


def create_medicare_baseline(procedures: List[Dict]) -> Dict[str, float]:
    """Create Medicare baseline from procedures"""
    return {
        proc['cpt_code']: proc['medicare_rate']
        for proc in procedures
        if proc.get('medicare_rate')
    }


def main():
    """Run complete pipeline"""
    
    logger.info("=" * 80)
    logger.info("Healthcare Price Transparency Pipeline")
    logger.info("=" * 80)
    
    # Step 1: Initialize database
    logger.info("\n[STEP 1] Initializing database...")
    db = init_database(drop_existing=True)
    loader = DatabaseLoader(db)
    
    # Step 2: Load seed data
    logger.info("\n[STEP 2] Loading seed data...")
    providers, procedures = load_seed_data()
    logger.info(f"  Loaded {len(providers)} providers")
    logger.info(f"  Loaded {len(procedures)} procedures")
    
    # Create procedures in database
    created_procedures = loader.bulk_create_procedures(procedures)
    logger.info(f"  Created {created_procedures} procedures in database")
    
    # Create providers in database
    provider_ids = {}
    for prov in providers:
        provider_id = loader.create_provider(
            name=prov['name'],
            npi=prov['npi'],
            address=prov.get('address'),
            city=prov.get('city'),
            state=prov.get('state'),
            zip_code=prov.get('zip'),
            latitude=prov.get('latitude'),
            longitude=prov.get('longitude'),
            phone=prov.get('phone'),
            website=prov.get('website')
        )
        provider_ids[prov['npi']] = provider_id
    
    logger.info(f"  Created {len(provider_ids)} providers in database")
    
    # Step 3: Parse hospital file
    logger.info("\n[STEP 3] Parsing hospital transparency file...")
    sample_file = Path(__file__).parent / 'data' / 'seeds' / 'sample_hospital_file.csv'
    
    # Initialize parser with OpenRouter LLM
    api_key = "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"
    llm_client = OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    parser = AdaptiveParsingAgent(llm_client=llm_client)
    
    parsed_records = parser.parse_hospital_file(str(sample_file))
    logger.info(f"  Parsed {len(parsed_records)} records")
    
    # Step 4: Validate records
    logger.info("\n[STEP 4] Validating records...")
    medicare_baseline = create_medicare_baseline(procedures)
    validator = DataValidator(medicare_baseline)
    
    valid_records, flagged_records = validator.validate_records(parsed_records)
    logger.info(f"  Valid records: {len(valid_records)}")
    logger.info(f"  Flagged records: {len(flagged_records)}")
    
    if flagged_records:
        logger.warning("  Flagged issues:")
        for record in flagged_records[:3]:  # Show first 3
            logger.warning(f"    - {record.get('cpt_code')}: {record.get('validation_issues')}")
    
    # Generate validation report
    report = validator.generate_validation_report(valid_records, flagged_records)
    logger.info(f"  Validation rate: {report['valid_rate']:.1%}")
    logger.info(f"  Average confidence: {report['avg_confidence']:.2f}")
    logger.info(f"  Unique CPT codes: {report['cpt_coverage']}")
    
    # Step 5: Load into database
    logger.info("\n[STEP 5] Loading records into database...")
    
    # Group records by provider
    records_by_provider = {}
    for record in valid_records:
        npi = record.get('provider_npi', '1234567890')  # Use Freeman as default
        if npi not in records_by_provider:
            records_by_provider[npi] = []
        records_by_provider[npi].append(record)
    
    total_loaded = 0
    for npi, records in records_by_provider.items():
        provider_id = provider_ids.get(npi, provider_ids['1234567890'])
        loaded_count = loader.load_parsed_records(
            records,
            provider_id,
            str(sample_file)
        )
        total_loaded += loaded_count
        logger.info(f"  Loaded {loaded_count} records for provider NPI {npi}")
    
    logger.info(f"  Total records loaded: {total_loaded}")
    
    # Step 6: Query database for verification
    logger.info("\n[STEP 6] Verifying database...")
    with db.session_scope() as session:
        from database import Provider, Procedure, PriceTransparency
        
        provider_count = session.query(Provider).count()
        procedure_count = session.query(Procedure).count()
        price_count = session.query(PriceTransparency).count()
        
        logger.info(f"  Providers in DB: {provider_count}")
        logger.info(f"  Procedures in DB: {procedure_count}")
        logger.info(f"  Price records in DB: {price_count}")
        
        # Show sample data
        logger.info("\n  Sample price records:")
        sample_prices = session.query(PriceTransparency).limit(3).all()
        for price in sample_prices:
            logger.info(f"    - CPT {price.cpt_code}: ${price.negotiated_rate:.2f} ({price.payer_name})")
    
    # Step 7: Summary
    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info(f"✓ Parsed {len(parsed_records)} records")
    logger.info(f"✓ Validated {len(valid_records)} records ({report['valid_rate']:.1%} valid)")
    logger.info(f"✓ Loaded {total_loaded} records into database")
    logger.info(f"✓ Database contains:")
    logger.info(f"  - {provider_count} providers")
    logger.info(f"  - {procedure_count} procedures")
    logger.info(f"  - {price_count} price transparency records")
    logger.info("\nDatabase location: backend/data/healthcare_prices.db")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
