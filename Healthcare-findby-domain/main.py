import warnings
warnings.filterwarnings("ignore")

import os
import sys
import argparse
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

# Local modules
from scanner import fetch_site_content
from healthcare_classifier import classify_domain_content, clean_domain_string

# Terminal styling using rich if available, with graceful fallback
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

console = Console() if RICH_AVAILABLE else None


def print_banner():
    """Displays attractive terminal header banner."""
    if RICH_AVAILABLE:
        banner_text = (
            "[bold cyan]🏥 HEALTHCARE DOMAIN FINDER & CLASSIFIER[/bold cyan]\n"
            "[white]Fast, Multi-threaded AI/Rule-based Healthcare & Clinic Detector[/white]\n"
            "[dim]Identifies: Hospitals, Medical Practices, Dental, Urgent Care, Mental Health & filters Non-HC[/dim]"
        )
        console.print(Panel(banner_text, expand=False, border_style="cyan"))
    else:
        print("=" * 60)
        print(" HEALTHCARE DOMAIN FINDER & CLASSIFIER ")
        print("=" * 60)


def detect_domain_column(df: pd.DataFrame) -> str:
    """Auto-detects the domain/URL column in a dataframe."""
    possible_names = [
        "domain", "domains", "website", "websites", "url", "urls",
        "company_domain", "company_website", "company_url", "site",
        "web_address", "link", "homepage"
    ]
    
    # Exact or case-insensitive match
    for col in df.columns:
        if str(col).strip().lower() in possible_names:
            return col
            
    # Substring match
    for col in df.columns:
        for name in possible_names:
            if name in str(col).strip().lower():
                return col

    # Fallback to the first column
    return df.columns[0]


def process_single_domain(row_data: Dict[str, Any], domain_col: str, timeout: int) -> Dict[str, Any]:
    """Scrapes and classifies a single domain."""
    raw_val = str(row_data.get(domain_col, "") or "").strip()
    clean_domain = clean_domain_string(raw_val)

    if not clean_domain or clean_domain.lower() in ["nan", "none", "null", ""]:
        res_dict = {
            **row_data,
            "Cleaned_Domain": "",
            "Is_Healthcare": "NO",
            "Healthcare_Category": "Invalid / Empty Domain",
            "Confidence": "High",
            "Reason": "Empty or invalid domain input",
            "Page_Title": "",
            "Site_Status": "Empty",
            "Detected_Specialties": ""
        }
        return res_dict

    # 1. Fetch site content
    fetch_res = fetch_site_content(clean_domain, timeout=timeout)
    
    # 2. Classify content
    classification = classify_domain_content(
        domain=clean_domain,
        html=fetch_res.get("html"),
        soup=fetch_res.get("soup"),
        page_title=fetch_res.get("page_title", ""),
        meta_description=fetch_res.get("meta_description", ""),
        status_msg=fetch_res.get("status_msg", "Live")
    )

    # 3. Combine result
    is_hc_str = "YES" if classification["is_healthcare"] else "NO"
    specialties_str = ", ".join(classification.get("detected_specialties", []))

    return {
        **row_data,
        "Cleaned_Domain": clean_domain,
        "Is_Healthcare": is_hc_str,
        "Healthcare_Category": classification["category"],
        "Confidence": classification["confidence"],
        "Reason": classification["reason"],
        "Page_Title": fetch_res.get("page_title", ""),
        "Site_Status": fetch_res.get("status_msg", ""),
        "Detected_Specialties": specialties_str
    }


def create_sample_input(file_path: str):
    """Creates a sample input.csv if none exists."""
    sample_data = [
        {"domain": "mayoclinic.org", "notes": "Top hospital"},
        {"domain": "aspendental.com", "notes": "Dental network"},
        {"domain": "citymd.com", "notes": "Urgent care"},
        {"domain": "clevelandclinic.org", "notes": "Health system"},
        {"domain": "apexroofing.com", "notes": "Roofing business"},
        {"domain": "dallasautocare.com", "notes": "Car repair"},
        {"domain": "morganandmorgan.com", "notes": "Law firm"},
        {"domain": "heartandvascularfl.com", "notes": "Cardiology clinic"},
        {"domain": "pacificdermcenter.com", "notes": "Dermatology"},
        {"domain": "starbucks.com", "notes": "Coffee retail"}
    ]
    df = pd.DataFrame(sample_data)
    df.to_csv(file_path, index=False)


