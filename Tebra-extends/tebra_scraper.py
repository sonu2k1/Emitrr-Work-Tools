#!/usr/bin/env python3
"""
================================================================================
           🏥 TEBRA CARE PROVIDER & PRACTICE DOMAIN SCRAPER 🏥
================================================================================
An interactive, high-performance scraper for Tebra healthcare provider profiles.
Extracts:
  - URL
  - Name
  - Specialties
  - Practice Name
  - NPI Number
  - Location
  - Phone
  - Practice Domian(According to practice Name column)

Features:
  - Rich interactive terminal UI with live progress, real-time metrics & sliding logs
  - Multi-threaded concurrent scraping with connection pooling
  - Dual-strategy Practice Domain resolution (Clearbit Autocomplete + DDG Search)
  - Persistent domain caching (practice_domains_cache.json) to eliminate duplicate queries
  - Automatic resume support (skips previously scraped URLs)
  - Thread-safe real-time CSV flushing (no data loss on Ctrl+C)
"""

import warnings
warnings.filterwarnings("ignore")

import argparse
import csv
import html
import json
import os
import re
import signal
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote, unquote, urlencode, urlparse

import requests
from bs4 import BeautifulSoup

# Rich UI imports
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

# Initialize Console
console = Console()

# Constants & Configuration
DEFAULT_INPUT_CSV = "Tebra-Browse - Profile URL.csv"
DEFAULT_OUTPUT_CSV = "tebra_providers_scraped.csv"
DOMAIN_CACHE_FILE = "practice_domains_cache.json"

CSV_HEADERS = [
    "URL",
    "Name",
    "Specialties",
    "Practice Name",
    "NPI Number",
    "Location",
    "Phone",
    "Practice Domian(According to practice Name column)",
]

# Domains to ignore during practice domain lookup
IGNORED_DOMAINS = {
    "tebra.com",
    "kareo.com",
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "yelp.com",
    "yellowpages.com",
    "healthgrades.com",
    "vitals.com",
    "webmd.com",
    "zocdoc.com",
    "doximity.com",
    "mapquest.com",
    "google.com",
    "duckduckgo.com",
    "bing.com",
    "yahoo.com",
    "wikipedia.org",
    "bbb.org",
    "sharecare.com",
    "npiprofile.com",
    "nextmd.ai",
    "findatopdoc.com",
    "usnews.com",
    "caredash.com",
    "castleconnolly.com",
    "opencorporates.com",
    "here.com",
    "legal.here.com",
    "npino.com",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tebra.com/care/",
}


