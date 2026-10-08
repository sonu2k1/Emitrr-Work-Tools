import os
import re
import csv
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Set, Tuple

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
MASTER_CSV_FILENAME = "weave_healthcare_customers.csv"

# Domains of search engines, social media, government portals, aggregators to exclude
EXCLUDED_DOMAINS = {
    "getweave.com", "weavecomm.com", "senja.io", "google.com", "yelp.com",
    "healthgrades.com", "zocdoc.com", "vitals.com", "webmd.com", "doximity.com",
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "wikipedia.org", "youtube.com", "mapquest.com", "yellowpages.com", "superpages.com",
    "bbb.org", "indeed.com", "glassdoor.com", "usnews.com", "carecredit.com",
    "valentin.app", "reddit.com", "quora.com", "patch.com", "chamberofcommerce.com",
    "bizapedia.com", "buzzfile.com", "apple.com", "bing.com", "yahoo.com",
    "duckduckgo.com", "opentable.com", "tripadvisor.com", "groupon.com", "angi.com",
    "thumbtack.com", "nextdoor.com", "whitepages.com", "dexknows.com", "citysearch.com",
    "manta.com", "ezdoctor.com", "topnpi.com", "npino.com", "npiprofiles.com",
    "countyoffice.org", "guidestar.org", "sharecare.com", "castleconnolly.com",
    "wellness.com", "healthcare4ppl.com", "zoominfo.com", "bloomberg.com",
    "crunchbase.com", "apollo.io", "definitivehc.com", "g2.com", "capterra.com",
    "softwareadvice.com", "trustpilot.com", "github.com", "amazon.com",
    "weence.com", "findatopdoc.com", "healthpost.com", "threebestrated.com", "usphonebook.com"
}

CSV_HEADERS = [
    "Practice / Company Name",
    "Official Website",
    "Clean Domain",
    "Healthcare Category",
    "Location",
    "Weave Evidence / Source",
    "Date Discovered"
]

def get_master_csv_path() -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, MASTER_CSV_FILENAME)

def clean_official_website(url: str) -> str:
    """
    Cleans tracking params, fragments, session IDs, trailing slashes from website URL.
    """
    if not url:
        return ""
    
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        # Rebuild clean scheme + netloc + path without tracking query params
        path = parsed.path.rstrip("/")
        clean_url = f"{parsed.scheme}://{parsed.netloc}{path}"
        if not path:
            clean_url = f"{parsed.scheme}://{parsed.netloc}"
        return clean_url
    except Exception:
        return url

def normalize_domain(domain_or_url: str) -> str:
    """
    Extracts root domain for exact deduplication (e.g., 'https://www.drsmithdental.com/contact' -> 'drsmithdental.com').
    """
    if not domain_or_url:
        return ""
    
    target = domain_or_url.lower().strip()
    if "://" in target:
        try:
            target = urlparse(target).netloc
        except Exception:
            pass
            
    # Strip port if any
    target = target.split(":")[0]
    
    # Strip www.
    if target.startswith("www."):
        target = target[4:]
        
    return target.strip()

def is_valid_practice_domain(domain_or_url: str) -> bool:
    """
    Validates if a domain belongs to a real practice / provider and not an excluded aggregator.
    """
    dom = normalize_domain(domain_or_url)
    if not dom or len(dom) < 4 or "." not in dom:
        return False
        
    if any(dom == ex or dom.endswith("." + ex) for ex in EXCLUDED_DOMAINS):
        return False
        
    if dom.endswith((".gov", ".edu.cn", ".pdf", ".jpg", ".png", ".zip")):
        return False
        
    return True

def clean_practice_name(name: str) -> str:
    """
    Removes SEO titles, doctor degree prefixes/suffixes if needed, and extraneous punctuation.
    """
    if not name:
        return ""
        
    # Strip common SEO suffixes
    name = re.sub(
        r"\s*[-–|•·:]\s*(Home|Welcome|About Us|Official Site|Contact Us|Top Doctors|Reviews|Near Me|Online Scheduling|Text Us).*$",
        "",
        name,
        flags=re.IGNORECASE
    )
    name = re.sub(r"\b\d+(\.\d+)?\s*(stars|\(\d+\)|reviews)\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(' "\'`-,:')
    return name

def load_master_records() -> Tuple[List[Dict[str, str]], Set[str], Set[str]]:
    """
    Loads all existing records from master CSV to populate known domains and names.
    """
    csv_path = get_master_csv_path()
    records: List[Dict[str, str]] = []
    unique_domains: Set[str] = set()
    unique_names: Set[str] = set()

    if not os.path.exists(csv_path):
        return records, unique_domains, unique_names

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            dom = normalize_domain(row.get("Clean Domain") or row.get("Official Website", ""))
            if dom:
                unique_domains.add(dom)
            name = clean_practice_name(row.get("Practice / Company Name", ""))
            if name:
                norm_name = re.sub(r"[^a-zA-Z0-9]", "", name.lower())
                if norm_name:
                    unique_names.add(norm_name)

    return records, unique_domains, unique_names

def append_to_master(rec: Dict[str, str]) -> bool:
    """
    Appends a new record to the master CSV file immediately.
    """
    csv_path = get_master_csv_path()
    file_exists = os.path.exists(csv_path)

    clean_site = clean_official_website(rec.get("official_website", ""))
    clean_dom = normalize_domain(clean_site)

    if not is_valid_practice_domain(clean_dom):
        return False

    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writerow(CSV_HEADERS)
            
        writer.writerow([
            rec.get("practice_name", "").strip(),
            clean_site,
            clean_dom,
            rec.get("category", "Healthcare Practice").strip(),
            rec.get("location", "US").strip(),
            rec.get("source", "Weave Customer").strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
    return True

def get_stats() -> Dict[str, any]:
    """
    Computes breakdown statistics of current CSV database.
    """
    records, unique_domains, _ = load_master_records()
    cat_counts: Dict[str, int] = {}
    for r in records:
        c = r.get("Healthcare Category", "Other") or "Other"
        cat_counts[c] = cat_counts.get(c, 0) + 1

    return {
        "total_records": len(records),
        "unique_domains": len(unique_domains),
        "category_counts": cat_counts,
        "csv_path": get_master_csv_path()
    }
