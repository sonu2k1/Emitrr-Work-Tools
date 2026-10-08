#!/usr/bin/env python3
"""
🩺 EHR & Patient Portal Scraper CLI
Processes CSV/Excel files containing healthcare & practice domains, extracts EHR names and patient portal links.
Features an interactive CLI, multi-threaded high concurrency, and a Rich terminal UI.
"""

import warnings
warnings.filterwarnings("ignore")

import sys
import os
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# Rich formatting imports with graceful fallback
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich import print as rprint
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

console = Console() if RICH_AVAILABLE else None

from detector import PatientPortalDetector, clean_domain

# Default candidate column names to look for if not explicitly specified
DOMAIN_COLUMN_CANDIDATES = [
    'domain', 'domains', 'website', 'websites', 'url', 'urls',
    'company_domain', 'company domain', 'practice_domain', 'practice domain',
    'web_address', 'web address', 'site', 'homepage', 'link', 'domain_name'
]

SAMPLE_TEST_DOMAINS = [
    {"domain": "hopkinsmedicine.org", "expected": "Epic (MyChart)"},
    {"domain": "clevelandclinic.org", "expected": "Epic (MyChart)"},
    {"domain": "cedars-sinai.org", "expected": "Epic (MyChart)"},
    {"domain": "massgeneral.org", "expected": "Epic (MyChart)"},
    {"domain": "texasdigestive.com", "expected": "ModMed (EMA)"},
    {"domain": "dermatologyandlasercenter.com", "expected": "ModMed / Athena / eCW"},
    {"domain": "manhattandermatologists.com", "expected": "EHR / Portal"},
    {"domain": "familycaremedicalgroup.com", "expected": "Athena / eCW"}
]


def print_banner():
    """Displays attractive terminal header banner."""
    if RICH_AVAILABLE:
        banner_content = (
            "[bold cyan]🩺 EHR & PATIENT PORTAL INTELLIGENCE SCRAPER[/bold cyan]\n"
            "[white]Fast, Multi-Threaded Detection for 50+ Healthcare EHRs & Patient Portals[/white]\n"
            "[dim]Epic • AthenaHealth • eClinicalWorks • ModMed • NextGen • Cerner • WebPT • Dentrix & more[/dim]"
        )
        console.print(Panel(banner_content, expand=False, border_style="cyan", padding=(1, 2)))
    else:
        print("=" * 65)
        print(" 🩺 EHR & PATIENT PORTAL INTELLIGENCE SCRAPER")
        print("=" * 65)


def detect_domain_column(df: pd.DataFrame) -> str:
    """Auto-detects the domain column in the DataFrame."""
    cols = list(df.columns)
    
    # Exact match lowercased
    for col in cols:
        col_clean = str(col).strip().lower().replace('_', ' ').replace('-', ' ')
        if col_clean in [c.replace('_', ' ') for c in DOMAIN_COLUMN_CANDIDATES]:
            return col
    
    # Substring match
    for col in cols:
        col_lower = str(col).lower()
        if 'domain' in col_lower or 'website' in col_lower or 'url' in col_lower or 'site' in col_lower:
            return col

    # Fallback to first column
    return cols[0]


def process_domain_worker(detector: PatientPortalDetector, domain_val: str, original_row: dict) -> dict:
    """Worker function for concurrent thread pool."""
    res = detector.detect_for_domain(domain_val)
    
    # Merge detected results with original row data
    output_row = dict(original_row)
    
    ehr_name_val = res["ehr_name"]
    output_row["Detected_Domain"] = res["domain"]
    output_row["Is_Healthcare"] = res.get("is_healthcare", "Yes")
    output_row["EHR_Name"] = ehr_name_val
    if "EHR Name" in output_row:
        output_row["EHR Name"] = ehr_name_val
    
    output_row["EHR_Category"] = res["ehr_category"]
    output_row["Patient_Portal_URL"] = res["portal_url"]
    output_row["Portal_Status"] = res["status"]
    output_row["Confidence"] = res["confidence"]
    output_row["Detection_Method"] = res["detection_method"]
    output_row["Portal_Anchor_Text"] = res["portal_text"]
    return output_row


