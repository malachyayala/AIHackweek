import os
import time
import re
import logging
import warnings
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import undetected_chromedriver as uc  # pip install undetected-chromedriver
import PyPDF2

# Suppress urllib3 warnings
warnings.filterwarnings("ignore", category=Warning)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_bill_info(url):
    """
    Extracts bill information from the LegiScan URL to create a meaningful filename.
    Works with both bill summary and text page URLs.
    """
    # Same function as in the original script
    text_pattern = r'https?://legiscan\.com/([^/]+)/text/([^/]+)/id/(\d+)'
    bill_pattern = r'https?://legiscan\.com/([^/]+)/bill/([^/]+)/(\d+)'
    drafts_pattern = r'https?://legiscan\.com/([^/]+)/drafts/([^/]+)/(\d+)'
    
    text_match = re.match(text_pattern, url)
    bill_match = re.match(bill_pattern, url)
    drafts_match = re.match(drafts_pattern, url)
    
    if text_match:
        state = text_match.group(1)
        bill_number = text_match.group(2)
        return f"{state}_{bill_number}"
    elif bill_match:
        state = bill_match.group(1)
        bill_number = bill_match.group(2)
        return f"{state}_{bill_number}"
    elif drafts_match:
        state = drafts_match.group(1)
        bill_number = drafts_match.group(2)
        return f"{state}_{bill_number}"
    else:
        return "unknown_bill"

def setup_undetected_driver(download_dir=None):
    """
    Set up and configure an undetectable Chrome driver with appropriate options.
    
    Args:
        download_dir: Directory to save downloaded files
        
    Returns:
        Configured WebDriver instance
    """
    # Configure Chrome options
    options = uc.ChromeOptions()
    
    if download_dir:
        # Ensure download directory exists
        os.makedirs(download_dir, exist_ok=True)
        
        # Set download preferences
        prefs = {
            'download.default_directory': download_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'plugins.always_open_pdf_externally': True  # Don't open PDF in browser
        }
        options.add_experimental_option('prefs', prefs)
    
    # Random common user agents
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    ]
    
    options.add_argument(f'user-agent={random.choice(user_agents)}')
    
    # Additional stealth options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        # Initialize undetected-chromedriver
        driver = uc.Chrome(options=options)
        
        # Set window size to a common resolution
        driver.set_window_size(1920, 1080)
        
        return driver
    except Exception as e:
        logging.error(f"Error setting up undetected Chrome driver: {e}")
        raise

