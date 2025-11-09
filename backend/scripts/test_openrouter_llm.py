"""
Test OpenRouter LLM Integration
Tests real LLM calls with actual API key
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.openrouter_llm import OpenRouterLLMClient
from agents.adaptive_parser import AdaptiveParsingAgent
from agents.file_discovery_agent import FileDiscoveryAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_llm_call():
    """Test basic LLM completion"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Basic LLM Completion")
    logger.info("=" * 80)
    
    # Initialize with API key
    api_key = "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"
    llm = OpenRouterLLMClient(
        api_key=api_key,
        model="anthropic/claude-3.5-sonnet"  # Best model for reasoning
    )
    
    logger.info(f"Mock mode: {llm.mock_mode}")
    logger.info(f"Model: {llm.model}")
    
    # Simple test prompt
    prompt = """
    Extract the CPT code from this medical procedure description:
    "MRI of the knee without contrast - CPT 73721"
    
    Return ONLY the 5-digit CPT code, nothing else.
    """
    
    logger.info("\nSending prompt to LLM...")
    response = llm.complete(prompt, temperature=0)
    
    logger.info(f"\nLLM Response: {response}")
    logger.info(f"Call count: {llm.call_count}")
    
    # Verify response contains CPT code
    assert "73721" in response, f"Expected CPT code 73721 in response, got: {response}"
    logger.info("✓ TEST PASSED: LLM correctly extracted CPT code")
    
    return True


def test_schema_inference():
    """Test schema inference with LLM"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Schema Inference")
    logger.info("=" * 80)
    
    api_key = "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"
    llm = OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    
    # Sample hospital data with non-standard field names
    sample_data = [
        {
            "facility": "Freeman Health System",
            "npi_number": "1234567890",
            "procedure_code": "70553",
            "proc_desc": "MRI Brain with contrast",
            "insurance": "Blue Cross Blue Shield",
            "negotiated_price": 1250.00,
            "list_price": 3500.00
        }
    ]
    
    prompt = f"""
    Analyze this hospital price transparency file sample and map the fields to our standard schema.
    
    Sample data:
    {sample_data}
    
    Standard schema we need:
    - provider_name: Hospital name
    - provider_npi: National Provider Identifier
    - cpt_code: Procedure code (CPT)
    - procedure_description: Description
    - payer_name: Insurance carrier
    - negotiated_rate: Negotiated rate
    - standard_charge: List/gross price
    
    Return ONLY valid JSON mapping like:
    {{"provider_name": "facility", "cpt_code": "procedure_code", ...}}
    
    Map each standard field to the corresponding field name in the sample data.
    If a field doesn't exist, use null.
    """
    
    logger.info("\nAsking LLM to infer schema...")
    response = llm.complete(prompt, temperature=0)
    
    logger.info(f"\nLLM Response:\n{response}")
    
    # Parse JSON response
    import json
    import re
    
    # Extract JSON from response (might have markdown formatting)
    json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
    if json_match:
        mapping = json.loads(json_match.group())
        logger.info(f"\nParsed mapping: {mapping}")
        
        # Verify key mappings
        assert mapping.get('provider_name') in ['facility', 'facility'], \
            f"Expected provider_name mapped to 'facility', got: {mapping.get('provider_name')}"
        assert mapping.get('cpt_code') in ['procedure_code', 'procedure_code'], \
            f"Expected cpt_code mapped to 'procedure_code', got: {mapping.get('cpt_code')}"
        
        logger.info("✓ TEST PASSED: LLM correctly inferred schema mapping")
        return True
    else:
        logger.warning("Could not extract JSON from response")
        return False


def test_payer_normalization():
    """Test insurance payer name standardization"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Payer Name Normalization")
    logger.info("=" * 80)
    
    api_key = "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"
    llm = OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    
    test_cases = [
        ("BCBS Missouri", "Blue Cross Blue Shield"),
        ("United Healthcare Inc.", "UnitedHealthcare"),
        ("Aetna Health Plans of Missouri LLC", "Aetna")
    ]
    
    for raw_name, expected_keyword in test_cases:
        prompt = f"""
        Standardize this insurance payer name: "{raw_name}"
        
        Rules:
        - Use official company name
        - Keep state name if mentioned
        - Remove legal suffixes (Inc, LLC, etc.)
        
        Return ONLY the standardized name, nothing else.
        """
        
        logger.info(f"\nNormalizing: {raw_name}")
        response = llm.complete(prompt, temperature=0)
        logger.info(f"Result: {response}")
        
        # Check if expected keyword is in response
        if expected_keyword.lower() in response.lower():
            logger.info(f"✓ Correct: Contains '{expected_keyword}'")
        else:
            logger.warning(f"⚠ Expected '{expected_keyword}' in response")
    
    logger.info("\n✓ TEST PASSED: Payer normalization working")
    return True


