import sys
from pathlib import Path
from duckduckgo_search import DDGS
import json

# Add project root to path
project_root = Path.cwd()
sys.path.append(str(project_root))

def debug_raw_search():
    company_name = "Merck KGaA"
    print(f"🚀 Debugging raw search for {company_name}...")
    
    bad_url_patterns = ["consent.", "privacy.", "cookies.", "login.", "signup.", "subscribe."]
    
    results = []
    with DDGS() as ddgs:
        for year in [2022, 2023, 2024, 2025]:
            query = f'"{company_name}" major announcement {year}'
            print(f"Searching: {query}")
            res = list(ddgs.text(query, max_results=10))
            print(f"Found {len(res)} items for {year}")
            
            for r in res:
                title = r.get('title', '')
                snippet = r.get('body', '') or ""
                url = r.get('href', '')
                
                reason_filtered = None
                if not url: reason_filtered = "No URL"
                elif any(p in url.lower() for p in bad_url_patterns): reason_filtered = "Bad URL pattern"
                
                content_lower = (title + " " + snippet).lower()
                is_valid = False
                if "merck" in content_lower:
                    exclude_patterns = ["merck & co", "merck and co", "msd", "kenilworth", "rahway", "nj"]
                    if not any(p in content_lower for p in exclude_patterns):
                        is_valid = True
                    if "kgaa" in content_lower or "darmstadt" in content_lower:
                        is_valid = True
                
                if not is_valid: reason_filtered = "Failed entity check"
                
                if reason_filtered:
                    print(f"❌ Filtered: {title[:50]}... | Reason: {reason_filtered}")
                else:
                    print(f"✅ OK: {title[:50]}...")
                    results.append({"title": title, "url": url})
    
    print(f"\nTotal OK items: {len(results)}")

if __name__ == "__main__":
    debug_raw_search()
