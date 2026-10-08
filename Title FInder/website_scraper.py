import warnings
warnings.filterwarnings("ignore")
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import requests
from bs4 import BeautifulSoup

from extractor_core import extract_title_from_text, ALL_KNOWN_TITLES

COMMON_TEAM_PATHS = [
    "/team", "/our-team", "/meet-the-team", "/about", "/about-us", 
    "/providers", "/our-providers", "/doctors", "/our-doctors", 
    "/staff", "/our-staff", "/leadership", "/who-we-are", "/faculty",
    "/people", "/directory", "/clinical-team"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def scrape_company_team_page(domain: str, full_name: str, first_name: str = "", last_name: str = "") -> Optional[Dict[str, Any]]:
    """
    Crawls website homepage and team/about pages to find a person's designation.
    """
    if not domain or not (full_name or last_name):
        return None

    # Exclude common public free domains
    free_domains = {
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", 
        "aol.com", "comcast.net", "sbcglobal.net", "verizon.net"
    }
    if domain.lower() in free_domains:
        return None

    base_url = f"https://{domain}" if not domain.startswith("http") else domain
    session = requests.Session()
    session.headers.update(HEADERS)

    paths_to_try = list(COMMON_TEAM_PATHS)

    # 1. Fetch Homepage to find dynamic team/about links
    try:
        home_resp = session.get(base_url, timeout=5, allow_redirects=True)
        if home_resp.status_code == 200:
            soup = BeautifulSoup(home_resp.text, "html.parser")
            
            # Check if name is already on homepage
            home_text = soup.get_text()
            if (full_name and full_name.lower() in home_text.lower()) or (last_name and len(last_name) > 3 and last_name.lower() in home_text.lower()):
                title = find_title_in_html_blocks(soup, full_name, last_name)
                if title:
                    return {
                        "job_title": title,
                        "confidence": "Medium",
                        "source": "Website (Homepage)",
                        "url": base_url
                    }

            # Discover dynamic team/about links
            for a in soup.find_all("a"):
                href = a.get("href", "")
                link_txt = a.get_text(strip=True).lower()
                if any(k in href.lower() or k in link_txt for k in ["team", "about", "staff", "provider", "doctor", "founder", "leadership", "faculty"]):
                    if href.startswith("/"):
                        paths_to_try.insert(0, href)
                    elif href.startswith(base_url):
                        rel = href.replace(base_url, "")
                        if rel and rel.startswith("/"):
                            paths_to_try.insert(0, rel)
    except Exception:
        pass

    # Deduplicate paths
    seen_paths = set()
    unique_paths = []
    for p in paths_to_try:
        if p not in seen_paths and len(p) < 60:
            seen_paths.add(p)
            unique_paths.append(p)

    # 2. Check each candidate page (limit to top 5)
    for path in unique_paths[:5]:
        target_url = urllib.parse.urljoin(base_url, path)
        try:
            resp = session.get(target_url, timeout=5, allow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 400:
                soup = BeautifulSoup(resp.text, "html.parser")
                page_text = soup.get_text()
                
                name_match = (
                    (full_name and full_name.lower() in page_text.lower()) or 
                    (last_name and len(last_name) > 3 and f"dr. {last_name.lower()}" in page_text.lower()) or
                    (last_name and len(last_name) > 3 and last_name.lower() in page_text.lower())
                )
                
                if name_match:
                    title = find_title_in_html_blocks(soup, full_name, last_name)
                    if title:
                        return {
                            "job_title": title,
                            "confidence": "Medium",
                            "source": f"Website ({path})",
                            "url": target_url
                        }
        except Exception:
            continue

    return None


def find_title_in_html_blocks(soup: BeautifulSoup, full_name: str, last_name: str = "") -> Optional[str]:
    """Finds title inside relevant card, heading, or paragraph blocks."""
    # Look for cards, list items, or profile blocks
    for card in soup.select("div, section, article, li, tr, p, h1, h2, h3, h4"):
        card_text = card.get_text(" ", strip=True)
        if (full_name and full_name.lower() in card_text.lower()) or (last_name and len(last_name) > 3 and last_name.lower() in card_text.lower()):
            if 10 < len(card_text) < 350:
                title = extract_title_from_text(card_text)
                if title:
                    return title
    return None
