#!/usr/bin/env python3
"""
ModMed FHIR Endpoint Scraper
Scrapes Company Name, Address, FHIR URL, and Health Care ID from ModMed FHIR Endpoint Display.
"""

import sys
import argparse
import requests
import pandas as pd

# API Endpoints configuration
API_ENDPOINTS = {
    'gastro': 'https://public-api.gastro.prod.fhir.ema-api.com/fhir/r4/Endpoint?_include=Endpoint:managingOrganization&connection-type=hl7-fhir-rest&_count=200',
    'ema': 'https://public-api.mmi.prod.fhir.ema-api.com/fhir/r4/Endpoint?_include=Endpoint:managingOrganization&connection-type=hl7-fhir-rest&_count=200'
}

def format_address(address_list):
    """Formats FHIR address objects into a single clean address string."""
    if not address_list:
        return ""
    
    formatted_addresses = []
    for addr in address_list:
        lines = ", ".join(addr.get("line", []))
        city = addr.get("city", "")
        state = addr.get("state", "")
        postal_code = addr.get("postalCode", "")
        country = addr.get("country", "")
        
        state_zip = f"{state} {postal_code}".strip()
        parts = [p for p in [lines, city, state_zip, country] if p]
        if parts:
            formatted_addresses.append(", ".join(parts))
            
    return " | ".join(formatted_addresses)

def fetch_fhir_records(api_key='gastro'):
    """Fetches and parses FHIR Endpoints & Organizations."""
    url = API_ENDPOINTS.get(api_key, API_ENDPOINTS['gastro'])
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/fhir+json, application/json'
    }
    
    print(f"Fetching data from {api_key.upper()} FHIR API endpoint...")
    
    view_records = []
    entries_map = {}
    organizations = {}

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        entries = data.get('entry', [])
        for entry in entries:
            res = entry.get('resource', {})
            res_type = res.get('resourceType')
            
            if res_type == 'Endpoint':
                address = res.get('address')
                status = res.get('status')
                if isinstance(address, str) and status == 'active':
                    item = {
                        'Company Name': res.get('name', ''),
                        'Address': '',
                        'FHIR URL': address,
                        'Health Care ID': ''
                    }
                    
                    # Extract OID / Health Care ID from Endpoint ID prefix (e.g. 2.100)
                    ep_id = res.get('id', '')
                    parts = ep_id.split('.')
                    if len(parts) >= 2:
                        item['Health Care ID'] = f"{parts[0]}.{parts[1]}"
                    
                    view_records.append(item)
                    
                    # Map managing Organization reference
                    managing_org = res.get('managingOrganization', {}).get('reference', '')
                    if managing_org:
                        org_ref_id = managing_org.split('/')[-1].strip()
                        if org_ref_id and not org_ref_id.endswith('.null'):
                            entries_map[org_ref_id] = item

            elif res_type == 'Organization':
                if res.get('active'):
                    org_id = res.get('id', '').strip()
                    if org_id and not org_id.endswith('.null'):
                        organizations[org_id] = res
                        
        # Check for next page in FHIR pagination
        next_url = None
        for link in data.get('link', []):
            if link.get('relation') == 'next':
                next_url = link.get('url')
                break
        url = next_url

    # Enrich endpoint items with Organization Name & Address
    for org_id, org_res in organizations.items():
        item = entries_map.get(org_id)
        if item:
            item['Health Care ID'] = org_id
            if org_res.get('name'):
                item['Company Name'] = org_res.get('name').strip()
            if org_res.get('address'):
                item['Address'] = format_address(org_res.get('address'))

    return view_records

def main():
    parser = argparse.ArgumentParser(description="ModMed FHIR Endpoint Scraper")
    parser.add_argument('--api', choices=['gastro', 'ema'], default='gastro', help="API to scrape (default: gastro - 897 records)")
    parser.add_argument('--output-csv', default='modmed_fhir_endpoints.csv', help="Output CSV filename")
    parser.add_argument('--output-xlsx', default='modmed_fhir_endpoints.xlsx', help="Output Excel filename")
    args = parser.parse_args()

    records = fetch_fhir_records(args.api)
    print(f"\nSuccessfully scraped {len(records)} records!")
    
    df = pd.DataFrame(records)
    # Ensure correct column ordering
    cols = ['Company Name', 'Address', 'FHIR URL', 'Health Care ID']
    df = df[cols]

    df.to_csv(args.output_csv, index=False)
    print(f"Saved CSV file to: {args.output_csv}")

    df.to_excel(args.output_xlsx, index=False, engine='openpyxl')
    print(f"Saved Excel file to: {args.output_xlsx}")

if __name__ == '__main__':
    main()
