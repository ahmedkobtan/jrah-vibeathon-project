"""
Download Real Hospital Price Transparency Files
Downloads MRF (Machine-Readable Files) from actual hospitals
"""

import os
import requests
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Real hospital transparency file URLs (Joplin, MO area)
HOSPITAL_FILES = {
    "freeman_health": {
        "name": "Freeman Health System",
        "npi": "1234567890",  # Would be real NPI
        "url": "https://www.freemanhealth.com/price-transparency",  # Example URL
        "note": "Would need actual MRF URL"
    },
    # For testing, we'll use publicly available hospital files
    "sample_hospitals": [
        {
            "name": "Sample Hospital 1",
            "url": "https://raw.githubusercontent.com/CMSgov/price-transparency-guide/master/examples/hospital-price-transparency/",
            "note": "CMS example files"
        }
    ]
}

# Alternative: Use these known working URLs from large hospitals
KNOWN_WORKING_URLS = [
    # Stanford Health Care
    # "https://stanfordhealthcare.org/standard-charges.json",
    
    # Johns Hopkins (CSV format)
    # Note: These URLs may change - hospitals update them frequently
]


def download_file(url: str, output_path: str) -> bool:
    """
    Download a file from URL
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading from {url}")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Save to file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(output_path)
        logger.info(f"Downloaded {file_size:,} bytes to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def create_sample_mrf_files():
    """
    Create sample MRF files in various formats for testing
    These mimic real hospital file structures
    """
    data_dir = Path(__file__).parent.parent / 'data' / 'real_mrf_samples'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample 1: JSON format (like many large hospitals)
    sample1_path = data_dir / 'sample_hospital_standard_charges.json'
    sample1_data = {
        "hospital_name": "Sample Community Hospital",
        "last_updated": "2024-01-01",
        "version": "1.0",
        "standard_charge_information": [
            {
                "description": "MRI - BRAIN W/O CONTRAST",
                "code": [
                    {
                        "type": "CPT",
                        "code": "70553"
                    }
                ],
                "standard_charges": [
                    {
                        "payer_name": "Blue Cross Blue Shield",
                        "plan_name": "PPO",
                        "negotiated_dollar_amount": "1,250.00",
                        "negotiated_percentage": None
                    },
                    {
                        "payer_name": "Medicare",
                        "plan_name": "Traditional",
                        "negotiated_dollar_amount": "423.00",
                        "negotiated_percentage": None
                    },
                    {
                        "payer_name": "UnitedHealthcare",
                        "plan_name": "Choice Plus",
                        "negotiated_dollar_amount": "1,350.00",
                        "negotiated_percentage": None
                    }
                ],
                "gross_charge": "3,500.00",
                "discounted_cash_price": "1,800.00"
            },
            {
                "description": "CT HEAD/BRAIN W/O DYE",
                "code": [
                    {
                        "type": "CPT",
                        "code": "70450"
                    }
                ],
                "standard_charges": [
                    {
                        "payer_name": "Blue Cross Blue Shield",
                        "plan_name": "PPO",
                        "negotiated_dollar_amount": "650.00",
                        "negotiated_percentage": None
                    },
                    {
                        "payer_name": "Medicare",
                        "plan_name": "Traditional",
                        "negotiated_dollar_amount": "234.00",
                        "negotiated_percentage": None
                    }
                ],
                "gross_charge": "2,100.00",
                "discounted_cash_price": "950.00"
            },
            {
                "description": "MRI LOWER EXTREMITY W/O DYE (Knee)",
                "code": [
                    {
                        "type": "CPT",
                        "code": "73721"
                    }
                ],
                "standard_charges": [
                    {
                        "payer_name": "Blue Cross Blue Shield",
                        "plan_name": "PPO",
                        "negotiated_dollar_amount": "825.00",
                        "negotiated_percentage": None
                    },
                    {
                        "payer_name": "Medicare",
                        "plan_name": "Traditional",
                        "negotiated_dollar_amount": "275.00",
                        "negotiated_percentage": None
                    },
                    {
                        "payer_name": "Aetna",
                        "plan_name": "HMO",
                        "negotiated_dollar_amount": "780.00",
                        "negotiated_percentage": None
                    }
                ],
                "gross_charge": "2,500.00",
                "discounted_cash_price": "1,200.00"
            }
        ]
    }
    
    import json
    with open(sample1_path, 'w') as f:
        json.dump(sample1_data, f, indent=2)
    logger.info(f"Created sample JSON file: {sample1_path}")
    
    # Sample 2: Different JSON structure (variant format)
    sample2_path = data_dir / 'variant_format_hospital.json'
    sample2_data = {
        "hospital_location": "Sample Regional Medical Center",
        "hospital_address": "123 Medical Plaza, Joplin, MO 64804",
        "affirmation": "To the best of our knowledge, this data is accurate as of 2024-01-15",
        "price_list": [
            {
                "proc_desc": "ARTHROSCOPY KNEE SURGICAL",
                "cpt_hcpcs": "29881",
                "revenue_code": "0360",
                "payers": {
                    "BCBS_Missouri": {
                        "rate": 2500.00,
                        "methodology": "case rate"
                    },
                    "Medicare_Traditional": {
                        "rate": 850.00,
                        "methodology": "fee schedule"
                    },
                    "UnitedHealthcare_PPO": {
                        "rate": 2650.00,
                        "methodology": "percent of charges",
                        "percent": 0.75
                    }
                },
                "standard_charge": 8000.00,
                "min_charge": 800.00,
                "max_charge": 8500.00
            },
            {
                "proc_desc": "OFFICE VISIT EST PATIENT LEVEL 3",
                "cpt_hcpcs": "99213",
                "revenue_code": "0510",
                "payers": {
                    "BCBS_Missouri": {
                        "rate": 150.00,
                        "methodology": "fee schedule"
                    },
                    "Medicare_Traditional": {
                        "rate": 93.00,
                        "methodology": "fee schedule"
                    }
                },
                "standard_charge": 250.00,
                "min_charge": 90.00,
                "max_charge": 280.00
            }
        ]
    }
    
    with open(sample2_path, 'w') as f:
        json.dump(sample2_data, f, indent=2)
    logger.info(f"Created variant JSON file: {sample2_path}")
    
    # Sample 3: CSV format (common format)
    sample3_path = data_dir / 'csv_format_hospital.csv'
    csv_content = """hospital_name,facility_npi,cpt_code,procedure_description,payer_code,payer_name,plan_type,negotiated_rate,gross_charge,cash_price
