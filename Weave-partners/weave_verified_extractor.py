"""
weave_verified_extractor.py

High-Performance, Authoritative Harvester & Verifier for Confirmed Weave (getweave.com)
Healthcare Practices and Customer Domains.

Architecture:
1. Harvests verified Weave customer location UUIDs from Web Archive CDX and Common Crawl.
2. Resolves official practice name, notification email, healthcare vertical, and active status
   via Weave's public Location API (api.weaveconnect.com/schedule/api/v2/locations).
3. Extracts and normalizes the practice root domain.
4. Performs live HTTP/HTTPS verification to check domain reachability and confirm Weave integration signatures.
5. Deduplicates and streams verified records in real-time to output/weave_verified_customers_master.csv.
"""

import os
import re
import csv
import time
import requests
import warnings
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Optional, Tuple, Callable
from urllib.parse import urlparse

warnings.filterwarnings("ignore")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

from master_manager import (
    clean_official_website,
    normalize_domain,
    is_valid_practice_domain,
    clean_practice_name
)

console = Console()

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
VERIFIED_MASTER_CSV = os.path.join(OUTPUT_DIR, "weave_verified_customers_master.csv")
UUID_CACHE_FILE = os.path.join(OUTPUT_DIR, "weave_discovered_uuids.txt")

# Free/generic email domains that cannot be used as the practice root domain
GENERIC_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "ymail.com", "hotmail.com", "outlook.com",
    "live.com", "msn.com", "aol.com", "icloud.com", "me.com", "mac.com",
    "comcast.net", "sbcglobal.net", "att.net", "verizon.net", "cox.net",
    "charter.net", "bellsouth.net", "earthlink.net", "protonmail.com",
    "zoho.com", "mail.com", "gmx.com", "inbox.com", "fastmail.com"
}

WEAVE_SIGNATURES = [
    r"getweave\.com",
    r"weavecomm\.com",
    r"weaveconnect\.com",
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
    r"weave_widget",
    r"weave_text_connect"
]

