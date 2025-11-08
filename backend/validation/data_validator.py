"""
Data Validation Module
Validates parsed healthcare pricing data for quality and correctness
"""

import logging
from typing import List, Dict, Any, Tuple
from statistics import mean, median, stdev

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validates healthcare pricing data
    
    Features:
    - Outlier detection vs Medicare baseline
    - Price reasonableness checks
    - Required field validation
    - Confidence scoring
    """
    
    def __init__(self, medicare_baseline: Dict[str, float] = None):
        """
        Initialize validator
        
        Args:
            medicare_baseline: Dict mapping CPT codes to Medicare rates
        """
        self.medicare_baseline = medicare_baseline or {}
    
    def validate_records(
        self,
        records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validate records and flag issues
        
        Args:
            records: List of parsed records
            
        Returns:
            Tuple of (valid_records, flagged_records)
        """
        valid = []
        flagged = []
        
        for record in records:
            issues = self.check_record(record)
            
            if issues:
                record['validation_issues'] = issues
                flagged.append(record)
                logger.warning(f"Flagged record {record.get('cpt_code')}: {issues}")
            else:
                valid.append(record)
        
        logger.info(f"Validation: {len(valid)} valid, {len(flagged)} flagged")
        return valid, flagged
    
    def check_record(self, record: Dict[str, Any]) -> List[str]:
        """
        Check a single record for issues
        
        Returns:
            List of issue descriptions (empty if valid)
        """
        issues = []
        
        # Check required fields
        if not record.get('cpt_code'):
            issues.append("Missing CPT code")
        
        if not record.get('negotiated_rate') and not record.get('standard_charge'):
            issues.append("Missing both negotiated rate and standard charge")
        
        # Check price reasonableness
        negotiated_rate = record.get('negotiated_rate')
        if negotiated_rate:
            # Check for obviously wrong values
            if negotiated_rate < 0:
                issues.append(f"Negative price: {negotiated_rate}")
            elif negotiated_rate == 0:
                issues.append("Zero price")
            elif negotiated_rate > 1000000:  # $1M seems excessive
                issues.append(f"Unusually high price: ${negotiated_rate:,.2f}")
            
            # Check vs Medicare baseline if available
            cpt_code = record.get('cpt_code')
            if cpt_code and cpt_code in self.medicare_baseline:
                medicare_rate = self.medicare_baseline[cpt_code]
                ratio = negotiated_rate / medicare_rate
                
                # Commercial rates typically 1.5x - 5x Medicare
                if ratio < 0.5:
                    issues.append(f"Price suspiciously low vs Medicare: {ratio:.1f}x")
                elif ratio > 10:
                    issues.append(f"Price very high vs Medicare: {ratio:.1f}x")
        
        # Check min/max consistency
        min_rate = record.get('min_negotiated_rate')
        max_rate = record.get('max_negotiated_rate')
        if min_rate and max_rate and min_rate > max_rate:
            issues.append(f"Min rate ({min_rate}) > Max rate ({max_rate})")
        
        # Check payer name
        if not record.get('payer_name'):
            issues.append("Missing payer name")
        
        return issues
    
    def calculate_confidence_score(self, record: Dict[str, Any]) -> float:
        """
        Calculate confidence score for a record (0-1)
        
        Higher score = more complete and reliable data
        """
        score = 0.0
        total_weight = 0.0
        
        # Required fields (40% weight)
        required_fields = ['cpt_code', 'negotiated_rate', 'payer_name']
        required_weight = 0.4
        required_present = sum(1 for f in required_fields if record.get(f))
        score += (required_present / len(required_fields)) * required_weight
        total_weight += required_weight
        
        # Optional fields (20% weight)
        optional_fields = ['provider_name', 'procedure_description', 'standard_charge']
        optional_weight = 0.2
        optional_present = sum(1 for f in optional_fields if record.get(f))
        score += (optional_present / len(optional_fields)) * optional_weight
        total_weight += optional_weight
        
        # Price consistency (20% weight)
        consistency_weight = 0.2
        if record.get('negotiated_rate') and record.get('standard_charge'):
            # Negotiated should be less than standard
            if record['negotiated_rate'] <= record['standard_charge']:
                score += consistency_weight
        total_weight += consistency_weight
        
        # Medicare baseline check (20% weight)
        baseline_weight = 0.2
        if record.get('cpt_code') and record.get('negotiated_rate'):
            cpt_code = record['cpt_code']
            if cpt_code in self.medicare_baseline:
                medicare_rate = self.medicare_baseline[cpt_code]
                ratio = record['negotiated_rate'] / medicare_rate
                # Ideal ratio: 1.5x - 5x Medicare
                if 1.5 <= ratio <= 5:
                    score += baseline_weight
                elif 0.5 <= ratio <= 10:
                    score += baseline_weight * 0.5
        total_weight += baseline_weight
        
        return min(score / total_weight if total_weight > 0 else 0, 1.0)
    
    def detect_outliers(
        self,
        records: List[Dict[str, Any]],
        cpt_code: str,
        threshold: float = 3.0
    ) -> List[Dict[str, Any]]:
        """
        Detect outlier prices for a specific CPT code
        
        Args:
            records: List of records
            cpt_code: CPT code to check
            threshold: Number of standard deviations for outlier
            
        Returns:
            List of outlier records
        """
        # Filter to this CPT code
        cpt_records = [
            r for r in records
            if r.get('cpt_code') == cpt_code and r.get('negotiated_rate')
        ]
        
        if len(cpt_records) < 3:
            return []  # Need at least 3 points
        
        # Get prices
        prices = [r['negotiated_rate'] for r in cpt_records]
        
        # Calculate statistics
        avg = mean(prices)
        med = median(prices)
        std = stdev(prices) if len(prices) > 1 else 0
        
        if std == 0:
            return []
        
        # Find outliers
        outliers = []
        for record in cpt_records:
            price = record['negotiated_rate']
            z_score = abs(price - avg) / std
            
            if z_score > threshold:
                record['outlier_info'] = {
                    'z_score': z_score,
                    'average': avg,
                    'median': med,
                    'std_dev': std
                }
                outliers.append(record)
        
        return outliers
    
    def generate_validation_report(
        self,
        valid_records: List[Dict],
        flagged_records: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate validation summary report
        
        Returns:
            Dict with validation statistics
        """
        total = len(valid_records) + len(flagged_records)
        
        report = {
            'total_records': total,
            'valid_count': len(valid_records),
            'flagged_count': len(flagged_records),
            'valid_rate': len(valid_records) / total if total > 0 else 0,
            'common_issues': self._count_issues(flagged_records),
            'cpt_coverage': self._count_unique_cpts(valid_records)
        }
        
        # Calculate average confidence
        if valid_records:
            confidences = [
                self.calculate_confidence_score(r) for r in valid_records
            ]
            report['avg_confidence'] = mean(confidences)
        else:
            report['avg_confidence'] = 0
        
        return report
    
    def _count_issues(self, flagged_records: List[Dict]) -> Dict[str, int]:
        """Count frequency of each issue type"""
        issue_counts = {}
        
        for record in flagged_records:
            for issue in record.get('validation_issues', []):
                # Extract issue type (first part before colon)
                issue_type = issue.split(':')[0]
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        return issue_counts
    
    def _count_unique_cpts(self, records: List[Dict]) -> int:
        """Count unique CPT codes"""
        return len(set(r.get('cpt_code') for r in records if r.get('cpt_code')))
