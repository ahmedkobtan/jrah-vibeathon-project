"""
End-to-End Integration Test
Tests complete pipeline with actual LLM and real hospital files
"""

import pytest
import sys
import os
import csv
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseManager
from database import Provider, Procedure, PriceTransparency
from agents.adaptive_parser import AdaptiveParsingAgent
from agents.openrouter_llm import OpenRouterLLMClient
from agents.file_discovery_agent import FileDiscoveryAgent
from loaders.database_loader import DatabaseLoader
from validation.data_validator import DataValidator


class TestEndToEndIntegration:
    """
    Comprehensive end-to-end tests using actual LLM and real hospital files
    """
    
    @pytest.fixture
    def test_db(self):
        """Create test database"""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        yield db
    
    @pytest.fixture
    def real_llm(self):
        """Create real OpenRouter LLM client"""
        api_key = "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"
        return OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")
    
    @pytest.fixture
    def real_mrfs_dir(self):
        """Path to real MRF files"""
        return Path(__file__).parent.parent.parent / 'real_mrfs'
    
    @pytest.fixture
    def output_dir(self):
        """Create output directory for test results"""
        output = Path(__file__).parent.parent.parent / 'test_output'
        output.mkdir(exist_ok=True)
        return output
    
    def test_file_discovery_local(self, real_mrfs_dir):
        """Test 1: File Discovery from Local Directory"""
        print("\n" + "="*80)
        print("TEST 1: FILE DISCOVERY FROM LOCAL DIRECTORY")
        print("="*80)
        
        agent = FileDiscoveryAgent()
        discovered = agent.discover_local_files(hospital_name="Freeman")
        
        assert len(discovered) > 0, "Should discover Freeman files in real_mrfs"
        
        print(f"\n✓ Discovered {len(discovered)} files:")
        for file_info in discovered:
            print(f"  - {file_info['filename']} ({file_info['size_mb']:.2f} MB)")
            print(f"    Hospital: {file_info['hospital']}")
        
        return discovered
    
    def test_parsing_with_real_llm(self, real_llm, real_mrfs_dir):
        """Test 2: Parse Real Hospital File with Actual LLM"""
        print("\n" + "="*80)
        print("TEST 2: PARSE REAL HOSPITAL FILE WITH ACTUAL LLM")
        print("="*80)
        
        # Use the Neosho hospital file (smaller, faster to parse)
        test_file = real_mrfs_dir / "431240629_freeman-neosho-hospital_standardcharges.json"
        
        assert test_file.exists(), f"Test file not found: {test_file}"
        
        print(f"\nParsing: {test_file.name}")
        print(f"Size: {test_file.stat().st_size / (1024*1024):.2f} MB")
        
        parser = AdaptiveParsingAgent(llm_client=real_llm)
        
        # Parse file (limit records for faster testing by slicing afterward)
        all_records = parser.parse_hospital_file(str(test_file))
        records = all_records[:100]  # Limit to first 100 for testing
        
        assert len(records) > 0, "Should parse at least some records"
        
        print(f"\n✓ Parsed {len(records)} records")
        print("\nSample record:")
        print(f"  CPT Code: {records[0].get('cpt_code')}")
        print(f"  Description: {records[0].get('procedure_description', 'N/A')[:50]}")
        print(f"  Payer: {records[0].get('payer_name', 'N/A')}")
        print(f"  Rate: ${records[0].get('negotiated_rate', 0):.2f}")
        print(f"  Confidence: {records[0].get('confidence_score', 0):.2f}")
        
        return records
    
    def test_validation(self, real_llm, real_mrfs_dir):
        """Test 3: Data Validation"""
        print("\n" + "="*80)
        print("TEST 3: DATA VALIDATION")
        print("="*80)
        
        # Parse file
        test_file = real_mrfs_dir / "431240629_freeman-neosho-hospital_standardcharges.json"
        parser = AdaptiveParsingAgent(llm_client=real_llm)
        all_records = parser.parse_hospital_file(str(test_file))
        records = all_records[:50]  # Limit to first 50 for testing
        
        # Validate
        medicare_baseline = {'70553': 423.00, '73721': 275.00, '99213': 93.00}
        validator = DataValidator(medicare_baseline)
        
        valid_records, flagged_records = validator.validate_records(records)
        
        print(f"\n✓ Total records: {len(records)}")
        print(f"✓ Valid records: {len(valid_records)}")
        print(f"✓ Flagged records: {len(flagged_records)}")
        
        if flagged_records:
            print("\nSample validation issues:")
            for i, record in enumerate(flagged_records[:3], 1):
                print(f"\n  [{i}] Record issues:")
                for issue in record.get('validation_issues', [])[:2]:
                    print(f"    - {issue}")
        
        assert len(valid_records) > 0, "Should have at least some valid records"
        
        return valid_records, flagged_records
    
    def test_database_loading(self, test_db, real_llm, real_mrfs_dir):
        """Test 4: Load Data into Database"""
        print("\n" + "="*80)
        print("TEST 4: LOAD DATA INTO DATABASE")
        print("="*80)
        
        # Parse and validate
        test_file = real_mrfs_dir / "431240629_freeman-neosho-hospital_standardcharges.json"
        parser = AdaptiveParsingAgent(llm_client=real_llm)
        all_records = parser.parse_hospital_file(str(test_file))
        records = all_records[:50]  # Limit to first 50 for testing
        
        validator = DataValidator()
        valid_records, _ = validator.validate_records(records)
        
        # Load into database
        loader = DatabaseLoader(test_db)
        
        provider_id = loader.create_provider(
            name="Freeman Neosho Hospital",
            npi="431240629",
            city="Neosho",
            state="MO",
            zip_code="64850"
        )
        
        print(f"\n✓ Created provider (ID: {provider_id})")
        
        loaded_count = loader.load_parsed_records(
            valid_records,
            provider_id,
            str(test_file)
        )
        
        print(f"✓ Loaded {loaded_count} records into database")
        
        # Verify data in database
        with test_db.session_scope() as session:
            provider = session.query(Provider).filter_by(id=provider_id).first()
            assert provider is not None
            print(f"✓ Provider: {provider.name} (NPI: {provider.npi})")
            
            procedures = session.query(Procedure).count()
            print(f"✓ Procedures in DB: {procedures}")
            
            prices = session.query(PriceTransparency).filter_by(provider_id=provider_id).count()
            print(f"✓ Price records in DB: {prices}")
            
            assert prices == loaded_count, "Loaded count should match DB count"
            
            # Show sample records
            sample_prices = session.query(PriceTransparency).filter_by(provider_id=provider_id).limit(3).all()
            print("\nSample database records:")
            for i, price in enumerate(sample_prices, 1):
                procedure = session.query(Procedure).filter_by(cpt_code=price.cpt_code).first()
                print(f"\n  [{i}] {price.cpt_code}: {procedure.description if procedure else 'N/A'}")
                print(f"      Payer: {price.payer_name}")
                print(f"      Rate: ${price.negotiated_rate:.2f}")
        
        return provider_id, loaded_count
    
    def test_csv_export(self, test_db, real_llm, real_mrfs_dir, output_dir):
        """Test 5: Export Results to CSV"""
        print("\n" + "="*80)
        print("TEST 5: EXPORT RESULTS TO CSV")
        print("="*80)
        
        # Parse, validate, and load
        test_file = real_mrfs_dir / "431240629_freeman-neosho-hospital_standardcharges.json"
        parser = AdaptiveParsingAgent(llm_client=real_llm)
        all_records = parser.parse_hospital_file(str(test_file))
        records = all_records[:50]  # Limit to first 50 for testing
        
        validator = DataValidator()
        valid_records, _ = validator.validate_records(records)
        
        loader = DatabaseLoader(test_db)
        provider_id = loader.create_provider(
            name="Freeman Neosho Hospital",
            npi="431240629"
        )
        loader.load_parsed_records(valid_records, provider_id, str(test_file))
        
        # Export to CSV
        csv_path = output_dir / "parsed_results.csv"
        
        with test_db.session_scope() as session:
            prices = session.query(PriceTransparency).join(Procedure).filter(
                PriceTransparency.provider_id == provider_id
            ).all()
            
            print(f"\n✓ Exporting {len(prices)} records to CSV...")
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'hospital_name',
                    'npi',
                    'cpt_code',
                    'procedure_description',
                    'payer_name',
                    'negotiated_rate',
                    'standard_charge',
                    'confidence_score',
                    'source_file'
                ])
                writer.writeheader()
                
                for price in prices:
                    provider = session.query(Provider).filter_by(id=price.provider_id).first()
                    procedure = session.query(Procedure).filter_by(cpt_code=price.cpt_code).first()
                    
                    writer.writerow({
                        'hospital_name': provider.name if provider else 'Unknown',
                        'npi': provider.npi if provider else '',
                        'cpt_code': price.cpt_code,
                        'procedure_description': procedure.description if procedure else '',
                        'payer_name': price.payer_name,
                        'negotiated_rate': price.negotiated_rate,
                        'standard_charge': price.standard_charge or '',
                        'confidence_score': price.confidence_score,
                        'source_file': str(test_file)
                    })
        
        assert csv_path.exists(), "CSV file should be created"
        csv_size = csv_path.stat().st_size / 1024
        
        print(f"✓ Created: {csv_path}")
        print(f"✓ Size: {csv_size:.2f} KB")
        
        # Verify CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) > 0, "CSV should have data rows"
            
            print(f"✓ CSV has {len(rows)} data rows")
            print("\nSample CSV rows:")
            for i, row in enumerate(rows[:3], 1):
                print(f"\n  [{i}] {row['cpt_code']}: {row['procedure_description'][:40]}...")
                print(f"      Payer: {row['payer_name']}")
                print(f"      Rate: ${float(row['negotiated_rate']):.2f}")
        
        return csv_path
    
    def test_complete_pipeline_with_web_discovery(self, test_db, real_llm, output_dir):
        """Test 6: Complete Pipeline with Web Discovery (uses local files as fallback)"""
        print("\n" + "="*80)
        print("TEST 6: COMPLETE PIPELINE END-TO-END")
        print("="*80)
        
        # Step 1: File Discovery
        print("\n[Step 1] File Discovery")
        print("-" * 40)
        
        agent = FileDiscoveryAgent()
        discovered = agent.discover_local_files(hospital_name="Freeman")
        
        assert len(discovered) > 0, "Should discover files"
        print(f"✓ Discovered {len(discovered)} files")
        
        # Use first discovered file
        file_to_parse = discovered[0]['path']
        hospital_name = discovered[0]['hospital']
        print(f"✓ Selected: {Path(file_to_parse).name}")
        
        # Step 2: Parse with LLM
        print("\n[Step 2] Parse with LLM")
        print("-" * 40)
        
        parser = AdaptiveParsingAgent(llm_client=real_llm)
        all_records = parser.parse_hospital_file(file_to_parse)
        records = all_records[:50]  # Limit to first 50 for testing
        
        print(f"✓ Parsed {len(records)} records")
        
        # Step 3: Validate
        print("\n[Step 3] Validate Records")
        print("-" * 40)
        
        validator = DataValidator()
        valid_records, flagged_records = validator.validate_records(records)
        
        print(f"✓ Valid: {len(valid_records)}")
        print(f"✓ Flagged: {len(flagged_records)}")
        
        # Step 4: Load to Database
        print("\n[Step 4] Load to Database")
        print("-" * 40)
        
        loader = DatabaseLoader(test_db)
        provider_id = loader.create_provider(
            name=hospital_name,
            npi="1234567890"
        )
        
        loaded = loader.load_parsed_records(
            valid_records,
            provider_id,
            file_to_parse
        )
        
        print(f"✓ Loaded {loaded} records")
        
        # Step 5: Export to CSV
        print("\n[Step 5] Export to CSV")
        print("-" * 40)
        
        csv_path = output_dir / "complete_pipeline_results.csv"
        
        with test_db.session_scope() as session:
            prices = session.query(PriceTransparency).filter_by(provider_id=provider_id).all()
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'hospital_name', 'cpt_code', 'procedure_description',
                    'payer_name', 'negotiated_rate', 'confidence_score'
                ])
                writer.writeheader()
                
                for price in prices:
                    provider = session.query(Provider).filter_by(id=provider_id).first()
                    procedure = session.query(Procedure).filter_by(cpt_code=price.cpt_code).first()
                    
                    writer.writerow({
                        'hospital_name': provider.name if provider else '',
                        'cpt_code': price.cpt_code,
                        'procedure_description': procedure.description if procedure else '',
                        'payer_name': price.payer_name,
                        'negotiated_rate': price.negotiated_rate,
                        'confidence_score': price.confidence_score
                    })
        
        print(f"✓ Created: {csv_path.name}")
        
        # Final Summary
        print("\n" + "="*80)
        print("PIPELINE SUMMARY")
        print("="*80)
        print(f"✓ Files discovered: {len(discovered)}")
        print(f"✓ Records parsed: {len(records)}")
        print(f"✓ Valid records: {len(valid_records)}")
        print(f"✓ Database loaded: {loaded}")
        print(f"✓ CSV exported: {csv_path.name}")
        print("\n✓ COMPLETE PIPELINE SUCCESS!")
        
        return {
            'discovered': len(discovered),
            'parsed': len(records),
            'valid': len(valid_records),
            'loaded': loaded,
            'csv_path': str(csv_path)
        }


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s'])
