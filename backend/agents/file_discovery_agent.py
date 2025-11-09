"""
File Discovery Agent
Uses LLM to find and validate real hospital price transparency files
"""

import re
import requests
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import time

logger = logging.getLogger(__name__)


class FileDiscoveryAgent:
    """
    LLM-powered agent to discover hospital price transparency files
    """
    
    def __init__(self, llm_client=None, local_directories: List[str] = None):
        """
        Initialize file discovery agent
        
        Args:
            llm_client: LLM client for intelligent search
            local_directories: List of local directories to search for MRF files
        """
        self.llm = llm_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Healthcare Price Transparency Research Bot)'
        })
        
        # Set up local directories to search
        if local_directories is None:
            # Default: check ../real_mrfs and current directory
            import os
            from pathlib import Path
            base_dir = Path(__file__).parent.parent.parent
            local_directories = [
                str(base_dir / 'real_mrfs'),
                str(base_dir / 'downloaded_mrfs'),
                str(Path.cwd() / 'real_mrfs'),
            ]
        self.local_directories = local_directories
    
    def discover_hospital_files(self, hospital_name: str, hospital_website: str = None) -> List[Dict]:
        """
        Discover price transparency files for a hospital
        
        Args:
            hospital_name: Name of the hospital
            hospital_website: Hospital website URL (optional)
            
        Returns:
            List of discovered file URLs with metadata
        """
        discovered_files = []
        
        logger.info(f"Discovering files for: {hospital_name}")
        
        # Strategy 1: Check common URL patterns
        if hospital_website:
            common_urls = self._generate_common_urls(hospital_website)
            for url in common_urls:
                if self._validate_url(url):
                    discovered_files.append({
                        'url': url,
                        'hospital': hospital_name,
                        'source': 'common_pattern',
                        'confidence': 0.7
                    })
        
        # Strategy 2: Use LLM to generate search queries and likely URLs
        if self.llm:
            llm_suggestions = self._llm_suggest_urls(hospital_name, hospital_website)
            discovered_files.extend(llm_suggestions)
        
        # Strategy 3: Check CMS Price Transparency catalog (if available)
        cms_files = self._check_cms_catalog(hospital_name)
        discovered_files.extend(cms_files)
        
        # Deduplicate and rank by confidence
        discovered_files = self._deduplicate_and_rank(discovered_files)
        
        logger.info(f"Discovered {len(discovered_files)} potential files for {hospital_name}")
        return discovered_files
    
    def _generate_common_urls(self, base_url: str) -> List[str]:
        """
        Generate common URL patterns for price transparency files
        
        Hospitals typically host files at predictable paths
        """
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        common_paths = [
            '/price-transparency',
            '/price-transparency.json',
            '/pricing/standard-charges.json',
            '/pricing/chargemaster.csv',
            '/patients/billing/price-transparency',
            '/financial-assistance/prices',
            '/cms-price-transparency',
            '/standard-charges',
            '/chargemaster',
            '/pricing-information',
            '/price-list.json',
            '/shoppable-services.json',
            '/negotiated-rates.json',
        ]
        
        urls = []
        for path in common_paths:
            urls.append(urljoin(base, path))
        
        return urls
    
    def _validate_url(self, url: str, timeout: int = 10) -> bool:
        """
        Validate if URL exists and contains price transparency data
        
        Returns:
            True if URL is valid and accessible
        """
        try:
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            
            # Check status code
            if response.status_code != 200:
                return False
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            valid_types = ['json', 'csv', 'xml', 'text', 'application/octet-stream']
            
            if not any(t in content_type for t in valid_types):
                # Try GET request to check content
                try:
                    get_response = self.session.get(url, timeout=timeout, stream=True)
                    first_chunk = next(get_response.iter_content(1024))
                    
                    # Check if looks like data file
                    first_chunk_str = first_chunk.decode('utf-8', errors='ignore').lower()
                    has_data_indicators = any(word in first_chunk_str for word in [
                        'cpt', 'hcpcs', 'charge', 'price', 'rate', 'payer', 'insurance'
                    ])
                    
                    if not has_data_indicators:
                        return False
                        
                except Exception:
                    return False
            
            # Check file size (should be substantial for real data)
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) < 1000:  # Too small
                return False
            
            logger.info(f"✓ Valid URL found: {url}")
            return True
            
        except Exception as e:
            logger.debug(f"URL validation failed for {url}: {e}")
            return False
    
    def _llm_suggest_urls(self, hospital_name: str, website: str = None) -> List[Dict]:
        """
        Use LLM to suggest likely URLs for price transparency files
        """
        if not self.llm:
            return []
        
        try:
            prompt = f"""
            A hospital called "{hospital_name}" {f"with website {website}" if website else ""} 
            is required by CMS to publish price transparency files.
            
            These files are typically hosted at URLs containing patterns like:
            - /price-transparency
            - /pricing
            - /standard-charges
            - /chargemaster
            
            The files are usually in JSON or CSV format.
            
            Based on the hospital name{" and website" if website else ""}, suggest 3-5 most likely 
            URLs where their price transparency file might be hosted.
            
            Return only the URLs, one per line, no explanations.
            """
            
            response = self.llm.complete(prompt, temperature=0.3)
            
            # Extract URLs from response
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', response)
            
            suggested_files = []
            for url in urls[:5]:  # Limit to 5 suggestions
                if self._validate_url(url):
                    suggested_files.append({
                        'url': url,
                        'hospital': hospital_name,
                        'source': 'llm_suggestion',
                        'confidence': 0.6
                    })
            
            return suggested_files
            
        except Exception as e:
            logger.error(f"LLM URL suggestion failed: {e}")
            return []
    
    def _check_cms_catalog(self, hospital_name: str) -> List[Dict]:
        """
        Check CMS Price Transparency catalog (mock implementation)
        
        In production, this would query actual CMS databases
        """
        # For now, return empty - in production would query CMS APIs
        # CMS doesn't have a centralized API yet, but hospitals report to them
        return []
    
    def _deduplicate_and_rank(self, files: List[Dict]) -> List[Dict]:
        """
        Remove duplicates and rank by confidence
        """
        seen_urls = {}
        
        for file in files:
            url = file['url']
            if url not in seen_urls or file['confidence'] > seen_urls[url]['confidence']:
                seen_urls[url] = file
        
        # Sort by confidence
        ranked = sorted(seen_urls.values(), key=lambda x: x['confidence'], reverse=True)
        return ranked
    
    def discover_by_location(self, city: str, state: str, limit: int = 10) -> List[Dict]:
        """
        Discover hospitals in a location and their price transparency files
        
        Args:
            city: City name
            state: State code (e.g., 'MO')
            limit: Maximum number of hospitals to discover
            
        Returns:
            List of hospitals with their file URLs
        """
        logger.info(f"Discovering hospitals in {city}, {state}")
        
        # In production, would:
        # 1. Query CMS Hospital Compare database
        # 2. Get NPI registry data
        # 3. Cross-reference with transparency file submissions
        
        # For now, use known hospitals in Joplin, MO as example
        if city.lower() == 'joplin' and state.upper() == 'MO':
            known_hospitals = [
                {
                    'name': 'Freeman Health System',
                    'website': 'https://www.freemanhealth.com',
                    'npi': '1023076264'
                },
                {
                    'name': 'Mercy Hospital Joplin',
                    'website': 'https://www.mercy.net',
                    'npi': '1053398066'
                },
            ]
            
            results = []
            for hospital in known_hospitals[:limit]:
                files = self.discover_hospital_files(
                    hospital['name'],
                    hospital['website']
                )
                if files:
                    results.append({
                        'hospital': hospital['name'],
                        'npi': hospital.get('npi'),
                        'website': hospital.get('website'),
                        'files': files
                    })
            
            return results
        
        return []
    
    def discover_local_files(self, hospital_name: str = None) -> List[Dict]:
        """
        Discover price transparency files in local directories
        
        Args:
            hospital_name: Optional filter by hospital name
            
        Returns:
            List of discovered local file paths with metadata
        """
        from pathlib import Path
        
        discovered_files = []
        
        logger.info(f"Searching for local MRF files in: {self.local_directories}")
        
        for directory in self.local_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            
            # Search for JSON and CSV files
            for pattern in ['*.json', '*.csv']:
                for file_path in dir_path.glob(pattern):
                    # Check if file matches hospital name filter
                    if hospital_name:
                        if hospital_name.lower() not in file_path.name.lower():
                            continue
                    
                    # Extract hospital name from filename (e.g., "freeman" from filename)
                    file_name = file_path.stem.lower()
                    detected_hospital = None
                    if 'freeman' in file_name:
                        detected_hospital = 'Freeman Health System'
                    elif 'mercy' in file_name:
                        detected_hospital = 'Mercy Hospital'
                    
                    discovered_files.append({
                        'path': str(file_path),
                        'filename': file_path.name,
                        'hospital': detected_hospital or 'Unknown',
                        'size_mb': file_path.stat().st_size / (1024 * 1024),
                        'source': 'local_directory',
                        'confidence': 1.0  # High confidence for local files
                    })
                    
                    logger.info(f"✓ Found local file: {file_path.name} ({discovered_files[-1]['size_mb']:.2f} MB)")
        
        logger.info(f"Discovered {len(discovered_files)} local files")
        return discovered_files
    
    def download_file(self, url: str, output_path: str, timeout: int = 60) -> bool:
        """
        Download a file from URL
        
        Args:
            url: URL to download from
            output_path: Local path to save file
            timeout: Request timeout in seconds
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Downloading: {url}")
            
            response = self.session.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"✓ Downloaded to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            return False
