import re
import time
import urllib.parse
from urllib.parse import urlparse, unquote
from typing import List, Dict, Set, Optional, Callable
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from valentin import geocode_location, get_valentin_search_params
from master_manager import normalize_domain, clean_official_website

# Primary Specialties for Women's Health & OB-GYN / FQHC
OBGYN_CATEGORIES = {
    1: "OB-GYN & Gynecology Practices",
    2: "Women's Health Clinics",
    3: "Maternal-Fetal Medicine (MFM)",
    4: "Reproductive Endocrinology & Fertility Clinics",
    5: "Midwifery & Birth Centers",
    6: "FQHC & Community Health Centers (Women's Health)",
    7: "Gynecological Surgery & Urogynecology"
}

CATEGORY_KEYWORDS = {
    "OB-GYN & Gynecology Practices": ["OB-GYN practice", "Obstetrics and Gynecology", "Gynecologist clinic"],
    "Women's Health Clinics": ["Women's Health Clinic", "Women's Healthcare center", "Women's Medical Group"],
    "Maternal-Fetal Medicine (MFM)": ["Maternal Fetal Medicine practice", "High Risk Pregnancy clinic", "Perinatology center"],
    "Reproductive Endocrinology & Fertility Clinics": ["Fertility Clinic", "Reproductive Endocrinology", "IVF Center"],
    "Midwifery & Birth Centers": ["Midwifery Care", "Women's Birth Center", "Certified Nurse Midwife clinic"],
    "FQHC & Community Health Centers (Women's Health)": ["Community Health Center Women's Health", "FQHC OB-GYN", "Community Women's Care"],
    "Gynecological Surgery & Urogynecology": ["Urogynecology center", "Gynecological Surgery", "Pelvic Health specialists"]
}

# Domains of general directories, social media, government aggregator portals to exclude
EXCLUDED_DOMAINS = {
    "yelp.com", "healthgrades.com", "zocdoc.com", "vitals.com", "webmd.com",
    "doximity.com", "linkedin.com", "facebook.com", "instagram.com", "twitter.com",
    "x.com", "wikipedia.org", "youtube.com", "google.com", "mapquest.com",
    "yellowpages.com", "superpages.com", "bbb.org", "indeed.com", "glassdoor.com",
    "usnews.com", "carecredit.com", "valentin.app", "reddit.com", "quora.com",
    "patch.com", "chamberofcommerce.com", "bizapedia.com", "buzzfile.com",
    "apple.com", "bing.com", "yahoo.com", "duckduckgo.com", "opentable.com",
    "tripadvisor.com", "groupon.com", "angi.com", "thumbtack.com", "nextdoor.com",
    "whitepages.com", "dexknows.com", "citysearch.com", "manta.com", "ezdoctor.com",
    "topnpi.com", "npino.com", "npiprofiles.com", "countyoffice.org", "chamberofcommerce.com",
    "guidestar.org", "sharecare.com", "castleconnolly.com", "wellness.com", "healthcare4ppl.com",
    "zoominfo.com", "bloomberg.com", "crunchbase.com", "apollo.io", "definitivehc.com"
}

def is_valid_practice_domain(domain: str) -> bool:
    """
    Validates if a domain belongs to a real medical practice / provider and not a general directory.
    """
    if not domain or len(domain) < 4 or "." not in domain:
        return False
    
    clean_dom = domain.lower().strip()
    if clean_dom.startswith("www."):
        clean_dom = clean_dom[4:]

    if any(clean_dom == ex or clean_dom.endswith("." + ex) for ex in EXCLUDED_DOMAINS):
        return False
    
    # Avoid file extensions or unrelated services
    if clean_dom.endswith((".gov", ".edu.cn", ".pdf", ".jpg", ".png", ".zip")):
        return False
        
    return True

def clean_practice_name(name: str) -> str:
    """
    Cleans noisy prefixes/suffixes, addresses, SEO headlines from practice names.
    """
    if not name:
        return ""
    
    # Strip common SEO suffixes like ' - Best OBGYN in Dallas'
    name = re.sub(
        r"\s*[-–|•·:]\s*(Home|Welcome|About Us|Official Site|Contact Us|Top Doctors|OB-GYN|Obstetrics|Gynecology|Women's Health|Best Doctor|Reviews|Near Me|Gynecologist).*$",
        "",
        name,
        flags=re.IGNORECASE
    )
    # Strip ratings or review counts if captured in raw text
    name = re.sub(r"\b\d+(\.\d+)?\s*(stars|\(\d+\)|reviews)\b", "", name, flags=re.IGNORECASE)
    # Strip extra whitespace and strange quotes
    name = re.sub(r"\s+", " ", name).strip(' "\'`-,:')
    return name

