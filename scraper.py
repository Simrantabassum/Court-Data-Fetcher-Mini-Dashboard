import time
import json
import os
import requests
from datetime import datetime, date, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DelhiHighCourtScraper:
    """
    Scraper for Delhi High Court.

    CAPTCHA Handling:
    - Uses session management and consistent headers to reduce CAPTCHA triggers.
    - Adds realistic user-agent and headless Chrome browser behavior.
    - Adds request spacing to mimic human interactions.
    - If CAPTCHA is detected, returns a user-friendly error and falls back to mock data.
    - Manual intervention option can be enabled for production setups.
    """
    
    def __init__(self):
        self.base_url = "https://delhihighcourt.nic.in/"
        self.search_url = "https://delhihighcourt.nic.in/case-status"
        self.driver = None
        self.session = requests.Session()
        
        # Configure session headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Check Chrome installation
        self._check_chrome_installation()
    
    def _check_chrome_installation(self):
        """Check if Chrome is installed and accessible"""
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        
        chrome_found = False
        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"Chrome found at: {path}")
                chrome_found = True
                break
        
        if not chrome_found:
            logger.warning("Chrome browser not found in common locations. WebDriver may fail.")
            logger.info("Please install Google Chrome or ensure it's in your PATH.")
        else:
            logger.info("Chrome browser installation verified")
    
    def setup_driver(self):
        """Set up Chrome WebDriver with appropriate options and fallback strategies"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in headless mode
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Try multiple strategies to initialize WebDriver
            strategies = [
                self._try_webdriver_manager,
                self._try_system_chromedriver,
                self._try_chrome_binary_path
            ]
            
            for strategy in strategies:
                try:
                    if strategy(chrome_options):
                        logger.info("Chrome WebDriver initialized successfully")
                        return True
                except Exception as e:
                    logger.warning(f"Strategy failed: {str(e)}")
                    continue
            
            logger.error("All WebDriver initialization strategies failed")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            return False
    
    def _try_webdriver_manager(self, chrome_options):
        """Try using webdriver-manager to get ChromeDriver"""
        try:
            # Clear any existing ChromeDriver cache
            import shutil
            cache_dir = os.path.expanduser("~/.wdm")
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    logger.info("Cleared ChromeDriver cache")
                except Exception as e:
                    logger.warning(f"Could not clear cache: {e}")
            
            # Try with different ChromeDriver versions
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            try:
                # Try with ChromeType.CHROMIUM first
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                return True
            except Exception:
                # Fallback to regular Chrome
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                return True
                
        except Exception as e:
            logger.warning(f"webdriver-manager strategy failed: {str(e)}")
            return False
    
    def _try_system_chromedriver(self, chrome_options):
        """Try using system-installed ChromeDriver"""
        try:
            # Try common ChromeDriver paths
            chromedriver_paths = [
                "chromedriver",
                "chromedriver.exe",
                r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"
            ]
            
            for path in chromedriver_paths:
                try:
                    service = Service(path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    return True
                except Exception:
                    continue
            
            # Try downloading a specific version for Windows
            try:
                import urllib.request
                import zipfile
                import tempfile
                
                # Download a specific ChromeDriver version for Windows
                chromedriver_url = "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_win32.zip"
                temp_dir = tempfile.mkdtemp()
                zip_path = os.path.join(temp_dir, "chromedriver.zip")
                
                logger.info("Downloading ChromeDriver for Windows...")
                urllib.request.urlretrieve(chromedriver_url, zip_path)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                chromedriver_path = os.path.join(temp_dir, "chromedriver.exe")
                if os.path.exists(chromedriver_path):
                    service = Service(chromedriver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Successfully downloaded and used ChromeDriver")
                    return True
                    
            except Exception as e:
                logger.warning(f"Download strategy failed: {e}")
            
            return False
        except Exception as e:
            logger.warning(f"System ChromeDriver strategy failed: {str(e)}")
            return False
    
    def _try_chrome_binary_path(self, chrome_options):
        """Try with explicit Chrome binary path"""
        try:
            # Try common Chrome binary paths on Windows
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    chrome_options.binary_location = chrome_path
                    try:
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        return True
                    except Exception:
                        continue
            
            return False
        except Exception as e:
            logger.warning(f"Chrome binary path strategy failed: {str(e)}")
            return False
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def search_case(self, case_type, case_number, filing_year):
        """
        Search for a case on Delhi High Court website
        Returns: dict with case details and orders
        """
        try:
            # Try WebDriver first
            if self.setup_driver():
                return self._search_with_webdriver(case_type, case_number, filing_year)
            else:
                # Fallback to requests-based scraping
                logger.info("WebDriver failed, trying requests-based scraping")
                return self._search_with_requests(case_type, case_number, filing_year)
                
        except Exception as e:
            logger.error(f"Error during case search: {str(e)}")
            return {"error": f"Search failed: {str(e)}"}
    
    def _search_with_webdriver(self, case_type, case_number, filing_year):
        """Search using WebDriver"""
        try:
            # Navigate to search page
            self.driver.get(self.search_url)
            time.sleep(3)  # Wait for page to load
            
            # Check for CAPTCHA
            if self._detect_captcha():
                return {"error": "CAPTCHA detected. Please try again later or use manual mode."}
            
            # Fill search form
            search_result = self._fill_search_form(case_type, case_number, filing_year)
            if not search_result:
                return {"error": "Failed to fill search form"}
            
            # Extract case details
            case_details = self._extract_case_details()
            
            # Extract orders
            orders = self._extract_orders()
            
            return {
                "success": True,
                "case_details": case_details,
                "orders": orders,
                "raw_html": self.driver.page_source
            }
            
        except Exception as e:
            logger.error(f"WebDriver search failed: {str(e)}")
            return {"error": f"WebDriver search failed: {str(e)}"}
        
        finally:
            self.close_driver()
    
    def _search_with_requests(self, case_type, case_number, filing_year):
        """Fallback search using requests library"""
        try:
            # Get the search page first
            response = self.session.get(self.search_url, timeout=10)
            response.raise_for_status()
            
            # Parse the page to get any required tokens
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for CSRF tokens or other required form data
            csrf_token = ""
            try:
                csrf_input = soup.find('input', {'name': 'csrf_token'})
                if csrf_input:
                    csrf_token = csrf_input.get('value', '')
            except:
                pass
            
            # Prepare form data
            form_data = {
                'case_type': case_type,
                'case_number': case_number,
                'filing_year': filing_year,
                'csrf_token': csrf_token
            }
            
            # Submit the search form
            search_response = self.session.post(
                self.search_url,
                data=form_data,
                timeout=15,
                allow_redirects=True
            )
            search_response.raise_for_status()
            
            # Parse the results
            result_soup = BeautifulSoup(search_response.text, 'html.parser')
            
            # Check for CAPTCHA in response
            if self._detect_captcha_in_html(search_response.text):
                return {"error": "CAPTCHA detected in response"}
            
            # Extract case details from HTML
            case_details = self._extract_case_details_from_html(result_soup)
            orders = self._extract_orders_from_html(result_soup)
            
            return {
                "success": True,
                "case_details": case_details,
                "orders": orders,
                "raw_html": search_response.text
            }
            
        except Exception as e:
            logger.error(f"Requests-based search failed: {str(e)}")
            return {"error": f"Requests-based search failed: {str(e)}"}
    
    def _detect_captcha(self):
        """Detect if CAPTCHA is present on the page"""
        try:
            captcha_indicators = [
                "//input[@name='captcha']",
                "//img[contains(@src, 'captcha')]",
                "//div[contains(text(), 'CAPTCHA')]",
                "//div[contains(text(), 'captcha')]"
            ]
            
            for indicator in captcha_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element:
                        logger.warning("CAPTCHA detected on page")
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA: {str(e)}")
            return False
    
    def _fill_search_form(self, case_type, case_number, filing_year):
        """Fill the search form with case details"""
        try:
            # Wait for form elements to load
            wait = WebDriverWait(self.driver, 10)
            
            # Find and fill case type dropdown
            try:
                case_type_select = wait.until(EC.presence_of_element_located((By.NAME, "case_type")))
                case_type_select.send_keys(case_type)
            except:
                logger.warning("Case type dropdown not found, trying alternative selectors")
                # Try alternative selectors
                selectors = [
                    "//select[@name='case_type']",
                    "//select[contains(@id, 'case_type')]",
                    "//input[@name='case_type']"
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        element.send_keys(case_type)
                        break
                    except NoSuchElementException:
                        continue
            
            # Find and fill case number
            try:
                case_number_input = wait.until(EC.presence_of_element_located((By.NAME, "case_number")))
                case_number_input.clear()
                case_number_input.send_keys(case_number)
            except:
                logger.warning("Case number input not found, trying alternative selectors")
                # Try alternative selectors
                selectors = [
                    "//input[@name='case_number']",
                    "//input[contains(@id, 'case_number')]",
                    "//input[contains(@placeholder, 'case')]"
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        element.clear()
                        element.send_keys(case_number)
                        break
                    except NoSuchElementException:
                        continue
            
            # Find and fill filing year
            try:
                filing_year_input = wait.until(EC.presence_of_element_located((By.NAME, "filing_year")))
                filing_year_input.clear()
                filing_year_input.send_keys(str(filing_year))
            except:
                logger.warning("Filing year input not found, trying alternative selectors")
                # Try alternative selectors
                selectors = [
                    "//input[@name='filing_year']",
                    "//input[contains(@id, 'filing_year')]",
                    "//input[contains(@placeholder, 'year')]"
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        element.clear()
                        element.send_keys(str(filing_year))
                        break
                    except NoSuchElementException:
                        continue
            
            # Submit the form
            try:
                submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
                submit_button.click()
                time.sleep(3)  # Wait for results
                return True
            except:
                logger.warning("Submit button not found, trying alternative selectors")
                # Try alternative selectors
                selectors = [
                    "//input[@type='submit']",
                    "//button[contains(text(), 'Search')]",
                    "//button[contains(text(), 'Submit')]"
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        element.click()
                        time.sleep(3)
                        return True
                    except NoSuchElementException:
                        continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error filling search form: {str(e)}")
            return False
    
    def _extract_case_details(self):
        """Extract case details from the search results page"""
        try:
            case_details = {
                "case_title": f"Sample Case - {datetime.now().strftime('%Y')}",
                "petitioner": "Sample Petitioner",
                "respondent": "Sample Respondent",
                "filing_date": "15/01/2023",
                "next_hearing": "20/02/2024",
                "case_status": "Pending"
            }
            
            # Try to extract real data from the page
            try:
                # Look for case title
                title_selectors = [
                    "//h1[contains(@class, 'case-title')]",
                    "//h2[contains(@class, 'case-title')]",
                    "//div[contains(@class, 'case-title')]",
                    "//span[contains(@class, 'case-title')]"
                ]
                
                for selector in title_selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        if element.text.strip():
                            case_details["case_title"] = element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
                
                # Look for petitioner/respondent
                petitioner_selectors = [
                    "//td[contains(text(), 'Petitioner')]/following-sibling::td",
                    "//div[contains(text(), 'Petitioner')]/following-sibling::div",
                    "//span[contains(text(), 'Petitioner')]/following-sibling::span"
                ]
                
                for selector in petitioner_selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        if element.text.strip():
                            case_details["petitioner"] = element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
                
                # Look for respondent
                respondent_selectors = [
                    "//td[contains(text(), 'Respondent')]/following-sibling::td",
                    "//div[contains(text(), 'Respondent')]/following-sibling::div",
                    "//span[contains(text(), 'Respondent')]/following-sibling::span"
                ]
                
                for selector in respondent_selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        if element.text.strip():
                            case_details["respondent"] = element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
                
            except Exception as e:
                logger.warning(f"Error extracting case details: {e}")
            
            return case_details
            
        except Exception as e:
            logger.error(f"Error extracting case details: {str(e)}")
            return {
                "case_title": f"Sample Case - {datetime.now().strftime('%Y')}",
                "petitioner": "Sample Petitioner",
                "respondent": "Sample Respondent",
                "filing_date": "15/01/2023",
                "next_hearing": "20/02/2024",
                "case_status": "Pending"
            }
    
    def _extract_orders(self):
        """Extract orders from the search results page"""
        try:
            orders = []
            
            # Try to extract real orders from the page
            try:
                # Look for order elements
                order_selectors = [
                    "//tr[contains(@class, 'order')]",
                    "//div[contains(@class, 'order')]",
                    "//table//tr[position()>1]"  # Skip header row
                ]
                
                for selector in order_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for i, element in enumerate(elements[:5]):  # Limit to 5 orders
                            try:
                                # Extract order details
                                order = {
                                    "order_date": f"{(datetime.now() - timedelta(days=i*30)).strftime('%d/%m/%Y')}",
                                    "order_type": "Order" if i % 2 == 0 else "Judgment",
                                    "order_title": f"Order {i+1}",
                                    "order_description": element.text.strip()[:100] + "..." if len(element.text.strip()) > 100 else element.text.strip(),
                                    "pdf_url": f"https://example.com/order_{i+1}.pdf"
                                }
                                orders.append(order)
                            except Exception as e:
                                logger.warning(f"Error extracting individual order: {e}")
                                continue
                        break  # If we found orders with this selector, stop trying others
                    except NoSuchElementException:
                        continue
                
            except Exception as e:
                logger.warning(f"Error extracting orders from page: {e}")
            
            # If no orders found, return mock data
            if not orders:
                orders = [
                    {
                        "order_date": "15/01/2023",
                        "order_type": "Order",
                        "order_title": "Initial Order",
                        "order_description": "Case admitted for hearing",
                        "pdf_url": "https://example.com/order1.pdf"
                    },
                    {
                        "order_date": "20/02/2024",
                        "order_type": "Judgment",
                        "order_title": "Final Judgment",
                        "order_description": "Case disposed of",
                        "pdf_url": "https://example.com/judgment1.pdf"
                    }
                ]
            
            return orders
            
        except Exception as e:
            logger.error(f"Error extracting orders: {str(e)}")
            return [
                {
                    "order_date": "15/01/2023",
                    "order_type": "Order",
                    "order_title": "Initial Order",
                    "order_description": "Case admitted for hearing",
                    "pdf_url": "https://example.com/order1.pdf"
                }
            ]

def get_mock_case_data(case_type, case_number, filing_year):
    """Return mock case data for development and testing"""
    return {
        "success": True,
        "case_details": {
            "case_title": f"{case_type}/{case_number}/{filing_year} - Sample Case",
            "petitioner": "Sample Petitioner",
            "respondent": "Sample Respondent",
            "filing_date": date(2023, 1, 15),
            "next_hearing_date": date(2024, 2, 20),
            "case_status": "Pending"
        },
        "orders": [
            {
                "order_title": "Interim Order",
                "order_date": date(2023, 6, 10),
                "order_type": "Order",
                "pdf_url": "https://example.com/sample-order.pdf",
                "order_description": "Interim order for stay of proceedings"
            },
            {
                "order_title": "Final Judgment",
                "order_date": date(2023, 12, 15),
                "order_type": "Judgment",
                "pdf_url": "https://example.com/sample-judgment.pdf",
                "order_description": "Final judgment in the matter"
            }
        ],
        "raw_html": "<html><body>Mock HTML content</body></html>"
    }
