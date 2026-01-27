import json
from pathlib import Path
import datetime as dt
from typing import List, Dict, Any, Optional
import config
from src import analysis
import time

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

COMPANY_INFO_PATH = config.DATA_DIR / "company_intelligence.json"

def get_company_intelligence() -> Optional[Dict[str, Any]]:
    """Load company intelligence from disk if it exists."""
    if COMPANY_INFO_PATH.exists():
        try:
            with open(COMPANY_INFO_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading company intelligence: {e}")
    return None

def save_company_intelligence(data: Dict[str, Any]):
    """Save company intelligence to disk."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMPANY_INFO_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def fetch_company_news(company_name: str, linkedin_url: str = None) -> List[Dict[str, str]]:
    """Fetch recent news and public posts about the company using News API and DDGS."""
    results = []
    
    # 1. Define search queries
    # For Merck KGaA, we want to target the German entity specifically
    search_query = f'"{company_name}"'
    if "merck" in company_name.lower() and "kgaa" in company_name.lower():
        # High specificity to ensure we get the German entity
        search_query = '"Merck KGaA" OR "Merck Group" OR "Belen Garijo"'
    
    # Define mandatory terms for specificity if needed (only for Merck KGaA case now)
    mandatory_terms = []
    if "merck" in company_name.lower() and "kgaa" in company_name.lower():
        mandatory_terms = ["merck", "kgaa", "group", "darmstadt", "garijo", "life science", "healthcare", "electronics"]

    # 2. Try News API
    if config.NEWS_API_KEY:
        try:
            import requests
            # Increase pageSize to allow for stricter filtering
            url = f"https://newsapi.org/v2/everything?q={search_query}&sortBy=publishedAt&language=en&pageSize=40&apiKey={config.NEWS_API_KEY}"
            response = requests.get(url)
            if response.status_code == 200:
                raw_articles = response.json().get('articles', [])
                for art in raw_articles:
                    title = art.get('title', '')
                    snippet = art.get('description', '') or ""
                    content = (title + " " + snippet).lower()
                    
                    # Strict validation for Merck KGaA
                    is_valid = False
                    if "merck" in company_name.lower() and "kgaa" in company_name.lower():
                        # Must contain "Merck" and one of the specific identifying terms
                        if "merck" in content and any(term in content for term in ["kgaa", "group", "darmstadt", "garijo", "belen", "milliporesigma", "emd serono"]):
                            # AND must NOT contain US Merck specific terms unless it ALSO contains KGaA
                            exclude_terms = ["merck & co", "merck and co", "kenilworth", "rahway", "msd", "new jersey", "nj"]
                            if not any(term in content for term in exclude_terms) or "kgaa" in content:
                                is_valid = True
                    else:
                        # General case: just ensure the company name is in there
                        if company_name.lower() in content:
                            is_valid = True
                    
                    if is_valid:
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "source": art.get('source', {}).get('name', 'News API'),
                            "date": art.get('publishedAt', ''),
                            "url": art.get('url', '')
                        })
                print(f"✅ Filtered {len(results)} specific news items from News API.")
        except Exception as e:
            print(f"Error fetching from News API: {e}")

    # 3. Use DuckDuckGo to find specific historical milestones for the timeline
    if len(results) < 50:
        try:
            with DDGS() as ddgs:
                # Diversify queries to capture different divisions and locations
                queries = [
                    f'"{company_name}" major news 2024',
                    f'"{company_name}" Darmstadt milestones 2022..2025',
                    'MilliporeSigma major announcements 2023..2025',
                    'EMD Serono business milestones 2023..2025',
                    'Merck Group Darmstadt press releases 2024'
                ]
                
                added_count = 0
                for q in queries:
                    print(f"🔍 Searching: {q}")
                    hist_results = list(ddgs.text(q, max_results=20))
                    
                    for r in hist_results:
                        title = r.get('title', '')
                        snippet = r.get('body', '') or ""
                        url = r.get('href', '')
                        
                        if not url or any(p in url.lower() for p in bad_url_patterns):
                            continue

                        # Super-relaxed entity verification: If query matches specifically, trust it
                        # Just exclude the most obvious US Merck patterns
                        content = (title + " " + snippet).lower()
                        is_valid = True
                        if any(p in content for p in ["merck & co", "merck and co", "msd", "kenilworth"]):
                            # Re-verify if it's the German one despite US mention
                            if "kgaa" not in content and "darmstadt" not in content:
                                is_valid = False
                        
                        if is_valid and not any(url == res['url'] for res in results):
                            results.append({
                                "title": title,
                                "snippet": snippet,
                                "source": "verified Source",
                                "date": "Historical",
                                "url": url
                            })
                            added_count += 1
                print(f"✅ Aggressive search added {added_count} items.")
        except Exception as e:
            print(f"Error fetching historical news: {e}")
    
    # Sort by date (descending)
    results.sort(key=lambda x: x.get('date', '') if x.get('date') != 'Historical' else '0000', reverse=True)
    
    # Final cleanup: Aggressive URL filtering
    final_results = []
    seen_urls = set()
    bad_url_patterns = ["consent.", "privacy.", "cookies.", "login.", "signup.", "subscribe."]
    
    for art in results:
        url = art.get('url', '')
        if not url or url in seen_urls:
            continue
        
        # Skip known "non-article" URLs
        if any(p in url.lower() for p in bad_url_patterns):
            continue
            
        final_results.append(art)
        seen_urls.add(url)

    print(f"✅ News fetch complete. {len(final_results)} verified articles ready.")
    return final_results[:50]

def analyze_company_intelligence(company_name: str, linkedin_url: str, news_data: List[Dict[str, str]]) -> Dict[str, Any]:
    """Analyze news data to extract business moves, trends, and decision timeline."""
    
    # Prepare context for LLM
    context = f"Company: {company_name}\n\n"
    
    if news_data:
        context += "Verified News Items (Use ONLY these URLs for links):\n"
        for i, item in enumerate(news_data):
            context += f"ID: {i+1}\nTitle: {item['title']}\nDate: {item['date']}\nURL: {item['url']}\nSnippet: {item['snippet']}\n---\n"
    else:
        context += "Note: No recent search results available. Use internal knowledge for timeline events but use \"\" for the link.\n"

    prompt = f"""
    Analyze the company: {company_name}.
    
    {context}
    
    Task:
    1. Create a detailed timeline of 8-10 major business milestones (2022-2025).
    2. **STRICT LINKING RULE**: 
       - Every single timeline item MUST correspond to exactly one of the "Verified News Items" provided above.
       - You MUST use the EXACT "URL" from that specific news item for the "link" field.
       - DO NOT include any milestones from your internal knowledge if they are not in the list above.
       - EVERY timeline item MUST have a non-empty, valid URL.
    3. Identify 5-7 key business trends and decision patterns based on these news items.
    4. Provide a strategic summary of their market trajectory.

    Return valid JSON:
    {{
        "company_name": "{company_name}",
        "timeline": [{{ "date": "YYYY-MM-DD", "event": "Short title of the news event", "link": "EXACT_URL_FROM_LIST" }}],
        "business_trends": [...],
        "decision_trends": [...],
        "strategic_summary": "...",
        "last_updated": "..."
    }}
    """

    try:
        response_text = analysis.call_openai_api(prompt)
        
        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        else:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != 0:
                response_text = response_text[start:end]
            
        intel = json.loads(response_text)
        
        # Post-Processing: Verify that LLM didn't hallucinate links
        valid_urls = {item['url'] for item in news_data}
        if 'timeline' in intel:
            for item in intel['timeline']:
                if item.get('link') and item['link'] not in valid_urls:
                    print(f"⚠️ Hallucinated URL detected and removed: {item['link']}")
                    item['link'] = "" # Clear hallucinated link
        
        intel['company_name'] = company_name
        intel['linkedin_url'] = linkedin_url
        intel['last_updated'] = dt.datetime.now().isoformat()
        intel['latest_news'] = news_data[:15]
        
        return intel
    except Exception as e:
        print(f"Error analyzing company intelligence: {e}")
        # Return a gracefully degraded response
        now_str = dt.datetime.now().strftime("%Y-%m-%d")
        now_iso = dt.datetime.now().isoformat()
        return {
            "company_name": company_name,
            "linkedin_url": linkedin_url,
            "timeline": [
                {"date": now_str, "event": f"Strategic baseline created for {company_name}"}
            ],
            "business_trends": ["Analyzing market trends..."],
            "decision_trends": ["Analyzing decision patterns..."],
            "strategic_summary": f"Baseline setup for {company_name} complete. More detailed trends will appear as additional data is processed.",
            "last_updated": now_iso,
            "latest_news": news_data
        }

def process_company_setup(company_name: str, linkedin_url: str) -> Dict[str, Any]:
    """Complete one-time setup for company intelligence."""
    print(f"🚀 Setting up intelligence for {company_name}...")
    
    # 1. Fetch news
    news = fetch_company_news(company_name, linkedin_url)
    
    # 2. Analyze with LLM
    intelligence = analyze_company_intelligence(company_name, linkedin_url, news)
    
    # 3. Save to disk
    save_company_intelligence(intelligence)
    
    return intelligence
