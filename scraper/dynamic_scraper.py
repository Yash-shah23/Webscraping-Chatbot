import undetected_chromedriver as uc
import time

def scrape_dynamic(url: str):
    """
    Uses an undetected-chromedriver instance to scrape dynamic content.
    Now runs in headless mode (no visible browser window).
    """
    print(f"[INFO] Using Undetected-Chromedriver (dynamic scraper) for: {url}")
    
    html = ""
    driver = None
    try:
        options = uc.ChromeOptions()
        # --- KEY CHANGE 1: Run the browser invisibly in the background ---
        options.add_argument('--headless=new')
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # --- KEY CHANGE 2: Force it to use the driver for your installed Chrome version ---
        driver = uc.Chrome(options=options, version_main=140)
        
        driver.get(url)
        time.sleep(5)
        
        html = driver.page_source
        
    except Exception as e:
        print(f"[ERROR] Dynamic scraping with Undetected-Chromedriver failed: {e}")
        
    finally:
        if driver:
            driver.quit()
            
    return html