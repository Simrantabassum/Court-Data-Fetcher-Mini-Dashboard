import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database/court_data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Selenium configuration
    SELENIUM_DRIVER_PATH = os.getenv('SELENIUM_DRIVER_PATH', 'chromedriver')
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'static/downloads'
    
    # Application settings
    CASES_PER_PAGE = 10
    SEARCH_TIMEOUT = 30  # seconds
    
    # Target court information
    TARGET_COURT = "Delhi High Court"
    COURT_URL = "https://delhihighcourt.nic.in/"
    
    # Case types for Delhi High Court
    CASE_TYPES = [
        'W.P.(C)', 'W.P.(CRL)', 'CRL.A.', 'CRL.M.C.', 'CRL.REV.P.',
        'LPA', 'FAO', 'CM(M)', 'CM(Main)', 'RFA', 'CS(OS)', 'CS(COMM)',
        'ARB.P.', 'O.M.P.', 'EX.P.', 'CONT.CAS(C)', 'CONT.CAS(CRL)',
        'BAIL APPLN.', 'CRL.M.A.', 'CRL.M.B.', 'CRL.REV.P.', 'CRL.W.P.',
        'W.P.(C) 1234/2023', 'W.P.(C) 5678/2022'
    ]

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 