# ==============================================================================
# Domain Lookup & Cache
# ==============================================================================
class DomainResolver:
    """Resolves website domain for a given practice name and location."""

    def __init__(self, cache_file: str = DOMAIN_CACHE_FILE):
        self.cache_file = cache_file
        self.lock = threading.Lock()
        self.search_lock = threading.Lock()
        self.last_search_time = 0.0
        self.cache: Dict[str, str] = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def _load_cache(self) -> Dict[str, str]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def extract_clean_domain(self, url_str: str) -> Optional[str]:
        if not url_str:
            return None
        try:
            clean = url_str.strip()
            if not clean.startswith(("http://", "https://")):
                clean = "https://" + clean
            parsed = urlparse(clean)
            host = parsed.netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            if ":" in host:
                host = host.split(":")[0]

            for ign in IGNORED_DOMAINS:
                if host == ign or host.endswith("." + ign):
                    return None

            if "." in host and not host.endswith(".") and len(host) >= 4:
                return host
            return None
        except Exception:
            return None

    def resolve(
        self,
        practice_name: str,
        location: str = "",
        city: str = "",
        state: str = "",
        session: Optional[requests.Session] = None,
    ) -> str:
        if not practice_name or practice_name.strip() in ("", "N/A", "None", "-"):
            return ""

        clean_pname = html.unescape(practice_name).strip()
        cache_key = clean_pname.lower()

        with self.lock:
            if cache_key in self.cache and self.cache[cache_key]:
                return self.cache[cache_key]

        # Normalize practice name (strip legal suffixes for clean search)
        search_name = re.sub(
            r"\b(LLC|PLLC|Inc|Corp|PC|PA|MD|DO|Ltd)\b\.?", "", clean_pname, flags=re.I
        ).strip()
        search_name = re.sub(r"[,.-]+$", "", search_name).strip()

        # Build location context
        loc_str = ""
        if city and state:
            loc_str = f"{city} {state}".strip()
        elif location:
            parts = [p.strip() for p in location.split(",") if p.strip()]
            if len(parts) >= 2:
                loc_str = f"{parts[1]} {parts[2] if len(parts) > 2 else ''}".strip()

        found_domain = ""
        sess = self.session

        # Strategy 1: Clearbit Autocomplete API (instant)
        try:
            cb_url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={quote(search_name)}"
            res = sess.get(cb_url, timeout=3)
            if res.status_code == 200:
                items = res.json()
                for item in items:
                    dom = self.extract_clean_domain(item.get("domain", ""))
                    if dom:
                        found_domain = dom
                        break
        except Exception:
            pass

        # Strategy 2: High-accuracy Yahoo Search (No rate-limits / 202 blocks)
        if not found_domain:
            with self.search_lock:
                now = time.time()
                diff = now - self.last_search_time
                if diff < 0.25:
                    time.sleep(0.25 - diff)
                self.last_search_time = time.time()

                try:
                    query = f"{search_name} {loc_str} website".strip()
                    y_url = f"https://search.yahoo.com/search?p={quote(query)}"
                    res = sess.get(y_url, timeout=5)
                    if res.status_code == 200:
                        for match in re.finditer(r"/RU=(http[^/]+?)/RK=", res.text):
                            raw = unquote(match.group(1))
                            dom = self.extract_clean_domain(raw)
                            if dom:
                                found_domain = dom
                                break
                except Exception:
                    pass

        # Strategy 3: DuckDuckGo Lite search (fallback)
        if not found_domain:
            with self.search_lock:
                try:
                    query = f"{search_name} {loc_str} website".strip()
                    ddg_url = "https://lite.duckduckgo.com/lite/"
                    res = sess.post(
                        ddg_url,
                        data={"q": query},
                        headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                        timeout=5,
                    )
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "html.parser")
                        for a in soup.select("a.result-link"):
                            href = a.get("href", "")
                            dom = self.extract_clean_domain(href)
                            if dom:
                                found_domain = dom
                                break
                except Exception:
                    pass

        # Cache result if found or keep track
        with self.lock:
            if found_domain:
                self.cache[cache_key] = found_domain
                self._save_cache()

        return found_domain

    def flush(self):
        with self.lock:
            self._save_cache()


