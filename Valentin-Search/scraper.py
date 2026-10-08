#!/usr/bin/env python3
"""
Valentin.app Practice Domain Scraper (Python CLI)
Localized Practice & Clinic Domain Finder for United States & Canada.
"""

import sys
import os
import re
import time
import base64
import argparse
import urllib.parse
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import pandas as pd

IGNORED_DOMAINS = {
    'linkedin.com', 'facebook.com', 'instagram.com', 'twitter.com', 'x.com',
    'youtube.com', 'pinterest.com', 'tiktok.com', 'threads.net', 'reddit.com',
    'quora.com', 'google.com', 'google.ca', 'yahoo.com', 'bing.com',
    'duckduckgo.com', 'wikipedia.org', 'wikimedia.org', 'yelp.com', 'yelp.ca',
    'yellowpages.com', 'yellowpages.ca', 'whitepages.com', 'mapquest.com',
    'bbb.org', 'dnb.com', 'bloomberg.com', 'reuters.com', 'crunchbase.com',
    'glassdoor.com', 'indeed.com', 'zoominfo.com', 'apollo.io', 'owler.com',
    'healthgrades.com', 'zocdoc.com', 'vitals.com', 'doximity.com', 'webmd.com',
    'sharecare.com', 'ratemds.com', 'opencare.com', '1800dentist.com',
    'drchrono.com', 'castleconnolly.com', 'wellness.com', 'threebestrated.ca',
    'psychologytoday.com', 'allaboutvision.com'
}

