"""
Adaptive Parsing Agent - LLM-powered hospital file parser
Uses LLM to adaptively parse varying hospital transparency file formats
"""

import json
import csv
import hashlib
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AdaptiveParsingAgent:
    """
    LLM-powered agent that adapts to any hospital file format
    
    Key features:
    - Automatic format detection (JSON, CSV, XML)
    - Schema inference using LLM
    - Field mapping to standard schema
    - CPT code extraction from free text
    - Payer name normalization
    - Schema caching for performance
    """
    
    def __init__(self, llm_client=None, cache_dir: str = None):
        """
        Initialize the adaptive parsing agent
        
        Args:
            llm_client: LLM client for schema inference (optional for testing)
            cache_dir: Directory to cache learned schemas
        """
        self.llm = llm_client
        self.schema_cache = {}
        
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(__file__),
                '..',
                'data',
                'schema_cache'
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load cached schemas
        self._load_schema_cache()
    
    def _load_schema_cache(self):
        """Load previously learned schemas from disk"""
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r') as f:
                    file_hash = cache_file.stem
                    self.schema_cache[file_hash] = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {e}")
    
    def _save_schema_to_cache(self, file_hash: str, schema_mapping: Dict):
        """Save learned schema to disk"""
        cache_file = self.cache_dir / f"{file_hash}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(schema_mapping, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache file {cache_file}: {e}")
    
    def parse_hospital_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse any hospital price transparency file
        
        Args:
            file_path: Path to the hospital file
            
        Returns:
            List of standardized price records
        """
        logger.info(f"Parsing file: {file_path}")
        
        # Step 1: Detect format
        file_format = self.detect_format(file_path)
        logger.info(f"Detected format: {file_format}")
        
        # Step 2: Load sample of data
        sample = self.load_sample(file_path, file_format, n_rows=20)
        logger.info(f"Loaded {len(sample)} sample records")
        
        # Step 3: LLM infers schema
        schema_mapping = self.infer_schema(sample, file_path)
        logger.info(f"Schema mapping: {schema_mapping}")
        
        # Step 4: Parse full file using inferred schema
        all_records = []
        for chunk in self.chunk_file(file_path, file_format):
            records = self.extract_records(chunk, schema_mapping)
            all_records.extend(records)
        
        logger.info(f"Extracted {len(all_records)} total records")
        
        # Step 5: Validate and normalize
        normalized = self.normalize_records(all_records)
        logger.info(f"Normalized to {len(normalized)} valid records")
        
        return normalized
    
    def detect_format(self, file_path: str) -> str:
        """Detect file format based on extension and content"""
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith('.json'):
            return 'json'
        elif file_path_lower.endswith('.csv'):
            return 'csv'
        elif file_path_lower.endswith('.xml'):
            return 'xml'
        elif file_path_lower.endswith('.zip'):
            return 'zip'
        else:
            # Try to detect by reading first bytes
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(100).decode('utf-8', errors='ignore')
                    if header.strip().startswith('{') or header.strip().startswith('['):
                        return 'json'
                    elif header.strip().startswith('<'):
                        return 'xml'
                    else:
                        return 'csv'  # Default to CSV
            except Exception:
                return 'csv'
    
    def load_sample(self, file_path: str, file_format: str, n_rows: int = 20) -> List[Dict]:
        """Load a sample of data from the file"""
        if file_format == 'json':
            return self._load_json_sample(file_path, n_rows)
        elif file_format == 'csv':
            return self._load_csv_sample(file_path, n_rows)
        else:
            raise ValueError(f"Unsupported format: {file_format}")
    
    def _load_json_sample(self, file_path: str, n_rows: int) -> List[Dict]:
        """Load sample from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                return data[:n_rows]
            elif isinstance(data, dict):
                # Find the key containing the data array
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        return value[:n_rows]
                return [data]
            else:
                return []
    
    def _load_csv_sample(self, file_path: str, n_rows: int) -> List[Dict]:
        """Load sample from CSV file"""
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= n_rows:
                    break
                records.append(row)
        return records
    
    def infer_schema(self, sample_data: List[Dict], file_path: str) -> Dict[str, Optional[str]]:
        """
        Use LLM to map file schema to standard schema
        
        Args:
            sample_data: Sample records from the file
            file_path: Path to the file (for caching)
            
        Returns:
            Mapping from standard fields to file fields
        """
        # Check cache first
        file_hash = self._hash_file(file_path)
        if file_hash in self.schema_cache:
            logger.info(f"Using cached schema for {file_hash}")
            return self.schema_cache[file_hash]
        
        if self.llm is None:
            # Fallback: Use heuristic matching
            logger.warning("No LLM client provided, using heuristic schema matching")
            schema_mapping = self._heuristic_schema_matching(sample_data)
        else:
            # Use LLM for schema inference
            schema_mapping = self._llm_schema_inference(sample_data)
        
        # Cache the mapping
        self.schema_cache[file_hash] = schema_mapping
        self._save_schema_to_cache(file_hash, schema_mapping)
        
        return schema_mapping
    
    def _hash_file(self, file_path: str) -> str:
        """Generate hash of file for caching"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            # Hash first 1MB to avoid reading huge files
            hasher.update(f.read(1024 * 1024))
        return hasher.hexdigest()
    
    def _heuristic_schema_matching(self, sample_data: List[Dict]) -> Dict[str, Optional[str]]:
        """
        Fallback heuristic matching when LLM is not available
        Looks for common field name patterns
        """
        if not sample_data:
            return {}
        
        fields = list(sample_data[0].keys())
        mapping = {}
        
        # Common patterns for each standard field
        patterns = {
            'provider_name': ['hospital', 'facility', 'provider', 'name'],
            'provider_npi': ['npi', 'provider_id', 'national_provider'],
            'cpt_code': ['cpt', 'code', 'procedure_code', 'hcpcs'],
            'procedure_description': ['description', 'procedure', 'service'],
            'payer_name': ['payer', 'insurance', 'carrier', 'plan'],
            'negotiated_rate': ['negotiated', 'rate', 'amount', 'price'],
            'standard_charge': ['standard', 'gross', 'charge', 'list_price']
        }
        
        for std_field, search_patterns in patterns.items():
            mapping[std_field] = None
            for field in fields:
                field_lower = field.lower().replace('_', '').replace(' ', '')
                for pattern in search_patterns:
                    if pattern in field_lower:
                        mapping[std_field] = field
                        break
                if mapping[std_field]:
                    break
        
        return mapping
    
    def _llm_schema_inference(self, sample_data: List[Dict]) -> Dict[str, Optional[str]]:
        """Use LLM to infer schema mapping"""
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

Return ONLY a JSON object mapping standard fields to file fields:
{{
    "provider_name": "field_name_in_file",
    "cpt_code": "field_name_in_file",
    ...
}}

If a field doesn't exist, use null.
Return ONLY the JSON, no explanations.
"""
        
        response = self.llm.complete(prompt, temperature=0.1)
        
        # Parse LLM response
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_clean = response.strip()
            if response_clean.startswith('```'):
                # Remove markdown code fences
                lines = response_clean.split('\n')
                response_clean = '\n'.join(lines[1:-1])
            if response_clean.startswith('json'):
                response_clean = response_clean[4:].strip()
            
            mapping = json.loads(response_clean)
            return mapping
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response}")
            # Fallback to heuristic
            return self._heuristic_schema_matching(sample_data)
    
    def chunk_file(self, file_path: str, file_format: str, chunk_size: int = 1000):
        """
        Yield chunks of records from file
        
        Args:
            file_path: Path to file
            file_format: Format of file
            chunk_size: Number of records per chunk
            
        Yields:
            Lists of records
        """
        if file_format == 'json':
            yield from self._chunk_json(file_path, chunk_size)
        elif file_format == 'csv':
            yield from self._chunk_csv(file_path, chunk_size)
    
    def _chunk_json(self, file_path: str, chunk_size: int):
        """Yield chunks from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            
            # Find the data array
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                # Find the key containing the data array
                records = []
                for value in data.values():
                    if isinstance(value, list) and len(value) > 0:
                        records = value
                        break
            else:
                records = []
            
            # Yield in chunks
            for i in range(0, len(records), chunk_size):
                yield records[i:i + chunk_size]
    
    def _chunk_csv(self, file_path: str, chunk_size: int):
        """Yield chunks from CSV file"""
        chunk = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                chunk.append(row)
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
            
            # Yield final chunk
            if chunk:
                yield chunk
    
    def extract_records(self, chunk: List[Dict], schema_mapping: Dict) -> List[Dict]:
        """
        Extract records using schema mapping
        
        Args:
            chunk: List of raw records
            schema_mapping: Mapping from standard to file fields
            
        Returns:
            List of records with standard fields
        """
        records = []
        
        for row in chunk:
            try:
                record = {}
                
                # Map fields using schema
                for std_field, file_field in schema_mapping.items():
                    if file_field and file_field in row:
                        record[std_field] = row[file_field]
                    else:
                        record[std_field] = None
                
                # Handle special cases
                if not record.get('cpt_code') and record.get('procedure_description'):
                    record['cpt_code'] = self.extract_cpt_from_text(
                        record['procedure_description']
                    )
                
                if record.get('payer_name'):
                    record['payer_name'] = self.normalize_payer_name(
                        record['payer_name']
                    )
                
                records.append(record)
                
            except Exception as e:
                logger.error(f"Failed to extract record: {e}")
                continue
        
        return records
    
    def extract_cpt_from_text(self, description: str) -> Optional[str]:
        """
        Extract CPT code from free-text description
        
        For hackathon: Use regex pattern matching
        For production: Could use LLM
        """
        if not description:
            return None
        
        import re
        
        # Pattern for CPT codes: 5 digits
        match = re.search(r'\b\d{5}\b', description)
        if match:
            return match.group(0)
        
        # Pattern for HCPCS codes: 1 letter + 4 digits
        match = re.search(r'\b[A-Z]\d{4}\b', description)
        if match:
            return match.group(0)
        
        return None
    
    def normalize_payer_name(self, payer: str) -> str:
        """
        Standardize insurance carrier names
        
        For hackathon: Use lookup table
        For production: Could use LLM
        """
        if not payer:
            return payer
        
        # Common normalizations
        normalizations = {
            'bcbs': 'Blue Cross Blue Shield',
            'blue cross': 'Blue Cross Blue Shield',
            'united healthcare': 'UnitedHealthcare',
            'united health': 'UnitedHealthcare',
            'aetna inc': 'Aetna',
            'cigna corporation': 'Cigna',
            'humana inc': 'Humana',
        }
        
        payer_lower = payer.lower().strip()
        for pattern, normalized in normalizations.items():
            if pattern in payer_lower:
                return normalized
        
        # Remove common suffixes
        payer = payer.replace(' Inc.', '').replace(' LLC', '').replace(' Corp', '')
        
        return payer.strip()
    
    def normalize_records(self, records: List[Dict]) -> List[Dict]:
        """
        Validate and normalize records
        
        Args:
            records: Raw extracted records
            
        Returns:
            List of validated records
        """
        normalized = []
        
        for record in records:
            # Skip records without required fields
            if not record.get('cpt_code'):
                continue
            
            # Convert price fields to float
            for field in ['negotiated_rate', 'standard_charge', 'min_negotiated_rate', 'max_negotiated_rate']:
                if record.get(field):
                    try:
                        # Handle string prices like "$1,234.56"
                        value = str(record[field]).replace('$', '').replace(',', '').strip()
                        record[field] = float(value) if value else None
                    except (ValueError, TypeError):
                        record[field] = None
            
            # Add confidence score (simple heuristic)
            required_fields = ['cpt_code', 'negotiated_rate', 'payer_name']
            present = sum(1 for f in required_fields if record.get(f))
            record['confidence_score'] = present / len(required_fields)
            
            normalized.append(record)
        
        return normalized
