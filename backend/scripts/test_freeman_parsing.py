"""
Test Parsing Real Freeman Health MRF Files
Downloads and parses actual price transparency files from Freeman Health
"""

import sys
import logging
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.openrouter_llm import OpenRouterLLMClient
from agents.adaptive_parser import AdaptiveParsingAgent
from agents.file_discovery_agent import FileDiscoveryAgent
from database.connection import init_database
from loaders.database_loader import DatabaseLoader
from validation.data_validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test parsing real Freeman Health files"""
    
    logger.info("=" * 80)
    logger.info("FREEMAN HEALTH MRF PARSING TEST")
    logger.info("=" * 80)
    
    # Initialize OpenRouter LLM with API key
    api_key = "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"
    llm = OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    logger.info(f"✓ OpenRouter LLM initialized (mock_mode: {llm.mock_mode})")
    
    # Check for real Freeman files
    real_mrfs_dir = Path(__file__).parent.parent.parent / 'real_mrfs'
    
    if not real_mrfs_dir.exists():
        logger.warning(f"Directory not found: {real_mrfs_dir}")
        logger.info("Creating directory...")
        real_mrfs_dir.mkdir(parents=True, exist_ok=True)
    
    # Find Freeman files
    freeman_files = list(real_mrfs_dir.glob('*.json'))
    
    if not freeman_files:
        logger.warning("No Freeman MRF files found in real_mrfs/")
        logger.info("\nTo get Freeman files:")
        logger.info("1. Visit: https://www.freemanhealth.com/price-transparency")
        logger.info("2. Download the JSON files")
        logger.info("3. Place them in: real_mrfs/")
        return
    
    logger.info(f"\n✓ Found {len(freeman_files)} Freeman Health files:")
    for f in freeman_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        logger.info(f"  - {f.name} ({size_mb:.2f} MB)")
    
    # Initialize parser with real LLM
    parser = AdaptiveParsingAgent(llm_client=llm)
    
    # Initialize database
    db = init_database(drop_existing=True)
    loader = DatabaseLoader(db)
    validator = DataValidator()
    
    # Create Freeman provider
    provider_id = loader.create_provider(
        name="Freeman Health System",
        npi="1234567890",
        city="Joplin",
        state="MO",
        zip_code="64804",
        website="https://www.freemanhealth.com"
    )
    logger.info(f"\n✓ Created Freeman Health provider (ID: {provider_id})")
    
    # Parse each file
    total_parsed = 0
    total_loaded = 0
    
    for file_path in freeman_files:
        logger.info(f"\n{'='*80}")
        logger.info(f"Parsing: {file_path.name}")
        logger.info(f"{'='*80}")
        
        try:
            # Parse file
            logger.info("Step 1: Parsing with adaptive parser + LLM...")
            records = parser.parse_hospital_file(str(file_path))
            logger.info(f"  ✓ Parsed {len(records)} records")
            total_parsed += len(records)
            
            # Show sample record
            if records:
                logger.info("\nSample parsed record:")
                sample = records[0]
                for key, value in list(sample.items())[:7]:
                    logger.info(f"  {key}: {value}")
            
            # Validate
            logger.info("\nStep 2: Validating records...")
            valid_records, flagged_records = validator.validate_records(records)
            logger.info(f"  ✓ Valid: {len(valid_records)}")
            logger.info(f"  ⚠ Flagged: {len(flagged_records)}")
            
            # Load to database
            logger.info("\nStep 3: Loading to database...")
            loaded = loader.load_parsed_records(
                valid_records[:100],  # Load first 100 for demo
                provider_id,
                str(file_path)
            )
            logger.info(f"  ✓ Loaded {loaded} records")
            total_loaded += loaded
            
            logger.info(f"\n✓ Successfully processed {file_path.name}")
            logger.info(f"  LLM calls made: {llm.call_count}")
            
        except Exception as e:
            logger.error(f"\n✗ Error processing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✓ Files processed: {len(freeman_files)}")
    logger.info(f"✓ Total records parsed: {total_parsed}")
    logger.info(f"✓ Total records loaded: {total_loaded}")
    logger.info(f"✓ Total LLM calls: {llm.call_count}")
    
    # Verify database and export to CSV
    logger.info("\n" + "=" * 80)
    logger.info("DATABASE VERIFICATION & CSV EXPORT")
    logger.info("=" * 80)
    
    with db.session_scope() as session:
        from database import Provider, Procedure, PriceTransparency
        import csv
        
        provider_count = session.query(Provider).count()
        procedure_count = session.query(Procedure).count()
        price_count = session.query(PriceTransparency).count()
        
        logger.info(f"Providers: {provider_count}")
        logger.info(f"Procedures: {procedure_count}")
        logger.info(f"Price records: {price_count}")
        
        # Show sample prices
        logger.info("\nSample price records from database:")
        prices = session.query(PriceTransparency).limit(5).all()
        for price in prices:
            logger.info(f"  CPT {price.cpt_code}: ${price.negotiated_rate:.2f} - {price.payer_name}")
        
        # Export all records to CSV
        logger.info("\n" + "=" * 80)
        logger.info("EXPORTING TO CSV")
        logger.info("=" * 80)
        
        output_path = Path(__file__).parent.parent.parent / 'freeman_parsed_results.csv'
        
        # Get all price records with joined data
        all_prices = session.query(PriceTransparency).all()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'cpt_code', 
                'procedure_description', 
                'payer_name', 
                'negotiated_rate',
                'standard_charge',
                'confidence_score',
                'provider_id',
                'data_source',
                'created_at'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for price in all_prices:
                # Get procedure description from Procedure table if available
                procedure_desc = ''
                if price.cpt_code:
                    proc = session.query(Procedure).filter_by(cpt_code=price.cpt_code).first()
                    if proc:
                        procedure_desc = proc.description or ''
                
                writer.writerow({
                    'cpt_code': price.cpt_code or '',
                    'procedure_description': procedure_desc,
                    'payer_name': price.payer_name or '',
                    'negotiated_rate': price.negotiated_rate or '',
                    'standard_charge': price.standard_charge or '',
                    'confidence_score': price.confidence_score or '',
                    'provider_id': price.provider_id,
                    'data_source': price.data_source or '',
                    'created_at': price.created_at
                })
        
        logger.info(f"✓ Exported {len(all_prices)} records to: {output_path}")
        logger.info(f"  File size: {output_path.stat().st_size / 1024:.2f} KB")
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ FREEMAN HEALTH PARSING TEST COMPLETE!")
    logger.info("=" * 80)
    
    logger.info(f"\nDatabase: backend/data/healthcare_prices.db")
    logger.info(f"Real LLM Used: Claude 3.5 Sonnet via OpenRouter")
    logger.info(f"Mock Mode: {llm.mock_mode}")


if __name__ == '__main__':
    main()
