import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from models import db, CaseQuery, CaseDetail, CourtOrder, SearchLog
from scraper import DelhiHighCourtScraper, get_mock_case_data
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Use consistent DB path with absolute path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'database', 'court_data.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{db_path}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Only create directories if not using in-memory database
    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///:memory:'):
        # Ensure directories exist
        os.makedirs('database', exist_ok=True)
        os.makedirs('static/downloads', exist_ok=True)
    
    db.init_app(app)
    
    # Import case types
    from config import Config
    CASE_TYPES = Config.CASE_TYPES
    
    @app.route('/')
    def index():
        return render_template('index.html', case_types=CASE_TYPES)

    @app.route('/search', methods=['POST'])
    def search_case():
        start_time = time.time()
        try:
            case_type = request.form.get('case_type', '').strip()
            case_number = request.form.get('case_number', '').strip()
            filing_year = request.form.get('filing_year', '').strip()

            if not all([case_type, case_number, filing_year]):
                flash('Please fill in all required fields.', 'error')
                return redirect(url_for('index'))

            try:
                filing_year = int(filing_year)
                if filing_year < 1900 or filing_year > datetime.now().year:
                    flash('Please enter a valid filing year.', 'error')
                    return redirect(url_for('index'))
            except ValueError:
                flash('Please enter a valid filing year.', 'error')
                return redirect(url_for('index'))

            search_log = SearchLog(
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                search_params=json.dumps({
                    'case_type': case_type,
                    'case_number': case_number,
                    'filing_year': filing_year
                })
            )
            db.session.add(search_log)
            db.session.commit()

            existing_query = CaseQuery.query.filter_by(
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year
            ).first()

            if existing_query and existing_query.case_details:
                search_log.response_time = time.time() - start_time
                search_log.success = True
                db.session.commit()
                return render_template('results.html',
                                       case_query=existing_query,
                                       case_details=existing_query.case_details,
                                       orders=existing_query.case_details.orders)

            case_query = CaseQuery(case_type=case_type, case_number=case_number, filing_year=filing_year)
            db.session.add(case_query)
            db.session.commit()

            scraper = DelhiHighCourtScraper()
            result = scraper.search_case(case_type, case_number, filing_year)

            if result.get('error'):
                # ✅ Better CAPTCHA handling
                if 'CAPTCHA' in result['error']:
                    flash('CAPTCHA detected on the court website. Showing mock data.', 'warning')
                else:
                    flash(f"Search failed: {result['error']}", 'error')

                logger.warning("Using mock data due to scraping error or CAPTCHA.")
                result = get_mock_case_data(case_type, case_number, filing_year)

            # Handle filing_date properly
            filing_date = result['case_details'].get('filing_date')
            if isinstance(filing_date, str) and filing_date:
                try:
                    filing_date = datetime.strptime(filing_date, '%d/%m/%Y').date()
                except ValueError:
                    filing_date = None
            elif not filing_date:
                filing_date = None
            
            # Handle next_hearing_date properly
            next_hearing_date = result['case_details'].get('next_hearing_date')
            if isinstance(next_hearing_date, str) and next_hearing_date:
                try:
                    next_hearing_date = datetime.strptime(next_hearing_date, '%d/%m/%Y').date()
                except ValueError:
                    next_hearing_date = None
            elif not next_hearing_date:
                next_hearing_date = None
            
            case_details = CaseDetail(
                query_id=case_query.id,
                case_title=result['case_details'].get('case_title', ''),
                petitioner=result['case_details'].get('petitioner', ''),
                respondent=result['case_details'].get('respondent', ''),
                filing_date=filing_date,
                next_hearing_date=next_hearing_date,
                case_status=result['case_details'].get('case_status', ''),
                raw_response=result.get('raw_html', '')
            )
            db.session.add(case_details)
            db.session.commit()

            # Save orders if available
            for order_data in result.get('orders', []):
                # Handle order_date properly
                order_date = order_data.get('order_date')
                if isinstance(order_date, str):
                    try:
                        order_date = datetime.strptime(order_date, '%d/%m/%Y')
                    except ValueError:
                        order_date = datetime.now()
                elif not order_date:
                    order_date = datetime.now()
                
                order = CourtOrder(
                    case_detail_id=case_details.id,
                    order_date=order_date,
                    order_type=order_data.get('order_type', 'Order'),
                    order_title=order_data.get('order_title', ''),
                    order_description=order_data.get('order_description', ''),
                    pdf_url=order_data.get('pdf_url', '')
                )
                db.session.add(order)

            case_query.status = 'success'
            db.session.commit()

            search_log.response_time = time.time() - start_time
            search_log.success = True
            db.session.commit()

            return render_template('results.html',
                                   case_query=case_query,
                                   case_details=case_details,
                                   orders=case_details.orders)

        except Exception as e:
            logger.error(f"Error in search_case: {str(e)}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('index'))

    @app.route('/api/search', methods=['POST'])
    def api_search():
        """API endpoint for case search"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
            case_type = data.get('case_type', '').strip()
            case_number = data.get('case_number', '').strip()
            filing_year = data.get('filing_year', '').strip()
            orders_page = data.get('orders_page', 1)
            orders_per_page = data.get('orders_per_page', 10)

            if not all([case_type, case_number, filing_year]):
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400

            try:
                filing_year = int(filing_year)
                if filing_year < 1900 or filing_year > datetime.now().year:
                    return jsonify({'success': False, 'error': 'Invalid filing year'}), 400
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid filing year'}), 400

            # Use the same search logic as the web form
            try:
                scraper = DelhiHighCourtScraper()
                result = scraper.search_case(case_type, case_number, filing_year)

                if result.get('error'):
                    # Always fall back to mock data for any error
                    logger.warning(f"Using mock data due to: {result['error']}")
                    result = get_mock_case_data(case_type, case_number, filing_year)
            except Exception as e:
                # If scraper fails, use mock data
                logger.warning(f"Scraper failed, using mock data: {str(e)}")
                result = get_mock_case_data(case_type, case_number, filing_year)

            # Save search to database
            try:
                case_query = CaseQuery(
                    case_type=case_type,
                    case_number=case_number,
                    filing_year=filing_year,
                    status='success' if result.get('success') else 'failed',
                    search_timestamp=datetime.now()
                )
                db.session.add(case_query)
                db.session.commit()

                # Save case details if available
                if result.get('case_details'):
                    # Handle filing_date properly
                    filing_date = result['case_details'].get('filing_date', '')
                    if isinstance(filing_date, str) and filing_date:
                        try:
                            filing_date = datetime.strptime(filing_date, '%d/%m/%Y').date()
                        except ValueError:
                            filing_date = None
                    elif not filing_date:
                        filing_date = None
                    
                    # Handle next_hearing_date properly
                    next_hearing_date = result['case_details'].get('next_hearing', '')
                    if isinstance(next_hearing_date, str) and next_hearing_date:
                        try:
                            next_hearing_date = datetime.strptime(next_hearing_date, '%d/%m/%Y').date()
                        except ValueError:
                            next_hearing_date = None
                    elif not next_hearing_date:
                        next_hearing_date = None
                    
                    case_details = CaseDetail(
                        query_id=case_query.id,
                        case_title=result['case_details'].get('case_title', ''),
                        petitioner=result['case_details'].get('petitioner', ''),
                        respondent=result['case_details'].get('respondent', ''),
                        filing_date=filing_date,
                        next_hearing_date=next_hearing_date,
                        case_status=result['case_details'].get('case_status', '')
                    )
                    db.session.add(case_details)

                # Save orders if available and case_details exists
                if result.get('orders') and 'case_details' in locals() and case_details and case_details.id:
                    for order_data in result['orders']:
                        # Handle order_date properly
                        order_date = order_data.get('order_date')
                        if isinstance(order_date, str):
                            try:
                                order_date = datetime.strptime(order_date, '%d/%m/%Y')
                            except ValueError:
                                order_date = datetime.now()
                        elif not order_date:
                            order_date = datetime.now()
                        
                        order = CourtOrder(
                            case_detail_id=case_details.id,
                            order_date=order_date,
                            order_type=order_data.get('order_type', 'Order'),
                            order_title=order_data.get('order_title', ''),
                            order_description=order_data.get('order_description', ''),
                            pdf_url=order_data.get('pdf_url', '')
                        )
                        db.session.add(order)

                db.session.commit()
                logger.info(f"Search saved to database: {case_type}/{case_number}/{filing_year}")

            except Exception as e:
                logger.error(f"Error saving search to database: {str(e)}")
                db.session.rollback()

            # Add pagination for orders
            orders = result.get('orders', [])
            total_orders = len(orders)
            start_idx = (orders_page - 1) * orders_per_page
            end_idx = start_idx + orders_per_page
            paginated_orders = orders[start_idx:end_idx]

            return jsonify({
                'success': True,
                'case_details': result['case_details'],
                'orders': paginated_orders,
                'orders_pagination': {
                    'page': orders_page,
                    'per_page': orders_per_page,
                    'total': total_orders,
                    'pages': (total_orders + orders_per_page - 1) // orders_per_page
                }
            })

        except Exception as e:
            logger.error(f"Error in API search: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/cases')
    def api_cases():
        """API endpoint for listing cases"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            cases = CaseQuery.query.paginate(
                page=page, 
                per_page=per_page, 
                error_out=False
            )
            
            cases_data = []
            for case in cases.items:
                case_data = {
                    'id': case.id,
                    'case_type': case.case_type,
                    'case_number': case.case_number,
                    'filing_year': case.filing_year,
                    'status': case.status,
                    'search_timestamp': case.search_timestamp.isoformat() if case.search_timestamp else None
                }
                if case.case_details:
                    case_data['case_title'] = case.case_details.case_title
                    case_data['petitioner'] = case.case_details.petitioner
                    case_data['respondent'] = case.case_details.respondent
                cases_data.append(case_data)
            
            return jsonify({
                'success': True,
                'cases': cases_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': cases.total,
                    'pages': cases.pages
                }
            })

        except Exception as e:
            logger.error(f"Error in API cases: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/stats')
    def stats():
        """Statistics page"""
        try:
            # Get basic statistics
            total_searches = SearchLog.query.count()
            successful_searches = SearchLog.query.filter_by(success=True).count()
            failed_searches = total_searches - successful_searches
            
            # Get recent searches
            recent_searches = SearchLog.query.order_by(SearchLog.timestamp.desc()).limit(10).all()
            
            # Get case type distribution
            case_types = db.session.query(CaseQuery.case_type, db.func.count(CaseQuery.id)).group_by(CaseQuery.case_type).all()
            
            stats_data = {
                'total_searches': total_searches,
                'successful_searches': successful_searches,
                'failed_searches': failed_searches,
                'success_rate': (successful_searches / total_searches * 100) if total_searches > 0 else 0,
                'recent_searches': [
                    {
                        'timestamp': search.timestamp.isoformat(),
                        'ip_address': search.ip_address,
                        'success': search.success,
                        'response_time': search.response_time
                    } for search in recent_searches
                ],
                'case_type_distribution': [
                    {'case_type': case_type, 'count': count} for case_type, count in case_types
                ]
            }
            
            return render_template('stats.html', stats=stats_data)
            
        except Exception as e:
            logger.error(f"Error in stats: {str(e)}")
            flash('Error loading statistics', 'error')
            return redirect(url_for('index'))

    @app.route('/download_pdf/<int:order_id>')
    def download_pdf(order_id):
        """Download PDF for a specific order"""
        try:
            order = CourtOrder.query.get_or_404(order_id)
            
            if not order.pdf_url:
                flash('No PDF available for this order.', 'error')
                return redirect(url_for('index'))
            
            # For now, just redirect to the PDF URL
            # In a production environment, you might want to download and serve the file locally
            return redirect(order.pdf_url)
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            flash('Error downloading PDF.', 'error')
            return redirect(url_for('index'))

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
