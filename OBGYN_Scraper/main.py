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
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from valentin import TOP_US_METROS, US_STATES
from master_manager import load_master_records, append_to_master, clean_official_website, get_master_csv_path
from scraper import OBGYN_CATEGORIES, OBGYNScraper

console = Console()

def get_live_output_filepath() -> str:
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, "live_session_records.csv")

def append_to_live_csv(rec: Dict[str, str]):
    """
    Appends newly discovered record immediately to live session CSV to prevent data loss.
    """
    filepath = get_live_output_filepath()
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Practice / Organization", "Official website", "Category", "Location", "Source"])
        writer.writerow([
            rec.get("practice_name", ""),
            rec.get("official_website", ""),
            rec.get("category", ""),
            rec.get("location", ""),
            rec.get("source", "")
        ])

def print_banner(master_count: int, unique_domains_count: int):
    banner_text = Text()
    banner_text.append("🌸 US OB-GYN & WOMEN'S HEALTH / FQHC SCRAPER 🌸\n", style="bold magenta")
    banner_text.append("Hyper-Targeted US Healthcare Practices & Official Domains Extractor\n", style="italic white")
    banner_text.append("Tailored for: ", style="cyan")
    banner_text.append("Master Data Sheet - Women’s Health _ OB-GYNFQHC.csv\n", style="bold yellow")
    banner_text.append(f"📊 Master Sheet Status: {master_count} records loaded ({unique_domains_count} unique domains indexed for deduplication)\n", style="green")
    banner_text.append("✨ Powered by Valentin.app Localized Coordinates + Google Maps Engine\n", style="dim")
    banner_text.append(f"⚡ Live Auto-Save Active: Records saved instantly to output/live_session_records.csv", style="bold cyan")
    
    console.print(Panel(banner_text, box=box.ROUNDED, border_style="magenta", padding=(1, 2)))

def select_categories() -> List[str]:
    console.print("\n[bold yellow]👉 Step 1: Select OB-GYN / Women's Health Category to Scrape:[/]")
    console.print("[dim]Choose specialty focus to target:[/dim]\n")
    
    for idx, cat_name in OBGYN_CATEGORIES.items():
        console.print(f"  [bold cyan][{idx}][/] {cat_name}")
    console.print(f"  [bold green][8][/] [bold]All 7 Categories (Full Spectrum Women's Health & FQHC)[/]")
    console.print(f"  [bold magenta][M][/] [italic]Custom Multi-select (e.g. '1,2,6' or '1,4')[/]\n")

    choice = Prompt.ask("[bold green]Enter your choice (1-8 or M)[/]", default="8").strip()

    if choice == "8":
        return list(OBGYN_CATEGORIES.values())
    elif choice.isdigit() and int(choice) in OBGYN_CATEGORIES:
        return [OBGYN_CATEGORIES[int(choice)]]
    else:
        cleaned_choice = choice.upper().replace("M", "").strip()
        if not cleaned_choice:
            cleaned_choice = Prompt.ask("[bold green]Enter category numbers separated by commas (e.g. 1,2,6)[/]", default="1,2,6")
        
        selected = []
        for num in cleaned_choice.split(","):
            num = num.strip()
            if num.isdigit() and int(num) in OBGYN_CATEGORIES:
                selected.append(OBGYN_CATEGORIES[int(num)])
        
        if not selected:
            console.print("[yellow]Defaulting to All Categories.[/]")
            return list(OBGYN_CATEGORIES.values())
        return selected

