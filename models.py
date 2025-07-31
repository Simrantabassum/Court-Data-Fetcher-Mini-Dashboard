from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class CaseQuery(db.Model):
    """Model for storing case search queries"""
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    filing_year = db.Column(db.Integer, nullable=False)
    search_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, success, error
    error_message = db.Column(db.Text, nullable=True)
    
    # Relationship to case details
    case_details = db.relationship('CaseDetail', backref='query', lazy=True, uselist=False)
    
    def __repr__(self):
        return f'<CaseQuery {self.case_type}/{self.case_number}/{self.filing_year}>'

class CaseDetail(db.Model):
    """Model for storing parsed case details"""
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('case_query.id'), nullable=False)
    
    # Case metadata
    case_title = db.Column(db.String(500), nullable=True)
    petitioner = db.Column(db.String(500), nullable=True)
    respondent = db.Column(db.String(500), nullable=True)
    filing_date = db.Column(db.Date, nullable=True)
    next_hearing_date = db.Column(db.Date, nullable=True)
    case_status = db.Column(db.String(100), nullable=True)
    
    # Raw response data (JSON)
    raw_response = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to orders
    orders = db.relationship('CourtOrder', backref='case', lazy=True)
    
    def __repr__(self):
        return f'<CaseDetail {self.case_title}>'

class CourtOrder(db.Model):
    """Model for storing court orders and judgments"""
    id = db.Column(db.Integer, primary_key=True)
    case_detail_id = db.Column(db.Integer, db.ForeignKey('case_detail.id'), nullable=False)
    
    # Order details
    order_date = db.Column(db.Date, nullable=True)
    order_type = db.Column(db.String(100), nullable=True)  # Order, Judgment, etc.
    order_title = db.Column(db.String(500), nullable=True)
    order_description = db.Column(db.Text, nullable=True)
    
    # PDF details
    pdf_url = db.Column(db.String(1000), nullable=True)
    pdf_filename = db.Column(db.String(255), nullable=True)
    pdf_downloaded = db.Column(db.Boolean, default=False)
    pdf_local_path = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CourtOrder {self.order_title}>'

class SearchLog(db.Model):
    """Model for logging all search activities"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    search_params = db.Column(db.Text, nullable=True)  # JSON string
    response_time = db.Column(db.Float, nullable=True)  # in seconds
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<SearchLog {self.timestamp}>' 