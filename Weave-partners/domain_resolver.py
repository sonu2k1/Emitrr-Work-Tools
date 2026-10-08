import re
import time
import urllib.parse
from urllib.parse import urlparse, unquote
from typing import Optional, Dict, List, Callable
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from master_manager import clean_official_website, normalize_domain, is_valid_practice_domain

class DomainResolver:
    """
    High-performance multi-engine domain resolver specifically optimized for US healthcare practices.
    """
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        self.pw = None
        self.browser = None
        self.page = None

    def start_browser(self):
        """Initializes reusable browser instance for batch resolving."""
        if not self.browser:
            try:
                self.pw = sync_playwright().start()
                self.browser = self.pw.chromium.launch(headless=self.headless)
                context = self.browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    locale="en-US"
                )
                self.page = context.new_page()
            except Exception:
                self.browser = None
                self.page = None

    def close_browser(self):
        """Closes browser session."""
        try:
            if self.browser:
                self.browser.close()
            if self.pw:
                self.pw.stop()
        except Exception:
            pass
        self.browser = None
        self.page = None
        self.pw = None

    def resolve_via_google_maps(self, practice_name: str, location: str = "") -> Optional[str]:
        """
        Uses persistent Playwright Google Maps session to extract practice website.
        """
        if not self.page:
            self.start_browser()
        if not self.page:
            return None

        query = f"{practice_name} {location}".strip()
        maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"

        try:
            self.page.goto(maps_url, wait_until="commit", timeout=12000)
            self.page.wait_for_timeout(2000)

            # 1. Authority website button
            web_btn = self.page.query_selector('a[data-item-id="authority"], a[aria-label*="website" i], a[data-value="Website"]')
            if web_btn:
                href = web_btn.get_attribute("href") or ""
                if href and not href.startswith("/aclk") and "googleadservices" not in href:
                    return clean_official_website(href)

            # 2. Check cards
            cards = self.page.query_selector_all('div[role="article"], div.Nv2PK')
            for card in cards[:2]:
                site_el = card.query_selector('a[data-value="Website"], a[aria-label*="website" i], a.lcr4fd')
                if site_el:
                    href = site_el.get_attribute("href") or ""
                    if href and not href.startswith("/aclk") and "googleadservices" not in href:
                        return clean_official_website(href)
                else:
                    try:
                        card.click(timeout=800)
                        self.page.wait_for_timeout(800)
                        authority = self.page.query_selector('a[data-item-id="authority"]')
                        if authority:
                            href = authority.get_attribute("href") or ""
                            if href and not href.startswith("/aclk"):
                                return clean_official_website(href)
                    except Exception:
                        pass
        except Exception:
            pass

        return None

    def resolve_via_web_search(self, practice_name: str, location: str = "") -> Optional[str]:
        """
        Fast web fallback query.
        """
        query = f'"{practice_name}" {location} official website'.strip()
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        try:
            r = requests.get(search_url, headers=self.headers, timeout=6)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select("a.result__url"):
                    href = a.get("href", "")
                    if "uddg=" in href:
                        clean = unquote(href.split("uddg=")[1].split("&")[0])
                        if is_valid_practice_domain(clean):
                            return clean_official_website(clean)
        except Exception:
            pass

        return None

    def resolve(self, practice_name: str, location: str = "") -> Optional[str]:
        """
        Resolves domain using best available engine.
        """
        site = self.resolve_via_google_maps(practice_name, location)
        if site and is_valid_practice_domain(site):
            return site

        site = self.resolve_via_web_search(practice_name, location)
        if site and is_valid_practice_domain(site):
            return site

        return None
