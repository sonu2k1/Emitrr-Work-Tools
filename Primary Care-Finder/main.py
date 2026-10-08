import os
import sys
import csv
import json
import warnings
from datetime import datetime
from typing import List, Dict

# Suppress urllib3 LibreSSL warning for clean terminal output
warnings.filterwarnings("ignore")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box

from valentin import TOP_US_METROS
from scraper import PRIMARY_CARE_CATEGORIES, PrimaryCareScraper

console = Console()
CHECKPOINT_INTERVAL = 250

def print_banner():
    banner_text = Text()
    banner_text.append("🏥 US PRIMARY CARE FINDER 🏥\n", style="bold cyan")
    banner_text.append("Targeted Company/Practice Name & Domain Scraper (Powered by Valentin.app)\n", style="italic white")
    banner_text.append("Extracts verified Company Names & Official Domains for US Healthcare Providers", style="dim")
    console.print(Panel(banner_text, box=box.ROUNDED, border_style="cyan", padding=(1, 2)))

def select_categories() -> List[str]:
    console.print("\n[bold yellow]👉 Step 1: Select Primary Care Category to Scrape:[/]")
    console.print("[dim]Choose the type of Primary Care data you need:[/dim]\n")
    
    for idx, cat_name in PRIMARY_CARE_CATEGORIES.items():
        console.print(f"  [bold cyan][{idx}][/] {cat_name}")
    console.print(f"  [bold green][7][/] [bold]All 6 Categories (Full Spectrum Primary Care)[/]")
    console.print(f"  [bold magenta][M][/] [italic]Custom Multi-select (e.g., '1,3,5' or '2,6')[/]\n")

    choice = Prompt.ask("[bold green]Enter your choice (1-7 or M)[/]", default="7").strip()

    if choice == "7":
        return list(PRIMARY_CARE_CATEGORIES.values())
    elif choice in ["1", "2", "3", "4", "5", "6"]:
        return [PRIMARY_CARE_CATEGORIES[int(choice)]]
    else:
        # Handle comma-separated custom selection
        cleaned_choice = choice.upper().replace("M", "").strip()
        if not cleaned_choice:
            cleaned_choice = Prompt.ask("[bold green]Enter category numbers separated by commas (e.g., 1,3,5)[/]", default="1,2,3")
        
        selected = []
        for num in cleaned_choice.split(","):
            num = num.strip()
            if num.isdigit() and int(num) in PRIMARY_CARE_CATEGORIES:
                selected.append(PRIMARY_CARE_CATEGORIES[int(num)])
        
        if not selected:
            console.print("[yellow]Invalid input. Defaulting to All 6 Categories.[/]")
            return list(PRIMARY_CARE_CATEGORIES.values())
        return selected

def select_locations() -> List[str]:
    console.print("\n[bold yellow]👉 Step 2: Select Target US Location(s):[/]")
    console.print("  [bold cyan][1][/] Specific City / State (e.g., Austin TX, Miami FL, Dallas TX, New York NY)")
    console.print("  [bold cyan][2][/] Top 5 US Metro Hubs (Dallas TX, Austin TX, Houston TX, Miami FL, Atlanta GA)")
    console.print("  [bold cyan][3][/] Top 20 Major US Metro Areas (Nationwide Bulk Scrape)")
    console.print("  [bold cyan][4][/] Custom Multiple Cities (Comma-separated)\n")

    loc_choice = Prompt.ask("[bold green]Select location mode (1-4)[/]", default="1").strip()

    if loc_choice == "1":
        city = Prompt.ask("[bold green]Enter US City and State (e.g., Austin, TX)[/]", default="Austin, TX").strip()
        return [city]
    elif loc_choice == "2":
        return ["Dallas, TX", "Austin, TX", "Houston, TX", "Miami, FL", "Atlanta, GA"]
    elif loc_choice == "3":
        return TOP_US_METROS
    elif loc_choice == "4":
        cities_raw = Prompt.ask("[bold green]Enter US Cities separated by comma[/]", default="Austin TX, Dallas TX, Miami FL")
        cities = [c.strip() for c in cities_raw.split(",") if c.strip()]
        return cities if cities else ["Austin, TX"]
    else:
        return ["Austin, TX"]

