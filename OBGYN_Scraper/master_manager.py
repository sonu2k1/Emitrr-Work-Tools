import os
import csv
import re
from urllib.parse import urlparse, parse_qs, urlunparse
from typing import Set, Tuple, List, Dict

MASTER_CSV_FILENAME = "Master Data Sheet - Women’s Health _ OB-GYNFQHC.csv"

def get_master_csv_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, MASTER_CSV_FILENAME)

def normalize_domain(url_or_domain: str) -> str:
    """
    Extracts root domain in lowercase without 'www.' or protocol.
    e.g. 'https://www.westarobgyn.com/?utm_source=xyz' -> 'westarobgyn.com'
    """
    if not url_or_domain:
        return ""
    text = url_or_domain.strip().lower()
    if "://" not in text:
        text = "http://" + text
    try:
        parsed = urlparse(text)
        netloc = parsed.netloc.split(":")[0]
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.strip()
    except Exception:
        return ""

def clean_official_website(url: str) -> str:
    """
    Cleans tracking parameters (utm_source, etc.) and returns clean HTTPS URL.
    e.g. 'https://www.obgynassoc.com/?utm_source=chatgpt.com' -> 'https://www.obgynassoc.com/'
    """
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        # Drop UTM / query parameters
        cleaned = urlunparse((
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path if parsed.path else "/",
            "", "", ""
        ))
        if not cleaned.endswith("/"):
            # If no path file, ensure trailing slash for root domain
            if "." not in cleaned.split("/")[-1]:
                cleaned += "/"
        return cleaned
    except Exception:
        return url

def load_master_records() -> Tuple[Set[str], Set[str], int]:
    """
    Loads existing records from Master CSV.
    Returns:
        existing_domains (set of normalized domains)
        existing_names (set of lowercase cleaned names)
        total_count (int)
    """
    master_path = get_master_csv_path()
    existing_domains: Set[str] = set()
    existing_names: Set[str] = set()
    total_count = 0

    if not os.path.exists(master_path):
        return existing_domains, existing_names, 0

    try:
        with open(master_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                name, website = row[0].strip(), row[1].strip()
                # Skip header rows
                if name.lower() in ["practice / organization", "organization", "practice name", "name"]:
                    continue
                
                dom = normalize_domain(website)
                if dom:
                    existing_domains.add(dom)
                
                norm_name = re.sub(r"[^a-zA-Z0-9]", "", name.lower())
                if norm_name:
                    existing_names.add(norm_name)
                
                total_count += 1
    except Exception as e:
        print(f"Warning loading master sheet: {e}")

    return existing_domains, existing_names, total_count

def append_to_master(new_records: List[Dict[str, str]]) -> int:
    """
    Appends new unique records to the Master CSV file.
    Returns count of added records.
    """
    if not new_records:
        return 0

    master_path = get_master_csv_path()
    file_exists = os.path.exists(master_path)
    
    # Reload existing to be 100% sure no race-condition duplicates
    existing_domains, _, _ = load_master_records()

    added = 0
    with open(master_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Practice / Organization", "Official website"])

        for rec in new_records:
            name = rec.get("practice_name", "").strip()
            raw_site = rec.get("official_website") or rec.get("website") or rec.get("domain") or ""
            site = clean_official_website(raw_site)
            dom = normalize_domain(site)

            if not name or not dom or dom in existing_domains:
                continue

            writer.writerow([name, site])
            existing_domains.add(dom)
            added += 1

    return added