def run_cli():
    parser = argparse.ArgumentParser(description="Healthcare Domain Finder & Classifier")
    parser.add_argument("-i", "--input", default="input.csv", help="Path to input CSV file (default: input.csv)")
    parser.add_argument("-o", "--output", default="output_healthcare_results.csv", help="Path to output CSV file (default: output_healthcare_results.csv)")
    parser.add_argument("-t", "--threads", type=int, default=15, help="Number of concurrent scraper threads (default: 15)")
    parser.add_argument("--timeout", type=int, default=8, help="HTTP request timeout in seconds (default: 8)")
    args = parser.parse_args()

    print_banner()

    input_path = args.input
    output_path = args.output
    threads = args.threads
    timeout = args.timeout

    # Check if input file exists
    if not os.path.exists(input_path):
        if input_path == "input.csv":
            if RICH_AVAILABLE:
                console.print(f"[yellow]⚠️  '{input_path}' not found. Creating a sample 'input.csv' with test domains...[/yellow]")
            else:
                print(f"'{input_path}' not found. Creating sample input.csv...")
            create_sample_input(input_path)
            if RICH_AVAILABLE:
                console.print(f"[green]✓ Created '{input_path}'. You can edit this file or run right away![/green]\n")
        else:
            if RICH_AVAILABLE:
                console.print(f"[red]❌ Error: Specified input file '{input_path}' does not exist.[/red]")
            else:
                print(f"Error: Specified input file '{input_path}' does not exist.")
            sys.exit(1)

    # Read CSV
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[red]❌ Error reading CSV file: {e}[/red]")
        else:
            print(f"Error reading CSV file: {e}")
        sys.exit(1)

    if df.empty:
        if RICH_AVAILABLE:
            console.print("[yellow]⚠️  Input CSV file is empty. Please add domains and try again.[/yellow]")
        else:
            print("Input CSV file is empty.")
        sys.exit(0)

    domain_col = detect_domain_column(df)
    total_domains = len(df)

    if RICH_AVAILABLE:
        console.print(f"📂 [bold]Input File:[/bold] [green]{input_path}[/green] ({total_domains} rows)")
        console.print(f"🔍 [bold]Domain Column Detected:[/bold] '[cyan]{domain_col}[/cyan]'")
        console.print(f"⚡ [bold]Concurrency:[/bold] [yellow]{threads} threads[/yellow] | [bold]Timeout:[/bold] {timeout}s\n")
    else:
        print(f"Input: {input_path} ({total_domains} rows)")
        print(f"Domain Column: {domain_col}")
        print(f"Threads: {threads} | Timeout: {timeout}s\n")

    records = df.to_dict(orient="records")
    results = []
    
    hc_count = 0
    non_hc_count = 0

    # Multi-threaded execution with Rich progress bar
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=35),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("• [green]HC: {task.fields[hc]}[/green] | [red]Non-HC: {task.fields[non_hc]}[/red]"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Scanning & Classifying domains...",
                total=total_domains,
                hc=0,
                non_hc=0
            )

            with ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_idx = {
                    executor.submit(process_single_domain, row, domain_col, timeout): i 
                    for i, row in enumerate(records)
                }

                # Maintain original order
                temp_results = [None] * total_domains
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        res = future.result()
                    except Exception as exc:
                        row = records[idx]
                        res = {
                            **row,
                            "Cleaned_Domain": clean_domain_string(str(row.get(domain_col, ""))),
                            "Is_Healthcare": "NO",
                            "Healthcare_Category": "Error",
                            "Confidence": "Low",
                            "Reason": f"Processing Exception: {str(exc)[:40]}",
                            "Page_Title": "",
                            "Site_Status": "Error",
                            "Detected_Specialties": ""
                        }

                    temp_results[idx] = res
                    if res["Is_Healthcare"] == "YES":
                        hc_count += 1
                    else:
                        non_hc_count += 1

                    progress.update(task, advance=1, hc=hc_count, non_hc=non_hc_count)

                results = temp_results
    else:
        print("Processing domains...")
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_idx = {
                executor.submit(process_single_domain, row, domain_col, timeout): i 
                for i, row in enumerate(records)
            }
            temp_results = [None] * total_domains
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    res = future.result()
                except Exception as exc:
                    row = records[idx]
                    res = {
                        **row,
                        "Cleaned_Domain": clean_domain_string(str(row.get(domain_col, ""))),
                        "Is_Healthcare": "NO",
                        "Healthcare_Category": "Error",
                        "Confidence": "Low",
                        "Reason": f"Processing Exception: {str(exc)[:40]}",
                        "Page_Title": "",
                        "Site_Status": "Error",
                        "Detected_Specialties": ""
                    }
                temp_results[idx] = res
                if res["Is_Healthcare"] == "YES":
                    hc_count += 1
                else:
                    non_hc_count += 1
                print(f"Processed: {len([r for r in temp_results if r])}/{total_domains} | HC: {hc_count} | Non-HC: {non_hc_count}", end="\r")
        results = temp_results
        print()

    # Save Output DataFrame
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_path, index=False)

    # Display Results & Summary Table
    if RICH_AVAILABLE:
        console.print("\n" + "=" * 60)
        console.print("[bold green]✅ Classification Complete![/bold green]")
        console.print(f"📁 [bold]Results Saved To:[/bold] [cyan]{output_path}[/cyan]\n")

        # Summary Table
        summary_table = Table(title="📊 Classification Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Count", justify="right")
        summary_table.add_column("Percentage", justify="right")

        hc_pct = (hc_count / total_domains * 100) if total_domains > 0 else 0
        non_hc_pct = (non_hc_count / total_domains * 100) if total_domains > 0 else 0

        summary_table.add_row("Total Domains Processed", str(total_domains), "100.0%")
        summary_table.add_row("[green]Healthcare / Clinics / Hospitals[/green]", f"[green]{hc_count}[/green]", f"[green]{hc_pct:.1f}%[/green]")
        summary_table.add_row("[red]Non-Healthcare / Other[/red]", f"[red]{non_hc_count}[/red]", f"[red]{non_hc_pct:.1f}%[/red]")
        console.print(summary_table)

        # Categories Breakdown Table
        cat_counts = out_df["Healthcare_Category"].value_counts().head(8)
        cat_table = Table(title="🩺 Top Detected Categories", show_header=True, header_style="bold blue")
        cat_table.add_column("Category / Specialty", style="cyan")
        cat_table.add_column("Count", justify="right")

        for cat, count in cat_counts.items():
            cat_table.add_row(str(cat), str(count))

        console.print(cat_table)

        # Preview Sample Results
        sample_preview = Table(title="🔍 Sample Results Preview (First 5 Rows)", show_header=True, header_style="bold yellow")
        sample_preview.add_column("Domain", style="white")
        sample_preview.add_column("Healthcare?", justify="center")
        sample_preview.add_column("Category", style="cyan")
        sample_preview.add_column("Confidence", justify="center")
        sample_preview.add_column("Status", style="dim")

        for _, row in out_df.head(5).iterrows():
            is_hc_tag = "[bold green]YES[/bold green]" if row["Is_Healthcare"] == "YES" else "[bold red]NO[/bold red]"
            sample_preview.add_row(
                str(row["Cleaned_Domain"])[:25],
                is_hc_tag,
                str(row["Healthcare_Category"])[:28],
                str(row["Confidence"]),
                str(row["Site_Status"])[:15]
            )
        console.print(sample_preview)

    else:
        print("\n" + "=" * 50)
        print("CLASSIFICATION COMPLETE")
        print(f"Results saved to: {output_path}")
        print(f"Total: {total_domains} | Healthcare: {hc_count} ({hc_count/total_domains*100:.1f}%) | Non-Healthcare: {non_hc_count} ({non_hc_count/total_domains*100:.1f}%)")


if __name__ == "__main__":
    run_cli()