class OBGYNScraper:
    def __init__(
        self,
        headless: bool = True,
        existing_domains: Optional[Set[str]] = None,
        existing_names: Optional[Set[str]] = None
    ):
        self.headless = headless
        self.existing_domains = existing_domains if existing_domains is not None else set()
        self.existing_names = existing_names if existing_names is not None else set()
        self.session_domains: Set[str] = set()
        self.session_names: Set[str] = set()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }

    def is_new_record(self, name: str, domain: str) -> bool:
        """
        Checks whether the record is already in the Master Sheet or current session.
        """
        if not domain or not is_valid_practice_domain(domain):
            return False
        
        dom = normalize_domain(domain)
        if not dom:
            return False
        
        if dom in self.existing_domains or dom in self.session_domains:
            return False
            
        norm_name = re.sub(r"[^a-zA-Z0-9]", "", name.lower()) if name else ""
        if norm_name and (norm_name in self.existing_names or norm_name in self.session_names):
            return False

        return True

    def register_record(self, name: str, domain: str):
        dom = normalize_domain(domain)
        if dom:
            self.session_domains.add(dom)
        norm_name = re.sub(r"[^a-zA-Z0-9]", "", name.lower()) if name else ""
        if norm_name:
            self.session_names.add(norm_name)

    def scrape_category_location(
        self,
        category: str,
        location: str,
        limit: int = 30,
        progress_callback: Optional[Callable[[any], None]] = None
    ) -> List[Dict[str, str]]:
        """
        Scrapes Practice Name & Official Domain for a given OB-GYN / Women's Health category in target location.
        """
        results: List[Dict[str, str]] = []

        # 1. Geocode via Valentin.app
        valentin_params = get_valentin_search_params(category, location)
        lat = valentin_params["lat"]
        lng = valentin_params["lng"]
        resolved_address = valentin_params["location"]

        if progress_callback:
            progress_callback({
                "type": "log",
                "message": f"Geocoded [green]{resolved_address}[/] (Lat: {lat:.4f}, Lng: {lng:.4f})"
            })

        # Search terms for this category
        keywords = CATEGORY_KEYWORDS.get(category, [category, f"{category} practice", f"{category} clinic"])

        # Engine 1: Playwright Localized Google Maps
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    locale="en-US"
                )
                page = context.new_page()

                for kw in keywords[:2]:
                    if len(results) >= limit:
                        break

                    maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(kw)}/@{lat},{lng},12z"
                    try:
                        page.goto(maps_url, timeout=25000)
                        page.wait_for_timeout(3000)
                    except Exception:
                        continue

                    # Scroll feed to load items
                    feed = page.query_selector('div[role="feed"]')
                    if feed:
                        for _ in range(6):
                            page.evaluate('document.querySelector("div[role=feed]").scrollTop += 2500')
                            page.wait_for_timeout(1000)
                            if len(results) >= limit:
                                break

                    # Extract listings
                    places = page.query_selector_all('div[role="article"], div.Nv2PK')
                    for place in places:
                        if len(results) >= limit:
                            break

                        name_el = place.query_selector('.qBF1Pd, .fontHeadlineSmall, [class*="headline"]')
                        raw_name = name_el.inner_text().strip() if name_el else ""
                        name = clean_practice_name(raw_name)

                        # Extract website link
                        web_el = place.query_selector('a[data-value="Website"], a[aria-label*="website" i], a.lcr4fd')
                        href = web_el.get_attribute('href') if web_el else ""

                        # If website is missing on card, click card to check side drawer
                        if not href and name:
                            try:
                                place.click(timeout=1200)
                                page.wait_for_timeout(800)
                                detail_web = page.query_selector('a[data-item-id="authority"], a[aria-label*="website" i]')
                                if detail_web:
                                    href = detail_web.get_attribute("href")
                            except Exception:
                                pass

                        if href:
                            clean_site = clean_official_website(href)
                            dom = normalize_domain(clean_site)

                            if name and self.is_new_record(name, dom):
                                self.register_record(name, dom)
                                item = {
                                    "practice_name": name,
                                    "official_website": clean_site,
                                    "category": category,
                                    "location": resolved_address,
                                    "source": "Google Maps"
                                }
                                results.append(item)
                                if progress_callback:
                                    progress_callback({"type": "record", "data": item})

                browser.close()
        except Exception as e:
            if progress_callback:
                progress_callback({"type": "log", "message": f"[yellow]Maps scraper notice:[/] {str(e)[:80]}"})

        # Engine 2: Localized Web Search Fallback (DuckDuckGo HTML)
        if len(results) < limit:
            for kw in keywords:
                if len(results) >= limit:
                    break
                
                query = f'"{kw}" {location} site:.com OR site:.org OR site:.health'
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
                            
                            raw_title = a_tag.text.strip()
                            name = clean_practice_name(raw_title)
                            clean_site = clean_official_website(href)
                            dom = normalize_domain(clean_site)

                            if name and self.is_new_record(name, dom):
                                self.register_record(name, dom)
                                item = {
                                    "practice_name": name,
                                    "official_website": clean_site,
                                    "category": category,
                                    "location": resolved_address,
                                    "source": "Web Search"
                                }
                                results.append(item)
                                if progress_callback:
                                    progress_callback({"type": "record", "data": item})
                    time.sleep(0.8)
                except Exception:
                    pass

        return results
