import warnings
from Wappalyzer import Wappalyzer, WebPage
import builtwith

warnings.filterwarnings("ignore", category=UserWarning, module='Wappalyzer')

def analyze_technology(url: str) -> dict:
    """
    Analyzes a URL's technology and returns a simplified dictionary of key technologies.
    """
    print(f"[INFO] Analyzing technologies for: {url}")
    technologies = set()
    
    # Run Wappalyzer
    try:
        webpage = WebPage.new_from_url(url, timeout=15)
        wappalyzer_client = Wappalyzer.latest()
        wappalyzer_data = wappalyzer_client.analyze(webpage)
        technologies.update(wappalyzer_data)
    except Exception:
        pass # Ignore errors

    # Run BuiltWith
    try:
        builtwith_data = builtwith.parse(url)
        for tech_list in builtwith_data.values():
            technologies.update(tech_list)
    except Exception:
        pass # Ignore errors

    # Return a clean list of unique, lowercased technology names
    return {"technologies": sorted([tech.lower() for tech in technologies])}

