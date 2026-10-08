import os
import sys
import csv
import warnings
from datetime import datetime
from typing import List, Dict

# Suppress urllib3 warnings for clean terminal output
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from valentin import TOP_US_METROS, US_STATES
from geo_coverage import US_STATES as ALL_US_STATES, CANADA_PROVINCES, TOP_US_CANADA_METROS, HEALTHCARE_SECTORS
from master_manager import (
    load_master_records,
    append_to_master,
    get_stats,
    get_master_csv_path,
    normalize_domain,
    clean_official_website
)
from weave_site_scraper import WeaveSiteScraper, WEAVE_HEALTHCARE_VERTICALS
from vertical_finder import VerticalFinder, HEALTHCARE_VERTICALS
from domain_resolver import DomainResolver
from mass_harvester import MassHarvester, MASS_CSV_PATH
from weave_verified_extractor import run_verified_harvester_cli, VERIFIED_MASTER_CSV

console = Console()

def print_banner(stats: Dict[str, any]):
    banner_text = Text()
    banner_text.append("🌐 WEAVE (GETWEAVE.COM) HEALTHCARE PARTNERS & CUSTOMERS HARVESTER 🌐\n", style="bold cyan")
    banner_text.append("Extracts Verified Healthcare Practices & Official Domains Across US + Canada\n", style="italic white")
    banner_text.append("Target Ecosystem: ", style="yellow")
    banner_text.append("Dental, Optometry, Veterinary, Physical Therapy, MedSpas, Podiatry & Mental Health\n", style="bold green")
    banner_text.append(f"📊 Master DB Status: {stats['total_records']} records ({stats['unique_domains']} unique domains indexed)\n", style="bold magenta")
    banner_text.append(f"⚡ Live Auto-Save Active: Records saved instantly to {stats['csv_path']}", style="dim cyan")
    
    console.print(Panel(banner_text, box=box.ROUNDED, border_style="cyan", padding=(1, 2)))