def select_limit() -> int:
    console.print("\n[bold yellow]👉 Step 3: Maximum Results Target:[/]")
    limit_str = Prompt.ask("[bold green]Maximum practices per category/location (or type 'all')[/]", default="50").strip()
    if limit_str.lower() in ["all", "unlimited", "max"]:
        return 10000
    try:
        limit = int(limit_str)
        return max(1, limit)
    except ValueError:
        return 50

def export_results(results: List[Dict[str, str]], categories: List[str]) -> str:
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Simple clean base name e.g. 'Family Medicine' or 'All Primary Care'
    if len(categories) == 1:
        base_name = categories[0]
    elif len(categories) == len(PRIMARY_CARE_CATEGORIES):
        base_name = "All Primary Care"
    else:
        base_name = "Primary Care"

    # Incremental file numbering: Family Medicine - 1.csv, Family Medicine - 2.csv, etc.
    counter = 1
    while True:
        csv_filename = f"{base_name} - {counter}.csv"
        json_filename = f"{base_name} - {counter}.json"
        csv_file = os.path.join(output_dir, csv_filename)
        json_file = os.path.join(output_dir, json_filename)
        if not os.path.exists(csv_file) and not os.path.exists(json_file):
            break
        counter += 1

    # Format output with Company Name in 1st column and Domain in 2nd column
    fieldnames = ["Company Name", "Domain", "Category", "Location"]
    formatted_rows = []
    for r in results:
        formatted_rows.append({
            "Company Name": r.get("practice_name", ""),
            "Domain": r.get("domain", ""),
            "Category": r.get("category", ""),
            "Location": r.get("location", "")
        })

    # Export to CSV
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in formatted_rows:
            writer.writerow(row)

    # Export to JSON
    with open(json_file, mode="w", encoding="utf-8") as f:
        json.dump(formatted_rows, f, indent=2)

    return csv_file

