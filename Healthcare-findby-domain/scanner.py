import warnings
warnings.filterwarnings("ignore")

import re
import urllib3
import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

# Suppress insecure SSL warnings
urllib3.disable_warnings()

HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Upgrade-Insecure-Requests": "1"
    }
]


def fetch_site_content(raw_domain_or_url: str, timeout: int = 8) -> Dict[str, Any]:
    """
    Fetches HTML content and metadata for a given domain/URL.
    Tries HTTPS first, falls back to HTTP and non-SSL if needed.
    """
    cleaned = (raw_domain_or_url or "").strip()
    if not cleaned:
        return {
            "success": False,
            "status_code": 0,
            "status_msg": "Empty Domain",
            "html": "",
            "final_url": "",
            "page_title": "",
            "meta_description": "",
            "soup": None
        }

    # Normalize target URL
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        urls_to_try = [f"https://{cleaned}", f"http://{cleaned}"]
    else:
        urls_to_try = [cleaned]

    session = requests.Session()
    headers = HEADERS_POOL[0]

    last_error = ""
    for url in urls_to_try:
        try:
            resp = session.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                verify=True
            )
            if resp.status_code < 400:
                return _parse_response(resp)
            elif resp.status_code in [403, 401, 406]:
                # Try with secondary user agent or ignore status if html exists
                if len(resp.text) > 500:
                    return _parse_response(resp)
                last_error = f"HTTP {resp.status_code}"
            else:
                last_error = f"HTTP {resp.status_code}"
        except requests.exceptions.SSLError:
            # Fallback retry without SSL verification
            try:
                resp = session.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                    verify=False
                )
                return _parse_response(resp)
            except Exception as e:
                last_error = f"SSL/Connection Error: {str(e)[:40]}"
        except requests.exceptions.Timeout:
            last_error = "Connection Timeout"
        except requests.exceptions.ConnectionError:
            last_error = "DNS / Connection Refused"
        except Exception as e:
            last_error = f"Error: {str(e)[:40]}"

    return {
        "success": False,
        "status_code": 0,
        "status_msg": last_error or "Unreachable",
        "html": "",
        "final_url": urls_to_try[0],
        "page_title": "",
        "meta_description": "",
        "soup": None
    }


def _parse_response(resp: requests.Response) -> Dict[str, Any]:
    """Parses response HTML and extracts key elements."""
    html_content = resp.text or ""
    soup = None
    page_title = ""
    meta_description = ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract title
        if soup.title and soup.title.string:
            page_title = str(soup.title.string).strip()
        
        # Extract meta description & og:description
        desc_tags = soup.find_all("meta", attrs={"name": re.compile(r"description", re.I)})
        if not desc_tags:
            desc_tags = soup.find_all("meta", attrs={"property": re.compile(r"og:description", re.I)})
        
        if desc_tags:
            meta_description = desc_tags[0].get("content", "").strip()

    except Exception:
        pass

    return {
        "success": True,
        "status_code": resp.status_code,
        "status_msg": f"Live ({resp.status_code})",
        "html": html_content,
        "final_url": str(resp.url),
        "page_title": page_title[:200],
        "meta_description": meta_description[:300],
        "soup": soup
    }
