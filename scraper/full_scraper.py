import os
import json
import asyncio
import uuid
from urllib.parse import urljoin, urlparse
import datetime
from bs4 import BeautifulSoup
from scraper.static_scraper import scrape_static
from scraper.dynamic_scraper import scrape_dynamic
from scraper.scraper_manager import detect_js_heavy
import requests

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

visited_urls = set()

async def scrape_url(url):
    if url in visited_urls:
        return None
    visited_urls.add(url)

    # Detect JS-heavy
    is_js, scripts_count, scripts_length = detect_js_heavy(url)
    scraper_type = "Dynamic (requests-html)" if is_js else "Static (BeautifulSoup/Selectolax)"
    print("-"*50)
    print(f"[INFO] URL processed: {url}")
    print(f"[INFO] Detected scripts: {scripts_count}, length={scripts_length}")
    print(f"[INFO] Suggested scraper: {scraper_type}")
    print("-"*50)

    if is_js:
        result = await scrape_dynamic(url)
    else:
        result = scrape_static(url)

    result.update({
        "id": str(uuid.uuid4()),
        "url": url,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    # Save JSON locally
    file_path = os.path.join(DATA_DIR, f"{uuid.uuid4()}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Crawl internal links
    try:
        base = urlparse(url).scheme + "://" + urlparse(url).netloc
        links = []
        if not is_js:
            # Only static scraping for links
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = urljoin(base, a['href'])
                if base in href and href not in visited_urls:
                    links.append(href)
        for link in links:
            await scrape_url(link)
    except Exception as e:
        print(f"[ERROR] Crawling failed for {url}: {e}")

    return result

async def scrape_site(url, session_id):
    visited_urls.clear()
    return await scrape_url(url)