def run_batch_enrichment(
    input_file: str,
    output_file: str = "ehr_results.csv",
    domain_col: str = None,
    threads: int = 15,
    timeout: int = 10,
    crawl_subpages: bool = True,
    export_excel: bool = False,
    only_ehr: bool = False
):
    """Main batch processing function."""
    print_banner()

    if not os.path.exists(input_file):
        if RICH_AVAILABLE:
            console.print(f"[bold red]❌ Error: Input file '{input_file}' not found![/bold red]")
        else:
            print(f"Error: Input file '{input_file}' not found!")
        sys.exit(1)

    # Read Input
    try:
        if input_file.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(input_file)
        else:
            df = pd.read_csv(input_file)
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]❌ Error reading input file: {e}[/bold red]")
        else:
            print(f"Error reading input file: {e}")
        sys.exit(1)

    total_rows = len(df)
    if total_rows == 0:
        if RICH_AVAILABLE:
            console.print("[bold yellow]⚠️ Input file is empty![/bold yellow]")
        else:
            print("Input file is empty!")
        return

    # Identify Domain Column
    if not domain_col:
        domain_col = detect_domain_column(df)
    else:
        if domain_col not in df.columns:
            if RICH_AVAILABLE:
                console.print(f"[bold red]❌ Column '{domain_col}' not found. Available: {list(df.columns)}[/bold red]")
            else:
                print(f"Column '{domain_col}' not found. Available: {list(df.columns)}")
            sys.exit(1)

    # Display configuration card
    if RICH_AVAILABLE:
        config_table = Table(show_header=False, box=None, padding=(0, 1))
        config_table.add_column("Key", style="bold cyan")
        config_table.add_column("Val", style="white")
        config_table.add_row("📁 Input File:", f"[green]{input_file}[/green] ({total_rows} domains)")
        config_table.add_row("🔍 Domain Column:", f"[yellow]{domain_col}[/yellow]")
        config_table.add_row("⚡ Threads / Timeout:", f"[white]{threads} threads | {timeout}s request timeout[/white]")
        config_table.add_row("🔄 Subpage Crawl:", f"[green]{'Enabled' if crawl_subpages else 'Disabled (Homepage only)'}[/green]")
        config_table.add_row("💾 Output Targets:", f"[cyan]{output_file}[/cyan]" + (" & .xlsx" if export_excel else ""))
        console.print(Panel(config_table, title="[bold]Configuration[/bold]", border_style="blue", padding=(0, 1)))
        console.print()
    else:
        print(f"📁 Input: {input_file} ({total_rows} domains) | Column: {domain_col}")
        print(f"⚡ Concurrency: {threads} threads | Timeout: {timeout}s | Subpages: {'Yes' if crawl_subpages else 'No'}")
        print(f"💾 Output: {output_file}\n")

    detector = PatientPortalDetector(timeout=timeout, crawl_subpages=crawl_subpages)
    
    stats = {
        "EHR_Found": 0,
        "Generic_Portal": 0,
        "No_Portal_Healthcare": 0,
        "Non_Healthcare": 0,
        "Errors": 0
    }

    start_time = time.time()
    records = df.to_dict(orient="records")
    temp_results = [None] * total_rows

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("• [bold green]EHR: {task.fields[ehr]}[/bold green] | [yellow]Generic: {task.fields[generic]}[/yellow] | [dim]No Portal: {task.fields[no_portal]}[/dim] | [magenta]Non-HC: {task.fields[non_hc]}[/magenta] | [red]Err: {task.fields[err]}[/red]"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Scraping Portals...",
                total=total_rows,
                ehr=0,
                generic=0,
                no_portal=0,
                non_hc=0,
                err=0
            )

            with ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_idx = {
                    executor.submit(process_domain_worker, detector, str(row.get(domain_col, "")), row): idx
                    for idx, row in enumerate(records)
                }

                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        res_row = future.result()
                    except Exception as e:
                        row = records[idx]
                        res_row = dict(row)
                        res_row["Detected_Domain"] = clean_domain(str(row.get(domain_col, "")))
                        res_row["Is_Healthcare"] = "Unknown"
                        res_row["EHR_Name"] = "Not Found"
                        if "EHR Name" in res_row:
                            res_row["EHR Name"] = "Not Found"
                        res_row["EHR_Category"] = "None"
                        res_row["Patient_Portal_URL"] = ""
                        res_row["Portal_Status"] = "Site Unreachable"
                        res_row["Confidence"] = "None"
                        res_row["Detection_Method"] = f"Error: {str(e)[:30]}"
                        res_row["Portal_Anchor_Text"] = ""

                    temp_results[idx] = res_row

                    st = res_row.get("Portal_Status", "")
                    ehr = res_row.get("EHR_Name", "")

                    if st == "Found" and ehr not in ["Not Found", "Custom / Practice Portal", "Not related to health care or clinics"]:
                        stats["EHR_Found"] += 1
                    elif st == "Generic Portal Found" or ehr == "Custom / Practice Portal":
                        stats["Generic_Portal"] += 1
                    elif "Not related to health care" in ehr or "Not related to health care" in st:
                        stats["Non_Healthcare"] += 1
                    elif st in ["Site Unreachable", "Invalid Domain"] or "Connection Failed" in res_row.get("Detection_Method", ""):
                        stats["Errors"] += 1
                    else:
                        stats["No_Portal_Healthcare"] += 1

                    progress.update(
                        task,
                        advance=1,
                        ehr=stats["EHR_Found"],
                        generic=stats["Generic_Portal"],
                        no_portal=stats["No_Portal_Healthcare"],
                        non_hc=stats["Non_Healthcare"],
                        err=stats["Errors"]
                    )

    else:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_idx = {
                executor.submit(process_domain_worker, detector, str(row.get(domain_col, "")), row): idx
                for idx, row in enumerate(records)
            }
            processed = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    res_row = future.result()
                except Exception as e:
                    row = records[idx]
                    res_row = dict(row)
                    res_row["Detected_Domain"] = clean_domain(str(row.get(domain_col, "")))
                    res_row["Is_Healthcare"] = "Unknown"
                    res_row["EHR_Name"] = "Not Found"
                    if "EHR Name" in res_row:
                        res_row["EHR Name"] = "Not Found"
                    res_row["EHR_Category"] = "None"
                    res_row["Patient_Portal_URL"] = ""
                    res_row["Portal_Status"] = "Site Unreachable"
                    res_row["Confidence"] = "None"
                    res_row["Detection_Method"] = f"Error: {str(e)[:30]}"
                    res_row["Portal_Anchor_Text"] = ""

                temp_results[idx] = res_row
                processed += 1
                st = res_row.get("Portal_Status", "")
                ehr = res_row.get("EHR_Name", "")

                if st == "Found" and ehr not in ["Not Found", "Custom / Practice Portal", "Not related to health care or clinics"]:
                    stats["EHR_Found"] += 1
                elif st == "Generic Portal Found" or ehr == "Custom / Practice Portal":
                    stats["Generic_Portal"] += 1
                elif "Not related to health care" in ehr or "Not related to health care" in st:
                    stats["Non_Healthcare"] += 1
                elif st in ["Site Unreachable", "Invalid Domain"] or "Connection Failed" in res_row.get("Detection_Method", ""):
                    stats["Errors"] += 1
                else:
                    stats["No_Portal_Healthcare"] += 1

                print(f"Scraping [{processed}/{total_rows}] | EHR: {stats['EHR_Found']} | Generic: {stats['Generic_Portal']} | No Portal: {stats['No_Portal_Healthcare']} | Non-HC: {stats['Non_Healthcare']} | Err: {stats['Errors']}", end="\r")
            print()

    elapsed = time.time() - start_time
    output_df = pd.DataFrame(temp_results)

    if only_ehr:
        cols_to_keep = [domain_col, "EHR_Name"]
        output_df = output_df[[c for c in cols_to_keep if c in output_df.columns]]

    # Determine paths
    if not output_file.lower().endswith('.csv'):
        output_csv = output_file + '.csv'
    else:
        output_csv = output_file

    output_df.to_csv(output_csv, index=False)

    excel_path = None
    if export_excel or output_file.lower().endswith(('.xlsx', '.xls')):
        excel_path = output_csv.rsplit('.', 1)[0] + '.xlsx'
        output_df.to_excel(excel_path, index=False)

    speed = total_rows / (elapsed or 1)

    # Rich summary output
    if RICH_AVAILABLE:
        console.print()
        console.print(f"[bold green]✨ Scraping Complete in {elapsed:.2f}s ({speed:.1f} domains/sec)[/bold green]\n")
        
        # 1. Main Stats Table
        summary_table = Table(title="📊 Overall Extraction Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Category / Status", style="bold")
        summary_table.add_column("Count", justify="right")
        summary_table.add_column("Percentage", justify="right")

        summary_table.add_row("[bold green]Verified EHR Portals Found[/bold green]", f"[bold green]{stats['EHR_Found']}[/bold green]", f"[bold green]{stats['EHR_Found']/total_rows*100:.1f}%[/bold green]")
        summary_table.add_row("[yellow]Generic / Practice-Specific Portals[/yellow]", f"[yellow]{stats['Generic_Portal']}[/yellow]", f"[yellow]{stats['Generic_Portal']/total_rows*100:.1f}%[/yellow]")
        summary_table.add_row("[cyan]Healthcare Verified (No Public Portal)[/cyan]", f"[cyan]{stats['No_Portal_Healthcare']}[/cyan]", f"[cyan]{stats['No_Portal_Healthcare']/total_rows*100:.1f}%[/cyan]")
        summary_table.add_row("[magenta]Non-Healthcare Domains Filtered[/magenta]", f"[magenta]{stats['Non_Healthcare']}[/magenta]", f"[magenta]{stats['Non_Healthcare']/total_rows*100:.1f}%[/magenta]")
        summary_table.add_row("[red]Unreachable / Network Errors[/red]", f"[red]{stats['Errors']}[/red]", f"[red]{stats['Errors']/total_rows*100:.1f}%[/red]")
        summary_table.add_row("[bold white]Total Scanned[/bold white]", f"[bold white]{total_rows}[/bold white]", "100.0%")
        console.print(summary_table)

        # 2. Dedicated Table for Unidentified / Blank Reasons
        reasons_table = Table(title="❓ Reason for Unidentified / Blank Results", show_header=True, header_style="bold yellow")
        reasons_table.add_column("Status / Outcome", style="bold white", max_width=30)
        reasons_table.add_column("Count", justify="right", style="cyan")
        reasons_table.add_column("Why EHR / Portal is Not Listed?", style="white")

        reasons_table.add_row(
            "[cyan]Healthcare Verified\n(No Portal Detected)[/cyan]",
            f"[bold cyan]{stats['No_Portal_Healthcare']}[/bold cyan]",
            "Valid healthcare practice, but operates via phone/in-person or uses internal private EHR with no public patient login link."
        )
        reasons_table.add_row(
            "[magenta]Non-Healthcare\nDomains[/magenta]",
            f"[bold magenta]{stats['Non_Healthcare']}[/bold magenta]",
            "Domain belongs to non-healthcare industries (e.g. Retail, Automotive, Law, Real Estate, Education) - filtered out."
        )
        reasons_table.add_row(
            "[red]Unreachable / Errors[/red]",
            f"[bold red]{stats['Errors']}[/bold red]",
            "Website connection failed (DNS error, timeout > 10s, SSL issue, or Cloudflare bot blocking)."
        )
        console.print(reasons_table)

        # 3. Top Detected EHR Providers Breakdown (Excluding Non-Healthcare and Generic)
        if "EHR_Name" in output_df.columns:
            # Filter to actual EHR vendors
            valid_ehrs = output_df[
                ~output_df["EHR_Name"].isin(["Not Found", "Not related to health care or clinics", "Custom / Practice Portal", ""])
            ]["EHR_Name"]
            
            ehr_counts = valid_ehrs.value_counts()
            total_valid_ehr = len(valid_ehrs)
            
            if not ehr_counts.empty:
                ehr_table = Table(title=f"🩺 Top Detected EHR Providers ({total_valid_ehr} total detected)", show_header=True, header_style="bold cyan")
                ehr_table.add_column("EHR System", style="bold white")
                ehr_table.add_column("Count", justify="right", style="cyan")
                ehr_table.add_column("Share of Verified EHRs", justify="right", style="green")

                for ehr_name, count in ehr_counts.head(12).items():
                    pct = (count / total_valid_ehr * 100) if total_valid_ehr > 0 else 0
                    ehr_table.add_row(str(ehr_name), str(count), f"{pct:.1f}%")
                console.print(ehr_table)

        # 4. Sample Results Preview Table
        preview_table = Table(title="🔍 First 8 Results Preview", show_header=True, header_style="bold yellow")
        preview_table.add_column("Website", style="white", max_width=25)
        preview_table.add_column("EHR Name", style="bold cyan", max_width=26)
        preview_table.add_column("Portal URL", style="blue", max_width=32)
        preview_table.add_column("Status Badge", justify="center")
        preview_table.add_column("Detection / Reason", style="dim", max_width=30)

        for _, row in output_df.head(8).iterrows():
            st = str(row.get("Portal_Status", ""))
            ehr = str(row.get("EHR_Name", "Not Found"))
            
            if st == "Found" and ehr not in ["Not Found", "Custom / Practice Portal", "Not related to health care or clinics"]:
                status_badge = "[bold green]EHR Found[/bold green]"
            elif st == "Generic Portal Found" or ehr == "Custom / Practice Portal":
                status_badge = "[yellow]Generic Portal[/yellow]"
            elif "Not related to health care" in ehr or "Not related to health care" in st:
                status_badge = "[magenta]Non-HC[/magenta]"
            elif "Unreachable" in st or "Error" in st:
                status_badge = "[red]Unreachable[/red]"
            else:
                status_badge = "[dim]No Portal[/dim]"

            portal_display = str(row.get("Patient_Portal_URL", "")) or "[dim]None[/dim]"
            reason_display = str(row.get("Detection_Method", ""))[:30]

            preview_table.add_row(
                str(row.get(domain_col, ""))[:25],
                ehr[:26],
                portal_display[:32],
                status_badge,
                reason_display
            )
        console.print(preview_table)

        # 5. Save Confirmation Banner
        save_text = f"[bold green]✅ Results saved successfully![/bold green]\n• CSV:   [cyan]{output_csv}[/cyan]"
        if excel_path:
            save_text += f"\n• Excel: [cyan]{excel_path}[/cyan]"
        console.print(Panel(save_text, border_style="green", padding=(0, 1)))
        console.print()

    else:
        print(f"\n=======================================================")
        print(f"✨ Scraping Complete in {elapsed:.2f}s ({speed:.1f} domains/sec)")
        print(f"  • Total Domains:             {total_rows}")
        print(f"  • EHR Portals Found:         {stats['EHR_Found']} ({stats['EHR_Found']/total_rows*100:.1f}%)")
        print(f"  • Generic Portals:           {stats['Generic_Portal']} ({stats['Generic_Portal']/total_rows*100:.1f}%)")
        print(f"  • Healthcare (No Portal):    {stats['No_Portal_Healthcare']}")
        print(f"  • Non-Healthcare Domains:    {stats['Non_Healthcare']}")
        print(f"  • Unreachable / Errors:      {stats['Errors']}")
        print(f"=======================================================")
        print(f"✅ Saved to: {output_csv}")
        if excel_path:
            print(f"✅ Excel: {excel_path}")