def display_stats_table():
    stats = get_stats()
    records, _, _ = load_master_records()

    table = Table(title="📊 Weave Healthcare Customer Database Overview", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Category / Specialty", style="white", no_wrap=True)
    table.add_column("Total Practices", justify="right", style="green")
    table.add_column("Share %", justify="right", style="magenta")

    total = stats["total_records"]
    if total == 0:
        console.print("[yellow]No records in database yet. Run a scraper mode to start extracting![/]")
        return

    for cat, count in sorted(stats["category_counts"].items(), key=lambda x: -x[1]):
        pct = (count / total) * 100
        table.add_row(cat, str(count), f"{pct:.1f}%")

    table.add_section()
    table.add_row("[bold]TOTAL UNIQUE PRACTICES[/]", f"[bold]{total}[/]", "[bold]100.0%[/]")
    console.print(table)
    console.print(f"\n[green]📂 Master CSV Path:[/] [cyan]{stats['csv_path']}[/]\n")

    if records:
        recent_table = Table(title="🔍 Recent Discovered Practices", box=box.SIMPLE, header_style="bold yellow")
        recent_table.add_column("Practice Name", style="white")
        recent_table.add_column("Clean Domain", style="cyan")
        recent_table.add_column("Category", style="green")
        recent_table.add_column("Location", style="dim")

        for r in records[-10:]:
            recent_table.add_row(
                r.get("Practice / Company Name", "")[:35],
                r.get("Clean Domain", "")[:30],
                r.get("Healthcare Category", "")[:25],
                r.get("Location", "")[:25]
            )
        console.print(recent_table)

def run_weave_official_scraper(headless: bool = True):
    console.print("\n[bold yellow]🚀 Launching Official Weave Customer Intelligence Extractor...[/]")
    _, existing_domains, existing_names = load_master_records()
    
    scraper = WeaveSiteScraper(
        headless=headless,
        existing_domains=existing_domains,
        existing_names=existing_names
    )

    new_records_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Extracting Weave Customers...", total=None)

        def handle_progress(event):
            nonlocal new_records_count
            etype = event.get("type")
            if etype == "log":
                progress.console.print(f"  [dim]•[/] {event.get('message')}")
            elif etype == "resolving":
                curr = event.get("current", 0)
                tot = event.get("total", 0)
                pname = event.get("practice", "")
                progress.update(task, description=f"[cyan]Resolving domain ({curr}/{tot}):[/] [white]{pname[:30]}[/]")
            elif etype == "record":
                rec = event.get("data", {})
                append_to_master(rec)
                new_records_count += 1
                dom = normalize_domain(rec.get("official_website", ""))
                progress.console.print(
                    f"  [bold green]✅ Added:[/] [bold white]{rec.get('practice_name', '')[:35]}[/] -> [cyan]{dom}[/] [dim]({rec.get('category', '')})[/]"
                )

        scraper.scrape_all_weave_sources(progress_callback=handle_progress)

    console.print(f"\n[bold green]✨ Weave Official Scraper Finished![/] Added [bold yellow]{new_records_count}[/] new verified healthcare customer domains.")

def run_us_canada_mass_harvester():
    console.print("\n[bold yellow]🌎 US + CANADA MASS HEALTHCARE PRACTICE HARVESTER (40K ECOSYSTEM)[/]")
    console.print("[dim]Select target geography to harvest:[/dim]\n")
    console.print("  [bold cyan][1][/] Top 100 US & Canadian Metro Hubs (Fastest & Highest Yield)")
    console.print("  [bold cyan][2][/] All 50 US States (Complete Nationwide US Sweep)")
    console.print("  [bold cyan][3][/] All 10 Canadian Provinces (Complete Canada Sweep)")
    console.print("  [bold cyan][4][/] Combined Full North America (All 50 US States + 10 Canadian Provinces)")
    console.print("  [bold cyan][5][/] Custom State/Province (e.g. California, Texas, Ontario, British Columbia)\n")

    geo_choice = Prompt.ask("[bold green]Select Geography (1-5)[/]", default="1").strip()
    
    locations_list = []
    country = "US"

    if geo_choice == "1":
        locations_list = [(m, "US" if ", " in m and m.split(", ")[1] not in ["ON","QC","BC","AB","MB","SK","NS","NB","NL","PE"] else "Canada") for m in TOP_US_CANADA_METROS]
    elif geo_choice == "2":
        locations_list = [(f"{s}, USA", "US") for s in ALL_US_STATES]
    elif geo_choice == "3":
        locations_list = [(f"{p}, Canada", "Canada") for p in CANADA_PROVINCES]
    elif geo_choice == "4":
        locations_list = [(f"{s}, USA", "US") for s in ALL_US_STATES] + [(f"{p}, Canada", "Canada") for p in CANADA_PROVINCES]
    elif geo_choice == "5":
        cust = Prompt.ask("[bold green]Enter State or Province Name (e.g. Ontario or Texas)[/]", default="Texas").strip()
        locations_list = [(cust, "Canada" if any(p.lower() in cust.lower() for p in CANADA_PROVINCES) else "US")]
    else:
        locations_list = [(m, "US") for m in TOP_US_METROS[:20]]

    # Select Sector
    console.print("\n[bold yellow]👉 Select Healthcare Sector to Harvest:[/]")
    sectors_keys = list(HEALTHCARE_SECTORS.keys())
    for idx, s in enumerate(sectors_keys, start=1):
        console.print(f"  [bold cyan][{idx}][/] {s}")
    console.print(f"  [bold green][{len(sectors_keys)+1}][/] [bold]All {len(sectors_keys)} Sectors (Complete Spectrum)[/]")

    sec_choice = Prompt.ask(f"[bold green]Select Sector (1-{len(sectors_keys)+1})[/]", default=str(len(sectors_keys)+1)).strip()
    
    selected_sectors = {}
    if sec_choice == str(len(sectors_keys)+1):
        selected_sectors = HEALTHCARE_SECTORS
    elif sec_choice.isdigit() and 1 <= int(sec_choice) <= len(sectors_keys):
        k = sectors_keys[int(sec_choice)-1]
        selected_sectors = {k: HEALTHCARE_SECTORS[k]}
    else:
        selected_sectors = HEALTHCARE_SECTORS

    limit_per_target = IntPrompt.ask("[bold green]Practices per sector/location query[/]", default=25)
    verify_live = Confirm.ask("[bold green]Perform live Weave signature verification on each website?[/]", default=True)

    console.print(f"\n[bold yellow]🚀 Launching Mass Harvester across {len(selected_sectors)} sectors and {len(locations_list)} regions...[/]")

    harvester = MassHarvester(headless=True)
    total_added = 0
    verified_added = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Harvesting Practices...", total=len(selected_sectors) * len(locations_list))

        for sec_name, keywords in selected_sectors.items():
            for loc, c_code in locations_list:
                progress.update(task, description=f"[cyan]Scanning:[/] [white]{sec_name[:20]}[/] in [yellow]{loc[:25]}[/]")

                def handle_record(event):
                    nonlocal total_added, verified_added
                    if event.get("type") == "record":
                        r = event["data"]
                        total_added += 1
                        if r.get("uses_weave"):
                            verified_added += 1
                            progress.console.print(
                                f"  [bold green]🎯 WEAVE VERIFIED:[/] [bold white]{r['practice_name'][:32]}[/] -> [cyan]{r['clean_domain']}[/] [dim]({r['location']})[/]"
                            )
                        else:
                            progress.console.print(
                                f"  [dim]• Discovered:[/] [white]{r['practice_name'][:32]}[/] -> [dim cyan]{r['clean_domain']}[/]"
                            )

                harvester.harvest_sector_location(
                    sector=sec_name,
                    keywords=keywords,
                    location=loc,
                    country=c_code,
                    limit=limit_per_target,
                    verify_on_fly=verify_live,
                    progress_callback=handle_record
                )
                progress.advance(task)

    console.print(f"\n[bold green]✨ Mass Harvest Complete![/]")
    console.print(f"  • Total Domains Discovered: [bold yellow]{total_added}[/]")
    console.print(f"  • Weave Verified Practices: [bold green]{verified_added}[/]")
    console.print(f"  • Master Database File: [bold cyan]{MASS_CSV_PATH}[/]\n")

def main():
    while True:
        stats = get_stats()
        print_banner(stats)

        console.print("\n[bold white]🛠️  MAIN SCRAPER & HARVESTER MENU:[/]")
        console.print("  [bold cyan][1][/] 🎯 [bold yellow]100% Verified Weave Customer Harvester[/] [bold green](Direct Weave Booking & API Extractor)[/]")
        console.print("  [bold cyan][2][/] 🌐 [bold]Official Weave Case Studies & Senja Reviews Scraper[/]")
        console.print("  [bold cyan][3][/] 🌎 🚀 [bold]US + Canada 40,000 Mass Healthcare Harvester[/] [bold dim](Broad Geographies)[/]")
        console.print("  [bold cyan][4][/] 🩺 [bold]Targeted Healthcare Vertical Scraper[/] (Dental, Vision, Vet, PT, MedSpa by City)")
        console.print("  [bold cyan][5][/] 🔍 [bold]Single Practice Domain Resolver[/]")
        console.print("  [bold cyan][6][/] 📊 [bold]View Master CSV Database & Analytics[/]")
        console.print("  [bold red][7][/] 🚪 [bold]Exit[/]\n")

        choice = Prompt.ask("[bold green]Select an option (1-7)[/]", default="1").strip()

        if choice == "1":
            run_verified_harvester_cli()
        elif choice == "2":
            run_weave_official_scraper(headless=True)
        elif choice == "3":
            run_us_canada_mass_harvester()
        elif choice == "4":
            cats = list(HEALTHCARE_VERTICALS.values())
            locs = TOP_US_METROS[:5]
            finder = VerticalFinder(headless=True)
            for c in cats[:2]:
                for l in locs[:2]:
                    finder.scrape_vertical_location(category=c, location=l, limit=10)
        elif choice == "5":
            name = Prompt.ask("\n[bold green]Enter Practice Name[/]").strip()
            loc = Prompt.ask("[bold green]Enter Location[/]", default="").strip()
            resolver = DomainResolver(headless=True)
            res = resolver.resolve(name, loc)
            console.print(f"Result: {res}")
        elif choice == "6":
            display_stats_table()
            Prompt.ask("\nPress Enter to return to menu...")
        elif choice == "7":
            console.print("[bold cyan]Exiting. Have a great day! 👋[/]\n")
            sys.exit(0)
        else:
            console.print("[yellow]Invalid choice, please select 1-7.[/]")

if __name__ == "__main__":
    main()
