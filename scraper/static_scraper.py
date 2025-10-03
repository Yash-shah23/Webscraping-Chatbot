from bs4 import BeautifulSoup
import requests

def scrape_static(url):
    print(f"[INFO] Using static scraper for: {url}")
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[ERROR] Static scraping failed: {e}")
        return ""
