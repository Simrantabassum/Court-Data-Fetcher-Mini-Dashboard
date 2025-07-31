#!/usr/bin/env python3
"""
Simple test script for Court Data Fetcher
This script tests basic functionality without requiring a full database setup
"""

import sys
import os
import requests
import json
from datetime import datetime

def test_basic_functionality():
    """Test basic application functionality"""
    print("🧪 Testing Court Data Fetcher Basic Functionality")
    print("=" * 50)
    
    # Test 1: Check if main modules can be imported
    print("1. Testing module imports...")
    try:
        from app import create_app
        from models import db, CaseQuery, CaseDetail, CourtOrder, SearchLog
        from scraper import DelhiHighCourtScraper, get_mock_case_data
        from config import Config
        print("   ✅ All modules imported successfully")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    # Test 2: Test Flask app creation
    print("2. Testing Flask app creation...")
    try:
        # Set environment variable for in-memory database
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
        print("   ✅ Flask app created successfully")
    except Exception as e:
        print(f"   ❌ Flask app creation failed: {e}")
        return False
    
    # Test 3: Test mock data generation
    print("3. Testing mock data generation...")
    try:
        mock_data = get_mock_case_data('W.P.(C)', '1234', 2023)
        assert 'success' in mock_data
        assert 'case_details' in mock_data
        assert 'orders' in mock_data
        print("   ✅ Mock data generation works")
    except Exception as e:
        print(f"   ❌ Mock data generation failed: {e}")
        return False
    
    # Test 4: Test configuration
    print("4. Testing configuration...")
    try:
        assert hasattr(Config, 'CASE_TYPES')
        assert isinstance(Config.CASE_TYPES, list)
        assert len(Config.CASE_TYPES) > 0
        assert 'W.P.(C)' in Config.CASE_TYPES
        print("   ✅ Configuration is valid")
    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False
    
    # Test 5: Test database models
    print("5. Testing database models...")
    try:
        with app.app_context():
            # Test CaseQuery model
            case_query = CaseQuery(
                case_type='W.P.(C)',
                case_number='1234',
                filing_year=2023
            )
            db.session.add(case_query)
            db.session.commit()
            assert case_query.id is not None
            
            # Test CaseDetail model
            case_detail = CaseDetail(
                query_id=case_query.id,
                case_title='Test Case',
                petitioner='Test Petitioner',
                respondent='Test Respondent'
            )
            db.session.add(case_detail)
            db.session.commit()
            assert case_detail.id is not None
            
            # Test CourtOrder model
            order = CourtOrder(
                case_detail_id=case_detail.id,
                order_title='Test Order',
                order_type='Order'
            )
            db.session.add(order)
            db.session.commit()
            assert order.id is not None
            
            print("   ✅ Database models work correctly")
    except Exception as e:
        print(f"   ❌ Database model test failed: {e}")
        return False
    
    # Test 6: Test scraper initialization
    print("6. Testing scraper initialization...")
    try:
        scraper = DelhiHighCourtScraper()
        assert scraper.base_url == "https://delhihighcourt.nic.in/"
        print("   ✅ Scraper initialized successfully")
    except Exception as e:
        print(f"   ❌ Scraper initialization failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All basic functionality tests passed!")
    return True

def test_web_endpoints(base_url="http://localhost:5000"):
    """Test web endpoints if the application is running"""
    print(f"\n🌐 Testing web endpoints at {base_url}")
    print("=" * 50)
    
    # Test 1: Home page
    print("1. Testing home page...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("   ✅ Home page accessible")
        else:
            print(f"   ⚠️  Home page returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Home page not accessible: {e}")
        return False
    
    # Test 2: API search endpoint
    print("2. Testing API search endpoint...")
    try:
        search_data = {
            'case_type': 'W.P.(C)',
            'case_number': '1234',
            'filing_year': '2023'
        }
        response = requests.post(f"{base_url}/api/search", 
                               json=search_data, 
                               timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ API search endpoint works")
            else:
                print(f"   ⚠️  API search returned error: {data.get('error')}")
        else:
            print(f"   ⚠️  API search returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API search endpoint not accessible: {e}")
    
    # Test 3: API cases endpoint
    print("3. Testing API cases endpoint...")
    try:
        response = requests.get(f"{base_url}/api/cases", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ API cases endpoint works")
            else:
                print(f"   ⚠️  API cases returned error: {data.get('error')}")
        else:
            print(f"   ⚠️  API cases returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API cases endpoint not accessible: {e}")
    
    # Test 4: Stats page
    print("4. Testing stats page...")
    try:
        response = requests.get(f"{base_url}/stats", timeout=5)
        if response.status_code == 200:
            print("   ✅ Stats page accessible")
        else:
            print(f"   ⚠️  Stats page returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Stats page not accessible: {e}")
    
    print("\n" + "=" * 50)
    print("🌐 Web endpoint tests completed!")
    return True

def main():
    """Main test function"""
    print("🚀 Starting Court Data Fetcher Tests")
    print(f"📅 Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run basic functionality tests
    basic_tests_passed = test_basic_functionality()
    
    # Run web endpoint tests if application is running
    web_tests_passed = test_web_endpoints()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Basic Functionality: {'✅ PASSED' if basic_tests_passed else '❌ FAILED'}")
    print(f"   Web Endpoints: {'✅ PASSED' if web_tests_passed else '⚠️  SKIPPED/FAILED'}")
    
    if basic_tests_passed:
        print("\n🎉 Core application functionality is working correctly!")
        print("💡 To test web endpoints, start the application with:")
        print("   python run_app.py")
        return 0
    else:
        print("\n❌ Some core functionality tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 