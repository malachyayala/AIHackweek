# Complete working example with full location information

# Method 1: Using the US Census Bureau ZIP Code Tabulation Area (ZCTA) Relationship files
# This approach uses pandas to read a CSV file from the Census Bureau that maps ZIP codes to counties
import pandas as pd
import requests
import io

def download_and_prepare_zip_county_mapping():
    """Download and prepare the ZIP Code to County mapping from the US Census Bureau"""
    # URL to the ZIP-county relationship file (2020 data)
    url = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt"
    
    try:
        # Download the file
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Read the file into a pandas DataFrame
        df = pd.read_csv(io.StringIO(response.text), sep=',', dtype={'ZCTA5': str, 'COUNTY': str})
        
        # Process the data: rename columns, extract county name
        mapping_df = df[['ZCTA5', 'COUNTY', 'COUNTYNAME']].copy()
        mapping_df.columns = ['zipcode', 'county_fips', 'county_name']
        
        return mapping_df
    
    except Exception as e:
        print(f"Error downloading or processing ZIP-county mapping: {e}")
        return None

def get_county_from_zip(zipcode, mapping_df=None):
    """Get county name from ZIP code using the Census mapping"""
    # If mapping_df is not provided, download it
    if mapping_df is None:
        mapping_df = download_and_prepare_zip_county_mapping()
        
    if mapping_df is None:
        return None
    
    # Ensure zipcode is a string with leading zeros
    zipcode = str(zipcode).zfill(5)
    
    # Find the zipcode in the mapping
    matches = mapping_df[mapping_df['zipcode'] == zipcode]
    
    if matches.empty:
        return None
    
    # If there are multiple counties for this ZIP (common), return all of them
    if len(matches) > 1:
        return matches['county_name'].tolist()
    
    # Return the single county name
    return matches['county_name'].iloc[0]


# Method 2: Using the pgeocode package to get complete location info
# Install with: pip install pgeocode pandas
import pgeocode
import pandas as pd

def get_location_info_from_zip(zipcode):
    """
    Get complete location information (county, city, state) from a ZIP code using pgeocode
    
    Args:
        zipcode (str or int): The ZIP code to look up
    
    Returns:
        dict: Dictionary containing location information
    """
    try:
        # Initialize the Nominatim geocoder for US
        nomi = pgeocode.Nominatim('us')
        
        # Query the postal code
        result = nomi.query_postal_code(str(zipcode))
        
        # Check if we got a valid result
        if result.empty or pd.isna(result['county_name']):
            return None
        
        # Create a more readable dictionary of the results
        location_info = {
            'zip_code': zipcode,
            'city': result['place_name'],
            'county': result['county_name'],
            'state': result['state_name'],
            'state_code': result['state_code'],
            'latitude': result['latitude'],
            'longitude': result['longitude'],
            'accuracy': result['accuracy']
        }
        
        return location_info
    except Exception as e:
        print(f"Error getting location info from pgeocode: {e}")
        return None

def get_county_from_zip_pgeocode(zipcode):
    """
    Get only the county name from a ZIP code using pgeocode
    
    Args:
        zipcode (str or int): The ZIP code to look up
    
    Returns:
        str: County name if found, None otherwise
    """
    try:
        nomi = pgeocode.Nominatim('us')
        result = nomi.query_postal_code(str(zipcode))
        if not result.empty and not pd.isna(result['county_name']):
            return result['county_name']
        return None
    except Exception as e:
        print(f"Error using pgeocode: {e}")
        return None


# Method 3: Using Census.gov API with requests (more reliable approach)
# This makes a direct request to the Census Bureau's geocoding service
import requests
import json

def get_county_from_zip_census(zipcode):
    # Ensure zipcode is a string
    zipcode = str(zipcode).zfill(5)
    
    # Census.gov API endpoint for ZIP Code Tabulation Areas (ZCTAs)
    url = f"https://geocoding.geo.census.gov/geocoder/geographies/address?street=&city=&state=&benchmark=Public_AR_Current&vintage=Current_Current&layers=84&zip={zipcode}&format=json"
    
    try:
        response = requests.get(url, timeout=10)  # Add timeout for reliability
        if response.status_code == 200:
            data = response.json()
            # Check if we got any matches
            if 'result' in data and 'addressMatches' in data['result'] and len(data['result']['addressMatches']) > 0:
                # Extract county information from response
                result = data['result']['addressMatches'][0]['geographies']['Counties'][0]
                county_name = result['BASENAME']
                county_state = result['STATE']
                return f"{county_name} County, {county_state}"
            else:
                print(f"No match found for ZIP code {zipcode}")
                return None
        else:
            print(f"Error: Census API returned status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Error using Census API: {e}")
        return None


