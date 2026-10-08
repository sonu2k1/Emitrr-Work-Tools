#!/usr/bin/env python3
"""
WebPT Practice Scraper CLI
Scans WebPT sites (https://sites.webpt.com/{id}/request-an-appointment)
Extracts Practice Names and their website Domains.
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys
import json
import time
import argparse
import html as html_lib
import re
import urllib.parse
from typing import Optional, Dict, Any, Set, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich import print as rprint

console = Console()

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Placeholder terms in template sites to ignore
DEFAULT_PLACEHOLDERS = {
    "get physical therapy",
    "choose us",
    "pt",
    "physical therapy",
    "us",
    "physical therapy?",
    "choose physical therapy",
    "see a physical therapist",
    "get pt",
    "request an appointment",
}

# Domains to ignore when resolving practice website
IGNORED_DOMAINS = {
    "webpt.com", "strivehub.com", "amazonaws.com", "google.com", "facebook.com",
    "instagram.com", "twitter.com", "x.com", "youtube.com", "linkedin.com",
    "yelp.com", "yellowpages.com", "whitepages.com", "mapquest.com", "chamberofcommerce.com",
    "us-info.com", "beaminghealth.com", "nationalclinics.com", "ourhealthnetwork.com",
    "fresha.com", "healthgrades.com", "zocdoc.com", "vitals.com", "doximity.com",
    "webmd.com", "bbb.org", "wikipedia.org", "indeed.com", "glassdoor.com",
    "w3.org", "schema.org", "sentry.io", "wixpress.com"
}


def print_banner():
    banner = (
        "[bold cyan]╔══════════════════════════════════════════════════════════════════╗[/bold cyan]\n"
        "[bold cyan]║[/bold cyan]            [bold green]🏥 WebPT Practice & Domain Scraper CLI 🏥[/bold green]             [bold cyan]║[/bold cyan]\n"
        "[bold cyan]║[/bold cyan]   [dim]Extracts Practice Names & Domains from sites.webpt.com[/dim]         [bold cyan]║[/bold cyan]\n"
        "[bold cyan]╚══════════════════════════════════════════════════════════════════╝[/bold cyan]"
    )
    console.print(banner)


def extract_clean_domain(url_or_domain: str) -> str:
    """Extracts clean hostname without www, path, or query params."""
    if not url_or_domain:
        return ""
    url_or_domain = str(url_or_domain).strip().lower()
    if url_or_domain.startswith(("http://", "https://")):
        try:
            parsed = urllib.parse.urlparse(url_or_domain)
            host = parsed.netloc or parsed.path
        except Exception:
            host = url_or_domain
    else:
        host = url_or_domain.split("/")[0]

    host = host.split(":")[0].strip()
    if host.startswith("www."):
        host = host[4:]
    return host


class WebPTScraper:
    def __init__(
        self,
        start_id: int = 20000,
        end_id: int = 30000,
        workers: int = 40,
        timeout: int = 8,
        output_csv: str = "webpt_practices.csv",
        output_xlsx: str = "webpt_practices.xlsx",
        checkpoint_file: str = "progress.json",
        resume: bool = True,
    ):
        self.start_id = start_id
        self.end_id = end_id
        self.workers = workers
        self.timeout = timeout
        self.output_csv = output_csv
        self.output_xlsx = output_xlsx
        self.checkpoint_file = checkpoint_file
        self.resume = resume

        self.lock = threading.Lock()
        self.session = self._create_session()
        self.discovered_practices: List[Dict[str, Any]] = []
        self.scanned_ids: Set[int] = set()
        self.found_ids: Set[int] = set()

        if self.resume:
            self._load_checkpoint_and_existing_data()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            pool_connections=self.workers * 2,
            pool_maxsize=self.workers * 2,
            max_retries=retries,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        return session

    def _load_checkpoint_and_existing_data(self):
        """Loads previous checkpoint and CSV if available to resume seamlessly."""
        # 1. Load CSV data if exists
        if os.path.exists(self.output_csv):
            try:
                df = pd.read_csv(self.output_csv)
                if not df.empty and "site_id" in df.columns:
                    for _, row in df.iterrows():
                        sid = int(row["site_id"])
                        self.found_ids.add(sid)
                        self.scanned_ids.add(sid)
                        self.discovered_practices.append(row.to_dict())
                console.print(
                    f"[green]✓ Loaded {len(self.discovered_practices)} existing practices from {self.output_csv}[/green]"
                )
            except Exception as e:
                console.print(f"[yellow]Warning loading {self.output_csv}: {e}[/yellow]")

        # 2. Load scanned IDs checkpoint
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    data = json.load(f)
                    saved_scanned = data.get("scanned_ids", [])
                    self.scanned_ids.update(saved_scanned)
                console.print(
                    f"[cyan]✓ Resuming with {len(self.scanned_ids)} previously scanned IDs[/cyan]"
                )
            except Exception as e:
                console.print(f"[yellow]Warning loading {self.checkpoint_file}: {e}[/yellow]")

    def _save_checkpoint(self):
        """Thread-safe checkpoint saving."""
        with self.lock:
            try:
                with open(self.checkpoint_file, "w") as f:
                    json.dump(
                        {
                            "start_id": self.start_id,
                            "end_id": self.end_id,
                            "total_scanned": len(self.scanned_ids),
                            "total_found": len(self.found_ids),
                            "scanned_ids": list(self.scanned_ids),
                        },
                        f,
                    )
            except Exception:
                pass

    def _save_results_to_files(self):
        """Thread-safe export of results to CSV and Excel."""
        with self.lock:
            if not self.discovered_practices:
                return

            try:
                df = pd.DataFrame(self.discovered_practices)
                # Deduplicate by site_id
                df = df.drop_duplicates(subset=["site_id"])
                # Sort by site_id
                df["site_id"] = pd.to_numeric(df["site_id"], errors="coerce")
                df = df.sort_values(by="site_id").reset_index(drop=True)

                # Ensure 'why_headline' is removed if present
                if "why_headline" in df.columns:
                    df = df.drop(columns=["why_headline"])

                # Desired column order
                cols = [
                    "site_id",
                    "practice_name",
                    "domain",
                    "page_title",
                    "footer_name",
                    "custom_domain",
                    "created_at",
                    "updated_at",
                    "url",
                ]
                existing_cols = [c for c in cols if c in df.columns]
                extra_cols = [c for c in df.columns if c not in cols]
                df = df[existing_cols + extra_cols]

                # Save CSV
                df.to_csv(self.output_csv, index=False)

                # Save Excel
                try:
                    df.to_excel(self.output_xlsx, index=False, engine="openpyxl")
                except Exception:
                    pass
            except Exception as e:
                console.print(f"[red]Error saving files: {e}[/red]")

    def find_practice_domain(
        self,
        practice_name: str,
        page_title: str = "",
        page_html: str = "",
        custom_domain: str = "",
    ) -> str:
        """Discovers the domain of the practice via page links, custom domain, or search."""
        # 1. Check customDomain
        if custom_domain:
            clean_cd = extract_clean_domain(custom_domain)
            if clean_cd and not any(ign in clean_cd for ign in IGNORED_DOMAINS):
                return clean_cd

        # 2. Check embedded links in WebPT page HTML/JSON
        if page_html:
            try:
                soup = BeautifulSoup(page_html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "")
                    d = extract_clean_domain(href)
                    if d and not any(ign in d for ign in IGNORED_DOMAINS) and "." in d:
                        return d
                
                # Check links inside script JSON
                script = soup.find("script", id="__NEXT_DATA__")
                if script and script.string:
                    raw_urls = re.findall(
                        r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"\'\\]*)?',
                        script.string,
                    )
                    for u in raw_urls:
                        d = extract_clean_domain(u)
                        if d and not any(ign in d for ign in IGNORED_DOMAINS) and "." in d:
                            return d
            except Exception:
                pass

        # 3. Search DuckDuckGo for practice official domain
        try:
            location = ""
            if page_title:
                parts = [p.strip() for p in re.split(r"[|•–—]", page_title) if p.strip()]
                if len(parts) > 1:
                    location = parts[-1]

            query = f"{practice_name} {location} physical therapy".strip()
            ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {"User-Agent": DEFAULT_USER_AGENT}
            resp = self.session.get(ddg_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select("a.result__url, .results_links a, .result__body a"):
                    href = a.get("href", "")
                    if "uddg=" in href:
                        try:
                            href = urllib.parse.parse_qs(
                                urllib.parse.urlparse(href).query
                            ).get("uddg", [""])[0]
                        except Exception:
                            pass
                    d = extract_clean_domain(href)
                    if d and not any(ign in d for ign in IGNORED_DOMAINS) and "." in d:
                        return d
        except Exception:
            pass

        return ""

    def extract_practice_info(self, html_text: str, site_id: int) -> Optional[Dict[str, Any]]:
        """Extracts Practice Name and metadata from WebPT appointment page HTML."""
        if not html_text or ("Request an appointment" not in html_text and "Why" not in html_text):
            return None

        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Parse __NEXT_DATA__ JSON if available
        next_script = soup.find("script", id="__NEXT_DATA__")
        page_blocks = []
        created_at = None
        updated_at = None
        custom_domain = None

        if next_script and next_script.string:
            try:
                next_json = json.loads(next_script.string)
                page_obj = (
                    next_json.get("props", {})
                    .get("pageProps", {})
                    .get("page", {})
                )
                page_data = page_obj.get("pageData", {})
                page_blocks = page_data.get("blocks", [])
                created_at = page_obj.get("createdAt")
                updated_at = page_obj.get("updatedAt")
                custom_domain = page_obj.get("customDomain")
            except Exception:
                pass

        # 2. Extract from "Why <Practice Name>?" heading in HTML
        why_practice = None
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong", "p"]):
            text = tag.get_text(" ", strip=True)
            m = re.search(r"Why\s+(.+?)\s*\?", text, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                cand = re.sub(r"\s+", " ", cand)
                cand = html_lib.unescape(cand)
                if cand.lower() not in DEFAULT_PLACEHOLDERS and len(cand) > 2:
                    why_practice = cand
                    break

        # 3. If not found in rendered HTML, check raw blocks in NEXT_DATA
        if not why_practice:
            for b in page_blocks:
                content_html = b.get("data", {}).get("content", {}).get("data", "")
                if content_html:
                    m = re.search(r"Why\s+([^?<\n]+)\?", content_html, re.IGNORECASE)
                    if m:
                        cand = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                        cand = re.sub(r"\s+", " ", cand)
                        cand = html_lib.unescape(cand)
                        if cand.lower() not in DEFAULT_PLACEHOLDERS and len(cand) > 2:
                            why_practice = cand
                            break

        # 4. Extract Footer block
        footer_practice = None
        for b in page_blocks:
            if b.get("block") == "Footer" or b.get("displayName") == "Footer":
                ft = b.get("data", {}).get("text", {}).get("data", "").strip()
                ft = html_lib.unescape(ft)
                if ft and "Copyright" not in ft and "All Rights Reserved" not in ft:
                    footer_practice = ft
                    break

        # 5. Extract Page Title
        page_title = soup.title.string.strip() if soup.title else ""
        page_title = html_lib.unescape(page_title)
        title_practice = None
        if page_title:
            parts = [p.strip() for p in re.split(r"[|•–—]", page_title) if p.strip()]
            for p in parts:
                if p.lower() not in ["request an appointment", "webpt", "home", "welcome", "about us"]:
                    title_practice = p
                    break

        # 6. Determine final Practice Name
        # Priority: Why headline (marked in screenshot) > Footer > Title
        practice_name = why_practice or footer_practice or title_practice

        # If page has no custom practice name and only default placeholder heading, skip it
        if not practice_name or (
            practice_name.lower() in DEFAULT_PLACEHOLDERS and not why_practice
        ):
            return None

        # Clean practice name
        practice_name = practice_name.strip(" .,:-_")

        # 7. Find Domain
        domain = self.find_practice_domain(
            practice_name=practice_name,
            page_title=page_title,
            page_html=html_text,
            custom_domain=custom_domain,
        )

        url = f"https://sites.webpt.com/{site_id}/request-an-appointment"

        return {
            "site_id": site_id,
            "practice_name": practice_name,
            "domain": domain or "",
            "page_title": page_title or "",
            "footer_name": footer_practice or "",
            "custom_domain": custom_domain or "",
            "created_at": created_at or "",
            "updated_at": updated_at or "",
            "url": url,
        }

    def check_site(self, site_id: int) -> Optional[Dict[str, Any]]:
        """Fetches and checks a single site ID."""
        url = f"https://sites.webpt.com/{site_id}/request-an-appointment"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None

            return self.extract_practice_info(resp.text, site_id)
        except Exception:
            return None

    def run(self):
        """Runs the multi-threaded scraper across the specified ID range."""
        all_ids = [
            sid for sid in range(self.start_id, self.end_id + 1)
            if sid not in self.scanned_ids
        ]

        total_to_scan = len(all_ids)

        console.print(Panel.fit(
            f"[bold green]Range:[/bold green] {self.start_id} ➔ {self.end_id} (Total: {self.end_id - self.start_id + 1:,})\n"
            f"[bold cyan]Already Scanned:[/bold cyan] {len(self.scanned_ids):,}\n"
            f"[bold yellow]Remaining to Scan:[/bold yellow] {total_to_scan:,}\n"
            f"[bold blue]Threads/Workers:[/bold blue] {self.workers}\n"
            f"[bold magenta]Output:[/bold magenta] {self.output_csv} / {self.output_xlsx}",
            title="[bold white]Scraper Configuration[/bold white]",
            border_style="cyan",
        ))

        if total_to_scan == 0:
            console.print("[bold green]All IDs in this range have already been scanned![/bold green]")
            self._print_summary_table()
            return

        console.print("[bold green]🚀 Starting Scraper... Press Ctrl+C at any time to pause and save.[/bold green]\n")

        processed_count = 0

        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("• [bold green]{task.fields[found]} Found[/bold green]"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                "Scraping WebPT sites",
                total=total_to_scan,
                found=len(self.found_ids),
            )

            try:
                with ThreadPoolExecutor(max_workers=self.workers) as executor:
                    future_to_id = {
                        executor.submit(self.check_site, sid): sid for sid in all_ids
                    }

                    for future in as_completed(future_to_id):
                        sid = future_to_id[future]
                        processed_count += 1
                        self.scanned_ids.add(sid)

                        try:
                            result = future.result()
                            if result:
                                with self.lock:
                                    if sid not in self.found_ids:
                                        self.found_ids.add(sid)
                                        self.discovered_practices.append(result)
                                        
                                        # Print found item in real time with domain
                                        domain_display = f" | [bold cyan]{result['domain']}[/bold cyan]" if result['domain'] else ""
                                        console.log(
                                            f"[bold green]✓ Found #{sid}:[/bold green] "
                                            f"[bold white]{result['practice_name']}[/bold white]"
                                            f"{domain_display} "
                                            f"[dim]({result['url']})[/dim]"
                                        )
                        except Exception:
                            pass

                        progress.update(
                            task_id,
                            advance=1,
                            found=len(self.found_ids),
                        )

                        # Periodically save results and checkpoint
                        if processed_count % 50 == 0:
                            self._save_checkpoint()
                            self._save_results_to_files()

            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️ Scrape paused by user. Saving current progress...[/yellow]")
            finally:
                self._save_checkpoint()
                self._save_results_to_files()

        console.print(f"\n[bold green]✓ Completed! Total practices found: {len(self.discovered_practices)}[/bold green]")
        self._print_summary_table()

    def _print_summary_table(self):
        """Displays a clean summary table of discovered practices."""
        if not self.discovered_practices:
            console.print("[dim]No practices found.[/dim]")
            return

        table = Table(title="Top Discovered WebPT Practices", border_style="green", show_lines=True)
        table.add_column("Site ID", style="cyan", justify="center")
        table.add_column("Practice Name", style="bold white")
        table.add_column("Domain", style="bold cyan")
        table.add_column("Page Title", style="dim")
        table.add_column("URL", style="blue")

        # Show preview of up to 15 items
        for p in self.discovered_practices[:15]:
            table.add_row(
                str(p.get("site_id", "")),
                str(p.get("practice_name", "")),
                str(p.get("domain", "")),
                str(p.get("page_title", ""))[:40] + ("..." if len(str(p.get("page_title", ""))) > 40 else ""),
                str(p.get("url", "")),
            )

        console.print(table)
        console.print(f"[bold green]📁 Saved {len(self.discovered_practices)} records to:[/bold green]")
        console.print(f"   • CSV:   [bold cyan]{os.path.abspath(self.output_csv)}[/bold cyan]")
        console.print(f"   • Excel: [bold cyan]{os.path.abspath(self.output_xlsx)}[/bold cyan]\n")


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="WebPT Practice Name & Domain Scraper")
    parser.add_argument(
        "--start",
        type=int,
        default=20000,
        help="Start Site ID (default: 20000)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=30000,
        help="End Site ID (default: 30000)",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=40,
        help="Number of concurrent threads (default: 40)",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=8,
        help="HTTP request timeout in seconds (default: 8)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="webpt_practices.csv",
        help="Output CSV filename (default: webpt_practices.csv)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume from previous checkpoint, scan from scratch",
    )

    args = parser.parse_args()

    xlsx_output = args.output.rsplit(".", 1)[0] + ".xlsx"

    scraper = WebPTScraper(
        start_id=args.start,
        end_id=args.end,
        workers=args.workers,
        timeout=args.timeout,
        output_csv=args.output,
        output_xlsx=xlsx_output,
        resume=not args.no_resume,
    )

    scraper.run()


if __name__ == "__main__":
    main()
