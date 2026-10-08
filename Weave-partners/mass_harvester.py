import os
import re
import csv
import time
import requests
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Set, Optional, Callable
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

warnings.filterwarnings("ignore")

from geo_coverage import US_STATES, CANADA_PROVINCES, TOP_US_CANADA_METROS, HEALTHCARE_SECTORS
from master_manager import (
    clean_official_website,
    normalize_domain,
    is_valid_practice_domain,
    clean_practice_name
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
MASS_CSV_PATH = os.path.join(OUTPUT_DIR, "weave_us_canada_customers.csv")

WEAVE_SIGNATURES = [
    r"getweave\.com",
    r"weavecomm\.com",
    r"weavehq",
    r"weave-widget",
    r"cdn\.getweave\.com",
    r"widget\.getweave\.com",
    r"app\.getweave\.com",
    r"book\.getweave\.com",
    r"book2\.getweave\.com",
    r"schedule\.getweave\.com",
    r"online-scheduling\.getweave\.com",
    r"payments\.getweave\.com",
    r"powered by weave",
    r"weave-chat",
    r"weave_widget"
]

SIGNATURE_RE = re.compile("|".join(WEAVE_SIGNATURES), re.IGNORECASE)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def verify_weave_signature(domain_or_url: str, timeout=(3.0, 4.0)) -> Dict[str, any]:
    """
    Scans a domain/URL homepage for active Weave widgets or booking integrations.
    """
    domain = normalize_domain(domain_or_url)
    if not domain:
        return {"uses_weave": False, "evidence": ""}

    url = f"https://{domain}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        html = resp.text or ""
        match = SIGNATURE_RE.search(html)
        if match:
            start = max(match.start() - 30, 0)
            end = min(match.end() + 30, len(html))
            evidence = html[start:end].replace("\n", " ").strip()
            return {"uses_weave": True, "evidence": evidence}
    except Exception:
        # Try HTTP fallback
        try:
            http_url = f"http://{domain}"
            resp = requests.get(http_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            html = resp.text or ""
            match = SIGNATURE_RE.search(html)
            if match:
                start = max(match.start() - 30, 0)
                end = min(match.end() + 30, len(html))
                evidence = html[start:end].replace("\n", " ").strip()
                return {"uses_weave": True, "evidence": evidence}
        except Exception:
            pass

    return {"uses_weave": False, "evidence": ""}

class MassHarvester:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.known_domains: Set[str] = set()
        self.load_existing_records()

    def load_existing_records(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if os.path.exists(MASS_CSV_PATH):
            try:
                with open(MASS_CSV_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dom = normalize_domain(row.get("Clean Domain") or row.get("Official Website", ""))
                        if dom:
                            self.known_domains.add(dom)
            except Exception:
                pass

    def append_record(self, rec: Dict[str, str]):
        file_exists = os.path.exists(MASS_CSV_PATH)
        with open(MASS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            fieldnames = [
                "Practice Name",
                "Official Website",
                "Clean Domain",
                "Healthcare Sector",
                "Location",
                "Country",
                "Weave Verified",
                "Weave Evidence",
                "Date Added"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists or os.path.getsize(MASS_CSV_PATH) == 0:
                writer.writeheader()

            clean_site = clean_official_website(rec.get("official_website", ""))
            clean_dom = normalize_domain(clean_site)

            writer.writerow({
                "Practice Name": rec.get("practice_name", ""),
                "Official Website": clean_site,
                "Clean Domain": clean_dom,
                "Healthcare Sector": rec.get("sector", "Healthcare"),
                "Location": rec.get("location", ""),
                "Country": rec.get("country", "US"),
                "Weave Verified": "Yes" if rec.get("uses_weave") else "Candidate",
                "Weave Evidence": rec.get("evidence", ""),
                "Date Added": time.strftime("%Y-%m-%d %H:%M:%S")
            })

    def harvest_sector_location(
        self,
        sector: str,
        keywords: List[str],
        location: str,
        country: str = "US",
        limit: int = 30,
        verify_on_fly: bool = True,
        progress_callback: Optional[Callable[[any], None]] = None
    ) -> List[Dict[str, any]]:
        """
        Scrapes practices for a given sector and location in US/Canada.
        """
        discovered: List[Dict[str, any]] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(user_agent=HEADERS["User-Agent"], locale="en-US")
                page = context.new_page()

                for kw in keywords[:2]:
                    if len(discovered) >= limit:
                        break

                    query = f"{kw} in {location}"
                    maps_url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"

                    try:
                        page.goto(maps_url, wait_until="commit", timeout=18000)
                        page.wait_for_timeout(2500)
                    except Exception:
                        continue

                    # Scroll feed
                    feed = page.query_selector('div[role="feed"]')
                    if feed:
                        for _ in range(4):
                            page.evaluate('document.querySelector("div[role=feed]").scrollTop += 2500')
                            page.wait_for_timeout(800)

                    places = page.query_selector_all('div[role="article"], div.Nv2PK')
                    for place in places:
                        if len(discovered) >= limit:
                            break

                        name_el = place.query_selector('.qBF1Pd, .fontHeadlineSmall, [class*="headline"]')
                        raw_name = name_el.inner_text().strip() if name_el else ""
                        name = clean_practice_name(raw_name)

                        web_el = place.query_selector('a[data-value="Website"], a[aria-label*="website" i], a.lcr4fd')
                        href = web_el.get_attribute('href') if web_el else ""

                        if not href and name:
                            try:
                                place.click(timeout=800)
                                page.wait_for_timeout(600)
                                authority = page.query_selector('a[data-item-id="authority"], a[aria-label*="website" i]')
                                if authority:
                                    href = authority.get_attribute("href")
                            except Exception:
                                pass

                        if href and not href.startswith("/aclk") and "googleadservices" not in href:
                            clean_site = clean_official_website(href)
                            dom = normalize_domain(clean_site)

                            if dom and is_valid_practice_domain(dom) and dom not in self.known_domains:
                                self.known_domains.add(dom)

                                # Live Verification
                                check_res = {"uses_weave": False, "evidence": ""}
                                if verify_on_fly:
                                    check_res = verify_weave_signature(dom)

                                item = {
                                    "practice_name": name,
                                    "official_website": clean_site,
                                    "clean_domain": dom,
                                    "sector": sector,
                                    "location": location,
                                    "country": country,
                                    "uses_weave": check_res["uses_weave"],
                                    "evidence": check_res["evidence"]
                                }

                                self.append_record(item)
                                discovered.append(item)

                                if progress_callback:
                                    progress_callback({"type": "record", "data": item})

                browser.close()
        except Exception as e:
            if progress_callback:
                progress_callback({"type": "log", "message": f"[yellow]Scanner notice for {location}:[/] {str(e)[:60]}"})

        return discovered
