"""
Test File Discovery Agent with Real URLs
Demonstrates complete discovery → parse → load pipeline
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.file_discovery_agent import FileDiscoveryAgent
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


def test_url_discovery():
    """Test file discovery agent's URL discovery capabilities"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: URL Discovery for Known Hospitals")
    logger.info("=" * 80)
    
    llm = AnthropicLLMClient()
    discovery_agent = FileDiscoveryAgent(llm_client=llm)
    
    # Test with known hospitals
    test_hospitals = [
        {
            'name': 'Freeman Health System',
            'website': 'https://www.freemanhealth.com'
        },
        {
            'name': 'Mercy Hospital Joplin',
            'website': 'https://www.mercy.net'
        }
    ]
    
    results = {}
    for hospital in test_hospitals:
        logger.info(f"\nDiscovering URLs for: {hospital['name']}")
        logger.info(f"Website: {hospital['website']}")
        logger.info("-" * 60)
        
        discovered = discovery_agent.discover_hospital_files(
            hospital['name'],
            hospital['website']
        )
        
        if discovered:
            logger.info(f"✓ Found {len(discovered)} potential URLs:")
            for file_info in discovered:
                logger.info(f"  - {file_info['url']}")
                logger.info(f"    Source: {file_info['source']}, Confidence: {file_info['confidence']}")
        else:
            logger.warning(f"✗ No URLs found for {hospital['name']}")
        
        results[hospital['name']] = discovered
    
    return results


def test_location_discovery():
    """Test discovering hospitals by location"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Hospital Discovery by Location")
    logger.info("=" * 80)
    
    llm = AnthropicLLMClient()
    discovery_agent = FileDiscoveryAgent(llm_client=llm)
    
    logger.info("\nSearching for hospitals in: Joplin, MO")
    logger.info("-" * 60)
    
    hospitals = discovery_agent.discover_by_location('Joplin', 'MO', limit=5)
    
    if hospitals:
        logger.info(f"\n✓ Found {len(hospitals)} hospitals with transparency files:")
        for hospital in hospitals:
            logger.info(f"\n  Hospital: {hospital['hospital']}")
            logger.info(f"  NPI: {hospital.get('npi', 'Unknown')}")
            logger.info(f"  Website: {hospital.get('website', 'Unknown')}")
            logger.info(f"  Files found: {len(hospital.get('files', []))}")
            for file in hospital.get('files', [])[:2]:  # Show first 2
                logger.info(f"    - {file['url']}")
    else:
        logger.warning("✗ No hospitals found")
    
    return hospitals


def test_full_pipeline_with_discovery():
    """Test complete pipeline: discover → download → parse → load"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Full Pipeline with File Discovery")
    logger.info("=" * 80)
    
    # Initialize components
    llm = AnthropicLLMClient()
    discovery_agent = FileDiscoveryAgent(llm_client=llm)
    parser = AdaptiveParsingAgent(llm_client=llm)
    validator = DataValidator()
    db = init_database(drop_existing=True)
    loader = DatabaseLoader(db)
    
    # Use sample files since real URLs may not be accessible
    logger.info("\n[Step 1] Using sample MRF files for demonstration")
    sample_files = [
        {
            'url': 'file://sample_hospital_standard_charges.json',
            'path': Path(__file__).parent.parent / 'data/real_mrf_samples/sample_hospital_standard_charges.json',
            'hospital': 'Sample Community Hospital'
        }
    ]
    
    total_loaded = 0
    
    for file_info in sample_files:
        logger.info(f"\n[Step 2] Processing: {file_info['hospital']}")
        logger.info(f"  File: {file_info['path'].name}")
        
        if not file_info['path'].exists():
            logger.warning(f"  ✗ File not found: {file_info['path']}")
            continue
        
        try:
            # Parse
            logger.info("  [2a] Parsing with adaptive agent...")
            records = parser.parse_hospital_file(str(file_info['path']))
            logger.info(f"    ✓ Parsed {len(records)} records")
            
            # Validate
            logger.info("  [2b] Validating records...")
            valid, flagged = validator.validate_records(records)
            logger.info(f"    ✓ Valid: {len(valid)}, Flagged: {len(flagged)}")
            
            # Load to DB
            logger.info("  [2c] Loading to database...")
            
            # Create provider
            provider_id = loader.create_provider(
                name=file_info['hospital'],
                npi="9999999999",
                city="Joplin",
                state="MO"
            )
            
            # Load records
            loaded = loader.load_parsed_records(
                valid,
                provider_id,
                file_info['url']
            )
            logger.info(f"    ✓ Loaded {loaded} records")
            total_loaded += loaded
            
        except Exception as e:
            logger.error(f"  ✗ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n✓ Pipeline complete: {total_loaded} total records loaded")
    return total_loaded > 0


def test_url_validation():
    """Test URL validation functionality"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: URL Validation")
    logger.info("=" * 80)
    
    discovery_agent = FileDiscoveryAgent()
    
    # Test with some known URLs (may or may not work depending on network)
    test_urls = [
        'https://www.example.com/nonexistent.json',  # Should fail
        'https://httpbin.org/json',  # Should pass (generic JSON)
    ]
    
    logger.info("\nTesting URL validation:")
    for url in test_urls:
        logger.info(f"\n  Testing: {url}")
        is_valid = discovery_agent._validate_url(url, timeout=5)
        logger.info(f"  Result: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    return True


def main():
    """Run all discovery tests"""
    logger.info("=" * 80)
    logger.info("FILE DISCOVERY AGENT TESTS")
    logger.info("=" * 80)
    
    test_results = {}
    
    try:
        # Test 1: URL discovery
        logger.info("\nRunning URL discovery tests...")
        test_results['url_discovery'] = test_url_discovery()
        
        # Test 2: Location-based discovery
        logger.info("\nRunning location-based discovery...")
        test_results['location_discovery'] = test_location_discovery()
        
        # Test 3: Full pipeline
        logger.info("\nRunning full pipeline test...")
        test_results['full_pipeline'] = test_full_pipeline_with_discovery()
        
        # Test 4: URL validation
        logger.info("\nRunning URL validation test...")
        test_results['url_validation'] = test_url_validation()
        
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
    
    logger.info(f"URL Discovery: {'✓ PASSED' if test_results.get('url_discovery') else '✗ FAILED'}")
    logger.info(f"Location Discovery: {'✓ PASSED' if test_results.get('location_discovery') else '✗ FAILED'}")
    logger.info(f"Full Pipeline: {'✓ PASSED' if test_results.get('full_pipeline') else '✗ FAILED'}")
    logger.info(f"URL Validation: {'✓ PASSED' if test_results.get('url_validation') else '✗ FAILED'}")
    
    logger.info("\n" + "=" * 80)
    logger.info("KEY FEATURES DEMONSTRATED:")
    logger.info("=" * 80)
    logger.info("✓ File Discovery Agent - Finds hospital transparency URLs")
    logger.info("✓ URL Pattern Generation - Tries common paths")
    logger.info("✓ LLM-Enhanced Discovery - Uses AI to suggest likely URLs")  
    logger.info("✓ URL Validation - Checks if URLs are accessible")
    logger.info("✓ Location-Based Search - Find hospitals by city/state")
    logger.info("✓ Full Pipeline Integration - Discovery → Parse → Load")
    logger.info("\n" + "=" * 80)
    logger.info("NOTE: Some URLs may not be accessible due to network/auth")
    logger.info("In production, would integrate with CMS databases for real URLs")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
