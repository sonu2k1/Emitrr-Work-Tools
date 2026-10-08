#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore")
import os
import sys
import time
import argparse
import concurrent.futures
from typing import Dict, Any, List, Optional
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich import print as rprint

from extractor_core import parse_email, classify_seniority, extract_title_from_text
from search_engine import SearchEngine
from website_scraper import scrape_company_team_page
from api_enricher import APIEnricher

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]     [bold white]💼 EMAIL JOB TITLE & SENIORITY FINDER CLI[/bold white]               [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]     [dim]Multi-Engine Search • Apollo & LinkedIn Dorking • Scraper[/dim] [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]
"""


def detect_email_column(df: pd.DataFrame) -> Optional[str]:
    """Auto-detects the email column from dataframe headers or contents."""
    common_names = [
        "email", "email_id", "email_address", "e-mail", "e_mail", 
        "contact_email", "work_email", "primary_email", "mail", "mail_id"
    ]
    for col in df.columns:
        if str(col).strip().lower() in common_names:
            return col

    # Substring match
    for col in df.columns:
        if "email" in str(col).strip().lower() or "e-mail" in str(col).strip().lower():
            return col

    # Fallback: check first row values for @ symbol
    for col in df.columns:
        sample_vals = df[col].dropna().astype(str).head(5)
        if any("@" in v and "." in v for v in sample_vals):
            return col

    return None


def process_single_email(
    email: str,
    search_engine: SearchEngine,
    api_enricher: APIEnricher,
    check_website: bool = True
) -> Dict[str, Any]:
    """
    Complete enrichment pipeline for a single email.
    """
    # 1. Parse Email & Heuristics
    parsed = parse_email(email)
    if not parsed["is_valid"]:
        return {
            "Email": email,
            "Detected_First_Name": "",
            "Detected_Last_Name": "",
            "Detected_Full_Name": "",
            "Job_Title": "",
            "Seniority": "Unknown",
            "Company_Name": "",
            "LinkedIn_URL": "",
            "Confidence_Score": "None",
            "Data_Source": "Invalid Email",
            "Status": "Invalid"
        }

    if parsed["is_role_based"]:
        return {
            "Email": parsed["email"],
            "Detected_First_Name": "",
            "Detected_Last_Name": "",
            "Detected_Full_Name": "",
            "Job_Title": "General Inbox / Staff",
            "Seniority": "Staff / Coordinator",
            "Company_Name": parsed["company_name"],
            "LinkedIn_URL": "",
            "Confidence_Score": "Medium",
            "Data_Source": "Role-based Mailbox",
            "Status": "Role-Based"
        }

    job_title = ""
    company_name = parsed["company_name"]
    linkedin_url = ""
    confidence = "None"
    data_source = ""
    seniority = "Unknown"

    # 2. Check API Enricher (if configured)
    if api_enricher.has_active_api():
        api_res = api_enricher.enrich(parsed)
        if api_res and api_res.get("job_title"):
            job_title = api_res.get("job_title", "")
            company_name = api_res.get("company_name") or company_name
            linkedin_url = api_res.get("linkedin_url", "")
            confidence = api_res.get("confidence", "High")
            data_source = api_res.get("source", "API")

    # 3. Web & LinkedIn Search Dorking
    if not job_title:
        search_res = search_engine.find_title_and_profile(parsed)
        if search_res and search_res.get("job_title"):
            job_title = search_res.get("job_title", "")
            linkedin_url = search_res.get("linkedin_url", "")
            confidence = search_res.get("confidence", "Medium")
            data_source = search_res.get("source", "Web/LinkedIn Search")

    # 4. Fallback: Company Team / About Page Scraper
    if not job_title and check_website and parsed["domain"]:
        site_res = scrape_company_team_page(
            domain=parsed["domain"],
            full_name=parsed["full_name"],
            first_name=parsed["first_name"],
            last_name=parsed["last_name"]
        )
        if site_res and site_res.get("job_title"):
            job_title = site_res.get("job_title", "")
            confidence = site_res.get("confidence", "Medium")
            data_source = site_res.get("source", "Company Website")

    # 5. Classify Seniority
    if job_title:
        seniority = classify_seniority(job_title)
        status = "Found"
    else:
        status = "Not Found"

    return {
        "Email": parsed["email"],
        "Detected_First_Name": parsed["first_name"],
        "Detected_Last_Name": parsed["last_name"],
        "Detected_Full_Name": parsed["full_name"],
        "Job_Title": job_title,
        "Seniority": seniority,
        "Company_Name": company_name,
        "LinkedIn_URL": linkedin_url,
        "Confidence_Score": confidence,
        "Data_Source": data_source,
        "Status": status
    }


def main():
    parser = argparse.ArgumentParser(
        description="Email to Job Title & Seniority Finder CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-i", "--input", help="Path to input CSV file containing emails")
    parser.add_argument("-o", "--output", help="Path to save enriched output CSV file")
    parser.add_argument("-e", "--email", help="Test a single email address directly in CLI")
    parser.add_argument("-t", "--threads", type=int, default=3, help="Number of concurrent threads (default: 3)")
    parser.add_argument("-d", "--delay", type=float, default=0.8, help="Delay between search requests in seconds (default: 0.8)")
    parser.add_argument("--apollo-key", help="Optional Apollo.io API Key")
    parser.add_argument("--skip-website", action="store_true", help="Skip fallback website team page scraping")

    parser.add_argument("-l", "--limit", type=int, default=0, help="Limit number of rows to process (0 = all)")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from existing output file (overwrite)")

    args = parser.parse_args()

    console.print(BANNER)

    # Setup Engines
    search_engine = SearchEngine(delay=args.delay)
    api_enricher = APIEnricher(apollo_key=args.apollo_key)

    # MODE 1: Single Email Lookup
    if args.email:
        console.print(f"[bold yellow]🔍 Enriching Single Email:[/bold yellow] [white]{args.email}[/white]\n")
        with console.status("[bold green]Searching LinkedIn, Web, and Team directories...[/bold green]"):
            result = process_single_email(
                args.email,
                search_engine,
                api_enricher,
                check_website=not args.skip_website
            )

        table = Table(title="Email Enrichment Result", show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan", width=22)
        table.add_column("Enriched Value", style="white")

        for k, v in result.items():
            val_str = str(v) if v else "[dim]--[/dim]"
            if k == "Job_Title" and v:
                val_str = f"[bold green]{v}[/bold green]"
            elif k == "Seniority" and v != "Unknown":
                val_str = f"[bold yellow]{v}[/bold yellow]"
            elif k == "Status":
                val_str = f"[green]{v}[/green]" if v == "Found" else f"[red]{v}[/red]"
            table.add_row(k, val_str)

        console.print(table)
        return

    # MODE 2: Batch CSV Processing
    if not args.input:
        console.print("[bold red]❌ Error:[/bold red] Please provide an input CSV file with [bold cyan]-i filename.csv[/bold cyan] or test a single email with [bold cyan]-e email@domain.com[/bold cyan]")
        console.print("\n[dim]Usage Example: python3 title_finder.py -i user_emails.csv -o output_enriched.csv[/dim]")
        sys.exit(1)

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        console.print(f"[bold red]❌ Error:[/bold red] File not found: [white]{input_path}[/white]")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_enriched.csv"

    # Read CSV
    try:
        df = pd.read_csv(input_path, on_bad_lines="skip")
    except Exception:
        try:
            df = pd.read_csv(input_path, sep=None, engine="python", on_bad_lines="skip")
        except Exception as e:
            console.print(f"[bold red]❌ Error reading CSV:[/bold red] {e}")
            sys.exit(1)

    email_col = detect_email_column(df)
    if not email_col:
        console.print("[bold red]❌ Error:[/bold red] Could not automatically detect an email column in the CSV.")
        console.print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    if args.limit > 0:
        df = df.head(args.limit)

    # Check for existing results to resume
    results = []
    already_processed_emails = set()
    found_count = 0

    if not args.no_resume and os.path.exists(output_path):
        try:
            existing_df = pd.read_csv(output_path)
            results = existing_df.to_dict(orient="records")
            already_processed_emails = {
                str(r.get(email_col) or r.get("Email") or "").strip().lower() 
                for r in results if str(r.get(email_col) or r.get("Email") or "").strip()
            }
            found_count = sum(1 for r in results if r.get("Status") == "Found")
            if already_processed_emails:
                console.print(f"[dim]⚡ Resuming: Found {len(already_processed_emails)} already processed rows.[/dim]")
        except Exception:
            results = []
            already_processed_emails = set()

    # Filter rows that need processing
    pending_indices = [
        idx for idx, row in df.iterrows()
        if str(row.get(email_col, "")).strip().lower() not in already_processed_emails
    ]
    pending_df = df.loc[pending_indices]

    console.print(f"📂 [bold green]Input File:[/bold green] {input_path}")
    console.print(f"🎯 [bold green]Detected Email Column:[/bold green] [yellow]{email_col}[/yellow]")
    console.print(f"💾 [bold green]Output File:[/bold green] {output_path}")
    console.print(f"⚡ [bold green]Concurrency Threads:[/bold green] {args.threads}")
    console.print(f"📋 [bold green]Total Emails to Process:[/bold green] {len(pending_df)} / {len(df)}")
    if api_enricher.has_active_api():
        console.print("🔑 [bold green]Active API Key:[/bold green] Connected to Apollo.io")
    console.print("")

    if len(pending_df) == 0:
        console.print("[bold green]✅ All emails in this file are already processed![/bold green]")
        return

    total_pending = len(pending_df)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("• {task.completed}/{task.total} processed"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Enriching Emails...", total=total_pending)

        def worker(row_idx, row_data):
            raw_email = str(row_data.get(email_col, "")).strip()
            res = process_single_email(
                raw_email,
                search_engine,
                api_enricher,
                check_website=not args.skip_website
            )
            # Combine original row with enrichment fields
            full_row = row_data.to_dict()
            full_row.update(res)
            return full_row

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(worker, idx, row): idx 
                for idx, row in pending_df.iterrows()
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    res_row = future.result()
                    results.append(res_row)
                    if res_row.get("Status") == "Found":
                        found_count += 1
                        
                    # Save incremental checkpoint every 5 rows or on last row
                    if len(results) % 5 == 0 or len(results) == len(df):
                        out_df = pd.DataFrame(results)
                        out_df.to_csv(output_path, index=False)

                except Exception:
                    pass
                finally:
                    progress.update(task, advance=1)

    # Final Save
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_path, index=False)

    # Display Summary
    total_processed = len(results)
    success_rate = (found_count / total_processed * 100) if total_processed > 0 else 0
    summary_panel = Panel(
        f"""[bold green]✅ Enrichment Complete![/bold green]
• [cyan]Total Emails Processed:[/cyan] [bold white]{total_processed}[/bold white]
• [cyan]Titles Found:[/cyan] [bold green]{found_count}[/bold green] ([yellow]{success_rate:.1f}%[/yellow])
• [cyan]Output Saved To:[/cyan] [bold underline]{output_path}[/bold underline]
""",
        title="[bold cyan]Run Summary[/bold cyan]",
        border_style="green"
    )
    console.print(summary_panel)


if __name__ == "__main__":
    main()
