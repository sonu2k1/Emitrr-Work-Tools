#!/usr/bin/env python3
"""
Tebra Care Provider Scraper
============================
Scrapes healthcare provider profile URLs and metadata from Tebra (https://www.tebra.com/care/)
by navigating the 'Browse' popup across 12 specialties and all respective city locations.

Features:
- Clicks Browse on navbar to extract all 12 specialties & their city links.
- Scrapes provider profile links, names, specialties, addresses, distances.
- Handles pagination automatically across all pages per location.
- Fast hybrid mode (uses requests.Session for quick provider fetching) or full Browser mode.
- Streams results directly into CSV in real-time.
"""

import argparse
import csv
import logging
import os
import sys
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TebraScraper")

BASE_URL = "https://www.tebra.com/care/"
DEFAULT_OUTPUT_CSV = "tebra_providers.csv"

# Target specialties from the browse modal
TARGET_SPECIALTIES = [
    "Cardiologists",
    "Chiropractors",
    "Dentists",
    "Dermatologists",
    "Family Physicians",
    "OB-GYNs",
    "Ophthalmologists",
    "Orthopedic Surgeons",
    "Pediatricians",
    "Physical Therapists",
    "Podiatrists",
    "Psychiatrists",
]


class TebraScraper:
    def __init__(
        self,
        output_file: str = DEFAULT_OUTPUT_CSV,
        mode: str = "fast",
        headed: bool = False,
        delay: float = 0.5,
        max_pages: Optional[int] = None,
        selected_specialties: Optional[List[str]] = None,
    ):
        self.output_file = output_file
        self.mode = mode
        self.headed = headed
        self.delay = delay
        self.max_pages = max_pages
        self.selected_specialties = (
            [s.lower() for s in selected_specialties] if selected_specialties else None
        )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.tebra.com/care/",
            }
        )

        self.visited_urls = set()
        self.total_saved = 0

    def init_csv(self):
        """Initializes CSV file with header if it doesn't exist."""
        file_exists = os.path.isfile(self.output_file)
        if not file_exists:
            with open(self.output_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Specialty Category",
                        "Location",
                        "Provider Name",
                        "Provider Specialty",
                        "Distance",
                        "Address",
                        "Profile URL",
                        "Location Page URL",
                    ]
                )
            logger.info(f"Created output CSV file: {self.output_file}")
        else:
            # Read existing URLs to prevent duplicate entries
            with open(self.output_file, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 7:
                        self.visited_urls.add((row[0], row[1], row[6]))  # (specialty, location, profile_url)
            logger.info(
                f"Loaded existing CSV with {len(self.visited_urls)} unique records. Continuing..."
            )

    def save_provider(self, row: List[str]):
        """Appends a provider row to CSV immediately."""
        key = (row[0], row[1], row[6])
        if key in self.visited_urls:
            return False

        self.visited_urls.add(key)
        with open(self.output_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
            f.flush()

        self.total_saved += 1
        return True

    def extract_browse_hierarchy(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Uses Playwright to open Tebra Care, click 'Browse' in Navbar,
        and extracts all specialties and their respective location links.
        """
        logger.info("Opening browser to inspect 'Browse' menu on Tebra Care...")
        hierarchy: Dict[str, List[Dict[str, str]]] = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not self.headed)
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            try:
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2000)

                # Find and click the desktop Browse trigger in the navbar
                browse_trigger = page.locator("#trigger-browse-overlay")
                if browse_trigger.count() == 0 or not browse_trigger.is_visible():
                    browse_trigger = page.locator("a:has-text('Browse')").first

                logger.info("Clicking navbar 'Browse' button...")
                browse_trigger.click()
                page.wait_for_timeout(1000)

                # Wait for overlay
                page.wait_for_selector("#browse-overlay", timeout=10000)

                # Extract specialty tabs and their location links
                raw_data = page.evaluate(
                    """() => {
                    const overlay = document.querySelector('#browse-overlay');
                    if (!overlay) return [];
                    
                    const specialtyEls = Array.from(overlay.querySelectorAll('.overlay-specialty'));
                    const contentEls = Array.from(overlay.querySelectorAll('.browse-overlay-content'));
                    
                    return specialtyEls.map((specEl, idx) => {
                        const specName = specEl.innerText ? specEl.innerText.trim() : '';
                        const contentEl = contentEls[idx];
                        let locations = [];
                        if (contentEl) {
                            locations = Array.from(contentEl.querySelectorAll('a[href]')).map(a => ({
                                city: a.innerText.trim(),
                                url: a.href
                            })).filter(x => x.city && x.url);
                        }
                        return {
                            specialty: specName,
                            locations: locations
                        };
                    });
                }"""
                )

                for item in raw_data:
                    spec_name = item.get("specialty", "").strip()
                    locs = item.get("locations", [])
                    if spec_name:
                        hierarchy[spec_name] = locs
                        logger.info(
                            f"  Found '{spec_name}': {len(locs)} location links"
                        )

            except Exception as e:
                logger.error(f"Error during Browse menu extraction: {e}")
                raise
            finally:
                browser.close()

        return hierarchy

    def scrape_providers_for_location(
        self, specialty_name: str, location_name: str, start_url: str
    ) -> int:
        """
        Scrapes all providers for a single location across all paginated pages.
        """
        current_url = start_url
        page_idx = 1
        count_for_loc = 0

        while current_url:
            if self.max_pages and page_idx > self.max_pages:
                logger.info(
                    f"    Reached max pages limit ({self.max_pages}) for {location_name}."
                )
                break

            try:
                r = self.session.get(current_url, timeout=25)
                if r.status_code != 200:
                    logger.warning(
                        f"    Status {r.status_code} on {current_url}. Skipping."
                    )
                    break

                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("div.col-12.d-flex")

                page_saved = 0
                for card in cards:
                    # Look for the primary profile link
                    link_el = card.select_one("a.article-link") or card.select_one(
                        "a[href*='/care/provider/']"
                    )
                    if not link_el:
                        continue

                    profile_url = link_el.get("href", "").strip()
                    if not profile_url:
                        continue

                    profile_url = urljoin(BASE_URL, profile_url)

                    # Extract doctor details
                    name_el = card.select_one(".provider-name")
                    spec_el = card.select_one(".provider-specialty")
                    dist_el = card.select_one(".location-distance")
                    loc_el = card.select_one(".provider-location")

                    provider_name = name_el.get_text(strip=True) if name_el else ""
                    provider_spec = spec_el.get_text(strip=True) if spec_el else ""
                    distance = dist_el.get_text(" ", strip=True) if dist_el else ""
                    address = loc_el.get_text(" ", strip=True) if loc_el else ""

                    row = [
                        specialty_name,
                        location_name,
                        provider_name,
                        provider_spec,
                        distance,
                        address,
                        profile_url,
                        current_url,
                    ]

                    if self.save_provider(row):
                        page_saved += 1
                        count_for_loc += 1

                logger.info(
                    f"    Page {page_idx}: saved {page_saved} providers (Total in file: {self.total_saved})"
                )

                # Check for next page
                next_btn = soup.find("a", class_="rel-next")
                if next_btn and next_btn.get("href"):
                    current_url = urljoin(BASE_URL, next_btn["href"])
                    page_idx += 1
                    time.sleep(self.delay)
                else:
                    break

            except Exception as e:
                logger.error(f"    Error scraping {current_url}: {e}")
                break

        return count_for_loc

    def scrape_providers_with_playwright(
        self, specialty_name: str, location_name: str, start_url: str, page
    ) -> int:
        """
        Scrapes providers using Playwright live browser interaction.
        """
        current_url = start_url
        page_idx = 1
        count_for_loc = 0

        while current_url:
            if self.max_pages and page_idx > self.max_pages:
                break

            try:
                page.goto(current_url, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(1500)

                # Extract all cards via evaluate
                card_data = page.evaluate(
                    """() => {
                    const cards = Array.from(document.querySelectorAll('div.col-12.d-flex'));
                    return cards.map(c => {
                        const linkEl = c.querySelector('a.article-link') || c.querySelector('a[href*=\"/care/provider/\"]');
                        if (!linkEl) return null;
                        const nameEl = c.querySelector('.provider-name');
                        const specEl = c.querySelector('.provider-specialty');
                        const distEl = c.querySelector('.location-distance');
                        const locEl = c.querySelector('.provider-location');
                        return {
                            href: linkEl.href,
                            name: nameEl ? nameEl.innerText.trim() : '',
                            specialty: specEl ? specEl.innerText.trim() : '',
                            distance: distEl ? distEl.innerText.trim() : '',
                            address: locEl ? locEl.innerText.replace(/\\n+/g, ' ').trim() : ''
                        };
                    }).filter(Boolean);
                }"""
                )

                page_saved = 0
                for item in card_data:
                    row = [
                        specialty_name,
                        location_name,
                        item["name"],
                        item["specialty"],
                        item["distance"],
                        item["address"],
                        item["href"],
                        current_url,
                    ]
                    if self.save_provider(row):
                        page_saved += 1
                        count_for_loc += 1

                logger.info(
                    f"    [Browser] Page {page_idx}: saved {page_saved} providers (Total in file: {self.total_saved})"
                )

                # Check if there is next button
                next_loc = page.locator("a.rel-next")
                if next_loc.count() > 0 and next_loc.first.is_visible():
                    next_href = next_loc.first.get_attribute("href")
                    if next_href:
                        current_url = urljoin(BASE_URL, next_href)
                        page_idx += 1
                        page.wait_for_timeout(int(self.delay * 1000))
                    else:
                        break
                else:
                    break

            except Exception as e:
                logger.error(f"    Error scraping with browser {current_url}: {e}")
                break

        return count_for_loc

    def run(self):
        """Main execution workflow."""
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("Starting Tebra Care Provider Scraper")
        logger.info(f"Output File: {self.output_file}")
        logger.info(f"Scraper Mode: {self.mode}")
        logger.info("=" * 60)

        self.init_csv()

        # Step 1: Extract Browse Menu & Locations
        hierarchy = self.extract_browse_hierarchy()

        if not hierarchy:
            logger.error("Failed to extract any specialties or locations. Exiting.")
            return

        # Filter specialties if specified
        target_keys = []
        for k in hierarchy.keys():
            if self.selected_specialties:
                if any(sel in k.lower() for sel in self.selected_specialties):
                    target_keys.append(k)
            else:
                target_keys.append(k)

        logger.info(f"Targeting {len(target_keys)} specialties:")
        for idx, k in enumerate(target_keys, 1):
            logger.info(f"  {idx}. {k} ({len(hierarchy[k])} locations)")

        # Step 2: Iterate through each specialty and its locations
        if self.mode == "browser":
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=not self.headed)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                for spec in target_keys:
                    locations = hierarchy[spec]
                    logger.info(
                        f"\n>>> Processing Specialty: {spec} ({len(locations)} locations)"
                    )
                    for loc_idx, loc in enumerate(locations, 1):
                        loc_name = loc["city"]
                        loc_url = loc["url"]
                        logger.info(
                            f"  [{loc_idx}/{len(locations)}] Location: {loc_name} -> {loc_url}"
                        )
                        self.scrape_providers_with_playwright(
                            spec, loc_name, loc_url, page
                        )
                browser.close()
        else:
            # Fast mode (requests.Session)
            for spec in target_keys:
                locations = hierarchy[spec]
                logger.info(
                    f"\n>>> Processing Specialty: {spec} ({len(locations)} locations)"
                )
                for loc_idx, loc in enumerate(locations, 1):
                    loc_name = loc["city"]
                    loc_url = loc["url"]
                    logger.info(
                        f"  [{loc_idx}/{len(locations)}] Location: {loc_name} -> {loc_url}"
                    )
                    self.scrape_providers_for_location(spec, loc_name, loc_url)

        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info("Scraping Completed Successfully!")
        logger.info(f"Total New Providers Saved: {self.total_saved}")
        logger.info(f"Total Unique Providers Recorded: {len(self.visited_urls)}")
        logger.info(f"Output File: {os.path.abspath(self.output_file)}")
        logger.info(f"Total Duration: {elapsed:.2f} seconds")
        logger.info("=" * 60)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape provider profile URLs from Tebra Care (tebra.com/care/)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT_CSV,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT_CSV})",
    )
    parser.add_argument(
        "--specialty",
        "-s",
        nargs="+",
        help="Specific specialty or specialties to scrape (e.g. 'Family Physicians' 'Dentists'). Default: all 12 specialties",
    )
    parser.add_argument(
        "--max-pages",
        "-m",
        type=int,
        default=None,
        help="Max pages to scrape per location (default: all pages)",
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "browser"],
        default="fast",
        help="'fast' (recommended, uses requests Session for rapid extraction) or 'browser' (full Playwright interaction)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in visible mode (default: headless)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Polite delay between requests in seconds (default: 0.5s)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    scraper = TebraScraper(
        output_file=args.output,
        mode=args.mode,
        headed=args.headed,
        delay=args.delay,
        max_pages=args.max_pages,
        selected_specialties=args.specialty,
    )
    scraper.run()