# ==============================================================================
# Provider Profile Parser
# ==============================================================================
def parse_provider_page(html_text: str, profile_url: str) -> Dict[str, str]:
    """Extracts all provider details from Tebra profile HTML."""
    soup = BeautifulSoup(html_text, "html.parser")
    json_ld_data: Dict[str, Any] = {}

    # 1. Parse JSON-LD metadata
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        raw_text = script.string.strip()
        # Repair malformed JSON produced by Tebra (unescaped newlines & extra trailing brace)
        repaired = re.sub(r"\}\s*\}\s*$", "}", raw_text)
        try:
            parsed = json.loads(repaired, strict=False)
            if isinstance(parsed, dict):
                types = parsed.get("@type", [])
                if isinstance(types, str):
                    types = [types]
                if "Person" in types or "MedicalBusiness" in types or "name" in parsed:
                    json_ld_data = parsed
                    break
        except Exception:
            pass

    # Name
    name = json_ld_data.get("name", "")
    if not name:
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)
    name = html.unescape(name).strip()

    # Specialties
    job_title = json_ld_data.get("jobTitle", "")
    types = json_ld_data.get("@type", [])
    if isinstance(types, str):
        types = [types]
    spec_types = [t for t in types if t not in ["Person", "MedicalBusiness", "Physician", "Thing"]]
    specialties = job_title or (", ".join(spec_types) if spec_types else "")
    if not specialties:
        # Fallback to meta description
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and "trusted " in meta_desc.get("content", ""):
            match = re.search(r"trusted\s+([^,]+)", meta_desc["content"])
            if match:
                specialties = match.group(1).strip()
    specialties = html.unescape(specialties).strip()

    # Practice Name & Location
    practice_name = ""
    location = ""
    city = ""
    state = ""
    wf = json_ld_data.get("worksFor", {})
    if isinstance(wf, dict):
        practice_name = wf.get("name", "")
        addr = wf.get("address", {})
        if isinstance(addr, dict):
            city = addr.get("addressLocality", "")
            state = addr.get("addressRegion", "")
            parts = [
                addr.get("streetAddress", ""),
                city,
                state,
                addr.get("postalCode", ""),
            ]
            location = ", ".join([p.strip() for p in parts if p and p.strip()])

    if not practice_name:
        p_link = soup.find("a", href=re.compile(r"/care/practice/"))
        if p_link:
            practice_name = p_link.get_text(strip=True)
    practice_name = html.unescape(practice_name).strip()
    location = html.unescape(location).strip()

    # NPI Number
    npi = ""
    ident = json_ld_data.get("identifier", "")
    if ident:
        m = re.search(r"\d{10}", ident)
        if m:
            npi = m.group(0)
    if not npi:
        m = re.search(r"-(\d{10})$", profile_url)
        if m:
            npi = m.group(1)

    # Phone Number
    phone = json_ld_data.get("telephone", "")
    if not phone:
        tel_link = soup.find("a", href=re.compile(r"^tel:"))
        if tel_link:
            phone = tel_link.get_text(strip=True)
    phone = phone.strip()

    return {
        "URL": profile_url,
        "Name": name,
        "Specialties": specialties,
        "Practice Name": practice_name,
        "NPI Number": npi,
        "Location": location,
        "Phone": phone,
        "City": city,
        "State": state,
    }