# Method 4: Using the Zippopotam.us API (Simple REST API solution)
# This is a simple, free API that requires no API key
import requests

def get_county_from_zip_zippopotamus(zipcode):
    # Ensure zipcode is a string
    zipcode = str(zipcode).zfill(5)
    
    # API endpoint
    url = f"https://api.zippopotam.us/us/{zipcode}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # The API doesn't directly provide county, but it gives state and place name
            state = data['places'][0]['state']
            place = data['places'][0]['place name']
            return f"{place}, {state}"
        elif response.status_code == 404:
            print(f"ZIP code {zipcode} not found")
            return None
        else:
            print(f"Error: API returned status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Error using Zippopotam.us API: {e}")
        return None


# Method 5: Simplified approach with a local CSV file
# If you have a ZIP-to-county CSV file downloaded
import pandas as pd

def get_county_from_zip_csv(zipcode, csv_path='zip_county_mapping.csv'):
    try:
        # Load the CSV file (should have 'zipcode' and 'county' columns)
        df = pd.read_csv(csv_path)
        # Convert zipcode to string to handle potential leading zeros
        df['zipcode'] = df['zipcode'].astype(str).str.zfill(5)
        
        # Look up the zipcode
        result = df[df['zipcode'] == str(zipcode).zfill(5)]
        
        if not result.empty:
            return result['county'].iloc[0]
        return None
    except Exception as e:
        print(f"Error using CSV file: {e}")
        return None


# Additional helper function to print location info
def print_location_info(zipcode):
    """
    Print formatted location information for a ZIP code
    
    Args:
        zipcode (str or int): The ZIP code to look up
    """
    location = get_location_info_from_zip(zipcode)
    
    if location:
        print(f"📍 Location Information for ZIP Code {location['zip_code']}")
        print(f"City: {location['city']}")
        print(f"County: {location['county']}")
        print(f"State: {location['state']} ({location['state_code']})")
        print(f"Coordinates: {location['latitude']}, {location['longitude']}")
    else:
        print(f"❌ Could not find information for ZIP code {zipcode}")


# Additional function to handle batch processing
def process_multiple_zipcodes(zip_codes):
    """
    Process multiple ZIP codes and return their location information
    
    Args:
        zip_codes (list): List of ZIP codes to process
    
    Returns:
        dict: Dictionary with ZIP codes as keys and location info as values
    """
    results = {}
    
    for zip_code in zip_codes:
        location_info = get_location_info_from_zip(zip_code)
        results[zip_code] = location_info
        
    return results


def main():
    # Get input from user
    zipcode = input("Enter a ZIP code to find location information: ")
    
    # First try to get complete location info using pgeocode (since this works for you)
    try:
        import pgeocode
        location_info = get_location_info_from_zip(zipcode)
        
        if location_info:
            print(f"\n✓ Found complete location information for ZIP code {zipcode}:")
            print(f"City: {location_info['city']}")
            print(f"County: {location_info['county']}")
            print(f"State: {location_info['state']} ({location_info['state_code']})")
            print(f"Coordinates: {location_info['latitude']}, {location_info['longitude']}")
            return
    except ImportError:
        print("pgeocode not installed. Try: pip install pgeocode")
    
    # If pgeocode didn't work, try with Census API
    print(f"\nLooking up county for ZIP code {zipcode}...")
    county = get_county_from_zip_census(zipcode)
    
    if county:
        print(f"✓ Found using Census API: {county}")
    else:
        # Try Zippopotam.us as last resort
        place_info = get_county_from_zip_zippopotamus(zipcode)
        if place_info:
            print(f"✓ Found place information: {place_info}")
            print("Note: This is city/place information, not county.")
        else:
            print(f"❌ Could not find location information for ZIP code {zipcode}")


# Example of how to run the script
if __name__ == "__main__":
    main()