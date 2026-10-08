import os
import re
import time
import urllib.parse
from urllib.parse import urlparse, unquote
from typing import List, Dict, Set, Optional, Callable
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from valentin import geocode_location, get_valentin_search_params
from master_manager import clean_practice_name, clean_official_website, normalize_domain, is_valid_practice_domain

# Healthcare categories where Weave is the leading patient communications & scheduling system
HEALTHCARE_VERTICALS = {
    1: "Dental & Orthodontics",
    2: "Optometry & Vision Care",
    3: "Veterinary Medicine & Animal Hospitals",
    4: "Physical Therapy & Sports Rehab",
    5: "Plastic Surgery & Medical Spas",
    6: "Podiatry & Foot Specialists",
    7: "Mental & Behavioral Health",
    8: "Primary Care & Family Practice",
    9: "Audiology & Hearing Specialists"
}

VERTICAL_KEYWORDS = {
    "Dental & Orthodontics": [
        "dental clinic",
        "family dentistry",
        "orthodontist",
        "pediatric dental practice"
    ],
    "Optometry & Vision Care": [
        "optometry clinic",
        "eyecare center",
        "family eye care",
        "vision center"
    ],
    "Veterinary Medicine & Animal Hospitals": [
        "veterinary hospital",
        "animal hospital",
        "pet care clinic",
        "veterinary clinic"
    ],
    "Physical Therapy & Sports Rehab": [
        "physical therapy clinic",
        "sports rehabilitation",
        "physical therapy practice"
    ],
    "Plastic Surgery & Medical Spas": [
        "plastic surgery clinic",
        "medical spa aesthetics",
        "facial plastic surgery"
    ],
    "Podiatry & Foot Specialists": [
        "podiatry clinic",
        "foot and ankle specialist",
        "podiatric medicine"
    ],
    "Mental & Behavioral Health": [
        "mental health clinic",
        "psychiatry practice",
        "behavioral health center"
    ],
    "Primary Care & Family Practice": [
        "primary care clinic",
        "family medicine practice",
        "internal medicine clinic"
    ],
    "Audiology & Hearing Specialists": [
        "audiology clinic",
        "hearing aid center",
        "hearing care specialists"
    ]
}

class VerticalFinder:
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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def is_new_record(self, name: str, domain: str) -> bool:
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

    def scrape_vertical_location(
        self,
        category: str,
        location: str,
        limit: int = 25,
        progress_callback: Optional[Callable[[any], None]] = None
    ) -> List[Dict[str, str]]:
        """
        Scrapes practice names & official website domains for a healthcare vertical in a target location.
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

        keywords = VERTICAL_KEYWORDS.get(category, [category, f"{category} clinic"])

        # Engine: Localized Google Maps via Playwright
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
                        page.goto(maps_url, wait_until="commit", timeout=20000)
                        page.wait_for_timeout(3000)
                    except Exception:
                        continue

                    # Scroll feed
                    feed = page.query_selector('div[role="feed"]')
                    if feed:
                        for _ in range(5):
                            page.evaluate('document.querySelector("div[role=feed]").scrollTop += 2500')
                            page.wait_for_timeout(1000)
                            if len(results) >= limit:
                                break

                    # Extract cards
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

                        if not href and name:
                            try:
                                place.click(timeout=1000)
                                page.wait_for_timeout(800)
                                detail_web = page.query_selector('a[data-item-id="authority"], a[aria-label*="website" i]')
                                if detail_web:
                                    href = detail_web.get_attribute("href")
                            except Exception:
                                pass

                        if href and not href.startswith("/aclk") and "googleadservices" not in href:
                            clean_site = clean_official_website(href)
                            dom = normalize_domain(clean_site)

                            if name and self.is_new_record(name, dom):
                                self.register_record(name, dom)
                                item = {
                                    "practice_name": name,
                                    "official_website": clean_site,
                                    "category": category,
                                    "location": resolved_address,
                                    "source": f"Weave Target Vertical - {category}"
                                }
                                results.append(item)
                                if progress_callback:
                                    progress_callback({"type": "record", "data": item})

                browser.close()
        except Exception as e:
            if progress_callback:
                progress_callback({
                    "type": "log",
                    "message": f"[yellow]Maps scanner notice:[/] {str(e)[:80]}"
                })

        return results
