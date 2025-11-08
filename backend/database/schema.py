"""
Database schema for Healthcare Price Transparency Platform
SQLAlchemy ORM models
"""

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, Date, 
    DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Provider(Base):
    """Hospitals, clinics, and healthcare facilities"""
    __tablename__ = 'providers'
    
    id = Column(Integer, primary_key=True)
    npi = Column(String(10), unique=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(2))
    zip = Column(String(10))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    phone = Column(String(20))
    website = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Provider(id={self.id}, name='{self.name}', npi='{self.npi}')>"


class Procedure(Base):
    """Medical procedures with CPT/HCPCS codes"""
    __tablename__ = 'procedures'
    
    cpt_code = Column(String(10), primary_key=True)
    description = Column(Text, nullable=False)
    category = Column(String(100))
    medicare_rate = Column(Numeric(10, 2))  # Baseline from CMS
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Procedure(cpt_code='{self.cpt_code}', description='{self.description[:50]}...')>"


class InsurancePlan(Base):
    """Insurance plans and carriers"""
    __tablename__ = 'insurance_plans'
    
    id = Column(Integer, primary_key=True)
    carrier = Column(String(255), nullable=False)
    plan_name = Column(String(255))
    plan_type = Column(String(50))  # PPO, HMO, EPO, POS
    network_id = Column(String(100))
    state = Column(String(2))
    deductible_individual = Column(Numeric(10, 2))
    deductible_family = Column(Numeric(10, 2))
    coinsurance_rate = Column(Numeric(5, 4))  # e.g., 0.20 for 20%
    copay_specialist = Column(Numeric(10, 2))
    out_of_pocket_max = Column(Numeric(10, 2))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<InsurancePlan(id={self.id}, carrier='{self.carrier}', plan_name='{self.plan_name}')>"


class PriceTransparency(Base):
    """Core pricing data from hospital transparency files"""
    __tablename__ = 'price_transparency'
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, ForeignKey('providers.id'))
    cpt_code = Column(String(10), ForeignKey('procedures.cpt_code'))
    payer_name = Column(String(255))  # Raw payer name from file
    insurance_plan_id = Column(Integer, ForeignKey('insurance_plans.id'))
    
    # Pricing data
    negotiated_rate = Column(Numeric(10, 2))
    min_negotiated_rate = Column(Numeric(10, 2))
    max_negotiated_rate = Column(Numeric(10, 2))
    standard_charge = Column(Numeric(10, 2))  # List/gross price
    cash_price = Column(Numeric(10, 2))
    
    # Metadata
    in_network = Column(Boolean, default=True)
    data_source = Column(String(255))  # URL of transparency file
    confidence_score = Column(Numeric(3, 2))  # 0-1 score from parsing agent
    last_updated = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for fast lookups
    __table_args__ = (
        Index('idx_lookup', 'provider_id', 'cpt_code', 'insurance_plan_id'),
        Index('idx_payer', 'payer_name'),
        Index('idx_cpt', 'cpt_code'),
    )
    
    def __repr__(self):
        return f"<PriceTransparency(id={self.id}, provider_id={self.provider_id}, cpt_code='{self.cpt_code}', rate={self.negotiated_rate})>"


class FileProcessingLog(Base):
    """Track processing of hospital transparency files"""
    __tablename__ = 'file_processing_log'
    
    id = Column(Integer, primary_key=True)
    file_url = Column(String(255))
    file_hash = Column(String(64))
    provider_id = Column(Integer, ForeignKey('providers.id'))
    status = Column(String(50))  # pending, processing, completed, failed
    records_parsed = Column(Integer)
    errors = Column(Text)
    processing_time_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<FileProcessingLog(id={self.id}, status='{self.status}', records={self.records_parsed})>"


class QueryLog(Base):
    """Log user queries for analytics and caching"""
    __tablename__ = 'query_log'
    
    id = Column(Integer, primary_key=True)
    user_query = Column(Text)
    parsed_intent = Column(JSON)  # Store as JSON instead of JSONB for SQLite compatibility
    cpt_codes = Column(Text)  # Store as comma-separated string for SQLite compatibility
    location = Column(String(10))
    insurance_carrier = Column(String(255))
    results_returned = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<QueryLog(id={self.id}, query='{self.user_query[:50]}...')>"
