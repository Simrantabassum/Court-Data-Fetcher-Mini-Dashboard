import os
from flask import Flask
from models import db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure Flask app for database initialization"""
    app = Flask(__name__)
    
    # Configure database with absolute path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'database', 'court_data.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Initialize database
    db.init_app(app)
    
    return app

def init_database():
    """Initialize the database and create all tables"""
    app = create_app()
    
    with app.app_context():
        # Create database directory if it doesn't exist
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_dir = os.path.join(current_dir, 'database')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            print(f"Created database directory: {db_dir}")
        
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Verify tables were created
        try:
            tables = db.engine.table_names()
            print(f"Created tables: {', '.join(tables)}")
        except Exception as e:
            print(f"Warning: Could not verify tables: {e}")

if __name__ == '__main__':
    init_database() 