# ==============================================================================
# Terminal UI & Scraper Controller
# ==============================================================================
class TebraInteractiveScraper:
    def __init__(
        self,
        input_file: str = DEFAULT_INPUT_CSV,
        output_file: str = DEFAULT_OUTPUT_CSV,
        threads: int = 8,
        find_domain: bool = True,
        limit: int = 0,
        resume: bool = True,
    ):
        self.input_file = input_file
        self.output_file = output_file
        self.num_threads = max(1, min(threads, 25))
        self.find_domain = find_domain
        self.limit = limit
        self.resume = resume

        self.domain_resolver = DomainResolver() if find_domain else None
        self.file_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        self.stop_requested = threading.Event()

        # Metrics
        self.total_to_process = 0
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.domains_found_count = 0
        self.start_time = 0.0

        # Activity log (sliding window of last 6 items)
        self.recent_activity: deque = deque(maxlen=6)

        # Thread local session
        self.thread_local = threading.local()

    def get_session(self) -> requests.Session:
        if not hasattr(self.thread_local, "session"):
            session = requests.Session()
            session.headers.update(BROWSER_HEADERS)
            # Configure adapter with pool size
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=self.num_threads * 2,
                pool_maxsize=self.num_threads * 2,
                max_retries=2,
            )
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            self.thread_local.session = session
        return self.thread_local.session

    def load_urls(self) -> List[str]:
        """Reads input CSV, filters duplicates, and handles resuming."""
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file '{self.input_file}' not found.")

        raw_urls = []
        with open(self.input_file, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row and row[0].strip().startswith("http"):
                    raw_urls.append(row[0].strip())

        # Deduplicate while preserving original order
        seen = set()
        unique_urls = []
        for u in raw_urls:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)

        # Resume support: check existing output file
        already_scraped = set()
        if self.resume and os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    for row in reader:
                        if row and row[0].strip():
                            already_scraped.add(row[0].strip())
            except Exception:
                pass

        if already_scraped:
            urls_to_scrape = [u for u in unique_urls if u not in already_scraped]
        else:
            urls_to_scrape = unique_urls

        if self.limit > 0:
            urls_to_scrape = urls_to_scrape[: self.limit]

        return urls_to_scrape

    def init_output_file(self):
        """Initializes output CSV with headers if it does not exist."""
        with self.file_lock:
            if not os.path.exists(self.output_file):
                with open(self.output_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_HEADERS)

    def write_result_row(self, row_data: Dict[str, str]):
        """Thread-safe append of a single result row to the CSV."""
        with self.file_lock:
            with open(self.output_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        row_data.get("URL", ""),
                        row_data.get("Name", ""),
                        row_data.get("Specialties", ""),
                        row_data.get("Practice Name", ""),
                        row_data.get("NPI Number", ""),
                        row_data.get("Location", ""),
                        row_data.get("Phone", ""),
                        row_data.get("Practice Domian(According to practice Name column)", ""),
                    ]
                )
                f.flush()

    def process_url(self, url: str) -> Optional[Dict[str, str]]:
        """Worker function that fetches, parses, and enriches a provider profile."""
        if self.stop_requested.is_set():
            return None

        session = self.get_session()
        result = None
        error_msg = ""

        try:
            resp = session.get(url, timeout=12)
            if resp.status_code == 200:
                result = parse_provider_page(resp.text, url)
                domain = ""
                if self.find_domain and self.domain_resolver and result.get("Practice Name"):
                    domain = self.domain_resolver.resolve(
                        practice_name=result["Practice Name"],
                        location=result.get("Location", ""),
                        city=result.get("City", ""),
                        state=result.get("State", ""),
                    )
                result["Practice Domian(According to practice Name column)"] = domain
            else:
                error_msg = f"HTTP {resp.status_code}"
        except Exception as e:
            error_msg = str(e)

        with self.stats_lock:
            self.processed_count += 1
            if result:
                self.success_count += 1
                dom = result.get("Practice Domian(According to practice Name column)", "")
                if dom:
                    self.domains_found_count += 1

                # Record in sliding activity
                now_str = datetime.now().strftime("%H:%M:%S")
                self.recent_activity.append(
                    {
                        "time": now_str,
                        "name": result.get("Name") or "Unknown",
                        "practice": result.get("Practice Name") or "-",
                        "specialty": result.get("Specialties") or "-",
                        "phone": result.get("Phone") or "-",
                        "domain": dom or "-",
                        "status": "[green]✓ Success[/green]",
                    }
                )
                self.write_result_row(result)
            else:
                self.error_count += 1
                now_str = datetime.now().strftime("%H:%M:%S")
                short_url = url.split("/")[-1]
                self.recent_activity.append(
                    {
                        "time": now_str,
                        "name": short_url[:20],
                        "practice": "-",
                        "specialty": "-",
                        "phone": "-",
                        "domain": "-",
                        "status": f"[red]✗ Error ({error_msg[:12]})[/red]",
                    }
                )

        return result

    def render_dashboard(self, progress: Progress, task_id) -> Panel:
        """Generates the live dashboard layout."""
        elapsed = time.time() - self.start_time
        rate = (self.processed_count / elapsed) if elapsed > 0 else 0.0

        # 1. Header Information Panel
        header_text = Text()
        header_text.append("⚡ TEBRA CARE SCRAPER ", style="bold cyan")
        header_text.append(f"| Input: [yellow]{os.path.basename(self.input_file)}[/yellow] ")
        header_text.append(f"| Output: [green]{os.path.basename(self.output_file)}[/green] ")
        header_text.append(f"| Threads: [magenta]{self.num_threads}[/magenta]")

        # 2. Stats Summary Table
        stats_table = Table(box=None, expand=True, padding=(0, 1))
        stats_table.add_column("📊 Total", style="cyan", justify="center")
        stats_table.add_column("⏳ Processed", style="white", justify="center")
        stats_table.add_column("✅ Success", style="green", justify="center")
        stats_table.add_column("❌ Errors", style="red", justify="center")
        stats_table.add_column("🌐 Domains Found", style="bright_blue", justify="center")
        stats_table.add_column("⚡ Speed", style="bright_yellow", justify="center")

        stats_table.add_row(
            str(self.total_to_process),
            f"{self.processed_count} ({((self.processed_count / self.total_to_process) * 100) if self.total_to_process else 0:.1f}%)",
            str(self.success_count),
            str(self.error_count),
            str(self.domains_found_count),
            f"{rate:.1f} req/s",
        )

        # 3. Recent Activity Table
        activity_table = Table(
            title="[bold dim]Recent Scraped Providers[/bold dim]",
            box=None,
            expand=True,
            show_header=True,
            header_style="bold dim cyan",
        )
        activity_table.add_column("Time", width=9, justify="center")
        activity_table.add_column("Provider Name", width=22, no_wrap=True)
        activity_table.add_column("Practice Name", width=25, no_wrap=True)
        activity_table.add_column("Specialty", width=18, no_wrap=True)
        activity_table.add_column("Phone", width=15)
        activity_table.add_column("Practice Domain", width=22, style="bright_cyan", no_wrap=True)
        activity_table.add_column("Status", width=12, justify="center")

        with self.stats_lock:
            for item in list(self.recent_activity):
                activity_table.add_row(
                    item["time"],
                    item["name"][:20],
                    item["practice"][:23],
                    item["specialty"][:16],
                    item["phone"],
                    item["domain"][:20],
                    item["status"],
                )

        # Combine into single Panel
        layout_group = Group(
            header_text,
            stats_table,
            Text(""),
            progress,
            Text(""),
            activity_table,
        )

        return Panel(
            layout_group,
            title="[bold cyan] Tebra Provider & Domain Scraper [/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )

    def run(self):
        """Main execution loop with Rich Live display."""
        # Load targets
        console.print("[dim]Reading input CSV and checking resume status...[/dim]")
        urls = self.load_urls()
        self.total_to_process = len(urls)

        if self.total_to_process == 0:
            console.print(
                "[bold green]✨ All URLs in input file are already scraped! Nothing to do.[/bold green]"
            )
            return

        self.init_output_file()
        self.start_time = time.time()

        # Progress bar setup
        progress = Progress(
            SpinnerColumn("dots", style="cyan"),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None, style="dim white", complete_style="bold green"),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            expand=True,
        )
        task_id = progress.add_task("Scraping Profiles", total=self.total_to_process)

        # Setup Ctrl+C signal handling
        def handle_signal(sig, frame):
            self.stop_requested.set()
            console.print("\n[bold yellow]⚠️  Cancellation requested! Stopping gracefully...[/bold yellow]")

        signal.signal(signal.SIGINT, handle_signal)

        # Live Display loop
        with Live(
            self.render_dashboard(progress, task_id),
            refresh_per_second=4,
            console=console,
            screen=False,
        ) as live:
            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                futures = {executor.submit(self.process_url, u): u for u in urls}

                for future in as_completed(futures):
                    if self.stop_requested.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    progress.update(task_id, completed=self.processed_count)
                    live.update(self.render_dashboard(progress, task_id))

        # Save domain cache on exit
        if self.domain_resolver:
            self.domain_resolver.flush()

        # Display Final Summary
        self.show_completion_summary()

    def show_completion_summary(self):
        """Displays completion metrics and preview table."""
        elapsed = time.time() - self.start_time
        mins, secs = divmod(int(elapsed), 60)

        summary_table = Table(
            title="[bold green]🏁 Scraping Session Finished[/bold green]",
            expand=True,
            show_header=True,
            header_style="bold cyan",
        )
        summary_table.add_column("Metric", style="bold white")
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Total URLs Processed", str(self.processed_count))
        summary_table.add_row("Successful Extractions", f"[green]{self.success_count}[/green]")
        summary_table.add_row("Failed Extractions", f"[red]{self.error_count}[/red]")
        summary_table.add_row("Practice Domains Discovered", f"[bright_blue]{self.domains_found_count}[/bright_blue]")
        summary_table.add_row("Total Execution Time", f"{mins}m {secs}s")
        summary_table.add_row(
            "Average Rate",
            f"{(self.processed_count / elapsed):.2f} req/s" if elapsed > 0 else "0",
        )
        summary_table.add_row("Output CSV File", f"[bold underline yellow]{os.path.abspath(self.output_file)}[/bold underline yellow]")

        console.print("\n")
        console.print(Panel(summary_table, border_style="green"))


