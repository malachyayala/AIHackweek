import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


url = "https://alaska.gov/communit.html"
response = requests.get(url)

soup = BeautifulSoup(response.text, 'html.parser')

# Only get hrefs that contain 'news'
news_links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True) if 'news' in a['href'].lower()]

for link in news_links:
    print(link)
