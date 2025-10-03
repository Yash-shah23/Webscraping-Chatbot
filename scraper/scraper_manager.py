import os
import json
import uuid
import datetime
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from scraper.static_scraper import scrape_static
from scraper.dynamic_scraper import scrape_dynamic
from scraper.tech_detector import analyze_technology
from scraper.supabase_manager import upsert_document, create_initial_session, update_session_status
from scraper.rag_handler import prepare_retriever_for_doc

DATA_FOLDER = "data"

def extract_and_clean_content(soup: BeautifulSoup) -> str:
    """Intelligently extracts and cleans the main content from a BeautifulSoup object."""
    main_content = None
    selectors = ['main', 'article', '#content', '#main', '.content', '.main-content']
    for selector in selectors:
        if soup.select_one(selector):
            main_content = soup.select_one(selector)
            break
            
    if not main_content:
        soup_clone = BeautifulSoup(str(soup), 'html.parser')
        noisy_tags = ['nav', 'header', 'footer', 'aside', 'script', 'style', 'form']
        for tag in soup_clone.find_all(noisy_tags):
            tag.decompose()
        main_content = soup_clone.body
        
    if not main_content: return ""

    text = main_content.get_text(separator='\n', strip=False)
    lines = (line.strip() for line in text.splitlines())
    return '\n'.join(line for line in lines if line)

def choose_scraper_strategy(tech_report: dict) -> str:
    """Makes a decision based on the simplified technology list."""
    if not isinstance(tech_report, dict):
        print("[STRATEGY_WARN] Tech report not in expected format. Defaulting to DYNAMIC.")
        return 'dynamic'

    all_techs = set(tech_report.get("technologies", []))
    
    bot_protectors = {'datadome', 'cloudflare bot management', 'akamai', 'imperva'}
    js_frameworks = {'react', 'vue.js', 'angular', 'svelte', 'next.js', 'nuxt.js'}
    
    if not bot_protectors.isdisjoint(all_techs):
        print("[STRATEGY] Bot protection detected. Choosing DYNAMIC scraper.")
        return 'dynamic'
    if not js_frameworks.isdisjoint(all_techs):
        print("[STRATEGY] JavaScript framework detected. Choosing DYNAMIC scraper.")
        return 'dynamic'
    print("[STRATEGY] Standard website detected. Choosing STATIC scraper.")
    return 'static'

def get_page_title_from_path(url: str, base_netloc: str) -> str:
    """Creates a clean title from the URL path."""
    parsed_url = urlparse(url)
    if parsed_url.netloc == base_netloc and parsed_url.path in ('', '/'): return "home"
    path = parsed_url.path.strip('/')
    title = path.split('/')[-1]
    return title if title else "index"

def scrape_and_process_site(start_url: str, doc_id: str, session_id: str):
    """
    The complete, robust pipeline with corrected database logic.
    """
    try:
        # --- STEP 1: Create placeholder records in the CORRECT order ---
        print("[PIPELINE] Creating initial placeholder records...")
        # First, create a placeholder document with an empty content field
        upsert_document(doc_id=doc_id, website_url=start_url, content_data={})
        # NOW, we can safely create the session because the document exists
        create_initial_session(doc_id, session_id)

        # --- STEP 2: Scrape the site (existing logic) ---
        parsed_start_url = urlparse(start_url)
        base_netloc = parsed_start_url.netloc
        if not base_netloc: raise ValueError("Invalid URL provided.")
        
        initial_technologies = analyze_technology(start_url)
        strategy = choose_scraper_strategy(initial_technologies)

        final_output = {
            "doc_id": doc_id, "website_url": f"{parsed_start_url.scheme}://{base_netloc}",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "technologies": initial_technologies, "pages": []
        }
        
        visited = set()
        queue = [start_url]

        while queue:
            current_url = queue.pop(0)
            if current_url in visited: continue
            visited.add(current_url)
            print(f"[CRAWL] Scraping page: {current_url}")

            html = scrape_dynamic(current_url) if strategy == 'dynamic' else scrape_static(current_url)
            if not html: continue

            soup = BeautifulSoup(html, "html.parser")
            content = extract_and_clean_content(soup)
            title = get_page_title_from_path(current_url, base_netloc)
            
            if content:
                final_output["pages"].append({"title": title, "url": current_url, "content": content})

            links = set()
            for a_tag in soup.find_all("a", href=True):
                href = a_tag['href']
                if href and not href.startswith(('mailto:', 'tel:', '#')):
                    full_url = urljoin(current_url, href)
                    if urlparse(full_url).netloc == base_netloc: links.add(full_url)
            for link in links:
                if link not in visited: queue.append(link)

        # --- STEP 3: Save results and finalize status ---
        if final_output["pages"]:
            print("[PIPELINE] Scrape successful. Saving results...")
            
            os.makedirs(DATA_FOLDER, exist_ok=True)
            file_path = os.path.join(DATA_FOLDER, f"{doc_id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(final_output, f, ensure_ascii=False, indent=4)
            print(f"[PIPELINE] Data saved locally to {file_path}")

            # Now, UPDATE the document record with the full scraped content
            upsert_document(doc_id, final_output["website_url"], final_output)

            print("[PIPELINE] Preparing RAG embeddings...")
            rag_ready = prepare_retriever_for_doc(doc_id)

            update_session_status(session_id, 'ready' if rag_ready else 'failed')
        else:
            print("[PIPELINE] No pages were scraped. Marking as failed.")
            update_session_status(session_id, 'failed')
        
        print("[PIPELINE] Background processing complete.")

    except Exception as e:
        print(f"[PIPELINE_ERROR] The background task failed critically: {e}")
        # Ensure the session is marked as failed on any unexpected error
        update_session_status(session_id, 'failed')

