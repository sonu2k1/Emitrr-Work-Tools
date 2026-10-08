import warnings
warnings.filterwarnings("ignore")
import re
import time
import random
import urllib.parse
from typing import Dict, Any, Optional, List
import requests
from bs4 import BeautifulSoup

from extractor_core import extract_title_from_text, clean_title_candidate

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


def get_random_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }


class SearchEngine:
    def __init__(self, session: Optional[requests.Session] = None, delay: float = 0.5):
        self.session = session or requests.Session()
        self.delay = delay

    def search_yahoo(self, query: str) -> List[Dict[str, str]]:
        """Searches Yahoo Web for public profiles and snippets."""
        results = []
        try:
            url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}&n=10"
            headers = get_random_headers()
            resp = self.session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for h3 in soup.select("h3"):
                    title_text = h3.get_text(strip=True)
                    link = ""
                    # Check parent <a> tag
                    parent_a = h3.find_parent("a") or h3.find("a")
                    if parent_a and parent_a.get("href"):
                        raw_href = parent_a.get("href")
                        if "/RU=" in raw_href:
                            try:
                                link = urllib.parse.unquote(raw_href.split("/RU=")[1].split("/RK=")[0])
                            except Exception:
                                link = raw_href
                        else:
                            link = raw_href

                    # Find accompanying snippet paragraph
                    p = h3.find_next("p")
                    snippet_text = p.get_text(strip=True) if p else ""

                    if title_text:
                        results.append({
                            "title": title_text,
                            "snippet": snippet_text,
                            "link": link
                        })
        except Exception:
            pass
        return results

    def search_bing_html(self, query: str) -> List[Dict[str, str]]:
        """Searches Bing Web for public profiles and snippets."""
        results = []
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
            headers = get_random_headers()
            resp = self.session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for item in soup.select("li.b_algo"):
                    title_elem = item.select_one("h2 a, h2")
                    snippet_elem = item.select_one(".b_caption p, .b_algoSlug, p")
                    link = ""
                    if title_elem and title_elem.name == "a":
                        link = title_elem.get("href", "")
                    elif title_elem:
                        a_inside = title_elem.find("a")
                        if a_inside:
                            link = a_inside.get("href", "")

                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "link": link
                        })
        except Exception:
            pass
        return results

    def search_google_public(self, query: str) -> List[Dict[str, str]]:
        """Searches Google search using randomized headers."""
        results = []
        try:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=en&gl=us&num=5"
            headers = get_random_headers()
            resp = self.session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for g in soup.select("div.g, div[data-hveid]"):
                    title_elem = g.select_one("h3")
                    link_elem = g.select_one("a[href]")
                    snippet_elem = g.select_one("div.VwiC3b, div[style*='webkit-line-clamp'], span.aCOpRe")
                    if title_elem and link_elem:
                        link = link_elem.get("href", "")
                        if link.startswith("/url?q="):
                            link = link.split("/url?q=")[1].split("&")[0]
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "link": link
                        })
        except Exception:
            pass
        return results

    def find_title_and_profile(self, email_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes smart cascading search strategy using Apollo.io, LinkedIn, and Web Dorking.
        """
        email = email_info.get("email", "")
        full_name = email_info.get("full_name", "")
        first_name = email_info.get("first_name", "")
        last_name = email_info.get("last_name", "")
        domain = email_info.get("domain", "")
        company_name = email_info.get("company_name", "")

        out = {
            "job_title": "",
            "seniority": "Unknown",
            "company_name": company_name,
            "linkedin_url": "",
            "apollo_url": "",
            "confidence": "None",
            "source": "",
            "raw_snippet": ""
        }

        # Build prioritized list of targeted search queries (Apollo + LinkedIn + Web)
        queries = []
        org = company_name or domain
        
        # 1. Apollo.io People Dork (Exact Name + Org/Domain)
        if full_name and org:
            queries.append(f'site:apollo.io/people "{full_name}" "{org}"')

        # 2. LinkedIn Profile Dork (Exact Name + Org/Domain)
        if full_name and org:
            queries.append(f'site:linkedin.com/in/ "{full_name}" "{org}"')

        # 3. Combined Directory Dork (Apollo + LinkedIn + ZoomInfo)
        if full_name and org:
            queries.append(f'"{full_name}" "{org}" (site:apollo.io OR site:linkedin.com/in/)')

        # 4. Exact Email Dork on Apollo.io
        if email:
            queries.append(f'site:apollo.io "{email}"')

        # 5. Exact Email Global Search
        if email:
            queries.append(f'"{email}"')

        # 6. General Fallback Query
        if full_name and org:
            queries.append(f'"{full_name}" "{org}" job title')

        # Iterate queries across engines
        for q in queries:
            # Random jitter delay to prevent rate limits
            if self.delay > 0:
                time.sleep(self.delay + random.uniform(0.1, 0.3))

            # Query Yahoo Search first (fast and reliable)
            results = self.search_yahoo(q)
            
            # Fallback to Bing
            if not results:
                results = self.search_bing_html(q)
                
            # Fallback to Google
            if not results:
                results = self.search_google_public(q)

            # Analyze search results
            for res in results:
                title_text = res.get("title", "")
                snippet_text = res.get("snippet", "")
                link = res.get("link", "")
                combined_text = f"{title_text} - {snippet_text}"

                # Check for LinkedIn URL
                if "linkedin.com/in/" in link.lower() and not out["linkedin_url"]:
                    out["linkedin_url"] = link

                # Check for Apollo URL
                if "apollo.io/people/" in link.lower() and not out["apollo_url"]:
                    out["apollo_url"] = link

                # Try to extract Job Title
                detected_title = extract_title_from_text(title_text, name=full_name, company=company_name)
                if not detected_title:
                    detected_title = extract_title_from_text(snippet_text, name=full_name, company=company_name)

                if detected_title:
                    out["job_title"] = detected_title
                    out["raw_snippet"] = snippet_text[:200]
                    
                    # Determine source & confidence
                    if "apollo.io" in link.lower() or "apollo" in title_text.lower():
                        out["source"] = "Apollo.io (Public Dork)"
                        out["confidence"] = "High" if full_name.lower() in combined_text.lower() else "Medium"
                        if not out["linkedin_url"] and out["apollo_url"]:
                            out["linkedin_url"] = out["apollo_url"]  # Fallback profile link
                    elif "linkedin.com/in/" in link.lower() or "linkedin" in title_text.lower():
                        out["source"] = "LinkedIn (Public Dork)"
                        out["confidence"] = "High" if full_name.lower() in combined_text.lower() else "Medium"
                    else:
                        out["source"] = "Web Search"
                        if full_name.lower() in combined_text.lower() or (company_name and company_name.lower() in combined_text.lower()):
                            out["confidence"] = "Medium"
                        else:
                            out["confidence"] = "Low"
                        
                    return out

        return out