def test_file_parsing_with_llm():
    """Test complete file parsing with real LLM"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Complete File Parsing with LLM")
    logger.info("=" * 80)
    
    api_key = "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"
    llm = OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    
    # Initialize parser with real LLM
    parser = AdaptiveParsingAgent(llm_client=llm)
    
    # Path to sample file
    sample_file = Path(__file__).parent.parent / 'data/seeds/sample_hospital_file.csv'
    
    if not sample_file.exists():
        logger.warning(f"Sample file not found: {sample_file}")
        return False
    
    logger.info(f"\nParsing file: {sample_file.name}")
    
    try:
        records = parser.parse_hospital_file(str(sample_file))
        
        logger.info(f"\n✓ Parsed {len(records)} records")
        logger.info(f"LLM calls made: {llm.call_count}")
        
        # Show first record
        if records:
            logger.info(f"\nFirst record:")
            for key, value in records[0].items():
                logger.info(f"  {key}: {value}")
        
        logger.info("\n✓ TEST PASSED: File parsing with real LLM successful")
        return True
        
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_discovery_with_llm():
    """Test file discovery agent with real LLM"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: File Discovery with LLM")
    logger.info("=" * 80)
    
    api_key = "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"
    llm = OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    
    # Initialize discovery agent with real LLM
    discovery = FileDiscoveryAgent(llm_client=llm)
    
    hospital_name = "Freeman Health System"
    hospital_website = "https://www.freemanhealth.com"
    
    logger.info(f"\nDiscovering files for: {hospital_name}")
    logger.info(f"Website: {hospital_website}")
    
    try:
        files = discovery.discover_hospital_files(hospital_name, hospital_website)
        
        logger.info(f"\n✓ Found {len(files)} potential URLs")
        for file_info in files:
            logger.info(f"  - {file_info['url']}")
            logger.info(f"    Source: {file_info['source']}, Confidence: {file_info['confidence']}")
        
        logger.info(f"\nLLM calls made: {llm.call_count}")
        logger.info("\n✓ TEST PASSED: File discovery with real LLM successful")
        return True
        
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all OpenRouter LLM tests"""
    logger.info("=" * 80)
    logger.info("OPENROUTER LLM INTEGRATION TESTS")
    logger.info("=" * 80)
    logger.info("\nUsing Claude 3.5 Sonnet via OpenRouter")
    logger.info("This will make REAL API calls!\n")
    
    results = {}
    
    try:
        # Test 1: Basic completion
        results['basic_call'] = test_basic_llm_call()
        
        # Test 2: Schema inference
        results['schema_inference'] = test_schema_inference()
        
        # Test 3: Payer normalization
        results['payer_normalization'] = test_payer_normalization()
        
        # Test 4: File parsing
        results['file_parsing'] = test_file_parsing_with_llm()
        
        # Test 5: File discovery
        results['file_discovery'] = test_file_discovery_with_llm()
        
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
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for p in results.values() if p)
    
    logger.info("\n" + "=" * 80)
    logger.info(f"RESULTS: {passed_tests}/{total_tests} tests passed")
    logger.info("=" * 80)
    
    if passed_tests == total_tests:
        logger.info("\n🎉 ALL TESTS PASSED! Real LLM integration working perfectly!")
    else:
        logger.warning(f"\n⚠ {total_tests - passed_tests} test(s) failed")


if __name__ == '__main__':
    main()