"Sample Medical Center",9876543210,45378,"Colonoscopy diagnostic",BCBS001,"Blue Cross Blue Shield of Missouri",PPO,1250.50,3500.00,1800.00
"Sample Medical Center",9876543210,45378,"Colonoscopy diagnostic",MCARE,"Medicare Traditional",N/A,350.00,3500.00,1800.00
"Sample Medical Center",9876543210,45378,"Colonoscopy diagnostic",UHC001,"UnitedHealthcare",Choice Plus,1320.00,3500.00,1800.00
"Sample Medical Center",9876543210,36415,"Routine venipuncture",BCBS001,"Blue Cross Blue Shield of Missouri",PPO,15.00,45.00,20.00
"Sample Medical Center",9876543210,36415,"Routine venipuncture",MCARE,"Medicare Traditional",N/A,3.00,45.00,20.00
"Sample Medical Center",9876543210,80053,"Comprehensive metabolic panel",BCBS001,"Blue Cross Blue Shield of Missouri",PPO,45.00,120.00,60.00
"Sample Medical Center",9876543210,80053,"Comprehensive metabolic panel",MCARE,"Medicare Traditional",N/A,14.00,120.00,60.00
"Sample Medical Center",9876543210,85025,"Complete blood count (CBC)",BCBS001,"Blue Cross Blue Shield of Missouri",PPO,35.00,95.00,50.00
"Sample Medical Center",9876543210,85025,"Complete blood count (CBC)",MCARE,"Medicare Traditional",N/A,11.00,95.00,50.00
"""
    
    with open(sample3_path, 'w') as f:
        f.write(csv_content)
    logger.info(f"Created CSV file: {sample3_path}")
    
    return data_dir


def main():
    """Main function to download/create hospital MRF files"""
    logger.info("=" * 80)
    logger.info("Hospital MRF File Preparation")
    logger.info("=" * 80)
    
    # Create sample files that mimic real hospital structures
    sample_dir = create_sample_mrf_files()
    
    logger.info(f"\n✓ Sample MRF files created in: {sample_dir}")
    logger.info("\nFiles created:")
    for file in sample_dir.glob('*'):
        size = os.path.getsize(file)
        logger.info(f"  - {file.name} ({size:,} bytes)")
    
    logger.info("\n" + "=" * 80)
    logger.info("Ready for LLM parsing tests!")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
