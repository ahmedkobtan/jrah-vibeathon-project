"""
Database Loader - Loads parsed data into database
"""

import logging
from typing import List, Dict, Any
from datetime import date, datetime

from database import (
    Provider, Procedure, InsurancePlan, PriceTransparency,
    FileProcessingLog
)
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class DatabaseLoader:
    """
    Loads parsed hospital transparency data into database
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize database loader
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
    
    def load_parsed_records(
        self,
        records: List[Dict[str, Any]],
        provider_id: int,
        data_source: str
    ) -> int:
        """
        Load parsed records into database
        
        Args:
            records: List of normalized records from parser
            provider_id: ID of the provider
            data_source: URL/path of source file
            
        Returns:
            Number of records successfully loaded
        """
        loaded_count = 0
        
        with self.db.session_scope() as session:
            for record in records:
                try:
                    # Create or update procedure if needed
                    if record.get('cpt_code'):
                        self._ensure_procedure(
                            session,
                            record['cpt_code'],
                            record.get('procedure_description')
                        )
                    
                    # Create price transparency record
                    price_record = PriceTransparency(
                        provider_id=provider_id,
                        cpt_code=record.get('cpt_code'),
                        payer_name=record.get('payer_name'),
                        negotiated_rate=record.get('negotiated_rate'),
                        min_negotiated_rate=record.get('min_negotiated_rate'),
                        max_negotiated_rate=record.get('max_negotiated_rate'),
                        standard_charge=record.get('standard_charge'),
                        cash_price=record.get('cash_price'),
                        in_network=True,
                        data_source=data_source,
                        confidence_score=record.get('confidence_score', 1.0),
                        last_updated=date.today()
                    )
                    
                    session.add(price_record)
                    loaded_count += 1
                    
                    # Commit in batches of 100
                    if loaded_count % 100 == 0:
                        session.commit()
                        logger.info(f"Loaded {loaded_count} records...")
                
                except Exception as e:
                    logger.error(f"Failed to load record: {e}")
                    logger.debug(f"Record: {record}")
                    continue
            
            # Final commit
            session.commit()
        
        logger.info(f"Successfully loaded {loaded_count} records")
        return loaded_count
    
    def _ensure_procedure(self, session, cpt_code: str, description: str = None):
        """Ensure procedure exists in database"""
        existing = session.query(Procedure).filter_by(cpt_code=cpt_code).first()
        
        if not existing:
            procedure = Procedure(
                cpt_code=cpt_code,
                description=description or f"Procedure {cpt_code}",
                category=None,
                medicare_rate=None
            )
            session.add(procedure)
            logger.debug(f"Created procedure: {cpt_code}")
    
    def create_provider(
        self,
        name: str,
        npi: str = None,
        address: str = None,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        latitude: float = None,
        longitude: float = None,
        phone: str = None,
        website: str = None
    ) -> int:
        """
        Create a provider record
        
        Returns:
            Provider ID
        """
        with self.db.session_scope() as session:
            provider = Provider(
                npi=npi,
                name=name,
                address=address,
                city=city,
                state=state,
                zip=zip_code,
                latitude=latitude,
                longitude=longitude,
                phone=phone,
                website=website
            )
            session.add(provider)
            session.flush()  # Get the ID
            provider_id = provider.id
        
        logger.info(f"Created provider: {name} (ID: {provider_id})")
        return provider_id
    
    def log_file_processing(
        self,
        file_url: str,
        file_hash: str,
        provider_id: int,
        status: str,
        records_parsed: int = None,
        errors: str = None,
        processing_time: int = None
    ) -> int:
        """
        Log file processing status
        
        Returns:
            Log entry ID
        """
        with self.db.session_scope() as session:
            log_entry = FileProcessingLog(
                file_url=file_url,
                file_hash=file_hash,
                provider_id=provider_id,
                status=status,
                records_parsed=records_parsed,
                errors=errors,
                processing_time_seconds=processing_time,
                completed_at=datetime.utcnow() if status == 'completed' else None
            )
            session.add(log_entry)
            session.flush()
            log_id = log_entry.id
        
        return log_id
    
    def create_insurance_plan(
        self,
        carrier: str,
        plan_name: str = None,
        plan_type: str = None,
        network_id: str = None,
        state: str = None,
        deductible_individual: float = None,
        deductible_family: float = None,
        coinsurance_rate: float = None,
        copay_specialist: float = None,
        out_of_pocket_max: float = None
    ) -> int:
        """
        Create an insurance plan record
        
        Returns:
            Insurance plan ID
        """
        with self.db.session_scope() as session:
            plan = InsurancePlan(
                carrier=carrier,
                plan_name=plan_name,
                plan_type=plan_type,
                network_id=network_id,
                state=state,
                deductible_individual=deductible_individual,
                deductible_family=deductible_family,
                coinsurance_rate=coinsurance_rate,
                copay_specialist=copay_specialist,
                out_of_pocket_max=out_of_pocket_max
            )
            session.add(plan)
            session.flush()
            plan_id = plan.id
        
        logger.info(f"Created insurance plan: {carrier} - {plan_name} (ID: {plan_id})")
        return plan_id
    
    def bulk_create_procedures(self, procedures: List[Dict[str, Any]]) -> int:
        """
        Bulk create procedures
        
        Args:
            procedures: List of dicts with cpt_code, description, category, medicare_rate
            
        Returns:
            Number of procedures created
        """
        created_count = 0
        
        with self.db.session_scope() as session:
            for proc_data in procedures:
                try:
                    existing = session.query(Procedure).filter_by(
                        cpt_code=proc_data['cpt_code']
                    ).first()
                    
                    if not existing:
                        procedure = Procedure(
                            cpt_code=proc_data['cpt_code'],
                            description=proc_data['description'],
                            category=proc_data.get('category'),
                            medicare_rate=proc_data.get('medicare_rate')
                        )
                        session.add(procedure)
                        created_count += 1
                    
                    # Commit in batches
                    if created_count % 100 == 0:
                        session.commit()
                
                except Exception as e:
                    logger.error(f"Failed to create procedure {proc_data.get('cpt_code')}: {e}")
                    continue
            
            session.commit()
        
        logger.info(f"Created {created_count} procedures")
        return created_count
