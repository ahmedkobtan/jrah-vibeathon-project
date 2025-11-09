"""
Comprehensive tests for all backend components
"""

import pytest
import json
import os
import tempfile
from pathlib import Path

# Import components to test
from database.connection import DatabaseManager, init_database
from database import Provider, Procedure, InsurancePlan, PriceTransparency
from agents.adaptive_parser import AdaptiveParsingAgent
from agents.openrouter_llm import OpenRouterLLMClient
from loaders.database_loader import DatabaseLoader
from validation.data_validator import DataValidator


# Fixtures

@pytest.fixture
def test_db():
    """Create a test database"""
    db = DatabaseManager("sqlite:///:memory:")
    db.create_tables()
    yield db
    # Cleanup happens automatically with in-memory DB


@pytest.fixture
def mock_llm():
    """Create OpenRouter LLM client with API key"""
    api_key = "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"
    return OpenRouterLLMClient(api_key=api_key, model="anthropic/claude-3.5-sonnet")


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("hospital_name,npi,code,description,payer,rate,gross_charge\n")
        f.write("Test Hospital,1234567890,70553,MRI brain,Blue Cross,1250.00,3500.00\n")
        f.write("Test Hospital,1234567890,99213,Office visit,Medicare,93.00,250.00\n")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def sample_json_file():
    """Create a sample JSON file for testing"""
    data = [
        {
            "hospital_name": "Test Hospital",
            "npi": "1234567890",
            "code": "73721",
            "description": "MRI knee",
            "payer": "Blue Cross",
            "rate": 825.00,
            "gross_charge": 2500.00
        }
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    
    yield temp_path
    
    os.unlink(temp_path)


# Database Tests

class TestDatabase:
    """Test database schema and connection"""
    
    def test_database_creation(self, test_db):
        """Test database tables are created"""
        assert test_db.engine is not None
        assert test_db.SessionLocal is not None
    
    def test_create_provider(self, test_db):
        """Test creating a provider"""
        with test_db.session_scope() as session:
            provider = Provider(
                npi="1234567890",
                name="Test Hospital",
                city="Joplin",
                state="MO",
                zip="64804"
            )
            session.add(provider)
            session.flush()
            assert provider.id is not None
    
    def test_create_procedure(self, test_db):
        """Test creating a procedure"""
        with test_db.session_scope() as session:
            procedure = Procedure(
                cpt_code="70553",
                description="MRI brain without and with contrast",
                category="Imaging",
                medicare_rate=423.00
            )
            session.add(procedure)
            session.flush()
            assert procedure.cpt_code == "70553"
    
    def test_create_price_record(self, test_db):
        """Test creating price transparency record"""
        with test_db.session_scope() as session:
            # First create provider and procedure
            provider = Provider(npi="1234567890", name="Test Hospital")
            procedure = Procedure(cpt_code="70553", description="MRI brain")
            session.add(provider)
            session.add(procedure)
            session.flush()
            
            # Create price record
            price = PriceTransparency(
                provider_id=provider.id,
                cpt_code=procedure.cpt_code,
                payer_name="Blue Cross Blue Shield",
                negotiated_rate=1250.00,
                standard_charge=3500.00,
                confidence_score=0.95
            )
            session.add(price)
            session.flush()
            assert price.id is not None
            assert price.negotiated_rate == 1250.00


# Adaptive Parser Tests

class TestAdaptiveParser:
    """Test adaptive parsing agent"""
    
    def test_parser_initialization(self, mock_llm):
        """Test parser initializes correctly"""
        parser = AdaptiveParsingAgent(llm_client=mock_llm)
        assert parser.llm is not None
        assert parser.schema_cache is not None
    
    def test_detect_csv_format(self, sample_csv_file):
        """Test CSV format detection"""
        parser = AdaptiveParsingAgent()
        format_type = parser.detect_format(sample_csv_file)
        assert format_type == 'csv'
    
    def test_detect_json_format(self, sample_json_file):
        """Test JSON format detection"""
        parser = AdaptiveParsingAgent()
        format_type = parser.detect_format(sample_json_file)
        assert format_type == 'json'
    
    def test_load_csv_sample(self, sample_csv_file):
        """Test loading CSV sample"""
        parser = AdaptiveParsingAgent()
        sample = parser.load_sample(sample_csv_file, 'csv', n_rows=5)
        assert len(sample) == 2  # Sample file has 2 records
        assert 'hospital_name' in sample[0]
        assert sample[0]['hospital_name'] == 'Test Hospital'
    
    def test_load_json_sample(self, sample_json_file):
        """Test loading JSON sample"""
        parser = AdaptiveParsingAgent()
        sample = parser.load_sample(sample_json_file, 'json', n_rows=5)
        assert len(sample) == 1
        assert sample[0]['code'] == '73721'
    
    def test_heuristic_schema_matching(self):
        """Test heuristic schema matching"""
        parser = AdaptiveParsingAgent()
        sample = [
            {
                'hospital_name': 'Test',
                'code': '12345',
                'payer': 'BCBS',
                'rate': '1250.00'
            }
        ]
        mapping = parser._heuristic_schema_matching(sample)
        assert mapping['provider_name'] == 'hospital_name'
        assert mapping['cpt_code'] == 'code'
        assert mapping['payer_name'] == 'payer'
        assert mapping['negotiated_rate'] == 'rate'
    
    def test_extract_cpt_from_text(self):
        """Test CPT code extraction"""
        parser = AdaptiveParsingAgent()
        
        # Test 5-digit CPT
        assert parser.extract_cpt_from_text("MRI scan 70553 procedure") == "70553"
        
        # Test HCPCS code
        assert parser.extract_cpt_from_text("HCPCS code A1234") == "A1234"
        
        # Test no code
        assert parser.extract_cpt_from_text("No code here") is None
    
    def test_normalize_payer_name(self):
        """Test payer name normalization"""
        parser = AdaptiveParsingAgent()
        
        assert "Blue Cross" in parser.normalize_payer_name("BCBS Missouri")
        assert parser.normalize_payer_name("United Healthcare") == "UnitedHealthcare"
        assert parser.normalize_payer_name("Aetna Inc") == "Aetna"
    
    def test_parse_full_csv_file(self, sample_csv_file, mock_llm):
        """Test parsing complete CSV file"""
        parser = AdaptiveParsingAgent(llm_client=mock_llm)
        records = parser.parse_hospital_file(sample_csv_file)
        
        assert len(records) > 0
        assert all('cpt_code' in r for r in records)
        assert all('confidence_score' in r for r in records)
    
    def test_parse_full_json_file(self, sample_json_file, mock_llm):
        """Test parsing complete JSON file"""
        parser = AdaptiveParsingAgent(llm_client=mock_llm)
        records = parser.parse_hospital_file(sample_json_file)
        
        assert len(records) > 0
        assert records[0]['cpt_code'] == '73721'


# Database Loader Tests

class TestDatabaseLoader:
    """Test database loader"""
    
    def test_loader_initialization(self, test_db):
        """Test loader initializes"""
        loader = DatabaseLoader(test_db)
        assert loader.db is not None
    
    def test_create_provider(self, test_db):
        """Test creating provider via loader"""
        loader = DatabaseLoader(test_db)
        provider_id = loader.create_provider(
            name="Freeman Health System",
            npi="1234567890",
            city="Joplin",
            state="MO",
            zip_code="64804"
        )
        assert provider_id > 0
    
    def test_load_parsed_records(self, test_db):
        """Test loading parsed records"""
        loader = DatabaseLoader(test_db)
        
        # Create provider first
        provider_id = loader.create_provider(name="Test Hospital", npi="1234567890")
        
        # Load records
        records = [
            {
                'cpt_code': '70553',
                'procedure_description': 'MRI brain',
                'payer_name': 'Blue Cross',
                'negotiated_rate': 1250.00,
                'confidence_score': 0.9
            },
            {
                'cpt_code': '99213',
                'procedure_description': 'Office visit',
                'payer_name': 'Medicare',
                'negotiated_rate': 93.00,
                'confidence_score': 1.0
            }
        ]
        
        loaded_count = loader.load_parsed_records(
            records, provider_id, "test_file.csv"
        )
        
        assert loaded_count == 2
    
    def test_bulk_create_procedures(self, test_db):
        """Test bulk procedure creation"""
        loader = DatabaseLoader(test_db)
        
        procedures = [
            {'cpt_code': '70553', 'description': 'MRI brain', 'medicare_rate': 423.00},
            {'cpt_code': '73721', 'description': 'MRI knee', 'medicare_rate': 275.00}
        ]
        
        created = loader.bulk_create_procedures(procedures)
        assert created == 2


# Data Validator Tests

class TestDataValidator:
    """Test data validator"""
    
    def test_validator_initialization(self):
        """Test validator initializes"""
        medicare_baseline = {'70553': 423.00, '73721': 275.00}
        validator = DataValidator(medicare_baseline)
        assert validator.medicare_baseline == medicare_baseline
    
    def test_validate_good_record(self):
        """Test validation of good record"""
        validator = DataValidator({'70553': 423.00})
        record = {
            'cpt_code': '70553',
            'negotiated_rate': 1250.00,
            'payer_name': 'Blue Cross',
            'standard_charge': 3500.00
        }
        issues = validator.check_record(record)
        assert len(issues) == 0
    
    def test_validate_missing_cpt(self):
        """Test validation catches missing CPT"""
        validator = DataValidator()
        record = {'negotiated_rate': 1250.00}
        issues = validator.check_record(record)
        assert any('CPT' in issue for issue in issues)
    
    def test_validate_negative_price(self):
        """Test validation catches negative price"""
        validator = DataValidator()
        record = {
            'cpt_code': '70553',
            'negotiated_rate': -100.00,
            'payer_name': 'Blue Cross'
        }
        issues = validator.check_record(record)
        assert any('Negative' in issue for issue in issues)
    
    def test_validate_vs_medicare_baseline(self):
        """Test validation against Medicare baseline"""
        validator = DataValidator({'70553': 423.00})
        
        # Too low
        record_low = {
            'cpt_code': '70553',
            'negotiated_rate': 100.00,  # 0.24x Medicare
            'payer_name': 'Blue Cross'
        }
        issues_low = validator.check_record(record_low)
        assert any('suspiciously low' in issue.lower() for issue in issues_low)
        
        # Too high
        record_high = {
            'cpt_code': '70553',
            'negotiated_rate': 5000.00,  # 11.8x Medicare
            'payer_name': 'Blue Cross'
        }
        issues_high = validator.check_record(record_high)
        assert any('very high' in issue.lower() for issue in issues_high)
    
    def test_confidence_score_calculation(self):
        """Test confidence score calculation"""
        validator = DataValidator({'70553': 423.00})
        
        # Complete record
        complete_record = {
            'cpt_code': '70553',
            'negotiated_rate': 1250.00,
            'payer_name': 'Blue Cross',
            'provider_name': 'Test Hospital',
            'procedure_description': 'MRI brain',
            'standard_charge': 3500.00
        }
        score = validator.calculate_confidence_score(complete_record)
        assert score > 0.8
        
        # Minimal record
        minimal_record = {
            'cpt_code': '70553',
            'negotiated_rate': 1250.00
        }
        score_min = validator.calculate_confidence_score(minimal_record)
        assert score_min < score
    
    def test_detect_outliers(self):
        """Test outlier detection"""
        validator = DataValidator()
        
        # Create a tight cluster with one clear outlier
        records = [
            {'cpt_code': '70553', 'negotiated_rate': 1200.00},
            {'cpt_code': '70553', 'negotiated_rate': 1220.00},
            {'cpt_code': '70553', 'negotiated_rate': 1250.00},
            {'cpt_code': '70553', 'negotiated_rate': 1280.00},
            {'cpt_code': '70553', 'negotiated_rate': 5000.00},  # Clear outlier (4x avg)
        ]
        
        # Use lower threshold to ensure detection
        outliers = validator.detect_outliers(records, '70553', threshold=1.5)
        assert len(outliers) >= 1
        # Verify the outlier is the high value
        assert any(r['negotiated_rate'] == 5000.00 for r in outliers)
    
    def test_validation_report(self):
        """Test validation report generation"""
        validator = DataValidator()
        
        valid_records = [
            {'cpt_code': '70553', 'negotiated_rate': 1250.00, 'payer_name': 'BCBS'},
            {'cpt_code': '73721', 'negotiated_rate': 825.00, 'payer_name': 'Medicare'}
        ]
        
        flagged_records = [
            {
                'cpt_code': '99999',
                'validation_issues': ['Missing CPT code', 'Zero price']
            }
        ]
        
        report = validator.generate_validation_report(valid_records, flagged_records)
        
        assert report['total_records'] == 3
        assert report['valid_count'] == 2
        assert report['flagged_count'] == 1
        assert 0 < report['valid_rate'] < 1


# Integration Tests

class TestIntegration:
    """Integration tests for complete pipeline"""
    
    def test_end_to_end_pipeline(self, test_db, sample_csv_file, mock_llm):
        """Test complete pipeline from file to database"""
        
        # 1. Parse file
        parser = AdaptiveParsingAgent(llm_client=mock_llm)
        parsed_records = parser.parse_hospital_file(sample_csv_file)
        assert len(parsed_records) > 0
        
        # 2. Validate records
        validator = DataValidator({'70553': 423.00, '99213': 93.00})
        valid_records, flagged_records = validator.validate_records(parsed_records)
        assert len(valid_records) > 0
        
        # 3. Load into database
        loader = DatabaseLoader(test_db)
        provider_id = loader.create_provider(
            name="Test Hospital",
            npi="1234567890"
        )
        
        loaded_count = loader.load_parsed_records(
            valid_records,
            provider_id,
            sample_csv_file
        )
        
        assert loaded_count > 0
        
        # 4. Verify data in database
        with test_db.session_scope() as session:
            prices = session.query(PriceTransparency).all()
            assert len(prices) == loaded_count
    
    def test_pipeline_with_bad_data(self, test_db, mock_llm):
        """Test pipeline handles bad data gracefully"""
        
        # Create file with bad data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("hospital_name,code,payer,rate\n")
            f.write("Test Hospital,,BCBS,1250.00\n")  # Missing CPT
            f.write("Test Hospital,70553,,-100.00\n")  # Missing payer, negative price
            temp_path = f.name
        
        try:
            parser = AdaptiveParsingAgent(llm_client=mock_llm)
            parsed_records = parser.parse_hospital_file(temp_path)
            
            validator = DataValidator()
            valid_records, flagged_records = validator.validate_records(parsed_records)
            
            # Should have flagged the bad records
            assert len(flagged_records) > 0
            
        finally:
            os.unlink(temp_path)




if __name__ == '__main__':
    pytest.main([__file__, '-v'])