def select_locations() -> List[str]:
    console.print("\n[bold yellow]👉 Step 2: Select Target US Location(s):[/]")
    console.print("  [bold cyan][1][/] Specific City / State (e.g., Dallas TX, Austin TX, Miami FL, New York NY)")
    console.print("  [bold cyan][2][/] Specific US State (e.g., Texas, California, Florida, Ohio, New York)")
    console.print("  [bold cyan][3][/] Top 5 US Metro Hubs (Dallas TX, Houston TX, Austin TX, Miami FL, Atlanta GA)")
    console.print("  [bold cyan][4][/] Top 20 Major US Metro Areas")
    console.print("  [bold cyan][5][/] Top 50 Nationwide US Metros (Bulk Deep Sweep)")
    console.print("  [bold cyan][6][/] Custom Multiple Cities (Comma-separated)\n")

    loc_choice = Prompt.ask("[bold green]Select location mode (1-6)[/]", default="1").strip()

    if loc_choice == "1":
        city = Prompt.ask("[bold green]Enter US City and State (e.g. Dallas, TX)[/]", default="Dallas, TX").strip()
        return [city]
    elif loc_choice == "2":
        state_input = Prompt.ask("[bold green]Enter State Name (e.g. Texas, Ohio, Florida)[/]", default="Texas").strip()
        return [f"{state_input}, USA"]
    elif loc_choice == "3":
        return ["Dallas, TX", "Houston, TX", "Austin, TX", "Miami, FL", "Atlanta, GA"]
    elif loc_choice == "4":
        return TOP_US_METROS[:20]
    elif loc_choice == "5":
        return TOP_US_METROS
    elif loc_choice == "6":
        cities_raw = Prompt.ask("[bold green]Enter US Cities separated by commas[/]", default="Houston TX, Dallas TX, Austin TX, Miami FL")
        cities = [c.strip() for c in cities_raw.split(",") if c.strip()]
        return cities if cities else ["Dallas, TX"]
    else:
        return ["Dallas, TX"]

def select_limit() -> int:
    console.print("\n[bold yellow]👉 Step 3: Target Limit per Category & Location:[/]")
    limit_str = Prompt.ask("[bold green]Maximum new practices per query (e.g., 20, 50, or 'all')[/]", default="30").strip()
    if limit_str.lower() in ["all", "unlimited", "max"]:
        return 5000
    try:
        limit = int(limit_str)
        return max(1, limit)
    except ValueError:
        return 30

def export_results_to_csv(results: List[Dict[str, str]]) -> str:
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"obgyn_scraped_records_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Practice / Organization", "Official website", "Category", "Location", "Source"])
        for r in results:
            writer.writerow([
                r.get("practice_name", ""),
                r.get("official_website", ""),
                r.get("category", ""),
                r.get("location", ""),
                r.get("source", "")
            ])
            
    return filepath