def run_single_domain_test(domain: str, timeout: int = 10, crawl_subpages: bool = True):
    """Deep scans and presents detailed results for a single domain."""
    print_banner()
    if RICH_AVAILABLE:
        console.print(f"🔍 [bold cyan]Deep scanning domain:[/bold cyan] [bold white]{domain}[/bold white] ...\n")
    else:
        print(f"Scanning domain: {domain} ...\n")

    detector = PatientPortalDetector(timeout=timeout, crawl_subpages=crawl_subpages)
    res = detector.detect_for_domain(domain)

    if RICH_AVAILABLE:
        table = Table(title="📋 Detailed Detection Report", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value", style="white")

        table.add_row("Target Domain", res.get("domain", domain))
        
        is_hc = res.get("is_healthcare", "Yes")
        hc_style = "[bold green]YES[/bold green]" if is_hc == "Yes" else "[bold red]NO[/bold red]"
        table.add_row("Is Healthcare?", hc_style)

        ehr = res.get("ehr_name", "Not Found")
        ehr_style = f"[bold green]{ehr}[/bold green]" if ehr not in ["Not Found", "Not related to health care or clinics"] else f"[dim]{ehr}[/dim]"
        table.add_row("EHR Provider", ehr_style)
        table.add_row("EHR Category", res.get("ehr_category", "None"))

        portal = res.get("portal_url", "")
        portal_style = f"[cyan]{portal}[/cyan]" if portal else "[dim]None[/dim]"
        table.add_row("Patient Portal URL", portal_style)

        st = res.get("status", "")
        st_badge = f"[bold green]{st}[/bold green]" if st == "Found" else f"[yellow]{st}[/yellow]"
        table.add_row("Portal Status", st_badge)
        table.add_row("Confidence", res.get("confidence", "None"))
        table.add_row("Detection Method", res.get("detection_method", ""))
        table.add_row("Anchor Text", res.get("portal_text", "") or "[dim]N/A[/dim]")

        console.print(table)
        console.print()
    else:
        print(f"Domain:          {res['domain']}")
        print(f"EHR Name:        {res['ehr_name']}")
        print(f"Category:        {res['ehr_category']}")
        print(f"Portal URL:      {res['portal_url']}")
        print(f"Status:          {res['status']}")
        print(f"Confidence:      {res['confidence']}")
        print(f"Method:          {res['detection_method']}\n")


def run_sample_test():
    """Runs a quick live test on sample healthcare domains."""
    print_banner()
    if RICH_AVAILABLE:
        console.print("[bold yellow]🔬 Running Live Test on Sample Medical & Practice Domains...[/bold yellow]\n")
    else:
        print("🔬 Running Live Test on Sample Medical & Practice Domains...\n")
        
    detector = PatientPortalDetector(timeout=8, crawl_subpages=True)
    
    for item in SAMPLE_TEST_DOMAINS:
        dom = item["domain"]
        if RICH_AVAILABLE:
            console.print(f"🔎 Testing: [cyan]{dom}[/cyan] ...", end=" ")
        else:
            print(f"🔎 Testing: {dom} ...", end=" ")
            
        res = detector.detect_for_domain(dom)
        
        if RICH_AVAILABLE:
            st = res['status']
            st_color = "green" if st == "Found" else "yellow"
            console.print(f"[{st_color}][{st}][/{st_color}]")
            console.print(f"   ├─ EHR Name:    [bold white]{res['ehr_name']}[/bold white]")
            console.print(f"   ├─ Portal URL:  [blue]{res['portal_url']}[/blue]")
            console.print(f"   └─ Method:      [dim]{res['detection_method']}[/dim]\n")
        else:
            print(f"[{res['status']}]")
            print(f"   ├─ EHR Name:    {res['ehr_name']}")
            print(f"   ├─ Portal URL:  {res['portal_url']}")
            print(f"   └─ Method:      {res['detection_method']}\n")


def interactive_mode():
    """Guides user with a clean terminal menu if no CLI arguments were passed."""
    print_banner()
    
    # Discover available CSV/XLSX files in current directory
    csv_files = [f for f in os.listdir('.') if f.endswith(('.csv', '.xlsx')) and not f.startswith(('enriched_', 'output_'))]
    if 'input_domains.csv' in csv_files:
        # Prioritize input_domains.csv
        csv_files.remove('input_domains.csv')
        csv_files.insert(0, 'input_domains.csv')
    
    if RICH_AVAILABLE:
        menu_table = Table(show_header=False, box=None, padding=(0, 1))
        menu_table.add_column("Option", style="bold cyan")
        menu_table.add_column("Description", style="white")
        menu_table.add_row("[1]", "Process a CSV or Excel file (e.g. input_domains.csv)")
        menu_table.add_row("[2]", "Test a single domain interactively")
        menu_table.add_row("[3]", "Run sample benchmark test suite")
        menu_table.add_row("[4]", "Exit")
        console.print(Panel(menu_table, title="[bold]Select an Option[/bold]", border_style="cyan"))
    else:
        print("Select an option:")
        print("  1) Process a CSV or Excel file")
        print("  2) Test a single domain interactively")
        print("  3) Run sample test suite")
        print("  4) Exit")
    
    try:
        choice = input("\nEnter choice (1-4) [default: 1]: ").strip() or "1"
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return
    
    if choice == "1":
        if csv_files:
            if RICH_AVAILABLE:
                console.print(f"\n[bold]Available files in directory:[/bold]")
                for i, f in enumerate(csv_files, 1):
                    console.print(f"  [cyan][{i}][/cyan] [white]{f}[/white]")
            else:
                print(f"\nAvailable files in directory:")
                for i, f in enumerate(csv_files, 1):
                    print(f"  [{i}] {f}")

            default_file = csv_files[0]
            file_input = input(f"\nEnter filename or number (1-{len(csv_files)}) [default: {default_file}]: ").strip()
            if file_input.isdigit() and 1 <= int(file_input) <= len(csv_files):
                input_file = csv_files[int(file_input)-1]
            else:
                input_file = file_input or default_file
        else:
            input_file = input("\nEnter path to CSV/Excel file: ").strip() or "input_domains.csv"

        output_file = input("Enter output CSV path [default: ehr_results.csv]: ").strip() or "ehr_results.csv"
        threads_str = input("Number of concurrent threads [default: 15]: ").strip() or "15"
        threads = int(threads_str) if threads_str.isdigit() else 15
        
        excel_choice = input("Also export to Excel (.xlsx)? (y/n) [default: y]: ").strip().lower()
        export_excel = excel_choice in ['y', 'yes', '']

        run_batch_enrichment(
            input_file=input_file,
            output_file=output_file,
            threads=threads,
            export_excel=export_excel
        )

    elif choice == "2":
        test_dom = input("\nEnter domain or website URL (e.g. hopkinsmedicine.org): ").strip()
        if test_dom:
            run_single_domain_test(test_dom)
    elif choice == "3":
        run_sample_test()
    else:
        if RICH_AVAILABLE:
            console.print("[dim]Goodbye![/dim]")
        else:
            print("Goodbye!")


def main():
    parser = argparse.ArgumentParser(description="EHR & Patient Portal Scraper for Healthcare Practice Domains")
    parser.add_argument("-i", "--input", help="Path to input CSV or Excel file containing domains (e.g. input_domains.csv)")
    parser.add_argument("-o", "--output", default="ehr_results.csv", help="Path to output CSV file (default: ehr_results.csv)")
    parser.add_argument("-c", "--column", default=None, help="Name of column containing domain/website (auto-detected if omitted)")
    parser.add_argument("-t", "--threads", type=int, default=15, help="Number of concurrent threads (default: 15)")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP request timeout in seconds (default: 10)")
    parser.add_argument("--no-subpages", action="store_true", help="Disable subpage crawling (faster, homepage only)")
    parser.add_argument("--excel", action="store_true", help="Also save results as an Excel (.xlsx) file")
    parser.add_argument("--only-ehr", action="store_true", help="Output only the Domain and EHR Name columns")
    parser.add_argument("--sample", action="store_true", help="Run live test on sample healthcare domains")
    parser.add_argument("--single", help="Test a single domain directly from CLI")

    args = parser.parse_args()

    if args.sample:
        run_sample_test()
    elif args.single:
        run_single_domain_test(args.single, timeout=args.timeout, crawl_subpages=not args.no_subpages)
    elif args.input:
        run_batch_enrichment(
            input_file=args.input,
            output_file=args.output,
            domain_col=args.column,
            threads=args.threads,
            timeout=args.timeout,
            crawl_subpages=not args.no_subpages,
            export_excel=args.excel,
            only_ehr=args.only_ehr
        )
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