def add_random_delay(min_seconds=2, max_seconds=7):
    """
    Adds a random delay to mimic human behavior.
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def find_text_link_on_summary_page(driver):
    """
    Find the link to the text page from a bill summary page.
    
    Args:
        driver: WebDriver instance on the bill summary page
        
    Returns:
        True if navigation successful, False otherwise
    """
    try:
        # Add random delay before looking for elements
        add_random_delay()
        
        # First try the text link in the status section (bill-last-action div)
        try:
            text_link = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@id='bill-last-action']//a[contains(@href, '/text/') and contains(text(), 'text')]"))
            )
            logging.info("Found text link in status section")
            
            # Simulate human-like interaction (move to element before clicking)
            driver.execute_script("arguments[0].scrollIntoView(true);", text_link)
            add_random_delay(1, 3)
            
            # Click with JavaScript instead of direct click
            driver.execute_script("arguments[0].click();", text_link)
            
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            return True
        except TimeoutException:
            logging.info("No text link found in status section, trying tabs")
            
        # If not found, look for the "Texts" tab
        try:
            texts_tab = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'tabs')]//a[contains(@href, '/drafts/') or contains(@href, '/text/')]"))
            )
            logging.info("Found Texts tab")
            
            # Simulate human-like interaction
            driver.execute_script("arguments[0].scrollIntoView(true);", texts_tab)
            add_random_delay(1, 3)
            
            # Click with JavaScript
            driver.execute_script("arguments[0].click();", texts_tab)
            
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            
            # Check if we're on a drafts page, if so click the first draft link
            if '/drafts/' in driver.current_url:
                try:
                    logging.info("On drafts page, looking for specific draft link")
                    add_random_delay()
                    
                    draft_link = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'tabs')]//a[contains(@href, '/text/') and contains(@href, '/id/')]"))
                    )
                    
                    # Simulate human-like interaction
                    driver.execute_script("arguments[0].scrollIntoView(true);", draft_link)
                    add_random_delay(1, 3)
                    
                    # Click with JavaScript
                    driver.execute_script("arguments[0].click();", draft_link)
                    
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                except TimeoutException:
                    logging.warning("No specific draft link found")
                    return False
            
            return True
        except TimeoutException:
            logging.warning("No text or drafts tab found")
            return False
            
    except Exception as e:
        logging.error(f"Error finding text link: {e}")
        return False

# The rest of the functions (is_html_bill_text, download_pdf_bill, extract_html_bill_text)
# can remain mostly the same, but add random delays in key places

def download_bill_text(url, download_dir=None, prefer_format=None, use_proxy=False, proxy_list=None):
    """
    Main function to download a bill text using undetected Selenium.
    
    Args:
        url: URL of a LegiScan bill page (either summary or text page)
        download_dir: Directory to save the downloaded files
        prefer_format: Preferred format ('pdf' or 'html') if both are available
        use_proxy: Whether to use a proxy
        proxy_list: List of proxy servers to try
        
    Returns:
        Path to the downloaded file or None if download failed
    """
    # Extract bill info for folder name
    bill_name = extract_bill_info(url)
    
    # Create a dedicated download folder if not specified
    if download_dir is None:
        download_dir = os.path.join(os.getcwd(), f"legiscan_bills/{bill_name}")
    
    # Ensure the directory exists
    os.makedirs(download_dir, exist_ok=True)
    
    driver = None
    
    # Try with multiple proxies if provided
    proxies_to_try = proxy_list if use_proxy and proxy_list else [None]
    
    for proxy in proxies_to_try:
        try:
            # Setup the undetected driver
            driver = setup_undetected_driver(download_dir)
            
            # Navigate to the provided URL first
            logging.info(f"Navigating to: {url}")
            driver.get(url)
            
            # Wait for the page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # Add delay before clearing data
            add_random_delay(2, 4)
            
            # Try to clear data, but wrap in try-except
            try:
                driver.execute_script("window.localStorage.clear();")
                driver.execute_script("window.sessionStorage.clear();")
                driver.delete_all_cookies()
            except Exception as e:
                logging.warning(f"Could not clear browser data: {e}")
                # Continue anyway as this is not critical
            
            # Check for Cloudflare challenge or block page
            if "You are being rate limited" in driver.page_source or "Please complete the security check" in driver.page_source:
                logging.warning("Hit Cloudflare protection, waiting...")
                # Wait longer for Cloudflare challenge to possibly resolve
                time.sleep(20)
                
                # Check again for block
                if "You are being rate limited" in driver.page_source or "Please complete the security check" in driver.page_source:
                    logging.error("Still blocked by Cloudflare, will try another proxy if available")
                    driver.quit()
                    driver = None
                    continue
            
            # Check if we're on a bill summary page or a text page
            if '/bill/' in url and '/text/' not in url:
                logging.info("On bill summary page, looking for text link...")
                
                # Find and click the link to the text page
                if not find_text_link_on_summary_page(driver):
                    logging.error("Could not navigate to text page")
                    driver.quit()
                    driver = None
                    continue
            
            # Add another random delay before proceeding
            add_random_delay()
            
            # Now we should be on a text page, determine if it's PDF or HTML
            if prefer_format == 'html' or (is_html_bill_text(driver) and prefer_format != 'pdf'):
                logging.info("Processing as HTML bill text")
                result = extract_html_bill_text(driver, download_dir, bill_name)
                if result:
                    return result
            else:
                logging.info("Processing as PDF bill")
                result = download_pdf_bill(driver, download_dir)
                if result:
                    return result
                
            # If we reach here, the current attempt failed
            logging.warning("Current attempt failed, will try with another proxy if available")
            
        except Exception as e:
            logging.error(f"Error in download process: {e}")
        finally:
            # Clean up
            if driver:
                driver.quit()
                driver = None
    
    # If we've tried all proxies and still failed
    return None

def is_html_bill_text(driver):
    """
    Check if the current page contains HTML bill text rather than a PDF.
    
    Args:
        driver: WebDriver instance on a bill text page
        
    Returns:
        True if it's an HTML bill text, False if it's a PDF or unknown
    """
    try:
        # Add random delay
        add_random_delay(1, 3)
        
        # Look for [HTML] text in the page
        if '[HTML]' in driver.page_source:
            return True
        
        # Look for common HTML bill text containers
        try:
            driver.find_element(By.CLASS_NAME, 'billtext')
            return True
        except NoSuchElementException:
            pass
            
        try:
            driver.find_element(By.ID, 'bill_all')
            return True
        except NoSuchElementException:
            pass
            
        # Check if there's no PDF object or link on the page
        try:
            driver.find_element(By.XPATH, "//object[@type='application/pdf'] | //a[contains(@href, '.pdf')]")
            return False  # If found, it's a PDF page, not HTML
        except NoSuchElementException:
            # No PDF elements found, might be HTML
            return True
            
        return False
    except Exception as e:
        logging.error(f"Error checking if page is HTML bill text: {e}")
        return False

def download_pdf_bill(driver, download_dir):
    """
    Download a PDF bill text from the current page, convert to text, and delete the PDF.
    
    Args:
        driver: WebDriver instance on a bill text page
        download_dir: Directory to save the PDF
        
    Returns:
        Path to the converted text file or None if download failed
    """
    try:
        # Add random delay
        add_random_delay(2, 5)
        
        pdf_path = None
        
        # First look for a direct PDF download link
        try:
            pdf_link = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '.pdf')]"))
            )
            pdf_url = pdf_link.get_attribute('href')
            pdf_filename = os.path.basename(pdf_url)
            
            logging.info(f"Found PDF link: {pdf_url}")
            
            # Simulate human behavior
            driver.execute_script("arguments[0].scrollIntoView(true);", pdf_link)
            add_random_delay(1, 3)
            
            # Click with JavaScript
            driver.execute_script("arguments[0].click();", pdf_link)
            
            # Wait for the download to complete
            pdf_path = os.path.join(download_dir, pdf_filename)
            
            # Wait for the file to exist with timeout
            timeout = 45
            start_time = time.time()
            
            while not os.path.exists(pdf_path) and time.time() - start_time < timeout:
                time.sleep(1)
            
            if os.path.exists(pdf_path):
                try:
                    # Create text filename from PDF filename
                    text_filename = os.path.splitext(pdf_filename)[0] + '.txt'
                    text_path = os.path.join(download_dir, text_filename)
                    
                    # Convert PDF to text using PyPDF2
                    with open(pdf_path, 'rb') as pdf_file:
                        # Create PDF reader object
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        
                        # Extract text from all pages
                        text_content = []
                        for page in pdf_reader.pages:
                            text_content.append(page.extract_text())
                        
                        # Write text content to file
                        with open(text_path, 'w', encoding='utf-8') as text_file:
                            text_file.write('\n\n'.join(text_content))
                    
                    # Delete the original PDF
                    os.remove(pdf_path)
                    logging.info(f"Converted PDF to text and deleted original PDF")
                    
                    return text_path
                    
                except Exception as e:
                    logging.error(f"Error converting PDF to text: {e}")
                    # Clean up PDF if conversion fails
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    return None
            else:
                logging.error("Download timed out or failed")
                return None
                
        except TimeoutException:
            logging.warning("No direct PDF link found, looking for embedded PDF")
            
            # Try embedded PDF object
            try:
                pdf_object = driver.find_element(By.XPATH, "//object[@type='application/pdf']")
                pdf_url = pdf_object.get_attribute('data')
                
                if pdf_url and pdf_url.endswith('.pdf'):
                    pdf_filename = os.path.basename(pdf_url)
                    pdf_path = os.path.join(download_dir, pdf_filename)
                    
                    # Navigate directly to PDF URL
                    driver.get(pdf_url)
                    
                    # Wait for download
                    timeout = 45
                    start_time = time.time()
                    
                    while not os.path.exists(pdf_path) and time.time() - start_time < timeout:
                        time.sleep(1)
                    
                    if os.path.exists(pdf_path):
                        try:
                            # Convert to text using same process as above
                            text_filename = os.path.splitext(pdf_filename)[0] + '.txt'
                            text_path = os.path.join(download_dir, text_filename)
                            
                            with open(pdf_path, 'rb') as pdf_file:
                                pdf_reader = PyPDF2.PdfReader(pdf_file)
                                text_content = []
                                for page in pdf_reader.pages:
                                    text_content.append(page.extract_text())
                                
                                with open(text_path, 'w', encoding='utf-8') as text_file:
                                    text_file.write('\n\n'.join(text_content))
                            
                            # Delete the original PDF
                            os.remove(pdf_path)
                            logging.info(f"Converted PDF to text and deleted original PDF")
                            
                            return text_path
                            
                        except Exception as e:
                            logging.error(f"Error converting PDF to text: {e}")
                            if os.path.exists(pdf_path):
                                os.remove(pdf_path)
                            return None
                    else:
                        logging.error("Download timed out or failed")
                        return None
                        
            except NoSuchElementException:
                logging.warning("No PDF object found")
        
        logging.error("Could not find any PDF to download")
        return None
        
    except Exception as e:
        logging.error(f"Error in PDF download process: {e}")
        # Clean up PDF if it exists
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        return None

def extract_html_bill_text(driver, download_dir, bill_name):
    """
    Extract the HTML bill text from the current page and save it to a file.
    
    Args:
        driver: WebDriver instance on an HTML bill text page
        download_dir: Directory to save the text file
        bill_name: Name of the bill for the filename
        
    Returns:
        Path to the saved text file or None if extraction failed
    """
    try:
        # Add random delay
        add_random_delay(1, 3)
        
        html_content = ""
        
        # Try different methods to find the bill text content
        
        # 1. Try California's billtext div
        try:
            bill_text_div = driver.find_element(By.CLASS_NAME, 'billtext')
            html_content = bill_text_div.get_attribute('outerHTML')
            logging.info("Found bill text in 'billtext' class")
        except NoSuchElementException:
            logging.info("No 'billtext' class found, trying other selectors")
        
        # 2. Try bill_all div
        if not html_content:
            try:
                bill_all_div = driver.find_element(By.ID, 'bill_all')
                html_content = bill_all_div.get_attribute('outerHTML')
                logging.info("Found bill text in 'bill_all' id")
            except NoSuchElementException:
                logging.info("No 'bill_all' id found, trying other selectors")
        
        # 3. Try bill div
        if not html_content:
            try:
                bill_div = driver.find_element(By.ID, 'bill')
                html_content = bill_div.get_attribute('outerHTML')
                logging.info("Found bill text in 'bill' id")
            except NoSuchElementException:
                logging.info("No 'bill' id found, trying other selectors")
        
        # 4. Last resort - get the whole page
        if not html_content:
            logging.warning("Could not find specific bill text container, using entire page")
            html_content = driver.page_source
        
        if html_content:
            # Create a timestamp for the filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_filename = f"{bill_name}_{timestamp}.html"
            
            # Set up the save path
            file_path = os.path.join(download_dir, html_filename)
            
            # Save the HTML content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logging.info(f"Successfully saved HTML bill text to: {file_path}")
            
            # Also save a text-only version for easier reading
            text_filename = f"{bill_name}_{timestamp}.txt"
            text_path = os.path.join(download_dir, text_filename)
            
            # Extract text content
            text_content = driver.find_element(By.TAG_NAME, 'body').text
            
            # Save the text content
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            logging.info(f"Also saved text-only version to: {text_path}")
            
            return file_path
        else:
            logging.error("Failed to extract any HTML content")
            return None
    except Exception as e:
        logging.error(f"Error extracting HTML bill text: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Download bill text from LegiScan using Selenium with anti-detection')
    parser.add_argument('url', help='URL of a LegiScan bill page (either summary or text page)')
    parser.add_argument('--output', '-o', help='Directory to save the downloaded file', default=None)
    parser.add_argument('--format', '-f', choices=['pdf', 'html'], help='Preferred format (pdf or html)', default=None)
    parser.add_argument('--use-proxy', '-p', action='store_true', help='Use proxy rotation (requires proxy list)')
    parser.add_argument('--proxy-file', help='File containing list of proxies (one per line)', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load proxy list if specified
    proxy_list = None
    if args.use_proxy and args.proxy_file:
        try:
            with open(args.proxy_file, 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
            logging.info(f"Loaded {len(proxy_list)} proxies")
        except Exception as e:
            logging.error(f"Error loading proxy file: {e}")
            proxy_list = None
    
    # Download the bill text
    file_path = download_bill_text(args.url, args.output, args.format, args.use_proxy, proxy_list)
    
    if file_path:
        print(f"SUCCESS: Bill text saved to {file_path}")
        exit(0)
    else:
        print("ERROR: Failed to download bill text")
        exit(1)