SECOND_LEVEL_TLDS = {
    'co.uk', 'org.uk', 'co.in', 'net.in', 'com.au', 'net.au',
    'gc.ca', 'on.ca', 'qc.ca', 'bc.ca', 'ab.ca', 'mb.ca', 'sk.ca', 'ns.ca'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

STOP_WORDS = {'of', 'and', 'the', 'for', 'in', 'on', 'at', 'to', 'a', 'an', 'with', 'by', 'de', 'la', 'le', 'et', '&', '+'}

PARKED_PATTERNS = [
    'is for sale', 'domain for sale', 'buy this domain', 'domain is available',
    'hugedomains', 'sedo.com', 'dan.com', 'afternic', 'godaddy.com/domain-search',
    'this domain name is', 'parked free', 'domainpark', 'namecheap.com/domains',
    'under construction', 'domain has expired', 'purchase this domain', 'this domain is for sale',
    'buy domain', 'domain for purchase', 'domain name for sale', 'domain is listed'
]

def normalize_string(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'[\'`’]', '', s).strip()

def clean_practice_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return ""
    cleaned = normalize_string(name)
    cleaned = re.sub(r'\(.*?\)', ' ', cleaned)
    cleaned = re.sub(r'\[.*?\]', ' ', cleaned)

    # Strip site codes like FL048, 008, AL001
    cleaned = re.sub(r'^[A-Z]{2}\d{2,4}\s+', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\d{2,4}\s+', ' ', cleaned)

    # Strip leading doctor title
    cleaned = re.sub(r'^\s*(dr\.|dr|doctor)\s+', ' ', cleaned, flags=re.IGNORECASE)

    suffixes = [
        r'\bd\.d\.s\.\b', r'\bdds\b', r'\bd\.m\.d\.\b', r'\bdmd\b', r'\bm\.d\.\b', r'\bmd\b',
        r'\bd\.o\.\b', r'\bdo\b', r'\bd\.c\.\b', r'\bdc\b', r'\bd\.p\.m\.\b', r'\bdpm\b',
        r'\bo\.d\.\b', r'\bod\b', r'\bf\.a\.c\.s\.\b', r'\bfacs\b', r'\bf\.a\.c\.o\.g\.\b', r'\bfacog\b',
        r'\bp\.a\.-c\b', r'\bpa-c\b', r'\bp\.a\.\b', r'\bnp\b', r'\baprn\b', r'\bcrna\b',
        r'\bp\.l\.l\.c\.\b', r'\bpllc\b', r'\bp\.c\.\b', r'\bpc\b', r'\bl\.l\.c\.\b', r'\bllc\b',
        r'\bl\.l\.p\.\b', r'\bllp\b', r'\bincorporated\b', r'\binc\.\b', r'\binc\b',
        r'\bcorporation\b', r'\bcorp\.\b', r'\bcorp\b', r'\bcompany\b', r'\bco\.\b', r'\bco\b',
        r'\blimited\b', r'\bltd\.\b', r'\bltd\b', r'\bs\.c\.\b', r'\bsc\b'
    ]

    for s in suffixes:
        cleaned = re.sub(s, ' ', cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r'[,;:\.\|/]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if len(cleaned) > 0 else name.strip()

def extract_clean_domain(url_str: str):
    if not url_str:
        return None
    url_str = url_str.strip()
    if not url_str.startswith(('http://', 'https://')):
        url_str = 'http://' + url_str
    try:
        parsed = urlparse(url_str)
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        if hostname.startswith('www.'):
            hostname = hostname[4:]
        
        parts = hostname.split('.')
        if len(parts) < 2:
            return None
        
        main_domain = '.'.join(parts[-2:])
        if len(parts) >= 3 and '.'.join(parts[-2:]) in SECOND_LEVEL_TLDS:
            main_domain = '.'.join(parts[-3:])
            
        if hostname in IGNORED_DOMAINS or main_domain in IGNORED_DOMAINS:
            return None
            
        return hostname
    except Exception:
        return None

def is_parked_page(html_text: str) -> bool:
    if not html_text:
        return False
    lower = html_text.lower()
    return any(p in lower for p in PARKED_PATTERNS)

def generate_uule_v1(canonical_name: str) -> str:
    """Generates Google UULE v1 Base64 Protobuf for localized search"""
    if not canonical_name:
        return ""
    encoded_str = canonical_name.strip().encode('utf-8')
    str_len = len(encoded_str)
    
    varint = bytearray()
    while str_len > 127:
        varint.append((str_len & 0x7F) | 0x80)
        str_len >>= 7
    varint.append(str_len & 0x7F)
    
    header = bytearray([0x08, 0x02, 0x10, 0x20, 0x22]) + varint
    pb = header + encoded_str
    return 'w+' + base64.b64encode(pb).decode('utf-8')

def calculate_score(domain: str, practice_name: str, location_ctx: str = '') -> int:
    if not domain or not practice_name:
        return 0
    clean_p = re.sub(r'[^a-z0-9]', '', clean_practice_name(practice_name).lower())
    d_slug = re.sub(r'[^a-z0-9]', '', domain.split('.')[0].lower())
    
    if not clean_p or not d_slug:
        return 0

    base = 0
    if clean_p == d_slug:
        base = 130
    elif d_slug.startswith(clean_p):
        base = 95
    elif clean_p.startswith(d_slug):
        ratio = len(d_slug) / len(clean_p)
        base = 90 if (ratio >= 0.55 or (len(clean_p) - len(d_slug)) <= 6) else 40
    elif d_slug in clean_p and len(d_slug) >= 6:
        ratio = len(d_slug) / len(clean_p)
        base = 75 if ratio >= 0.5 else 45
    else:
        cleaned = clean_practice_name(practice_name)
        words = [w for w in re.split(r'[\s,-]+', cleaned.lower()) if len(w) >= 2]
        meaningful = [w for w in words if w not in STOP_WORDS]
        
        init1 = ''.join(w[0] for w in words)
        init2 = ''.join(w[0] for w in meaningful)
        if (len(words) >= 3 and len(init1) >= 3 and d_slug == init1) or (len(meaningful) >= 3 and len(init2) >= 3 and d_slug == init2):
            base = 95
        else:
            match_count = sum(1 for w in meaningful if len(w) >= 4 and w in d_slug)
            if match_count >= 2:
                base = 60 + (match_count * 10)

    if base <= 0:
        return 0

    if domain.endswith(('.com', '.ca')):
        base += 20
    elif domain.endswith(('.org', '.net', '.clinic', '.health')):
        base += 15

    return base

# 1. Direct Domain Verification
def probe_direct_domain(practice_name: str, country: str = 'US'):
    cleaned = clean_practice_name(practice_name)
    clean_slug = re.sub(r'[^a-z0-9]', '', cleaned.lower())
    if not clean_slug or len(clean_slug) < 3:
        return None

    candidates = []
    if country.upper() == 'CA':
        candidates.extend([f"{clean_slug}.ca", f"{clean_slug}.com"])
    else:
        candidates.extend([f"{clean_slug}.com", f"{clean_slug}.org", f"{clean_slug}.net"])

    # Stripped generic specialty brand candidate
    stripped_brand = re.sub(r'(urgentcare|medicalcenter|familymedicine|pediatrics|specialists|healthcare|pediatriccenter|familycare|medicalgroup|clinic|associates)$', '', clean_slug)
    if len(stripped_brand) >= 5 and stripped_brand != clean_slug and (len(stripped_brand) / len(clean_slug)) >= 0.5:
        if country.upper() == 'CA':
            candidates.extend([f"{stripped_brand}.ca", f"{stripped_brand}.com"])
        else:
            candidates.extend([f"{stripped_brand}.com", f"{stripped_brand}.org"])

    for candidate in candidates:
        test_url = f"https://www.{candidate}"
        try:
            resp = requests.get(test_url, headers=HEADERS, timeout=2.5, allow_redirects=True)
            if 200 <= resp.status_code < 400 and resp.text:
                if not is_parked_page(resp.text):
                    score = calculate_score(candidate, practice_name)
                    if score >= 70:
                        return {
                            'domain': candidate,
                            'url': f"https://{candidate}",
                            'source': 'Direct Practice Verification',
                            'confidence': 'High'
                        }
        except Exception:
            pass
    return None

# 2. Clearbit Autocomplete
def search_clearbit(practice_name: str):
    cleaned = clean_practice_name(practice_name)
    queries = [cleaned, practice_name]
    for q in queries:
        try:
            url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={urllib.parse.quote(q)}"
            resp = requests.get(url, headers=HEADERS, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data:
                        d = extract_clean_domain(item.get('domain'))
                        if d:
                            score = calculate_score(d, practice_name)
                            if score >= 45:
                                return {
                                    'domain': d,
                                    'url': f"https://{d}",
                                    'source': 'Clearbit Autocomplete',
                                    'confidence': 'High' if score >= 80 else 'Medium'
                                }
        except Exception:
            pass
    return None

# 3. Valentin Localized Google Search
def search_valentin_google(practice_name: str, country: str = 'US', city: str = '', state: str = ''):
    cleaned = clean_practice_name(practice_name)
    country = country.upper()
    gl = 'CA' if country == 'CA' else 'US'
    
    loc_str = f"{city}, {state}, Canada" if gl == 'CA' else f"{city}, {state}, USA"
    uule = generate_uule_v1(loc_str if city or state else ('Canada' if gl == 'CA' else 'United States'))

    candidate_domains = []
    # Autocomplete
    try:
        suggest_url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(cleaned)}&gl={gl}&hl=en&uule={urllib.parse.quote(uule)}"
        s_resp = requests.get(suggest_url, headers=HEADERS, timeout=3.5)
        if s_resp.status_code == 200:
            data = s_resp.json()
            if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                for item in data[1]:
                    d = extract_clean_domain(item)
                    if d and d not in candidate_domains:
                        candidate_domains.append(d)
    except Exception:
        pass

    for d in candidate_domains:
        score = calculate_score(d, practice_name, city or state)
        if score >= 60:
            return {
                'domain': d,
                'url': f"https://{d}",
                'source': f"Valentin Google ({country})",
                'confidence': 'High' if score >= 75 else 'Medium'
            }
    return None

# 4. DuckDuckGo Localized Search
def search_duckduckgo(practice_name: str, country: str = 'US', city: str = '', state: str = ''):
    cleaned = clean_practice_name(practice_name)
    country = country.upper()
    gl = 'CA' if country == 'CA' else 'US'
    kl = 'ca-en' if gl == 'CA' else 'us-en'
    
    queries = [
        f'"{cleaned}" official website',
        f'{cleaned} official website',
        f'{cleaned} practice {city}'
    ]

    candidate_domains = []
    for q in queries:
        if candidate_domains:
            break
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}&kl={kl}"
            resp = requests.get(ddg_url, headers=HEADERS, timeout=4)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.select('a.result__url, a.result__snippet, .results_links a'):
                    href = a.get('href', '')
                    if 'uddg=' in href:
                        try:
                            href = urllib.parse.parse_qs(urlparse(href).query).get('uddg', [''])[0]
                        except Exception:
                            pass
                    d = extract_clean_domain(href)
                    if d and d not in candidate_domains:
                        candidate_domains.append(d)
        except Exception:
            pass

    for d in candidate_domains:
        score = calculate_score(d, practice_name, city or state)
        if score >= 35:
            return {
                'domain': d,
                'url': f"https://{d}",
                'source': f"DuckDuckGo ({country})",
                'confidence': 'High' if score >= 70 else 'Medium'
            }
    return None

# Main Domain Search Cascade
def find_practice_domain(practice_name: str, country: str = 'US', city: str = '', state: str = ''):
    cleaned = clean_practice_name(practice_name)
    country = country.upper()

    # 1. Direct Probing
    res = probe_direct_domain(practice_name, country)
    
    # 2. Clearbit
    if not res:
        res = search_clearbit(practice_name)

    # 3. Valentin Google
    if not res:
        res = search_valentin_google(practice_name, country, city, state)

    # 4. DuckDuckGo
    if not res:
        res = search_duckduckgo(practice_name, country, city, state)

    if res:
        return {
            'Practice Name': practice_name,
            'Cleaned Name': cleaned,
            'Country': country,
            'Domain': res['domain'],
            'Website URL': res['url'],
            'Status': 'Found',
            'Confidence': res['confidence'],
            'Source': res['source']
        }

    return {
        'Practice Name': practice_name,
        'Cleaned Name': cleaned,
        'Country': country,
        'Domain': '',
        'Website URL': '',
        'Status': 'Not Found',
        'Confidence': 'None',
        'Source': 'N/A'
    }

def main():
    parser = argparse.ArgumentParser(description='Valentin.app Practice Domain Scraper')
    parser.add_argument('-i', '--input', help='Path to input CSV / Excel file')
    parser.add_argument('-o', '--output', default='output_practices_domains.csv', help='Path to output CSV file')
    parser.add_argument('-c', '--country', default='US', choices=['US', 'CA', 'ALL'], help='Target country (US or CA)')
    parser.add_argument('-s', '--single', help='Single practice name search')
    parser.add_argument('-w', '--workers', type=int, default=6, help='Number of concurrent worker threads')
    args = parser.parse_args()

    if args.single:
        print(f"🔍 Searching domain for: {args.single} (Country: {args.country})...")
        res = find_practice_domain(args.single, args.country)
        print("\nResult:")
        for k, v in res.items():
            print(f"  {k}: {v}")
        return

    if not args.input:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"❌ Error: File '{args.input}' not found!")
        sys.exit(1)

    print('===============================================================')
    print('  🏥 VALENTIN.APP PRACTICE & CLINIC DOMAIN FINDER (US & CA)')
    print('===============================================================')
    print(f"📁 Reading input:      {args.input}")
    print(f"💾 Output file:        {args.output}")
    print(f"🌎 Target Country:     {args.country}")
    print(f"⚡ Concurrent Threads: {args.workers}\n")

    if args.input.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(args.input)
    else:
        df = pd.read_csv(args.input)

    # Detect practice column
    col_name = None
    for c in df.columns:
        if re.search(r'^(practice_?name|practice|clinic_?name|clinic|doctor|hospital|company|name)$', str(c).strip(), re.I):
            col_name = c
            break
    if not col_name:
        col_name = df.columns[0]

    total_records = len(df)
    print(f"📊 Total Records: {total_records} | Using column: '{col_name}'\n")

    # Initialize output CSV with headers
    initial_cols = list(df.columns) + ['Cleaned Name', 'Domain', 'Website URL', 'Status', 'Confidence', 'Source']
    out_df_init = pd.DataFrame(columns=initial_cols)
    out_df_init.to_csv(args.output, index=False)

    results = [None] * total_records
    completed_count = 0
    found_count = 0

    def process_row(index, row):
        p_name = str(row[col_name]).strip()
        country = args.country
        if 'Country' in row and pd.notna(row['Country']):
            c_val = str(row['Country']).upper()
            if 'CA' in c_val or 'CANADA' in c_val:
                country = 'CA'
            elif 'US' in c_val or 'USA' in c_val:
                country = 'US'
                
        city = str(row['City']) if 'City' in row and pd.notna(row['City']) else ''
        state = str(row['State']) if 'State' in row and pd.notna(row['State']) else ''

        res = find_practice_domain(p_name, country, city, state)
        combined = row.to_dict()
        combined.update(res)
        return index, combined, res

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_row, idx, row): idx for idx, row in df.iterrows()}

        for future in as_completed(futures):
            idx, combined_row, res = future.result()
            results[idx] = combined_row
            completed_count += 1

            if res['Status'] == 'Found':
                found_count += 1
                sym = "\033[92m✔ FOUND\033[0m"
                dom_str = f"\033[96m{res['Domain']}\033[0m ({res['Source']})"
            else:
                sym = "\033[91m✖ NOT FOUND\033[0m"
                dom_str = ""

            p_display = str(combined_row.get(col_name, ''))[:30]
            pct = int((completed_count / total_records) * 100)
            print(f"[{completed_count}/{total_records}] ({pct}%) {sym} {p_display:<30} ➜ {dom_str}")

            # Append to output CSV file in real-time
            pd.DataFrame([combined_row]).to_csv(args.output, mode='a', header=False, index=False)

    print('\n===============================================================')
    print('🎉 BATCH PROCESSING COMPLETE!')
    print(f"📊 Processed: {completed_count}/{total_records}")
    print(f"✔ Found:     {found_count} ({int((found_count/total_records)*100)}%)")
    print(f"💾 Saved to:  {os.path.abspath(args.output)}")
    print('===============================================================')

if __name__ == '__main__':
    main()