# ==============================================================================
# Interactive CLI Prompter
# ==============================================================================
def prompt_interactive_options() -> Dict[str, Any]:
    """Displays banner and prompts user interactively."""
    console.clear()
    banner = """
[bold cyan]████████╗███████╗██████╗ ██████╗  █████╗ [/bold cyan]
[bold cyan]╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔══██╗[/bold cyan]
[bold cyan]   ██║   █████╗  ██████╔╝██████╔╝███████║[/bold cyan]
[bold cyan]   ██║   ██╔══╝  ██╔══██╗██╔══██╗██╔══██║[/bold cyan]
[bold cyan]   ██║   ███████╗██████╔╝██║  ██║██║  ██║[/bold cyan]
[bold dim cyan]Provider Profile & Practice Domain Intelligence Scraper[/bold dim cyan]
    """
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))

    # 1. Input CSV File
    input_file = Prompt.ask(
        "[bold cyan]📁 Input CSV file path[/bold cyan]",
        default=DEFAULT_INPUT_CSV,
    )

    # 2. Output CSV File
    output_file = Prompt.ask(
        "[bold cyan]💾 Output CSV file path[/bold cyan]",
        default=DEFAULT_OUTPUT_CSV,
    )

    # 3. Practice Domain Discovery
    find_domains = Confirm.ask(
        "[bold cyan]🌐 Find Practice Domains (Clearbit + DDG Search)?[/bold cyan]",
        default=True,
    )

    # 4. Worker Threads / Concurrency
    threads = IntPrompt.ask(
        "[bold cyan]⚡ Worker Threads (Concurrency)[/bold cyan] [dim](Recommended: 5 - 15)[/dim]",
        default=8,
    )

    # 5. Limit for Test Run
    limit_choice = Prompt.ask(
        "[bold cyan]🎯 Number of URLs to scrape[/bold cyan] [dim]('all' or enter a number e.g. 50)[/dim]",
        default="all",
    )
    limit = 0 if limit_choice.lower() == "all" else int(limit_choice)

    # 6. Auto-Resume
    resume = True
    if os.path.exists(output_file):
        resume = Confirm.ask(
            f"[bold yellow]🔄 Output file '{output_file}' exists. Resume & skip already scraped?[/bold yellow]",
            default=True,
        )

    console.print("\n[bold green]🚀 Configuration set! Launching scraper...[/bold green]\n")
    time.sleep(1)

    return {
        "input_file": input_file,
        "output_file": output_file,
        "find_domain": find_domains,
        "threads": threads,
        "limit": limit,
        "resume": resume,
    }


