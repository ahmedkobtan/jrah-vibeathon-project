"""
Test Backend with Real LLM and Real MRF Files
Comprehensive integration test
"""

import sys
import os
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.adaptive_parser import AdaptiveParsingAgent
from agents.anthropic_llm import AnthropicLLMClient
from database.connection import init_database
from loaders.database_loader import DatabaseLoader
from validation.data_validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_llm_schema_inference():
    """Test LLM's ability to infer schemas from different file formats"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: LLM Schema Inference")
    logger.info("=" * 80)
    
    # Initialize LLM
    llm = AnthropicLLMClient()
    parser = AdaptiveParsingAgent(llm_client=llm)
    
    # Test with different file formats
    test_files = [
        "data/real_mrf_samples/sample_hospital_standard_charges.json",
        "data/real_mrf_samples/variant_format_hospital.json",
        "data/real_mrf_samples/csv_format_hospital.csv"
    ]
    
    results = []
    for file_path in test_files:
        full_path = Path(__file__).parent.parent / file_path
        if not full_path.exists():
            logger.warning(f"File not found: {full_path}")
            continue
        
        logger.info(f"\nTesting file: {full_path.name}")
        logger.info("-" * 60)
        
        try:
            # Parse the file
            records = parser.parse_hospital_file(str(full_path))
            
            # Results
            logger.info(f"✓ Successfully parsed {len(records)} records")
            logger.info(f"  LLM calls made: {llm.call_count}")
            
            # Show sample record
            if records:
                sample = records[0]
                logger.info(f"  Sample record:")
                logger.info(f"    CPT Code: {sample.get('cpt_code')}")
                logger.info(f"    Procedure: {sample.get('procedure_description')}")
                logger.info(f"    Payer: {sample.get('payer_name')}")
                logger.info(f"    Rate: ${sample.get('negotiated_rate')}")
                logger.info(f"    Confidence: {sample.get('confidence_score', 0):.2f}")
            
            results.append({
                'file': full_path.name,
                'success': True,
                'records': len(records),
                'llm_calls': llm.call_count
            })
            
        except Exception as e:
            logger.error(f"✗ Failed to parse {full_path.name}: {e}")
            results.append({
                'file': full_path.name,
                'success': False,
                'error': str(e)
            })
    
    return results


def test_end_to_end_with_llm():
    """Test complete pipeline with LLM"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: End-to-End Pipeline with LLM")
    logger.info("=" * 80)
    
    # Initialize components
    llm = AnthropicLLMClient()
    parser = AdaptiveParsingAgent(llm_client=llm)
    db = init_database(drop_existing=True)
    loader = DatabaseLoader(db)
    validator = DataValidator()
    
    # Test file
    test_file = Path(__file__).parent.parent / "data/real_mrf_samples/sample_hospital_standard_charges.json"
    
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return False
    
    logger.info(f"\nProcessing: {test_file.name}")
    
    try:
        # Step 1: Parse with LLM
        logger.info("\n[1/4] Parsing with LLM...")
        parsed_records = parser.parse_hospital_file(str(test_file))
        logger.info(f"  ✓ Parsed {len(parsed_records)} records")
        logger.info(f"  LLM calls: {llm.call_count}")
        
        # Step 2: Validate
        logger.info("\n[2/4] Validating records...")
        valid_records, flagged_records = validator.validate_records(parsed_records)
        logger.info(f"  ✓ Valid: {len(valid_records)}")
        logger.info(f"  ✗ Flagged: {len(flagged_records)}")
        
        if flagged_records:
            logger.warning("  Issues found:")
            for record in flagged_records[:3]:
                issues = record.get('validation_issues', [])
                logger.warning(f"    - {record.get('cpt_code')}: {', '.join(issues)}")
        
        # Step 3: Load to database
        logger.info("\n[3/4] Loading to database...")
        
        # Create provider
        provider_id = loader.create_provider(
            name="Sample Community Hospital",
            npi="9999999999",
            city="Joplin",
            state="MO",
            zip_code="64801"
        )
        
        # Load records
        loaded_count = loader.load_parsed_records(
            valid_records,
            provider_id,
            str(test_file)
        )
        logger.info(f"  ✓ Loaded {loaded_count} records")
        
        # Step 4: Verify in database
        logger.info("\n[4/4] Verifying database...")
        with db.session_scope() as session:
            from database import PriceTransparency, Procedure
            
            price_count = session.query(PriceTransparency).count()
            procedure_count = session.query(Procedure).count()
            
            logger.info(f"  ✓ Price records in DB: {price_count}")
            logger.info(f"  ✓ Procedures in DB: {procedure_count}")
            
            # Show sample data
            sample_prices = session.query(PriceTransparency).limit(3).all()
            logger.info("\n  Sample prices from database:")
            for price in sample_prices:
                logger.info(f"    CPT {price.cpt_code}: ${price.negotiated_rate} - {price.payer_name}")
        
        logger.info("\n✓ End-to-end test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"\n✗ End-to-end test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_variant_formats():
    """Test LLM's ability to handle different MRF format variations"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Variant Format Handling")
    logger.info("=" * 80)
    
    llm = AnthropicLLMClient()
    parser = AdaptiveParsingAgent(llm_client=llm)
    
    # Test the variant JSON format
    variant_file = Path(__file__).parent.parent / "data/real_mrf_samples/variant_format_hospital.json"
    
    if not variant_file.exists():
        logger.warning(f"Variant file not found: {variant_file}")
        return False
    
    logger.info(f"\nTesting variant format: {variant_file.name}")
    logger.info("This file has a completely different structure:")
    logger.info("  - Different field names")
    logger.info("  - Nested payer structure")
    logger.info("  - Multiple pricing methodologies")
    
    try:
        records = parser.parse_hospital_file(str(variant_file))
        
        logger.info(f"\n✓ Successfully parsed {len(records)} records from variant format")
        logger.info(f"  LLM calls: {llm.call_count}")
        
        # Verify data extraction
        for i, record in enumerate(records[:3], 1):
            logger.info(f"\n  Record {i}:")
            logger.info(f"    CPT: {record.get('cpt_code')}")
            logger.info(f"    Description: {record.get('procedure_description')}")
            logger.info(f"    Payer: {record.get('payer_name')}")
            logger.info(f"    Rate: ${record.get('negotiated_rate')}")
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Variant format test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("=" * 80)
    logger.info("COMPREHENSIVE LLM INTEGRATION TESTS")
    logger.info("=" * 80)
    
    # First, create the sample files
    logger.info("\nPreparing test data...")
    from download_hospital_files import create_sample_mrf_files
    sample_dir = create_sample_mrf_files()
    logger.info(f"✓ Test files ready in: {sample_dir}")
    
    # Run tests
    test_results = {}
    
    try:
        # Test 1: Schema inference
        test_results['schema_inference'] = test_llm_schema_inference()
        
        # Test 2: End-to-end pipeline
        test_results['end_to_end'] = test_end_to_end_with_llm()
        
        # Test 3: Variant formats
        test_results['variant_formats'] = test_variant_formats()
        
    except KeyboardInterrupt:
        logger.warning("\nTests interrupted by user")
        return
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    if isinstance(test_results.get('schema_inference'), list):
        passed = sum(1 for r in test_results['schema_inference'] if r.get('success'))
        total = len(test_results['schema_inference'])
        logger.info(f"Schema Inference: {passed}/{total} files parsed successfully")
    
    if test_results.get('end_to_end'):
        logger.info("End-to-End Pipeline: ✓ PASSED")
    else:
        logger.info("End-to-End Pipeline: ✗ FAILED")
    
    if test_results.get('variant_formats'):
        logger.info("Variant Format Handling: ✓ PASSED")
    else:
        logger.info("Variant Format Handling: ✗ FAILED")
    
    logger.info("\n" + "=" * 80)
    logger.info("Tests complete!")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
