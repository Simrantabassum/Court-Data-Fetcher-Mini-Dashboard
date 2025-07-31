#!/usr/bin/env python3
"""
Simple runner script for the Court Data Fetcher application
"""

import os
import sys
from pathlib import Path

def ensure_directories():
    """Ensure all necessary directories exist"""
    directories = ['database', 'static/downloads']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Ensured directory exists: {directory}")

def main():
    """Main function to run the application"""
    print("🚀 Starting Court Data Fetcher...")
    
    # Ensure directories exist
    ensure_directories()
    
    # Set environment variables
    os.environ.setdefault('FLASK_APP', 'app.py')
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('SECRET_KEY', 'dev-secret-key-change-in-production')
    os.environ.setdefault('DATABASE_URL', 'sqlite:///court_data.db')
    
    try:
        # Import and run the app
        from app import app
        
        print("✅ Application loaded successfully")
        print("🌐 Starting server on http://localhost:5000")
        print("📝 Press Ctrl+C to stop the server")
        
        # Run the app
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except ImportError as e:
        print(f"❌ Failed to import application: {e}")
        print("💡 Make sure you have activated the virtual environment:")
        print("   venv\\Scripts\\activate")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 