import re
import time
import urllib.parse
from urllib.parse import urlparse, unquote
from typing import List, Dict, Set, Optional
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from valentin import geocode_location, get_valentin_search_params

PRIMARY_CARE_CATEGORIES = {
    1: "Family Medicine",
    2: "Internal Medicine",
    3: "Pediatrics",
    4: "Geriatrics",
    5: "Direct Primary Care",
    6: "Concierge Medicine"
}

EXCLUDED_DOMAINS = {
    "yelp.com", "healthgrades.com", "zocdoc.com", "vitals.com", "webmd.com",
    "doximity.com", "linkedin.com", "facebook.com", "instagram.com", "twitter.com",
    "x.com", "wikipedia.org", "youtube.com", "google.com", "mapquest.com",
    "yellowpages.com", "superpages.com", "bbb.org", "indeed.com", "glassdoor.com",
    "usnews.com", "carecredit.com", "valentin.app", "reddit.com", "quora.com",
    "patch.com", "chamberofcommerce.com", "bizapedia.com", "buzzfile.com",
    "apple.com", "bing.com", "yahoo.com", "duckduckgo.com", "opentable.com",
    "tripadvisor.com", "groupon.com", "angi.com", "thumbtack.com", "nextdoor.com",
    "whitepages.com", "dexknows.com", "citysearch.com", "manta.com"
}

def clean_domain(url_or_domain: str) -> str:
    """
    Extracts and cleans the root domain from a URL or raw domain string.
    """
    if not url_or_domain:
        return ""
    if "://" not in url_or_domain:
        url_or_domain = "http://" + url_or_domain
    try:
        parsed = urlparse(url_or_domain)
        domain = parsed.netloc.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        # Remove trailing port if any
        domain = domain.split(":")[0]
        return domain
    except Exception:
        return ""

def is_valid_practice_domain(domain: str) -> bool:
    """
    Validates if a domain belongs to a real medical practice and not a public directory.
    """
    if not domain or len(domain) < 4 or "." not in domain:
        return False
    if any(domain == ex or domain.endswith("." + ex) for ex in EXCLUDED_DOMAINS):
        return False
    # Avoid file extensions or common search artifacts
    if domain.endswith((".gov", ".edu.cn", ".pdf", ".jpg", ".png")):
        return False
    return True

def clean_practice_name(name: str) -> str:
    """
    Cleans noisy prefixes/suffixes from practice names.
    """
    if not name:
        return ""
    # Strip common SEO suffixes
    name = re.sub(
        r"\s*[-–|•·:]\s*(Home|Welcome|About Us|Official Site|Contact Us|Top Doctors|Primary Care|Family Medicine|Internal Medicine|Pediatrics|Geriatrics|Best Doctor|Reviews|Near Me).*$",
        "",
        name,
        flags=re.IGNORECASE
    )
    # Strip extra whitespace and strange quotes
    name = re.sub(r"\s+", " ", name).strip(' "\'`-,:')
    return name

class PrimaryCareScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def scrape_category_for_location(
        self,
        category: str,
        location: str,
        limit: int = 30,
        progress_callback = None
    ) -> List[Dict[str, str]]:
        """
        Scrapes Practice Name & Domain for a given primary care category in a target US location.
        Uses Valentin.app geocoding + Google Maps localized feed + Search engine fallback.
        """
        results: List[Dict[str, str]] = []
        seen_domains: Set[str] = set()
        seen_names: Set[str] = set()

        # Step 1: Valentin.app Geocoding & Localized Parameters
        valentin_params = get_valentin_search_params(category, location)
        lat = valentin_params["lat"]
        lng = valentin_params["lng"]
        resolved_address = valentin_params["location"]

        if progress_callback:
            progress_callback(f"[bold cyan]Valentin.app:[/] Geocoded [green]{resolved_address}[/] (Lat: {lat:.4f}, Lng: {lng:.4f})")

        # Step 2: Primary Engine - Localized Google Maps with Valentin coordinates
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    locale="en-US"
                )
                page = context.new_page()

                # Search URL with exact Valentin coordinates
                maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(category)}/@{lat},{lng},12z"
                page.goto(maps_url, timeout=30000)
                page.wait_for_timeout(3500)

                # Scroll the feed to load more listings
                feed = page.query_selector('div[role="feed"]')
                if feed:
                    for scroll_idx in range(5):
                        page.evaluate('document.querySelector("div[role=feed]").scrollTop += 2500')
                        page.wait_for_timeout(1200)
                        if len(results) >= limit:
                            break

                # Extract practice cards
                places = page.query_selector_all('div[role="article"], div.Nv2PK')
                for place in places:
                    if len(results) >= limit:
                        break

                    name_el = place.query_selector('.qBF1Pd, .fontHeadlineSmall, [class*="headline"]')
                    raw_name = name_el.inner_text().strip() if name_el else ""
                    name = clean_practice_name(raw_name)

                    # Look for website link
                    web_el = place.query_selector('a[data-value="Website"], a[aria-label*="website" i], a.lcr4fd')
                    href = web_el.get_attribute('href') if web_el else ""

                    domain = clean_domain(href)

                    # If website button wasn't directly in feed card, click the card to inspect details
                    if not domain and name:
                        try:
                            place.click(timeout=1500)
                            page.wait_for_timeout(1000)
                            detail_web = page.query_selector('a[data-item-id="authority"], a[aria-label*="website" i]')
                            if detail_web:
                                detail_href = detail_web.get_attribute("href")
                                domain = clean_domain(detail_href)
                        except Exception:
                            pass

                    if name and is_valid_practice_domain(domain):
                        norm_name = name.lower()
                        if domain not in seen_domains and norm_name not in seen_names:
                            seen_domains.add(domain)
                            seen_names.add(norm_name)
                            item = {
                                "practice_name": name,
                                "domain": domain,
                                "category": category,
                                "location": resolved_address
                            }
                            results.append(item)
                            if progress_callback:
                                progress_callback(item)

                browser.close()
        except Exception as e:
            if progress_callback:
                progress_callback(f"[yellow]Maps engine note:[/] {str(e)[:80]}")

        # Step 3: Secondary Resilient Engine - Localized Web Search Fallback
        if len(results) < limit:
            search_queries = [
                f"{category} practice {location}",
                f"{category} clinic {location}",
                f"{category} doctors {location}"
            ]
            for query in search_queries:
                if len(results) >= limit:
                    break
                try:
                    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                    r = requests.get(search_url, headers=self.headers, timeout=10)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.text, "html.parser")
                        for res in soup.select("div.result"):
                            if len(results) >= limit:
                                break
                            a_tag = res.select_one("a.result__a")
                            if not a_tag:
                                continue
                            href = a_tag.get("href", "")
                            if "uddg=" in href:
                                href = unquote(href.split("uddg=")[1].split("&")[0])
                            
                            domain = clean_domain(href)
                            raw_title = a_tag.text.strip()
                            name = clean_practice_name(raw_title)

                            if name and is_valid_practice_domain(domain):
                                norm_name = name.lower()
                                if domain not in seen_domains and norm_name not in seen_names:
                                    seen_domains.add(domain)
                                    seen_names.add(norm_name)
                                    item = {
                                        "practice_name": name,
                                        "domain": domain,
                                        "category": category,
                                        "location": resolved_address
                                    }
                                    results.append(item)
                                    if progress_callback:
                                        progress_callback(item)
                    time.sleep(1)
                except Exception:
                    pass

        return results
