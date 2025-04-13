import time
import random
import logging
import os
import argparse
import csv
import pandas as pd
import numpy as np

from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
# --- End Selenium Imports ---


# Set up logging (same as before)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def human_like_delay():
    """Generate a human-like delay between requests/actions"""
    # Base delay between 2-7 seconds
    base_delay = np.random.uniform(2, 7)

    # Occasionally add longer delays (20% chance)
    if np.random.random() < 0.2:
        base_delay += np.random.uniform(5, 15)

    # Add micro-variations
    micro_delay = np.random.normal(0, 0.5)
    total_delay = max(1, base_delay + micro_delay) # Ensure at least 1 second

    logger.debug(f"Waiting {total_delay:.2f} seconds...")
    return total_delay

class LegiScanScraperSelenium:
    def __init__(self, state="AK", html_content=None, file_path=None):
        self.state = state.upper()  # Ensure uppercase state code
        self.soup = self._initialize_scraper(html_content, file_path)

    def _initialize_scraper(self, html_content=None, file_path=None):
        """Get BeautifulSoup object using Selenium, HTML content, or file"""
        if html_content:
            logger.info("Initializing scraper from provided HTML content.")
            return BeautifulSoup(html_content, 'html.parser')
        elif file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file.read(), 'html.parser')
                    logger.info(f"Successfully loaded HTML from file: {file_path}")
                    return soup
            except Exception as e:
                logger.error(f"Error loading file: {e}")
                return None
        else:
            # --- Use Selenium to fetch the page ---
            url = f"https://legiscan.com/{self.state}"
            driver = None # Initialize driver variable
            try:
                # User agent setup
                try:
                    ua_string = UserAgent().random
                except:
                    ua_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

                # Configure Chrome options
                chrome_options = ChromeOptions()
                chrome_options.add_argument(f"user-agent={ua_string}")
                chrome_options.add_argument("--headless")  # Run in background
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--log-level=3") # Suppress unnecessary logs
                chrome_options.page_load_strategy = 'normal' # Wait for full page load

                logger.info(f"Initializing WebDriver for {self.state}...")
                # Initialize WebDriver using webdriver-manager
                service = ChromeService('/Users/mj/Desktop/Misc/VSCodeStuff/AIHackweek/chromedriver')
                driver = webdriver.Chrome(service=service, options=chrome_options)

                # Set timeouts
                driver.set_page_load_timeout(30) # Max time for page to load
                driver.implicitly_wait(5) # Implicit wait for elements if needed later

                logger.info(f"Navigating to {url}...")
                # Add human-like delay before navigation
                time.sleep(human_like_delay())
                driver.get(url)

                # Optional: Add a small wait after page load just in case
                # time.sleep(2)

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                logger.info(f"Successfully retrieved and parsed webpage for {self.state}")
                return soup

            except TimeoutException:
                logger.error(f"Timeout error while loading page {url}")
                return None
            except WebDriverException as e:
                logger.error(f"WebDriver error for {self.state}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error fetching the webpage with Selenium for {self.state}: {e}")
                return None
            finally:
                if driver:
                    logger.info(f"Closing WebDriver for {self.state}.")
                    driver.quit()
            # --- End Selenium fetch ---

    # ========================================================================
    # == SCRAPING METHODS (No changes needed from the original script) ==
    # These methods operate on self.soup, which is populated by _initialize_scraper
    # ========================================================================

    def scrape_active_bills(self):
        """Scrape active bills from LegiScan page"""
        if not self.soup:
            logger.warning(f"Soup object not available for {self.state}. Cannot scrape active bills.")
            return None

        try:
            # Find the active bills table - it's the first table with class 'gaits-browser' after the 'latest' anchor
            latest_anchor = self.soup.find("a", {"name": "latest"})
            if not latest_anchor:
                logger.error(f"Could not find 'latest' anchor in the HTML for {self.state}")
                return None

            active_bills_table = latest_anchor.find_next("table", {"class": "gaits-browser"})
            if not active_bills_table:
                logger.error(f"Could not find active bills table for {self.state}")
                # Fallback: Maybe it's the very first table? (Less reliable)
                # active_bills_table = self.soup.find("table", {"class": "gaits-browser"})
                # if not active_bills_table:
                #     logger.error(f"Could not find active bills table (fallback failed) for {self.state}")
                #     return None
                return None # Stick to the anchor method first

            # Extract the data
            bills_data = []

            # Get all rows except the header
            rows = active_bills_table.find_all("tr")[1:]  # Skip the header row

            for row in rows:
                try:
                    columns = row.find_all("td")
                    if len(columns) < 3: # Ensure row has expected columns
                        logger.warning(f"Skipping malformed active bill row for {self.state}: {row.text[:50]}...")
                        continue

                    # Extract bill number and link
                    bill_cell = columns[0]
                    bill_link = bill_cell.find("a")
                    if not bill_link or not bill_link.get("href"):
                        logger.warning(f"Could not find bill link in cell: {bill_cell.text[:50]}...")
                        continue
                    bill_number = bill_link.text.strip()
                    bill_url = "https://legiscan.com" + bill_link["href"]

                    # Extract summary
                    summary = columns[1].text.strip()

                    # Extract action and date
                    action_cell = columns[2]
                    date_span = action_cell.find("span", {"class": "gaits-browse-date"})
                    date = date_span.text.strip() if date_span else "N/A"

                    action_div = action_cell.find("div", {"class": "gaits-browse-action"})
                    if not action_div:
                         logger.warning(f"Could not find action div in cell: {action_cell.text[:50]}...")
                         action = "N/A"
                         action_url = ""
                    else:
                        # Check if action contains a link or just text
                        action_link = action_div.find("a")
                        if action_link and action_link.get("href"):
                            action = action_link.text.strip()
                            action_url = "https://legiscan.com" + action_link["href"]
                        else:
                            action = action_div.text.strip()
                            action_url = ""

                    # Append to bills_data
                    bills_data.append({
                        "Bill Number": bill_number,
                        "Bill URL": bill_url,
                        "Summary": summary,
                        "Action": action,
                        "Action URL": action_url,
                        "Date": date,
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing active bills row for {self.state}: {e} - Row: {row.text[:100]}...")
                    continue # Skip problematic row

            logger.info(f"Successfully scraped {len(bills_data)} active bills for {self.state}")
            return bills_data

        except Exception as e:
            logger.error(f"Error parsing active bills HTML for {self.state}: {e}")
            return None

    def scrape_sponsors(self):
        """Scrape top sponsors from LegiScan page"""
        if not self.soup:
            logger.warning(f"Soup object not available for {self.state}. Cannot scrape sponsors.")
            return None

        try:
            sponsors_anchor = self.soup.find("a", {"name": "sponsors"})
            if not sponsors_anchor:
                logger.error(f"Could not find 'sponsors' anchor in the HTML for {self.state}")
                return None

            # Get the two sponsor tables (House and Senate) - use find_next_siblings
            sponsor_tables = sponsors_anchor.find_next_siblings("table", {"class": "gaits-browser"}, limit=2)

            if len(sponsor_tables) < 1: # Allow for possibility of only one chamber listed or errors
                 logger.warning(f"Could not find any sponsor tables for {self.state} after 'sponsors' anchor.")
                 return None # Or return empty list? Depends on desired behavior. Let's return None if nothing found.
            elif len(sponsor_tables) < 2:
                 logger.warning(f"Found only {len(sponsor_tables)} sponsor table(s) for {self.state}. Expected 2.")

            all_sponsors = []

            # Process tables found
            for i, table in enumerate(sponsor_tables):
                 # Infer chamber based on order, assuming House then Senate if two tables exist
                 chamber = "Unknown"
                 if len(sponsor_tables) == 2:
                     chamber = "House" if i == 0 else "Senate"
                 elif len(sponsor_tables) == 1:
                     # Attempt to infer from preceding header if possible, otherwise 'Unknown'
                     prev_header = table.find_previous(["h3", "h4"])
                     if prev_header:
                         if "House" in prev_header.text: chamber = "House"
                         elif "Senate" in prev_header.text: chamber = "Senate"
                     logger.info(f"Processing single sponsor table found for {self.state}, inferred chamber: {chamber}")

                 rows = table.find_all("tr")[1:]  # Skip header
                 chamber_sponsors = []

                 for row in rows:
                     try:
                         columns = row.find_all("td")
                         if len(columns) < 3:
                             logger.warning(f"Skipping malformed sponsor row for {self.state}: {row.text[:50]}...")
                             continue

                         # Extract sponsor name and link
                         sponsor_cell = columns[0]
                         sponsor_link = sponsor_cell.find("a")
                         if not sponsor_link or not sponsor_link.get("href"):
                             logger.warning(f"Could not find sponsor link in cell: {sponsor_cell.text[:50]}...")
                             continue
                         sponsor_name = sponsor_link.text.strip()
                         sponsor_url = "https://legiscan.com" + sponsor_link["href"]

                         # Extract party if available
                         party = ""
                         party_text = sponsor_cell.text.strip()
                         if "[" in party_text and "]" in party_text:
                             party = party_text[party_text.find("[")+1:party_text.find("]")]

                         # Extract number of bills
                         bill_count = columns[1].text.strip()

                         # Extract RSS feed URL if available
                         rss_cell = columns[2]
                         rss_link = rss_cell.find("a")
                         rss_url = rss_link["href"] if rss_link and rss_link.get("href") else ""

                         chamber_sponsors.append({
                             "Name": sponsor_name,
                             "Party": party,
                             "URL": sponsor_url,
                             "Bills Count": bill_count,
                             "RSS URL": rss_url,
                             "Chamber": chamber,
                             "State": self.state
                         })
                     except Exception as e:
                         logger.warning(f"Error processing sponsor row for {self.state} ({chamber}): {e} - Row: {row.text[:100]}...")
                         continue # Skip problematic row

                 logger.info(f"Scraped {len(chamber_sponsors)} {chamber} sponsors for {self.state}")
                 all_sponsors.extend(chamber_sponsors)

            logger.info(f"Successfully scraped a total of {len(all_sponsors)} sponsors for {self.state}")
            return all_sponsors if all_sponsors else None # Return None if list is empty

        except Exception as e:
            logger.error(f"Error parsing sponsors HTML for {self.state}: {e}")
            return None

    def scrape_committees(self):
        """Scrape top committees from LegiScan page"""
        if not self.soup:
            logger.warning(f"Soup object not available for {self.state}. Cannot scrape committees.")
            return None

        try:
            committees_anchor = self.soup.find("a", {"name": "committees"})
            if not committees_anchor:
                logger.error(f"Could not find 'committees' anchor in the HTML for {self.state}")
                return None

            # Get the committee tables (expecting up to 2)
            committee_tables = committees_anchor.find_next_siblings("table", {"class": "gaits-browser"}, limit=2)

            if len(committee_tables) < 1:
                 logger.warning(f"Could not find any committee tables for {self.state} after 'committees' anchor.")
                 return None
            elif len(committee_tables) < 2:
                 logger.warning(f"Found only {len(committee_tables)} committee table(s) for {self.state}. Expected 2.")

            all_committees = []

            # Process tables found
            for i, table in enumerate(committee_tables):
                 chamber = "Unknown"
                 if len(committee_tables) == 2:
                     chamber = "House" if i == 0 else "Senate"
                 elif len(committee_tables) == 1:
                     prev_header = table.find_previous(["h3", "h4"])
                     if prev_header:
                         if "House" in prev_header.text: chamber = "House"
                         elif "Senate" in prev_header.text: chamber = "Senate"
                     logger.info(f"Processing single committee table found for {self.state}, inferred chamber: {chamber}")


                 rows = table.find_all("tr")[1:]  # Skip header
                 chamber_committees = []

                 for row in rows:
                     try:
                         columns = row.find_all("td")
                         if len(columns) < 3:
                             logger.warning(f"Skipping malformed committee row for {self.state}: {row.text[:50]}...")
                             continue

                         # Extract committee name and link
                         committee_cell = columns[0]
                         committee_link = committee_cell.find("a")
                         if not committee_link or not committee_link.get("href"):
                             logger.warning(f"Could not find committee link in cell: {committee_cell.text[:50]}...")
                             continue
                         committee_name = committee_link.text.strip()
                         committee_url = "https://legiscan.com" + committee_link["href"]

                         # Extract number of bills
                         bill_count = columns[1].text.strip()

                         # Extract RSS feed URL if available
                         rss_cell = columns[2]
                         rss_link = rss_cell.find("a")
                         rss_url = rss_link["href"] if rss_link and rss_link.get("href") else ""

                         chamber_committees.append({
                             "Committee Name": committee_name,
                             "URL": committee_url,
                             "Bills Count": bill_count,
                             "RSS URL": rss_url,
                             "Chamber": chamber,
                             "State": self.state
                         })
                     except Exception as e:
                         logger.warning(f"Error processing committee row for {self.state} ({chamber}): {e} - Row: {row.text[:100]}...")
                         continue

                 logger.info(f"Scraped {len(chamber_committees)} {chamber} committees for {self.state}")
                 all_committees.extend(chamber_committees)

            logger.info(f"Successfully scraped a total of {len(all_committees)} committees for {self.state}")
            return all_committees if all_committees else None

        except Exception as e:
            logger.error(f"Error parsing committees HTML for {self.state}: {e}")
            return None

    def scrape_viewed_bills(self):
        """Scrape most viewed bills from LegiScan page"""
        if not self.soup:
            logger.warning(f"Soup object not available for {self.state}. Cannot scrape viewed bills.")
            return None

        try:
            viewed_anchor = self.soup.find("a", {"name": "viewed"})
            if not viewed_anchor:
                logger.error(f"Could not find 'viewed' anchor in the HTML for {self.state}")
                return None

            viewed_bills_table = viewed_anchor.find_next("table", {"class": "gaits-browser"})
            if not viewed_bills_table:
                logger.error(f"Could not find viewed bills table for {self.state}")
                return None

            # Extract the data
            viewed_bills = []

            # Get all rows except the header
            rows = viewed_bills_table.find_all("tr")[1:]  # Skip the header row

            for row in rows:
                try:
                    columns = row.find_all("td")
                    if len(columns) < 3:
                        logger.warning(f"Skipping malformed viewed bill row for {self.state}: {row.text[:50]}...")
                        continue

                    # Extract bill number and link
                    bill_cell = columns[0]
                    bill_link = bill_cell.find("a")
                    if not bill_link or not bill_link.get("href"):
                        logger.warning(f"Could not find bill link in viewed cell: {bill_cell.text[:50]}...")
                        continue
                    bill_number = bill_link.text.strip()
                    bill_url = "https://legiscan.com" + bill_link["href"]

                    # Extract summary
                    summary = columns[1].text.strip()

                    # Extract bill text link if available
                    text_cell = columns[2]
                    text_link = text_cell.find("a")
                    text_url = "https://legiscan.com" + text_link["href"] if text_link and text_link.get("href") else ""

                    viewed_bills.append({
                        "Bill Number": bill_number,
                        "Bill URL": bill_url,
                        "Summary": summary,
                        "Text URL": text_url,
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing viewed bills row for {self.state}: {e} - Row: {row.text[:100]}...")
                    continue

            logger.info(f"Successfully scraped {len(viewed_bills)} viewed bills for {self.state}")
            return viewed_bills if viewed_bills else None

        except Exception as e:
            logger.error(f"Error parsing viewed bills HTML for {self.state}: {e}")
            return None

    def scrape_monitored_bills(self):
        """Scrape most monitored bills from LegiScan page"""
        if not self.soup:
            logger.warning(f"Soup object not available for {self.state}. Cannot scrape monitored bills.")
            return None

        try:
            monitored_anchor = self.soup.find("a", {"name": "monitored"})
            if not monitored_anchor:
                logger.error(f"Could not find 'monitored' anchor in the HTML for {self.state}")
                return None

            monitored_bills_table = monitored_anchor.find_next("table", {"class": "gaits-browser"})
            if not monitored_bills_table:
                logger.error(f"Could not find monitored bills table for {self.state}")
                return None

            # Extract the data
            monitored_bills = []

            # Get all rows except the header
            rows = monitored_bills_table.find_all("tr")[1:]  # Skip the header row

            for row in rows:
                try:
                    columns = row.find_all("td")
                    if len(columns) < 3:
                        logger.warning(f"Skipping malformed monitored bill row for {self.state}: {row.text[:50]}...")
                        continue

                    # Extract bill number and link
                    bill_cell = columns[0]
                    bill_link = bill_cell.find("a")
                    if not bill_link or not bill_link.get("href"):
                        logger.warning(f"Could not find bill link in monitored cell: {bill_cell.text[:50]}...")
                        continue
                    bill_number = bill_link.text.strip()
                    bill_url = "https://legiscan.com" + bill_link["href"]

                    # Extract summary
                    summary = columns[1].text.strip()

                    # Extract bill text link if available
                    text_cell = columns[2]
                    text_link = text_cell.find("a")
                    text_url = "https://legiscan.com" + text_link["href"] if text_link and text_link.get("href") else ""

                    monitored_bills.append({
                        "Bill Number": bill_number,
                        "Bill URL": bill_url,
                        "Summary": summary,
                        "Text URL": text_url,
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing monitored bills row for {self.state}: {e} - Row: {row.text[:100]}...")
                    continue

            logger.info(f"Successfully scraped {len(monitored_bills)} monitored bills for {self.state}")
            return monitored_bills if monitored_bills else None

        except Exception as e:
            logger.error(f"Error parsing monitored bills HTML for {self.state}: {e}")
            return None


# ========================================================================
# == HELPER FUNCTIONS (save_to_csv, save_to_excel - No changes needed) ==
# ========================================================================
def save_to_csv(data, filename):
    """Save the extracted data to a CSV file"""
    if not data:
        logger.warning(f"No data provided to save to {filename}")
        return False

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Get the fieldnames from the first item in data
        fieldnames = list(data[0].keys())

        # Write the data to a CSV file
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Data successfully saved to {filename}")
        return True
    except IndexError:
         logger.error(f"Cannot save empty data to {filename}")
         return False
    except Exception as e:
        logger.error(f"Error saving to CSV {filename}: {e}")
        return False

def save_to_excel(data_dict, filename):
    """Save multiple datasets to an Excel file with multiple sheets"""
    if not data_dict:
        logger.warning(f"No data dictionary provided to save to {filename}")
        return False

    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    try:
        # Create a Pandas Excel writer using XlsxWriter as the engine
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            found_data = False
            # Write each dataframe to a different worksheet
            for sheet_name, data in data_dict.items():
                if data:
                    found_data = True
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.debug(f"Writing sheet: {sheet_name} with {len(data)} rows")
                else:
                    # Create an empty dataframe if data is None or empty list
                    pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.debug(f"Writing empty sheet: {sheet_name}")

            if not found_data:
                logger.warning(f"No actual data found in dictionary to save to Excel file {filename}. File will contain empty sheets.")
                # The file is still created with empty sheets, which might be desired.

        logger.info(f"Data successfully saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving to Excel {filename}: {e}")
        return False

# ========================================================================
# == MAIN EXECUTION LOGIC (Minor changes for new class name) ==
# ========================================================================
def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Scrape legislative data from LegiScan state pages using Selenium') # Updated description
    parser.add_argument('--state', type=str, default='AK', help='Two-letter state code (default: AK)')
    parser.add_argument('--file', type=str, help='Path to local HTML file instead of downloading')
    parser.add_argument('--output_dir', type=str, default='legiscan_data_selenium', help='Directory to save output files (default: legiscan_data_selenium)') # Changed default dir
    parser.add_argument('--all', action='store_true', help='Scrape all states')
    parser.add_argument('--states', type=str, help='Comma-separated list of state codes to scrape')
    return parser.parse_args()

def scrape_state(state, file_path=None, output_dir='legiscan_data_selenium'):
    """Scrape data for a single state using Selenium"""
    logger.info(f"--- Starting scrape for {state} ---")

    # Create state-specific output directory
    state_dir = os.path.join(output_dir, state.upper()) # Use upper for consistency
    os.makedirs(state_dir, exist_ok=True)

    # Initialize scraper using the Selenium version
    scraper = LegiScanScraperSelenium(state=state, file_path=file_path)

    if not scraper or not scraper.soup:
        logger.error(f"Failed to initialize scraper or get soup for {state}. Aborting scrape for this state.")
        return False # Indicate failure for this state

    # Scrape all data sections
    # Note: Delays between sections might be less critical if Selenium loaded everything,
    # but still good practice if we were doing more interactions or multiple page loads.
    # Keep them for politeness/realism.
    logger.info(f"Scraping active bills for {state}...")
    active_bills = scraper.scrape_active_bills()
    time.sleep(random.uniform(0.5, 1.5)) # Shorter delay between internal scrapes ok

    logger.info(f"Scraping sponsors for {state}...")
    sponsors = scraper.scrape_sponsors()
    time.sleep(random.uniform(0.5, 1.5))

    logger.info(f"Scraping committees for {state}...")
    committees = scraper.scrape_committees()
    time.sleep(random.uniform(0.5, 1.5))

    logger.info(f"Scraping viewed bills for {state}...")
    viewed_bills = scraper.scrape_viewed_bills()
    time.sleep(random.uniform(0.5, 1.5))

    logger.info(f"Scraping monitored bills for {state}...")
    monitored_bills = scraper.scrape_monitored_bills()

    # Check if any data was scraped
    all_data = {
        "active_bills": active_bills,
        "sponsors": sponsors,
        "committees": committees,
        "viewed_bills": viewed_bills,
        "monitored_bills": monitored_bills
    }

    if not any(all_data.values()):
        logger.warning(f"No data scraped for any section in {state}. Check HTML structure or logs.")
        # Decide if this counts as failure or just an empty state page
        return True # Let's say scraping technically worked, just found nothing.

    # --- Save data ---
    save_individual_csv = True # Option to save individual CSVs
    save_combined_excel = True # Option to save one Excel per state

    overall_success = True # Track if all saving operations succeed

    if save_individual_csv:
        logger.info(f"Saving individual CSV files for {state} to {state_dir}")
        overall_success &= save_to_csv(active_bills, os.path.join(state_dir, f"{state.lower()}_active_bills.csv"))
        overall_success &= save_to_csv(sponsors, os.path.join(state_dir, f"{state.lower()}_sponsors.csv"))
        overall_success &= save_to_csv(committees, os.path.join(state_dir, f"{state.lower()}_committees.csv"))
        overall_success &= save_to_csv(viewed_bills, os.path.join(state_dir, f"{state.lower()}_viewed_bills.csv"))
        overall_success &= save_to_csv(monitored_bills, os.path.join(state_dir, f"{state.lower()}_monitored_bills.csv"))

    if save_combined_excel:
         excel_filename = os.path.join(state_dir, f"{state.lower()}_legiscan_summary.xlsx")
         logger.info(f"Saving combined Excel file for {state} to {excel_filename}")
         # Prepare dict for Excel function (using more descriptive sheet names)
         excel_data = {
             "Active Bills": active_bills,
             "Sponsors": sponsors,
             "Committees": committees,
             "Viewed Bills": viewed_bills,
             "Monitored Bills": monitored_bills
         }
         overall_success &= save_to_excel(excel_data, excel_filename)

    logger.info(f"--- Finished scrape for {state} ---")
    return overall_success


def main():
    # Parse command line arguments
    args = parse_args()

    # Create base output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Determine which states to scrape
    states_to_scrape = []
    all_us_states = [ # Added US territories commonly found
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'US', # Federal
        'AS', 'GU', 'MP', 'PR', 'VI' # Territories often included
    ]

    if args.all:
        states_to_scrape = all_us_states
    elif args.states:
        # Parse comma-separated list of states, ensure uppercase, remove duplicates
        states_to_scrape = sorted(list(set([state.strip().upper() for state in args.states.split(',') if state.strip()])))
    else:
        # Single state
        states_to_scrape = [args.state.upper()]

    # Report what we're about to do
    print(f"LegiScan Legislative Data Scraper (using Selenium)")
    print(f"=================================================")
    if args.file:
        print(f"Mode: Scraping from local file: {args.file}")
        if len(states_to_scrape) > 1:
             print("WARNING: --file option provided with multiple states. The same file will be processed for each state specified.")
    else:
        print(f"Mode: Fetching live data from LegiScan")
    print(f"States to scrape: {', '.join(states_to_scrape)}")
    print(f"Output directory: {os.path.abspath(args.output_dir)}")
    print(f"WebDriver: ChromeDriver (via webdriver-manager)")
    print("-" * 50)

    # Track results
    results = {}

    # Scrape each state
    total_states = len(states_to_scrape)
    for i, state in enumerate(states_to_scrape):
        # Use file_path only if it's provided AND we're processing the *first* state (or only one state)
        # Otherwise, default to live fetching for subsequent states unless --all or --states explicitly used with --file (which is weird)
        current_file_path = args.file if (args.file and (total_states == 1 or i == 0)) else None
        if args.file and total_states > 1 and i > 0:
             logger.warning(f"Processing state {state} ({i+1}/{total_states}) without using --file '{args.file}' as it was likely intended only for the first state.")

        print(f"\n[{i+1}/{total_states}] Processing {state}...")
        try:
            success = scrape_state(state, current_file_path, args.output_dir)
            results[state] = "Success" if success else "Failed"
            print(f"[{i+1}/{total_states}] Result for {state}: {results[state]}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during scraping process for state {state}: {e}", exc_info=True)
            results[state] = "ERROR"
            print(f"[{i+1}/{total_states}] Result for {state}: ERROR")


        # Add a delay between states to avoid hammering the site/getting blocked
        # Only sleep if there are more states to process
        if len(states_to_scrape) > 1 and i < total_states - 1:
            # Use a longer delay between states as this involves browser startup/shutdown
            delay = random.uniform(10, 25)
            print(f"Waiting {delay:.1f} seconds before processing next state...")
            time.sleep(delay)

    # Print summary of results
    print("\n" + "=" * 50)
    print("Scraping Run Summary")
    print("=" * 50)
    for state, result in results.items():
        print(f"- {state}: {result}")

    # Count successes and failures
    success_count = list(results.values()).count("Success")
    failed_count = list(results.values()).count("Failed")
    error_count = list(results.values()).count("ERROR")

    print("-" * 50)
    print(f"Total States Processed: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed (data not saved/found): {failed_count}")
    print(f"Errors (unexpected exceptions): {error_count}")
    print(f"\nOutput data saved in: {os.path.abspath(args.output_dir)}")
    print("=" * 50)

if __name__ == "__main__":
    main()