"""
Parse ALL Freeman Hospital Data - Complete Production Run
Parses all available records from Freeman files and saves to database and CSV
"""

import sys
import csv
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseManager
from database import Provider, Procedure, PriceTransparency
from agents.adaptive_parser import AdaptiveParsingAgent
from agents.openrouter_llm import OpenRouterLLMClient
from agents.file_discovery_agent import FileDiscoveryAgent
from loaders.database_loader import DatabaseLoader
from validation.data_validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Parse all Freeman hospital data"""
    
    print("="*80)
    print("FREEMAN HOSPITAL DATA - COMPLETE PARSING")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize database
    db_path = Path(__file__).parent.parent / 'data' / 'healthcare_prices.db'
    db = DatabaseManager(f"sqlite:///{db_path}")
    db.create_tables()
    
    # Initialize LLM
    api_key = "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"
    llm = OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    
    # Initialize agents
    parser = AdaptiveParsingAgent(llm_client=llm)
    validator = DataValidator()
    loader = DatabaseLoader(db)
    agent = FileDiscoveryAgent()
    
    # Discover Freeman files
    print("[Step 1] Discovering Freeman hospital files...")
    print("-" * 80)
    discovered = agent.discover_local_files(hospital_name="Freeman")
    
    if not discovered:
        print("✗ No Freeman files found!")
        return
    
    print(f"✓ Found {len(discovered)} files:")
    for file_info in discovered:
        print(f"  - {file_info['filename']} ({file_info['size_mb']:.2f} MB)")
    print()
    
    # Process each file
    all_stats = []
    
    for i, file_info in enumerate(discovered, 1):
        file_path = file_info['path']
        filename = file_info['filename']
        hospital_name = file_info['hospital']
        
        print(f"[Step 2.{i}] Processing: {filename}")
        print("-" * 80)
        
        # Parse file (NO LIMITS - parse everything)
        print(f"Parsing all records from {filename}...")
        try:
            all_records = parser.parse_hospital_file(file_path)
            print(f"✓ Parsed {len(all_records):,} records")
        except Exception as e:
            print(f"✗ Failed to parse {filename}: {e}")
            continue
        
        # Validate
        print("Validating records...")
        valid_records, flagged_records = validator.validate_records(all_records)
        print(f"✓ Valid: {len(valid_records):,}")
        print(f"✓ Flagged: {len(flagged_records):,}")
        
        # Create provider (extract NPI from filename if available)
        npi = None
        if filename.startswith('431240629'):
            npi = '431240629'
            provider_name = 'Freeman Neosho Hospital'
        elif filename.startswith('431704371'):
            npi = '431704371'
            provider_name = 'Freeman Health System - Freeman West'
        else:
            provider_name = hospital_name
        
        # Check if provider already exists
        print(f"Checking for existing provider: {provider_name} (NPI: {npi or 'UNKNOWN'})")
        with db.session_scope() as session:
            from database import Provider
            existing = session.query(Provider).filter_by(npi=npi or "UNKNOWN").first()
            if existing:
                provider_id = existing.id
                print(f"✓ Using existing provider (ID: {provider_id})")
            else:
                print(f"Creating new provider: {provider_name}")
                provider_id = loader.create_provider(
                    name=provider_name,
                    npi=npi or "UNKNOWN",
                    city="Joplin",
                    state="MO"
                )
                print(f"✓ Created provider (ID: {provider_id})")
        
        # Load to database
        print("Loading records to database...")
        loaded_count = loader.load_parsed_records(
            valid_records,
            provider_id,
            file_path
        )
        print(f"✓ Loaded {loaded_count:,} records to database")
        
        all_stats.append({
            'filename': filename,
            'parsed': len(all_records),
            'valid': len(valid_records),
            'flagged': len(flagged_records),
            'loaded': loaded_count,
            'provider_id': provider_id
        })
        
        print()
    
    # Export all data to CSV
    print("[Step 3] Exporting all data to CSV...")
    print("-" * 80)
    
    output_dir = Path(__file__).parent.parent.parent / 'test_output'
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / f"freeman_all_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with db.session_scope() as session:
        # Get all price records
        all_prices = session.query(PriceTransparency).all()
        
        print(f"Exporting {len(all_prices):,} total records...")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'provider_id',
                'hospital_name',
                'npi',
                'cpt_code',
                'procedure_description',
                'payer_name',
                'negotiated_rate',
                'standard_charge',
                'confidence_score'
            ])
            writer.writeheader()
            
            for price in all_prices:
                provider = session.query(Provider).filter_by(id=price.provider_id).first()
                procedure = session.query(Procedure).filter_by(cpt_code=price.cpt_code).first()
                
                writer.writerow({
                    'provider_id': price.provider_id,
                    'hospital_name': provider.name if provider else 'Unknown',
                    'npi': provider.npi if provider else '',
                    'cpt_code': price.cpt_code,
                    'procedure_description': procedure.description if procedure else '',
                    'payer_name': price.payer_name,
                    'negotiated_rate': price.negotiated_rate,
                    'standard_charge': price.standard_charge or '',
                    'confidence_score': price.confidence_score
                })
    
    csv_size = csv_path.stat().st_size / (1024 * 1024)
    print(f"✓ Created: {csv_path.name}")
    print(f"✓ Size: {csv_size:.2f} MB")
    print()
    
    # Final Summary
    print("="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    total_parsed = sum(s['parsed'] for s in all_stats)
    total_valid = sum(s['valid'] for s in all_stats)
    total_loaded = sum(s['loaded'] for s in all_stats)
    
    print(f"\nFiles processed: {len(all_stats)}")
    print(f"Total records parsed: {total_parsed:,}")
    print(f"Total valid records: {total_valid:,}")
    print(f"Total loaded to database: {total_loaded:,}")
    print(f"\nCSV export: {csv_path}")
    print(f"Database: {db_path}")
    
    print("\nPer-file breakdown:")
    for stat in all_stats:
        print(f"\n  {stat['filename']}:")
        print(f"    Parsed: {stat['parsed']:,}")
        print(f"    Valid: {stat['valid']:,}")
        print(f"    Loaded: {stat['loaded']:,}")
    
    # Database statistics
    with db.session_scope() as session:
        provider_count = session.query(Provider).count()
        procedure_count = session.query(Procedure).count()
        price_count = session.query(PriceTransparency).count()
        
        print(f"\nDatabase Statistics:")
        print(f"  Providers: {provider_count:,}")
        print(f"  Unique Procedures: {procedure_count:,}")
        print(f"  Price Records: {price_count:,}")
    
    print(f"\n✓ COMPLETE - Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