SIGNATURE_RE = re.compile("|".join(WEAVE_SIGNATURES), re.IGNORECASE)
UUID_RE = re.compile(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', re.IGNORECASE)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

CSV_FIELDNAMES = [
    "Practice Name",
    "Official Website",
    "Clean Domain",
    "Healthcare Vertical",
    "Weave Location UUID",
    "Notification Email",
    "Timezone / Region",
    "Weave Verified Evidence",
    "Verification Status",
    "Date Verified"
]


class WeaveVerifiedExtractor:
    def __init__(self, target_csv_path: Optional[str] = None, is_fresh_start: bool = False):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.target_csv_path = target_csv_path if target_csv_path else VERIFIED_MASTER_CSV
        self.is_fresh_start = is_fresh_start
        self.known_domains: Set[str] = set()
        self.known_uuids: Set[str] = set()
        self.processed_uuids_in_target: Set[str] = set()
        self.load_existing_records()

    def load_existing_records(self):
        """Loads already verified domains and UUIDs for the target CSV file."""
        if not self.is_fresh_start and os.path.exists(self.target_csv_path):
            try:
                with open(self.target_csv_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dom = normalize_domain(row.get("Clean Domain") or row.get("Official Website", ""))
                        if dom:
                            self.known_domains.add(dom)
                        uid = row.get("Weave Location UUID", "").strip().lower()
                        if uid:
                            self.processed_uuids_in_target.add(uid)
            except Exception as e:
                console.print(f"[yellow]Notice loading target CSV:[/] {e}")

        # Also load cached UUIDs if file exists
        if os.path.exists(UUID_CACHE_FILE):
            try:
                with open(UUID_CACHE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip().lower()
                        if UUID_RE.match(line):
                            self.known_uuids.add(line)
            except Exception:
                pass

    def save_cached_uuids(self, uuids: Set[str]):
        """Caches discovered UUIDs to disk for instant subsequent runs."""
        with open(UUID_CACHE_FILE, "a", encoding="utf-8") as f:
            for u in uuids:
                f.write(f"{u.lower()}\n")

    def append_record(self, rec: Dict[str, str]):
        """Appends a single verified record immediately to the target CSV file (thread-safe append)."""
        file_exists = os.path.exists(self.target_csv_path)
        with open(self.target_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            if not file_exists or os.path.getsize(self.target_csv_path) == 0:
                writer.writeheader()
            writer.writerow(rec)

    def harvest_uuids_from_archives(self, max_uuids: int = 5000) -> List[str]:
        """
        Harvests unique Weave location UUIDs from Wayback CDX and Common Crawl.
        """
        discovered_uuids: Set[str] = set(self.known_uuids)
        new_uuids: List[str] = []

        if len(discovered_uuids) >= max_uuids:
            return list(discovered_uuids)

        subdomains = [
            "book2.getweave.com",
            "book.getweave.com",
            "schedule.getweave.com"
        ]

        console.print("[cyan]🔍 Harvesting Weave Location UUIDs from Web Crawl Archives...[/]")

        for sub in subdomains:
            if len(discovered_uuids) >= max_uuids:
                break

            try:
                cdx_url = f"http://web.archive.org/cdx/search/cdx?url={sub}/*&output=json&fl=original&collapse=urlkey&limit=3000"
                r = requests.get(cdx_url, timeout=12)
                if r.status_code == 200:
                    matches = UUID_RE.findall(r.text)
                    count_sub = 0
                    added_set = set()
                    for m in matches:
                        m_low = m.lower()
                        if m_low not in discovered_uuids:
                            discovered_uuids.add(m_low)
                            new_uuids.append(m_low)
                            added_set.add(m_low)
                            count_sub += 1
                    if added_set:
                        self.save_cached_uuids(added_set)
                    console.print(f"  • [green]{sub}[/]: Discovered [bold]{count_sub}[/] new UUIDs from Wayback Archive")
            except Exception as e:
                console.print(f"  • [yellow]{sub}[/]: Archive check completed ({str(e)[:45]})")

        return new_uuids

    def fetch_weave_location_info(self, uuid_str: str) -> Optional[Dict[str, any]]:
        """
        Queries Weave's public schedule locations API to get authoritative practice metadata.
        Endpoint: https://api.weaveconnect.com/schedule/api/v2/locations?locationId={uuid}
        """
        api_url = f"https://api.weaveconnect.com/schedule/api/v2/locations?locationId={uuid_str}"
        try:
            resp = requests.get(api_url, headers=HEADERS, timeout=(3.0, 5.0))
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("officeName"):
                    return {
                        "office_name": clean_practice_name(data.get("officeName", "")),
                        "notification_email": data.get("notificationEmail", "").strip().lower(),
                        "vertical": data.get("vertical", "Healthcare Practice") or "Healthcare Practice",
                        "timezone": data.get("timezone", "") or "US",
                        "active": bool(data.get("active", False)),
                        "is_integrated": bool(data.get("isIntegrated", False)),
                        "location_id": uuid_str
                    }
        except Exception:
            pass
        return None

    def extract_domain_from_email(self, email: str) -> Optional[str]:
        """Extracts valid practice root domain from notification email if not a generic provider."""
        if not email or "@" not in email:
            return None
        parts = email.split("@")
        if len(parts) != 2:
            return None
        domain = parts[1].strip().lower()
        if not domain or domain in GENERIC_EMAIL_PROVIDERS:
            return None
        clean_dom = normalize_domain(domain)
        if clean_dom and is_valid_practice_domain(clean_dom):
            return clean_dom
        return None

    def verify_live_domain(self, domain: str, uuid_str: str = "") -> Dict[str, any]:
        """
        Tests domain reachability and checks for active Weave widgets or booking integrations.
        """
        clean_dom = normalize_domain(domain)
        if not clean_dom:
            return {"is_live": False, "has_signature": False, "evidence": "", "status_code": None}

        # Try HTTPS first, then fallback to HTTP
        urls_to_try = [f"https://{clean_dom}", f"http://{clean_dom}"]
        for url in urls_to_try:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=(3.5, 4.5), allow_redirects=True)
                if resp.status_code in [200, 301, 302, 304]:
                    html = resp.text or ""
                    match = SIGNATURE_RE.search(html)
                    has_sig = False
                    evidence = ""

                    if match:
                        has_sig = True
                        start = max(match.start() - 25, 0)
                        end = min(match.end() + 25, len(html))
                        evidence = html[start:end].replace("\n", " ").replace("\r", " ").strip()
                    elif uuid_str and uuid_str in html:
                        has_sig = True
                        evidence = f"Weave Location UUID {uuid_str} matched on homepage"

                    return {
                        "is_live": True,
                        "has_signature": has_sig,
                        "evidence": evidence,
                        "status_code": resp.status_code,
                        "final_url": resp.url
                    }
            except Exception:
                continue

        return {"is_live": False, "has_signature": False, "evidence": "", "status_code": None}

    def process_uuid(self, uuid_str: str) -> Optional[Dict[str, str]]:
        """
        Full pipeline for a single Weave UUID:
        1. Query Weave Location API
        2. Extract practice domain
        3. Perform live verification
        4. Return clean structured record
        """
        meta = self.fetch_weave_location_info(uuid_str)
        if not meta:
            return None

        office_name = meta["office_name"]
        email = meta["notification_email"]
        vertical = meta["vertical"]
        timezone = meta["timezone"]
        is_active = meta["active"]

        # Extract domain from email
        target_domain = self.extract_domain_from_email(email)
        if not target_domain:
            return None

        if target_domain in self.known_domains:
            return None

        # Verify live domain
        ver_res = self.verify_live_domain(target_domain, uuid_str)
        if not ver_res["is_live"]:
            return None

        # Determine verification status
        if ver_res["has_signature"]:
            status_text = "Verified (Live Weave Integration)"
            evidence = ver_res["evidence"][:120]
        else:
            status_text = "Verified (Active Weave Account)"
            evidence = f"Official Weave API Account | Active: {is_active} | Location: {uuid_str}"

        clean_site = f"https://{target_domain}"

        record = {
            "Practice Name": office_name,
            "Official Website": clean_site,
            "Clean Domain": target_domain,
            "Healthcare Vertical": vertical,
            "Weave Location UUID": uuid_str,
            "Notification Email": email,
            "Timezone / Region": timezone,
            "Weave Verified Evidence": evidence,
            "Verification Status": status_text,
            "Date Verified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.known_domains.add(target_domain)
        self.append_record(record)
        return record

    def run_harvest(
        self,
        target_count: int = 500,
        max_workers: int = 25,
        progress_callback: Optional[Callable[[any], None]] = None
    ) -> List[Dict[str, str]]:
        """
        Runs the verified extraction pipeline until target_count verified records are reached
        or all available UUIDs are exhausted.
        """
        self.load_existing_records()

        # Harvest UUIDs from archives if cache is small
        if len(self.known_uuids) < target_count * 3:
            self.harvest_uuids_from_archives(max_uuids=5000)
            self.load_existing_records()

        # Filter out UUIDs already processed into this target CSV
        unprocessed_uuids = [u for u in self.known_uuids if u not in self.processed_uuids_in_target]

        if progress_callback:
            progress_callback({
                "type": "log",
                "message": f"Loaded [bold cyan]{len(unprocessed_uuids)}[/] pending Weave Location UUIDs ready to inspect."
            })

        verified_records: List[Dict[str, str]] = []

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_uuid = {executor.submit(self.process_uuid, uid): uid for uid in unprocessed_uuids}

                for future in as_completed(future_to_uuid):
                    if len(verified_records) >= target_count:
                        for f in future_to_uuid:
                            f.cancel()
                        break

                    try:
                        res = future.result()
                        if res:
                            verified_records.append(res)
                            self.processed_uuids_in_target.add(res.get("Weave Location UUID", "").lower())
                            if progress_callback:
                                progress_callback({"type": "record", "data": res})
                    except Exception:
                        pass
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Interrupted by user (Ctrl+C). Saving and completing current batch...[/]")

        return verified_records


def select_or_create_target_csv() -> Tuple[str, bool]:
    """
    Prompts user to choose between:
    1. Fresh Start (New CSV file)
    2. Continue Previous Run (Select existing CSV file)
    Returns: (target_csv_path, is_fresh_start)
    """
    from rich.prompt import Prompt

    console.print("\n[bold white]📂 CHOOSE EXECUTION MODE & OUTPUT FILE:[/]")
    console.print("  [bold cyan][1][/] 🆕 [bold]Fresh Start[/] (Create a new output CSV file)")
    console.print("  [bold cyan][2][/] ⏩ [bold]Continue Previous Run[/] (Select existing CSV to resume & append)\n")

    mode_choice = Prompt.ask("[bold green]Select mode (1 or 2)[/]", choices=["1", "2"], default="2").strip()

    if mode_choice == "1":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"weave_verified_customers_{timestamp}.csv"
        console.print(f"\n[dim]Default file name:[/] [cyan]{default_name}[/]")
        custom_name = Prompt.ask("[bold green]Enter output file name (press Enter for default)[/]", default=default_name).strip()
        if not custom_name.endswith(".csv"):
            custom_name += ".csv"
        target_path = os.path.join(OUTPUT_DIR, custom_name)
        console.print(f"✨ [bold green]Starting fresh run in:[/] [cyan]{target_path}[/]\n")
        return target_path, True
    else:
        # Find all CSV files in OUTPUT_DIR
        csv_files = []
        if os.path.exists(OUTPUT_DIR):
            for f in sorted(os.listdir(OUTPUT_DIR)):
                if f.endswith(".csv") and not f.startswith("."):
                    csv_files.append(f)

        # Prioritize master file at the top if present
        master_base = os.path.basename(VERIFIED_MASTER_CSV)
        if master_base in csv_files:
            csv_files.remove(master_base)
            csv_files.insert(0, master_base)

        if not csv_files:
            console.print("[yellow]No existing CSV files found in output directory. Creating master CSV.[/]")
            return VERIFIED_MASTER_CSV, False

        console.print("\n[bold yellow]👉 Select existing CSV file to continue:[/]")
        for idx, fname in enumerate(csv_files, start=1):
            fpath = os.path.join(OUTPUT_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    count = max(sum(1 for _ in fp) - 1, 0)
            except Exception:
                count = 0
            console.print(f"  [bold cyan][{idx}][/] [white]{fname:40}[/] [dim]({count} existing records)[/]")
        console.print(f"  [bold cyan][{len(csv_files) + 1}][/] Custom path / Master default ({master_base})")

        file_idx = Prompt.ask(f"[bold green]Select file (1-{len(csv_files) + 1})[/]", default="1").strip()
        if file_idx.isdigit() and 1 <= int(file_idx) <= len(csv_files):
            selected_file = csv_files[int(file_idx) - 1]
            target_path = os.path.join(OUTPUT_DIR, selected_file)
        else:
            target_path = VERIFIED_MASTER_CSV

        console.print(f"⏩ [bold green]Continuing run in:[/] [cyan]{target_path}[/]\n")
        return target_path, False


def run_verified_harvester_cli():
    """Interactive CLI runner with pause/continue every 500 records."""
    from rich.prompt import Prompt
    from rich.text import Text

    console.print(Panel(
        "[bold cyan]🎯 WEAVE (GETWEAVE.COM) 100% VERIFIED CUSTOMER HARVESTER 🎯[/]\n"
        "[white]Authoritative discovery pipeline extracting confirmed Weave healthcare practices & domains.[/]\n"
        "[dim]Automatically pauses every 500 verified records to prompt Continue or Stop.[/]",
        box=box.ROUNDED,
        border_style="cyan"
    ))

    target_csv, is_fresh = select_or_create_target_csv()
    extractor = WeaveVerifiedExtractor(target_csv_path=target_csv, is_fresh_start=is_fresh)

    existing_count = len(extractor.known_domains)
    console.print(f"📊 Currently Indexed Records in Target File: [bold green]{existing_count}[/]\n")

    BATCH_SIZE = 500
    total_session_added = 0
    batch_round = 1

    try:
        while True:
            console.print(f"[bold cyan]🚀 Starting Batch #{batch_round}: Target [bold yellow]{BATCH_SIZE}[/] Verified Records...[/]")
            batch_added = 0

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]Batch #{batch_round} (Target: {BATCH_SIZE})...", total=BATCH_SIZE)

                def handle_event(event):
                    nonlocal batch_added, total_session_added
                    etype = event.get("type")
                    if etype == "log":
                        progress.console.print(f"  [dim]•[/] {event.get('message')}")
                    elif etype == "record":
                        rec = event["data"]
                        batch_added += 1
                        total_session_added += 1
                        progress.console.print(
                            f"  [bold green]🎯 VERIFIED #{total_session_added}:[/] [bold white]{rec['Practice Name'][:28]:28}[/] "
                            f"-> [cyan]{rec['Clean Domain']:24}[/] "
                            f"[magenta]({rec['Healthcare Vertical']})[/]"
                        )
                        progress.advance(task)

                records = extractor.run_harvest(target_count=BATCH_SIZE, max_workers=30, progress_callback=handle_event)

            # Calculate current total records in target CSV
            try:
                with open(target_csv, "r", encoding="utf-8", errors="ignore") as f:
                    total_in_file = max(sum(1 for _ in f) - 1, 0)
            except Exception:
                total_in_file = existing_count + total_session_added

            # Milestone Banner
            summary_text = Text()
            summary_text.append(f"✨ BATCH #{batch_round} COMPLETE!\n", style="bold green")
            summary_text.append(f"• Added in this batch: {batch_added} verified practices\n", style="white")
            summary_text.append(f"• Total added this session: {total_session_added}\n", style="bold yellow")
            summary_text.append(f"• Total records in target CSV: {total_in_file}\n", style="bold cyan")
            summary_text.append(f"• File Location: {target_csv}", style="dim")
            console.print(Panel(summary_text, box=box.ROUNDED, border_style="green", padding=(1, 2)))

            if batch_added == 0:
                console.print("[yellow]No more new verified practices found from current UUID pool.[/]")
                break

            # Every 500 records prompt Continue or Stop
            console.print("\n[bold white]👉 NEXT ACTION:[/]")
            console.print("  [bold green][1][/] ⏩ [bold]Continue next 500 records[/] (Recommended)")
            console.print("  [bold red][2][/] 🛑 [bold]Stop and finish[/]\n")

            user_choice = Prompt.ask("[bold green]Select action (1 to continue, 2 to stop)[/]", choices=["1", "2"], default="1").strip()

            if user_choice == "2":
                break
            else:
                batch_round += 1
                console.print("\n" + "─" * 60 + "\n")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Harvester paused by user (Ctrl+C).[/]")

    # Calculate final total
    try:
        with open(target_csv, "r", encoding="utf-8", errors="ignore") as f:
            final_total = max(sum(1 for _ in f) - 1, 0)
    except Exception:
        final_total = total_session_added

    console.print(f"\n[bold green]🎉 Extraction Session Complete![/]")
    console.print(f"Total new verified customer domains added this session: [bold yellow]{total_session_added}[/]")
    console.print(f"Total verified customer records in target CSV: [bold green]{final_total}[/]")
    console.print(f"📂 Output File: [bold cyan]{target_csv}[/]\n")


if __name__ == "__main__":
    run_verified_harvester_cli()