# ==============================================================================
# CLI Entrypoint
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Tebra Provider Profile & Practice Domain Scraper"
    )
    parser.add_argument(
        "-i", "--input", default=DEFAULT_INPUT_CSV, help="Path to input CSV containing Profile URLs"
    )
    parser.add_argument(
        "-o", "--output", default=DEFAULT_OUTPUT_CSV, help="Path to output CSV destination"
    )
    parser.add_argument(
        "-t", "--threads", type=int, default=8, help="Number of concurrent worker threads (default: 8)"
    )
    parser.add_argument(
        "-l", "--limit", type=int, default=0, help="Limit number of profiles to scrape (0 = all)"
    )
    parser.add_argument(
        "--no-domain",
        action="store_true",
        help="Disable practice domain resolution for maximum scraping speed",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Overwrite or do not skip already scraped URLs in output CSV",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Non-interactive mode: accept all defaults and start"
    )

    args = parser.parse_args()

    # Determine interactive vs non-interactive mode
    if not args.yes and len(sys.argv) == 1:
        opts = prompt_interactive_options()
    else:
        opts = {
            "input_file": args.input,
            "output_file": args.output,
            "threads": args.threads,
            "find_domain": not args.no_domain,
            "limit": args.limit,
            "resume": not args.no_resume,
        }

    scraper = TebraInteractiveScraper(**opts)
    scraper.run()


if __name__ == "__main__":
    main()
