"""
Seed common medical procedures (CPT codes) into the database.
These are actual medical procedures that patients commonly search for.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import connection, schema
from sqlalchemy.orm import Session

# Common medical procedures with their CPT codes
COMMON_PROCEDURES = [
    # Surgical Procedures
    ("27447", "Total Knee Replacement (Arthroplasty)", "Orthopedic Surgery", 15000.00),
    ("27130", "Total Hip Replacement (Arthroplasty)", "Orthopedic Surgery", 16000.00),
    ("29827", "Arthroscopy, Shoulder, Surgical", "Orthopedic Surgery", 7500.00),
    ("29881", "Arthroscopy, Knee, with Meniscectomy", "Orthopedic Surgery", 4500.00),
    ("47562", "Laparoscopic Cholecystectomy (Gallbladder Removal)", "General Surgery", 8500.00),
    ("43239", "Upper Endoscopy with Biopsy", "Gastroenterology", 2500.00),
    ("45378", "Colonoscopy", "Gastroenterology", 3200.00),
    ("45380", "Colonoscopy with Biopsy", "Gastroenterology", 3500.00),
    ("45385", "Colonoscopy with Polyp Removal", "Gastroenterology", 4000.00),
    ("58150", "Total Abdominal Hysterectomy", "Gynecology", 9500.00),
    ("58558", "Laparoscopic Hysterectomy", "Gynecology", 10500.00),
    ("19125", "Breast Biopsy", "General Surgery", 2800.00),
    ("19301", "Partial Mastectomy", "General Surgery", 8000.00),
    ("60240", "Thyroidectomy, Total", "Endocrine Surgery", 9000.00),
    ("43644", "Laparoscopic Gastric Bypass", "Bariatric Surgery", 22000.00),
    ("49505", "Hernia Repair, Inguinal", "General Surgery", 5500.00),
    ("49650", "Laparoscopic Hernia Repair", "General Surgery", 6500.00),
    
    # Imaging and Diagnostics
    ("70450", "CT Scan, Head/Brain without Contrast", "Radiology", 800.00),
    ("70486", "CT Scan, Face without Contrast", "Radiology", 750.00),
    ("70553", "MRI, Brain with and without Contrast", "Radiology", 1800.00),
    ("71250", "CT Scan, Chest without Contrast", "Radiology", 850.00),
    ("72148", "MRI, Lumbar Spine without Contrast", "Radiology", 1500.00),
    ("73221", "MRI, Upper Extremity without Contrast", "Radiology", 1400.00),
    ("73721", "MRI, Lower Extremity without Contrast", "Radiology", 1400.00),
    ("74177", "CT Scan, Abdomen and Pelvis with Contrast", "Radiology", 1200.00),
    ("76700", "Ultrasound, Abdominal", "Radiology", 400.00),
    ("76805", "Ultrasound, Obstetric", "Radiology", 350.00),
    ("76856", "Ultrasound, Pelvic", "Radiology", 380.00),
    ("76942", "Ultrasound Guidance for Needle Biopsy", "Radiology", 250.00),
    ("77067", "Screening Mammography", "Radiology", 280.00),
    ("77065", "Diagnostic Mammography", "Radiology", 320.00),
    
    # Cardiovascular Procedures
    ("93000", "Electrocardiogram (ECG/EKG)", "Cardiology", 150.00),
    ("93015", "Cardiovascular Stress Test", "Cardiology", 450.00),
    ("93306", "Echocardiography (Heart Ultrasound)", "Cardiology", 800.00),
    ("93454", "Cardiac Catheterization", "Cardiology", 8500.00),
    ("92928", "Coronary Angioplasty with Stent", "Cardiology", 18000.00),
    ("33533", "Coronary Artery Bypass (CABG), Single Graft", "Cardiac Surgery", 45000.00),
    
    # Emergency and Hospital Services
    ("99281", "Emergency Department Visit, Level 1 (Minor)", "Emergency Medicine", 300.00),
    ("99282", "Emergency Department Visit, Level 2 (Low)", "Emergency Medicine", 450.00),
    ("99283", "Emergency Department Visit, Level 3 (Moderate)", "Emergency Medicine", 650.00),
    ("99284", "Emergency Department Visit, Level 4 (High)", "Emergency Medicine", 950.00),
    ("99285", "Emergency Department Visit, Level 5 (Critical)", "Emergency Medicine", 1500.00),
    ("99222", "Initial Hospital Care, Moderate Complexity", "Hospital Medicine", 350.00),
    ("99223", "Initial Hospital Care, High Complexity", "Hospital Medicine", 450.00),
    ("99232", "Subsequent Hospital Care", "Hospital Medicine", 200.00),
    
    # Office Visits
    ("99201", "Office Visit, New Patient, Level 1", "Primary Care", 80.00),
    ("99202", "Office Visit, New Patient, Level 2", "Primary Care", 135.00),
    ("99203", "Office Visit, New Patient, Level 3", "Primary Care", 180.00),
    ("99204", "Office Visit, New Patient, Level 4", "Primary Care", 240.00),
    ("99205", "Office Visit, New Patient, Level 5", "Primary Care", 310.00),
    ("99211", "Office Visit, Established Patient, Level 1", "Primary Care", 45.00),
    ("99212", "Office Visit, Established Patient, Level 2", "Primary Care", 85.00),
    ("99213", "Office Visit, Established Patient, Level 3", "Primary Care", 130.00),
    ("99214", "Office Visit, Established Patient, Level 4", "Primary Care", 185.00),
    ("99215", "Office Visit, Established Patient, Level 5", "Primary Care", 245.00),
    
    # Lab Tests
    ("80053", "Comprehensive Metabolic Panel", "Laboratory", 50.00),
    ("80061", "Lipid Panel", "Laboratory", 45.00),
    ("85025", "Complete Blood Count (CBC) with Differential", "Laboratory", 35.00),
    ("84443", "Thyroid Stimulating Hormone (TSH) Test", "Laboratory", 75.00),
    ("82947", "Glucose Blood Test", "Laboratory", 25.00),
    ("83036", "Hemoglobin A1C Test", "Laboratory", 55.00),
    ("84478", "Triglycerides Test", "Laboratory", 40.00),
    
    # Physical Therapy
    ("97110", "Therapeutic Exercise", "Physical Therapy", 85.00),
    ("97112", "Neuromuscular Re-education", "Physical Therapy", 90.00),
    ("97140", "Manual Therapy", "Physical Therapy", 85.00),
    ("97161", "Physical Therapy Evaluation, Low Complexity", "Physical Therapy", 120.00),
    ("97162", "Physical Therapy Evaluation, Moderate Complexity", "Physical Therapy", 150.00),
    ("97163", "Physical Therapy Evaluation, High Complexity", "Physical Therapy", 180.00),
    
    # Obstetrics
    ("59400", "Obstetric Care (Vaginal Delivery)", "Obstetrics", 4500.00),
    ("59510", "Cesarean Section Delivery", "Obstetrics", 6500.00),
    ("59610", "Vaginal Birth After Cesarean (VBAC)", "Obstetrics", 5000.00),
    
    # Dental-Adjacent Medical Procedures
    ("21089", "Unlisted Maxillofacial Prosthetic Procedure", "Oral Surgery", 800.00),
    ("41899", "Unlisted Oral/Dentoalveolar Surgery", "Oral Surgery", 600.00),
    
    # Pain Management
    ("64483", "Lumbar/Sacral Epidural Steroid Injection", "Pain Management", 1200.00),
    ("64493", "Facet Joint Injection, Lumbar/Sacral", "Pain Management", 800.00),
    ("20610", "Arthrocentesis (Joint Drainage)", "Orthopedics", 350.00),
    
    # Ophthalmology
    ("66984", "Cataract Surgery with IOL Insertion", "Ophthalmology", 3500.00),
    ("67228", "Photocoagulation for Diabetic Retinopathy", "Ophthalmology", 1800.00),
    ("92004", "Comprehensive Eye Exam, New Patient", "Ophthalmology", 200.00),
    ("92012", "Comprehensive Eye Exam, Established Patient", "Ophthalmology", 150.00),
]


def seed_procedures():
    """Add common medical procedures to the database."""
    db_manager = connection.get_db_manager()
    db = db_manager.get_session()
    
    try:
        # Check which procedures already exist
        existing_codes = {
            proc.cpt_code 
            for proc in db.query(schema.Procedure.cpt_code).all()
        }
        
        added_count = 0
        updated_count = 0
        
        for cpt_code, description, category, medicare_rate in COMMON_PROCEDURES:
            if cpt_code in existing_codes:
                # Update existing procedure
                procedure = db.query(schema.Procedure).filter(
                    schema.Procedure.cpt_code == cpt_code
                ).first()
                if procedure:
                    procedure.description = description
                    procedure.category = category
                    if procedure.medicare_rate is None:
                        procedure.medicare_rate = medicare_rate
                    updated_count += 1
            else:
                # Add new procedure
                procedure = schema.Procedure(
                    cpt_code=cpt_code,
                    description=description,
                    category=category,
                    medicare_rate=medicare_rate,
                )
                db.add(procedure)
                added_count += 1
        
        db.commit()
        print(f"✅ Successfully added {added_count} new procedures")
        print(f"✅ Updated {updated_count} existing procedures")
        print(f"📊 Total procedures in database: {len(existing_codes) + added_count}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding procedures: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_procedures()

