import os
import csv
import argparse
import logging
import time
from scrapeBillText import download_bill_text, setup_undetected_driver # Import necessary functions

# Set up logging (similar to scrapeBillText.py)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_csv_files(input_dir, url_column_name, output_dir, preferred_format, use_proxy, proxy_list):
    """
    Processes all CSV files in the input directory, extracts URLs, and downloads bill text.
    """
    processed_urls = 0
    successful_downloads = 0
    failed_downloads = 0

    # Ensure output directory exists
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        # Default output directory if none provided
        output_dir = os.path.join(os.getcwd(), "batch_scraped_bills")
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"No output directory specified. Using default: {output_dir}")


    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.csv'):
            filepath = os.path.join(input_dir, filename)
            logging.info(f"Processing CSV file: {filename}")

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as csvfile:
                    # Use DictReader to easily access columns by name
                    reader = csv.DictReader(csvfile)

                    # Check if the URL column exists
                    if url_column_name not in reader.fieldnames:
                        logging.error(f"Column '{url_column_name}' not found in {filename}. Skipping file.")
                        # Try to list available columns
                        logging.info(f"Available columns in {filename}: {reader.fieldnames}")
                        continue

                    for row_num, row in enumerate(reader, start=2): # start=2 for header row + 1-based index
                        url = row.get(url_column_name)

                        if url and url.strip().startswith('http'):
                            processed_urls += 1
                            logging.info(f"Attempting download for URL #{processed_urls} from {filename} (Row {row_num}): {url}")

                            # Define a specific output subdirectory for this bill based on the URL
                            # This uses the same logic as in download_bill_text to create a consistent name
                            try:
                                from scrapeBillText import extract_bill_info
                                bill_name = extract_bill_info(url)
                                bill_output_dir = os.path.join(output_dir, bill_name)
                            except Exception: # Fallback if extract_bill_info fails
                                bill_output_dir = os.path.join(output_dir, f"bill_{processed_urls}")

                            # Call the download function from scrapeBillText.py
                            file_path = download_bill_text(
                                url,
                                bill_output_dir, # Pass the specific subdirectory
                                preferred_format,
                                use_proxy,
                                proxy_list
                            )

                            if file_path:
                                logging.info(f"SUCCESS: Bill text saved to {file_path}")
                                successful_downloads += 1
                            else:
                                logging.warning(f"FAILED: Could not download bill text for URL: {url}")
                                failed_downloads += 1

                            # Add a delay between requests to be respectful to the server
                            time.sleep(random.uniform(5, 15)) # Random delay between 5 and 15 seconds

                        elif url:
                            logging.warning(f"Skipping invalid URL in {filename} (Row {row_num}): {url}")
                        # else: URL is empty, skip silently or log if needed

            except FileNotFoundError:
                logging.error(f"CSV file not found: {filepath}")
            except Exception as e:
                logging.error(f"Error processing file {filename}: {e}")

    logging.info("--------------------")
    logging.info("Batch Processing Summary:")
    logging.info(f"Total URLs processed: {processed_urls}")
    logging.info(f"Successful downloads: {successful_downloads}")
    logging.info(f"Failed downloads: {failed_downloads}")
    logging.info("--------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Batch download bill texts from LegiScan URLs found in CSV files.')

    parser.add_argument('input_dir', help='Directory containing the CSV files (e.g., legiscan_dats)')
    parser.add_argument('url_column', help='Name of the column containing the LegiScan URLs in the CSV files')
    parser.add_argument('--output', '-o', help='Base directory to save downloaded files (subfolders will be created)', default=None)
    parser.add_argument('--format', '-f', choices=['pdf', 'html'], help='Preferred format (pdf or html)', default=None)
    parser.add_argument('--use-proxy', '-p', action='store_true', help='Use proxy rotation (requires proxy list)')
    parser.add_argument('--proxy-file', help='File containing list of proxies (one per line)', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO) # Ensure INFO level if not verbose

    # Load proxy list if specified (similar to scrapeBillText.py)
    proxy_list = None
    if args.use_proxy:
        if args.proxy_file:
            try:
                with open(args.proxy_file, 'r') as f:
                    proxy_list = [line.strip() for line in f if line.strip()]
                logging.info(f"Loaded {len(proxy_list)} proxies from {args.proxy_file}")
            except Exception as e:
                logging.error(f"Error loading proxy file '{args.proxy_file}': {e}")
                proxy_list = None
                # Decide if you want to exit or continue without proxies
                # exit(1) # Uncomment to exit if proxy file fails
        else:
            logging.warning("Proxy use enabled (--use-proxy) but no proxy file specified (--proxy-file). Proceeding without proxies.")


    # Import random here if not already imported in scrapeBillText
    import random

    # Start processing
    process_csv_files(
        args.input_dir,
        args.url_column,
        args.output,
        args.format,
        args.use_proxy,
        proxy_list
    )

    print("Batch scraping process finished. Check logs for details.")