def main():
    print_banner()

    # Step 1: Category selection
    selected_categories = select_categories()
    console.print(f"\n[bold green]✓ Selected Categories:[/] {', '.join(selected_categories)}")

    # Step 2: Location selection
    selected_locations = select_locations()
    console.print(f"[bold green]✓ Target Location(s):[/] {', '.join(selected_locations)}")

    # Step 3: Results limit
    limit_per_search = select_limit()
    console.print(f"[bold green]✓ Target Limit:[/] {limit_per_search} practices per query\n")

    # Confirmation
    console.print(Panel(
        f"[bold]Summary of Search Parameters:[/]\n"
        f"• [cyan]Primary Care Types:[/] {len(selected_categories)} ({', '.join(selected_categories)})\n"
        f"• [cyan]Locations:[/] {len(selected_locations)} ({', '.join(selected_locations[:3])}{'...' if len(selected_locations)>3 else ''})\n"
        f"• [cyan]Target per Query:[/] {limit_per_search}\n"
        f"• [cyan]Checkpoint Prompt:[/] Every {CHECKPOINT_INTERVAL} records\n"
        f"• [cyan]Search Engine:[/] Valentin.app Geocoding & Localized Maps/SERP",
        title="Ready to Scrape",
        border_style="green"
    ))

    if not Confirm.ask("[bold green]Start scraping now?[/]", default=True):
        console.print("[yellow]Scraping cancelled by user.[/]")
        sys.exit(0)

    # Initialize Scraper Engine
    scraper = PrimaryCareScraper(headless=True)

    all_results: List[Dict[str, str]] = []
    seen_domains = set()
    last_checkpoint_count = 0
    stop_scraping = False

    def on_item_found(item_or_msg):
        if isinstance(item_or_msg, dict):
            console.print(f"  [green]+ Found:[/] [bold]{item_or_msg['practice_name']}[/] -> [cyan]{item_or_msg['domain']}[/]")
        elif isinstance(item_or_msg, str):
            console.print(f"  {item_or_msg}")

    console.print("\n[bold cyan]🚀 Starting Scraper Engine...[/]\n")

    try:
        for cat in selected_categories:
            if stop_scraping:
                break
            console.print(f"\n[bold magenta]══════ Category: {cat} ══════[/]")
            for loc in selected_locations:
                if stop_scraping:
                    break
                console.print(f"\n[bold yellow]🔍 Searching in {loc}...[/]")
                records = scraper.scrape_category_for_location(
                    category=cat,
                    location=loc,
                    limit=limit_per_search,
                    progress_callback=on_item_found
                )
                for r in records:
                    if r["domain"] not in seen_domains:
                        seen_domains.add(r["domain"])
                        all_results.append(r)

                        # Check 250 records checkpoint threshold
                        current_count = len(all_results)
                        if current_count > 0 and (current_count - last_checkpoint_count) >= CHECKPOINT_INTERVAL:
                            last_checkpoint_count = current_count
                            console.print("\n" + "="*70)
                            console.print(Panel(
                                f"🎯 [bold yellow]Checkpoint Reached:[/] [bold green]{current_count}[/] unique records scraped so far!\n\n"
                                f"[white]Would you like to continue scraping the next batch or stop now and generate the output CSV file?[/]",
                                title="250 Records Milestone",
                                border_style="yellow"
                            ))
                            ans = Prompt.ask(
                                "[bold green]Do you want to continue or stop?[/]",
                                choices=["continue", "stop", "c", "s"],
                                default="continue"
                            ).strip().lower()

                            if ans in ["stop", "s"]:
                                console.print("[bold yellow]🛑 Stopping scraping as requested. Generating final CSV file...[/]")
                                stop_scraping = True
                                break
                            else:
                                console.print("[bold green]▶ Continuing scraping...[/]\n")

    except KeyboardInterrupt:
        console.print("\n[bold red]⚠️ Interrupted by user (Ctrl+C). Saving collected records...[/]")

    console.print("\n" + "="*70 + "\n")
    if all_results:
        results_table = Table(title="Discovered Primary Care Practices", box=box.SIMPLE_HEAVY)
        results_table.add_column("#", style="dim", width=4)
        results_table.add_column("Company Name", style="bold white", min_width=30)
        results_table.add_column("Domain", style="bold cyan", min_width=25)
        results_table.add_column("Category", style="green")
        results_table.add_column("Location", style="dim")

        # Show preview of up to 30 records in terminal
        display_limit = min(30, len(all_results))
        for idx, item in enumerate(all_results[:display_limit], 1):
            results_table.add_row(
                str(idx),
                item["practice_name"],
                item["domain"],
                item["category"],
                item["location"].split(",")[0]
            )

        console.print(results_table)
        if len(all_results) > display_limit:
            console.print(f"[dim]... and {len(all_results) - display_limit} more records saved in CSV.[/dim]\n")

        csv_path = export_results(all_results, selected_categories)
        console.print(Panel(
            f"[bold green]✨ Scraping Completed Successfully![/]\n\n"
            f"• [bold white]Total Unique Records Extracted:[/] [bold cyan]{len(all_results)}[/]\n"
            f"• [bold white]CSV Export File:[/] [bold yellow]{csv_path}[/]\n"
            f"• [bold white]JSON Export File:[/] [bold yellow]{csv_path.replace('.csv', '.json')}[/]\n\n"
            f"[bold cyan]CSV Columns:[/]\n"
            f"  [bold]Column 1:[/] Company Name\n"
            f"  [bold]Column 2:[/] Domain\n"
            f"  [bold]Column 3:[/] Category\n"
            f"  [bold]Column 4:[/] Location",
            title="Export Summary",
            border_style="green"
        ))
    else:
        console.print("[bold red]No practices found. Please verify location / internet connection.[/]")

if __name__ == "__main__":
    main()
