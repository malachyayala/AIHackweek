import requests
from bs4 import BeautifulSoup
import pandas as pd
import csv
import time
import random
from fake_useragent import UserAgent
import logging
import os
import argparse
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def human_like_delay():
    """Generate a human-like delay between requests"""
    # Base delay between 2-7 seconds
    base_delay = np.random.uniform(2, 7)
    
    # Occasionally add longer delays (20% chance)
    if np.random.random() < 0.2:
        base_delay += np.random.uniform(5, 15)
        
    # Add micro-variations
    micro_delay = np.random.normal(0, 0.5)
    total_delay = max(1, base_delay + micro_delay)
    
    logger.debug(f"Waiting {total_delay:.2f} seconds...")
    return total_delay

class LegiScanScraper:
    def __init__(self, state="AK", html_content=None, file_path=None):
        self.state = state.upper()  # Ensure uppercase state code
        self.soup = self._get_soup(html_content, file_path)
        
    def _get_soup(self, html_content=None, file_path=None):
        """Get BeautifulSoup object from HTML content or file"""
        if html_content:
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
            # URL of the LegiScan page for the specified state
            url = f"https://legiscan.com/{self.state}"
            
            # Create a user agent rotation
            try:
                ua = UserAgent()
                headers = {
                    "User-Agent": ua.random,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Cache-Control": "max-age=0",
                    "Referer": "https://www.google.com/"
                }
            except:
                # Fallback user agent if fake_useragent fails
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5"
                }
            
            try:
                # Add human-like delay
                time.sleep(human_like_delay())
                
                response = requests.get(url, headers=headers, timeout=10)
                
                # Check if the request was successful
                if response.status_code != 200:
                    logger.error(f"Failed to retrieve the webpage: Status code {response.status_code}")
                    logger.info("Please save the webpage HTML manually and use the file_path parameter instead")
                    return None
                
                soup = BeautifulSoup(response.content, 'html.parser')
                logger.info(f"Successfully retrieved webpage for {self.state}")
                return soup
                
            except Exception as e:
                logger.error(f"Error fetching the webpage: {e}")
                return None
    
    def scrape_active_bills(self):
        """Scrape active bills from LegiScan page"""
        if not self.soup:
            return None
        
        try:
            # Find the active bills table - it's the first table with class 'gaits-browser'
            latest_anchor = self.soup.find("a", {"name": "latest"})
            if not latest_anchor:
                logger.error("Could not find 'latest' anchor in the HTML")
                return None
                
            active_bills_table = latest_anchor.find_next("table", {"class": "gaits-browser"})
            if not active_bills_table:
                logger.error("Could not find active bills table")
                return None
            
            # Extract the data
            bills_data = []
            
            # Get all rows except the header
            rows = active_bills_table.find_all("tr")[1:]  # Skip the header row
            
            for row in rows:
                try:
                    columns = row.find_all("td")
                    
                    # Extract bill number and link
                    bill_cell = columns[0]
                    bill_link = bill_cell.find("a")
                    bill_number = bill_link.text.strip()
                    bill_url = "https://legiscan.com" + bill_link["href"]
                    
                    # Extract summary
                    summary = columns[1].text.strip()
                    
                    # Extract action and date
                    action_cell = columns[2]
                    date = action_cell.find("span", {"class": "gaits-browse-date"}).text.strip()
                    action_div = action_cell.find("div", {"class": "gaits-browse-action"})
                    
                    # Check if action contains a link or just text
                    action_link = action_div.find("a")
                    if action_link:
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
                    logger.warning(f"Error processing active bills row: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(bills_data)} active bills for {self.state}")
            return bills_data
            
        except Exception as e:
            logger.error(f"Error parsing active bills HTML: {e}")
            return None
    
    def scrape_sponsors(self):
        """Scrape top sponsors from LegiScan page"""
        if not self.soup:
            return None
        
        try:
            # Find the sponsors section
            sponsors_anchor = self.soup.find("a", {"name": "sponsors"})
            if not sponsors_anchor:
                logger.error("Could not find 'sponsors' anchor in the HTML")
                return None
            
            # Get the two sponsor tables (House and Senate)
            sponsor_tables = sponsors_anchor.find_next_siblings("table", {"class": "gaits-browser"}, limit=2)
            
            if len(sponsor_tables) != 2:
                logger.error(f"Expected 2 sponsor tables, found {len(sponsor_tables)}")
                return None
            
            house_sponsor_table = sponsor_tables[0]
            senate_sponsor_table = sponsor_tables[1]
            
            # Extract House sponsors
            house_sponsors = []
            house_rows = house_sponsor_table.find_all("tr")[1:]  # Skip header
            
            for row in house_rows:
                try:
                    columns = row.find_all("td")
                    
                    # Extract sponsor name and link
                    sponsor_cell = columns[0]
                    sponsor_link = sponsor_cell.find("a")
                    sponsor_name = sponsor_link.text.strip()
                    sponsor_url = "https://legiscan.com" + sponsor_link["href"]
                    
                    # Extract party if available (in brackets after name)
                    party = ""
                    party_text = sponsor_cell.text.strip()
                    if "[" in party_text and "]" in party_text:
                        party = party_text[party_text.find("[")+1:party_text.find("]")]
                    
                    # Extract number of bills
                    bill_count = columns[1].text.strip()
                    
                    # Extract RSS feed URL if available
                    rss_cell = columns[2]
                    rss_link = rss_cell.find("a")
                    rss_url = rss_link["href"] if rss_link else ""
                    
                    house_sponsors.append({
                        "Name": sponsor_name,
                        "Party": party,
                        "URL": sponsor_url,
                        "Bills Count": bill_count,
                        "RSS URL": rss_url,
                        "Chamber": "House",
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing house sponsor row: {e}")
                    continue
            
            # Extract Senate sponsors
            senate_sponsors = []
            senate_rows = senate_sponsor_table.find_all("tr")[1:]  # Skip header
            
            for row in senate_rows:
                try:
                    columns = row.find_all("td")
                    
                    # Extract sponsor name and link
                    sponsor_cell = columns[0]
                    sponsor_link = sponsor_cell.find("a")
                    sponsor_name = sponsor_link.text.strip()
                    sponsor_url = "https://legiscan.com" + sponsor_link["href"]
                    
                    # Extract party if available (in brackets after name)
                    party = ""
                    party_text = sponsor_cell.text.strip()
                    if "[" in party_text and "]" in party_text:
                        party = party_text[party_text.find("[")+1:party_text.find("]")]
                    
                    # Extract number of bills
                    bill_count = columns[1].text.strip()
                    
                    # Extract RSS feed URL if available
                    rss_cell = columns[2]
                    rss_link = rss_cell.find("a")
                    rss_url = rss_link["href"] if rss_link else ""
                    
                    senate_sponsors.append({
                        "Name": sponsor_name,
                        "Party": party,
                        "URL": sponsor_url,
                        "Bills Count": bill_count,
                        "RSS URL": rss_url,
                        "Chamber": "Senate",
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing senate sponsor row: {e}")
                    continue
            
            # Combine the data
            all_sponsors = house_sponsors + senate_sponsors
            
            logger.info(f"Successfully scraped {len(house_sponsors)} House sponsors and {len(senate_sponsors)} Senate sponsors for {self.state}")
            return all_sponsors
            
        except Exception as e:
            logger.error(f"Error parsing sponsors HTML: {e}")
            return None
    
    def scrape_committees(self):
        """Scrape top committees from LegiScan page"""
        if not self.soup:
            return None
        
        try:
            # Find the committees section
            committees_anchor = self.soup.find("a", {"name": "committees"})
            if not committees_anchor:
                logger.error("Could not find 'committees' anchor in the HTML")
                return None
            
            # Get the two committee tables (House and Senate)
            committee_tables = committees_anchor.find_next_siblings("table", {"class": "gaits-browser"}, limit=2)
            
            if len(committee_tables) != 2:
                logger.error(f"Expected 2 committee tables, found {len(committee_tables)}")
                return None
            
            house_committee_table = committee_tables[0]
            senate_committee_table = committee_tables[1]
            
            # Extract House committees
            house_committees = []
            house_rows = house_committee_table.find_all("tr")[1:]  # Skip header
            
            for row in house_rows:
                try:
                    columns = row.find_all("td")
                    
                    # Extract committee name and link
                    committee_cell = columns[0]
                    committee_link = committee_cell.find("a")
                    committee_name = committee_link.text.strip()
                    committee_url = "https://legiscan.com" + committee_link["href"]
                    
                    # Extract number of bills
                    bill_count = columns[1].text.strip()
                    
                    # Extract RSS feed URL if available
                    rss_cell = columns[2]
                    rss_link = rss_cell.find("a")
                    rss_url = rss_link["href"] if rss_link else ""
                    
                    house_committees.append({
                        "Committee Name": committee_name,
                        "URL": committee_url,
                        "Bills Count": bill_count,
                        "RSS URL": rss_url,
                        "Chamber": "House",
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing house committee row: {e}")
                    continue
            
            # Extract Senate committees
            senate_committees = []
            senate_rows = senate_committee_table.find_all("tr")[1:]  # Skip header
            
            for row in senate_rows:
                try:
                    columns = row.find_all("td")
                    
                    # Extract committee name and link
                    committee_cell = columns[0]
                    committee_link = committee_cell.find("a")
                    committee_name = committee_link.text.strip()
                    committee_url = "https://legiscan.com" + committee_link["href"]
                    
                    # Extract number of bills
                    bill_count = columns[1].text.strip()
                    
                    # Extract RSS feed URL if available
                    rss_cell = columns[2]
                    rss_link = rss_cell.find("a")
                    rss_url = rss_link["href"] if rss_link else ""
                    
                    senate_committees.append({
                        "Committee Name": committee_name,
                        "URL": committee_url,
                        "Bills Count": bill_count,
                        "RSS URL": rss_url,
                        "Chamber": "Senate",
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing senate committee row: {e}")
                    continue
            
            # Combine the data
            all_committees = house_committees + senate_committees
            
            logger.info(f"Successfully scraped {len(house_committees)} House committees and {len(senate_committees)} Senate committees for {self.state}")
            return all_committees
            
        except Exception as e:
            logger.error(f"Error parsing committees HTML: {e}")
            return None
    
    def scrape_viewed_bills(self):
        """Scrape most viewed bills from LegiScan page"""
        if not self.soup:
            return None
        
        try:
            # Find the viewed bills section
            viewed_anchor = self.soup.find("a", {"name": "viewed"})
            if not viewed_anchor:
                logger.error("Could not find 'viewed' anchor in the HTML")
                return None
                
            viewed_bills_table = viewed_anchor.find_next("table", {"class": "gaits-browser"})
            if not viewed_bills_table:
                logger.error("Could not find viewed bills table")
                return None
            
            # Extract the data
            viewed_bills = []
            
            # Get all rows except the header
            rows = viewed_bills_table.find_all("tr")[1:]  # Skip the header row
            
            for row in rows:
                try:
                    columns = row.find_all("td")
                    
                    # Extract bill number and link
                    bill_cell = columns[0]
                    bill_link = bill_cell.find("a")
                    bill_number = bill_link.text.strip()
                    bill_url = "https://legiscan.com" + bill_link["href"]
                    
                    # Extract summary
                    summary = columns[1].text.strip()
                    
                    # Extract bill text link if available
                    text_cell = columns[2]
                    text_link = text_cell.find("a")
                    text_url = "https://legiscan.com" + text_link["href"] if text_link else ""
                    
                    viewed_bills.append({
                        "Bill Number": bill_number,
                        "Bill URL": bill_url,
                        "Summary": summary,
                        "Text URL": text_url,
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing viewed bills row: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(viewed_bills)} viewed bills for {self.state}")
            return viewed_bills
            
        except Exception as e:
            logger.error(f"Error parsing viewed bills HTML: {e}")
            return None
    
    def scrape_monitored_bills(self):
        """Scrape most monitored bills from LegiScan page"""
        if not self.soup:
            return None
        
        try:
            # Find the monitored bills section
            monitored_anchor = self.soup.find("a", {"name": "monitored"})
            if not monitored_anchor:
                logger.error("Could not find 'monitored' anchor in the HTML")
                return None
                
            monitored_bills_table = monitored_anchor.find_next("table", {"class": "gaits-browser"})
            if not monitored_bills_table:
                logger.error("Could not find monitored bills table")
                return None
            
            # Extract the data
            monitored_bills = []
            
            # Get all rows except the header
            rows = monitored_bills_table.find_all("tr")[1:]  # Skip the header row
            
            for row in rows:
                try:
                    columns = row.find_all("td")
                    
                    # Extract bill number and link
                    bill_cell = columns[0]
                    bill_link = bill_cell.find("a")
                    bill_number = bill_link.text.strip()
                    bill_url = "https://legiscan.com" + bill_link["href"]
                    
                    # Extract summary
                    summary = columns[1].text.strip()
                    
                    # Extract bill text link if available
                    text_cell = columns[2]
                    text_link = text_cell.find("a")
                    text_url = "https://legiscan.com" + text_link["href"] if text_link else ""
                    
                    monitored_bills.append({
                        "Bill Number": bill_number,
                        "Bill URL": bill_url,
                        "Summary": summary,
                        "Text URL": text_url,
                        "State": self.state
                    })
                except Exception as e:
                    logger.warning(f"Error processing monitored bills row: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(monitored_bills)} monitored bills for {self.state}")
            return monitored_bills
            
        except Exception as e:
            logger.error(f"Error parsing monitored bills HTML: {e}")
            return None

def save_to_csv(data, filename):
    """Save the extracted data to a CSV file"""
    if not data:
        logger.warning(f"No data to save to {filename}")
        return False
    
    try:
        # Get the fieldnames from the first item in data
        fieldnames = list(data[0].keys())
        
        # Write the data to a CSV file
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Data successfully saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving to CSV {filename}: {e}")
        return False

def save_to_excel(data_dict, filename):
    """Save multiple datasets to an Excel file with multiple sheets"""
    if not data_dict:
        logger.warning(f"No data to save to {filename}")
        return False
    
    try:
        # Create a Pandas Excel writer using XlsxWriter as the engine
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        
        # Write each dataframe to a different worksheet
        for sheet_name, data in data_dict.items():
            if data:
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # Create an empty dataframe if data is None
                pd.DataFrame().to_excel(writer, sheet_name=sheet_name)
        
        # Close the Pandas Excel writer and output the Excel file
        writer.close()
        
        logger.info(f"Data successfully saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving to Excel {filename}: {e}")
        return False

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Scrape legislative data from LegiScan state pages')
    parser.add_argument('--state', type=str, default='AK', help='Two-letter state code (default: AK)')
    parser.add_argument('--file', type=str, help='Path to local HTML file instead of downloading')
    parser.add_argument('--output_dir', type=str, default='legiscan_data', help='Directory to save output files')
    parser.add_argument('--all', action='store_true', help='Scrape all states')
    parser.add_argument('--states', type=str, help='Comma-separated list of state codes to scrape')
    return parser.parse_args()

def scrape_state(state, file_path=None, output_dir='legiscan_data'):
    """Scrape data for a single state"""
    logger.info(f"Scraping data for {state}...")
    
    # Create state-specific output directory
    state_dir = os.path.join(output_dir, state.lower())
    os.makedirs(state_dir, exist_ok=True)
    
    # Initialize scraper
    scraper = LegiScanScraper(state=state, file_path=file_path)
    
    if not scraper or not scraper.soup:
        logger.error(f"Failed to initialize scraper for {state}")
        return False
    
    # Scrape all data with delays between sections
    active_bills = scraper.scrape_active_bills()
    time.sleep(human_like_delay())
    
    sponsors = scraper.scrape_sponsors()
    time.sleep(human_like_delay())
    
    committees = scraper.scrape_committees()
    time.sleep(human_like_delay())
    
    viewed_bills = scraper.scrape_viewed_bills()
    time.sleep(human_like_delay())
    
    monitored_bills = scraper.scrape_monitored_bills()
    
    # Check if any data was scraped
    if not any([active_bills, sponsors, committees, viewed_bills, monitored_bills]):
        logger.error(f"Failed to scrape any data for {state}")
        return False
    
    # Save data as CSV files
    success = True
    if active_bills:
        success &= save_to_csv(active_bills, os.path.join(state_dir, "active_bills.csv"))
    if sponsors:
        success &= save_to_csv(sponsors, os.path.join(state_dir, "sponsors.csv"))
    if committees:
        success &= save_to_csv(committees, os.path.join(state_dir, "committees.csv"))
    if viewed_bills:
        success &= save_to_csv(viewed_bills, os.path.join(state_dir, "viewed_bills.csv"))
    if monitored_bills:
        success &= save_to_csv(monitored_bills, os.path.join(state_dir, "monitored_bills.csv"))
    
    return success

def main():
    # Parse command line arguments
    args = parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Determine which states to scrape
    states_to_scrape = []
    
    if args.all:
        # All US states plus DC and US Congress
        states_to_scrape = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
            'DC', 'US'
        ]
    elif args.states:
        # Parse comma-separated list of states
        states_to_scrape = [state.strip().upper() for state in args.states.split(',')]
    else:
        # Single state
        states_to_scrape = [args.state.upper()]
    
    # Report what we're about to do
    print(f"LegiScan Legislative Data Scraper")
    print(f"--------------------------------")
    print(f"States to scrape: {', '.join(states_to_scrape)}")
    print(f"Output directory: {args.output_dir}")
    print()
    
    # Track results
    results = {}
    
    # Scrape each state
    for state in states_to_scrape:
        file_path = args.file if args.file else None
        
        print(f"Processing {state}...")
        success = scrape_state(state, file_path, args.output_dir)
        results[state] = "Success" if success else "Failed"
        
        # Add a delay between states to avoid rate limiting
        if len(states_to_scrape) > 1 and state != states_to_scrape[-1]:
            delay = random.uniform(5, 15)
            print(f"Waiting {delay:.1f} seconds before processing next state...")
            time.sleep(delay)
    
    # Print summary of results
    print("\nScraping Results:")
    print("----------------")
    for state, result in results.items():
        print(f"{state}: {result}")
    
    # Count successes and failures
    successes = list(results.values()).count("Success")
    failures = list(results.values()).count("Failed")
    
    print(f"\nSummary: {successes} successful, {failures} failed")
    print(f"Data saved to: {os.path.abspath(args.output_dir)}")

if __name__ == "__main__":
    main()