def main():
    console.clear()
    
    # 1. Load Master CSV
    existing_domains, existing_names, master_count = load_master_records()
    print_banner(master_count, len(existing_domains))

    # 2. Interactive Prompts
    categories = select_categories()
    locations = select_locations()
    limit = select_limit()
    
    headless = True

    # 3. Confirmation
    console.print("\n[bold yellow]📋 Scraping Task Summary:[/]")
    console.print(f"  • [bold]Categories ({len(categories)}):[/] {', '.join(categories[:3])}{'...' if len(categories) > 3 else ''}")
    console.print(f"  • [bold]Locations ({len(locations)}):[/] {', '.join(locations[:3])}{'...' if len(locations) > 3 else ''}")
    console.print(f"  • [bold]Target Limit:[/] Up to {limit} records per location")
    console.print(f"  • [bold]Deduplication:[/] Active ({len(existing_domains)} existing domains skipped automatically)")
    console.print(f"  • [bold]Live Auto-Save:[/] Active ([dim]output/live_session_records.csv[/dim])\n")

    if not Confirm.ask("[bold green]🚀 Ready to start scraping?[/]", default=True):
        console.print("[yellow]Scraping aborted by user.[/]")
        return

    # 4. Initialize Scraper
    scraper = OBGYNScraper(
        headless=headless,
        existing_domains=existing_domains,
        existing_names=existing_names
    )

    all_scraped_results: List[Dict[str, str]] = []
    
    total_tasks = len(categories) * len(locations)
    current_task = 0

    console.print("\n" + "="*70)
    console.print("[bold green]⚡ Scraping in progress... Records are auto-saved in real time to output/live_session_records.csv[/]")
    console.print("[bold cyan]💡 Tip: Press Ctrl+C at any time to pause and finalize export into Master Sheet.[/]")
    console.print("="*70 + "\n")

    try:
        for loc in locations:
            for cat in categories:
                current_task += 1
                console.print(f"\n[bold cyan]🔍 [{current_task}/{total_tasks}] Searching for:[/] [bold white]{cat}[/] in [bold yellow]{loc}[/]")

                def progress_listener(event):
                    if isinstance(event, dict):
                        if event.get("type") == "record":
                            rec = event["data"]
                            # Real-time auto save to file
                            append_to_live_csv(rec)
                            console.print(f"  [bold green]✓ NEW:[/] [white]{rec['practice_name']}[/] → [cyan]{rec['official_website']}[/]")
                        elif event.get("type") == "log":
                            console.print(f"  [dim]{event.get('message')}[/]")

                batch = scraper.scrape_category_location(
                    category=cat,
                    location=loc,
                    limit=limit,
                    progress_callback=progress_listener
                )

                all_scraped_results.extend(batch)
                console.print(f"  [green]➔ Batch completed:[/] Found [bold]{len(batch)}[/] new unique verified records for {loc}")

    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Interrupted by user. Preparing captured records for saving...[/]")

    # 5. Review & Summary
    console.print("\n" + "="*70)
    console.print(f"[bold green]🎉 Scraping Phase Finished! Total New Unique Records Found: {len(all_scraped_results)}[/]")
    console.print("="*70 + "\n")

    if not all_scraped_results:
        console.print("[yellow]No new unique records were found in this session (or all matched existing Master records).[/]")
        return

    # Print summary table preview (up to first 15)
    preview_table = Table(title=f"Sample Extracted Records ({min(15, len(all_scraped_results))} of {len(all_scraped_results)})", box=box.ROUNDED)
    preview_table.add_column("#", style="dim", width=4)
    preview_table.add_column("Practice / Organization", style="bold white")
    preview_table.add_column("Official Website", style="cyan")
    preview_table.add_column("Category", style="magenta")
    preview_table.add_column("Location", style="yellow")

    for i, r in enumerate(all_scraped_results[:15], 1):
        preview_table.add_row(
            str(i),
            r["practice_name"],
            r["official_website"],
            r["category"][:20],
            r["location"][:18]
        )
    console.print(preview_table)

    # 6. Export Options
    console.print("\n[bold yellow]💾 Step 4: Export & Master Sheet Options:[/]")
    console.print("  [bold cyan][1][/] [bold green]Append Directly into Master Sheet[/] ([dim]Master Data Sheet - Women’s Health _ OB-GYNFQHC.csv[/dim])")
    console.print("  [bold cyan][2][/] Save to Standalone Timestamped CSV ([dim]output/obgyn_scraped_records_*.csv[/dim])")
    console.print("  [bold cyan][3][/] [bold]Both (Append to Master Sheet + Save Standalone CSV Backup)[/]")
    console.print("  [bold cyan][4][/] Skip Final Save (Already in live_session_records.csv)\n")

    export_choice = Prompt.ask("[bold green]Select export option (1-4)[/]", default="3").strip()

    if export_choice in ["1", "3"]:
        added_count = append_to_master(all_scraped_results)
        console.print(f"\n[bold green]✅ Successfully added {added_count} new unique records to {get_master_csv_path()}![/]")

    if export_choice in ["2", "3"]:
        saved_file = export_results_to_csv(all_scraped_results)
        console.print(f"[bold green]✅ Standalone CSV saved to:[/] [cyan]{saved_file}[/]")

    # Final Master Sheet Total
    _, _, final_master_count = load_master_records()
    console.print(f"\n[bold magenta]📊 Updated Master Sheet Total Records: {final_master_count}[/]\n")

if __name__ == "__main__":
    main()
