"""
check_weave_usage.py (High Performance & Auto-saving)

Checks a list of domains to see if they appear to use Weave (getweave.com)
by fetching each homepage and scanning the raw HTML for known signatures.
"""

import os
import sys
import time
import re
import csv
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# Suppress urllib3 warnings for clean terminal output
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

console = Console()

# Comprehensive signatures that indicate Weave usage
SIGNATURES = [
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
    r"weave_widget",
]

SIGNATURE_RE = re.compile("|".join(SIGNATURES), re.IGNORECASE)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def check_domain(domain: str, timeout=(3.0, 4.0)):
    domain = domain.strip()
    if not domain:
        return None
    url = domain if domain.startswith("http") else f"https://{domain}"
    
    # Try HTTPS first
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        html = resp.text or ""
        match = SIGNATURE_RE.search(html)
        if match:
            start = max(match.start() - 35, 0)
            end = min(match.end() + 35, len(html))
            evidence = html[start:end].replace("\n", " ").replace("\r", " ").strip()
            return {
                "domain": domain,
                "uses_weave": "Yes",
                "evidence": evidence,
                "http_status": resp.status_code,
                "error": "",
            }
        else:
            return {
                "domain": domain,
                "uses_weave": "No",
                "evidence": "",
                "http_status": resp.status_code,
                "error": "",
            }
    except Exception:
        # Fallback to HTTP
        try:
            http_url = f"http://{domain}"
            resp = requests.get(http_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            html = resp.text or ""
            match = SIGNATURE_RE.search(html)
            if match:
                start = max(match.start() - 35, 0)
                end = min(match.end() + 35, len(html))
                evidence = html[start:end].replace("\n", " ").replace("\r", " ").strip()
                return {
                    "domain": domain,
                    "uses_weave": "Yes",
                    "evidence": evidence,
                    "http_status": resp.status_code,
                    "error": "",
                }
            return {
                "domain": domain,
                "uses_weave": "No",
                "evidence": "",
                "http_status": resp.status_code,
                "error": "",
            }
        except Exception as e:
            return {
                "domain": domain,
                "uses_weave": "Unknown",
                "evidence": "",
                "http_status": "",
                "error": str(e)[:150],
            }

def main():
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        default_file = os.path.join(curr_dir, "domains.txt")
        if os.path.exists(default_file):
            input_file = default_file
        else:
            console.print("[bold red]Usage:[/] python check_weave_usage.py domains.txt")
            sys.exit(1)

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        domains = [line.strip() for line in f if line.strip()]

    total = len(domains)
    console.print(Panel(
        f"[bold cyan]🔍 WEAVE USAGE DETECTOR & VERIFIER[/]\n"
        f"[white]Total Target Domains to Inspect:[/] [bold yellow]{total}[/]\n"
        f"[white]Concurrency:[/] [bold green]40 Parallel Workers[/] | [dim]Scanning for Weave widgets & signatures...[/]",
        box=box.ROUNDED,
        border_style="cyan"
    ))

    out_file = "weave_check_results.csv"
    verified_file = "weave_verified_customers.csv"

    # Initialize CSVs with headers
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["domain", "uses_weave", "evidence", "http_status", "error"])
        writer.writeheader()

    with open(verified_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["domain", "uses_weave", "evidence", "http_status", "error"])
        writer.writeheader()

    results = []
    yes_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Scanning {total} domains...", total=total)

        with ThreadPoolExecutor(max_workers=40) as executor:
            future_to_domain = {executor.submit(check_domain, d): d for d in domains}

            for future in as_completed(future_to_domain):
                res = future.result()
                if res:
                    results.append(res)
                    
                    # Append immediately to out_file
                    with open(out_file, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=["domain", "uses_weave", "evidence", "http_status", "error"])
                        writer.writerow(res)

                    if res["uses_weave"] == "Yes":
                        yes_results.append(res)
                        with open(verified_file, "a", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=["domain", "uses_weave", "evidence", "http_status", "error"])
                            writer.writerow(res)
                            
                        progress.console.print(
                            f"  [bold green]🎯 WEAVE DETECTED:[/] [bold white]{res['domain']:35}[/] | [dim]{res['evidence'][:60]}[/]"
                        )
                progress.advance(task)

    yes_count = len(yes_results)
    no_count = sum(1 for r in results if r["uses_weave"] == "No")
    err_count = sum(1 for r in results if r["uses_weave"] == "Unknown")

    summary_table = Table(title="📊 Weave Verification Summary", box=box.ROUNDED, header_style="bold cyan")
    summary_table.add_column("Status", style="white")
    summary_table.add_column("Count", justify="right", style="bold")
    summary_table.add_column("Percentage", justify="right")

    summary_table.add_row("[bold green]✅ Uses Weave (Verified)[/]", f"[bold green]{yes_count}[/]", f"{(yes_count/total)*100:.1f}%")
    summary_table.add_row("[dim]❌ No Direct Signature Found[/]", f"{no_count}", f"{(no_count/total)*100:.1f}%")
    summary_table.add_row("[yellow]⚠️ Unreachable / Error[/]", f"{err_count}", f"{(err_count/total)*100:.1f}%")
    summary_table.add_section()
    summary_table.add_row("[bold]Total Domains Checked[/]", f"[bold]{total}[/]", "100.0%")

    console.print("\n")
    console.print(summary_table)
    console.print(f"\n[green]📂 Full Results CSV:[/] [cyan]{out_file}[/]")
    console.print(f"[green]🎯 Verified Customers CSV:[/] [bold cyan]{verified_file}[/]\n")

if __name__ == "__main__":
    main()