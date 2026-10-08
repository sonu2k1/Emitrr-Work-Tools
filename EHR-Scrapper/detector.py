"""
Deep Patient Portal & EHR Detection Engine
Performs deep multi-layered inspection of healthcare websites to identify EHR systems and patient portals.
"""

import warnings
warnings.filterwarnings("ignore")

import re
import urllib.parse
import urllib3
import requests
from bs4 import BeautifulSoup
from ehr_signatures import (
    EHR_SIGNATURES,
    PORTAL_INTENT_KEYWORDS,
    COMMON_PORTAL_PATHS,
    match_ehr_from_url,
    match_ehr_from_text
)
from healthcare_classifier import classify_healthcare

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0'
]

HEADERS = {
    'User-Agent': USER_AGENTS[0],
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="123", "Not:A-Brand";v="8", "Google Chrome";v="123"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Upgrade-Insecure-Requests': '1'
}

DEFAULT_TIMEOUT = 10

IGNORE_URL_PATTERNS = [
    r"/news(/|$)",
    r"/blog(/|$)",
    r"/privacy(-policy)?(/|$)",
    r"/terms(-of-use|-of-service)?(/|$)",
    r"/sitemap(/|\.xml)?$",
    r"/accessibility(/|$)",
    r"/disclaimer(/|$)",
    r"/cookie-policy(/|$)"
]

# Additional deep portal path patterns
EXPANDED_PORTAL_PATHS = [
    "/patient-portal",
    "/patient-portal/",
    "/portal",
    "/portal/",
    "/patient-login",
    "/patients/patient-portal",
    "/patients/portal",
    "/patient-resources/patient-portal",
    "/for-patients/patient-portal",
    "/patient-center/patient-portal",
    "/patients",
    "/patient-info",
    "/patient-resources",
    "/patient-center",
    "/patient-forms",
    "/for-patients",
    "/online-services",
    "/mychart",
    "/healow",
    "/login",
    "/pay-my-bill",
    "/bill-pay"
]


def clean_domain(raw_domain: str) -> str:
    """Normalizes raw domain input string."""
    if not raw_domain or not isinstance(raw_domain, str):
        return ""
    
    cleaned = raw_domain.strip().strip('"\'').strip()
    cleaned = re.sub(r'^https?://', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^www\.', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.split('/')[0].split('?')[0].split('#')[0]
    return cleaned.strip().lower()


def should_ignore_url(url: str) -> bool:
    """Filters out news, sitemaps, blogs, and legal pages."""
    url_lower = url.lower()
    for pattern in IGNORE_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False


def extract_onclick_url(tag_elem) -> str:
    """Extracts URL from onclick handler if present."""
    onclick = tag_elem.get('onclick', '')
    if onclick:
        # Match window.open('...'), location.href='...', window.location='...'
        m = re.search(r"(?:window\.open|location\.href|window\.location)\s*\(?['\"]([^'\"]+)['\"]", onclick)
        if m:
            return m.group(1)
    
    # Check data-href, data-url, data-link
    for attr in ['data-href', 'data-url', 'data-link', 'data-target']:
        val = tag_elem.get(attr)
        if val and isinstance(val, str) and (val.startswith('http') or val.startswith('/')):
            return val
            
    return ""


class PatientPortalDetector:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, crawl_subpages: bool = True):
        self.timeout = timeout
        self.crawl_subpages = crawl_subpages
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_page(self, url: str, timeout: int = None):
        """Fetches page content with fast targeted fallback strategies."""
        req_timeout = timeout or self.timeout
        if url.startswith('http://') or url.startswith('https://'):
            try:
                resp = self.session.get(
                    url,
                    timeout=req_timeout,
                    verify=False,
                    allow_redirects=True
                )
                if resp.status_code in [200, 301, 302, 307, 308] and resp.text:
                    return resp.text, resp.url
            except Exception:
                pass

        parsed = urllib.parse.urlparse(url)
        base_netloc = parsed.netloc or url.replace('https://', '').replace('http://', '').split('/')[0]
        clean_d = clean_domain(base_netloc)
        path = parsed.path or ""

        candidates = [
            f"https://www.{clean_d}{path}",
            f"https://{clean_d}{path}",
            f"http://www.{clean_d}{path}"
        ]

        for target in candidates:
            if target == url:
                continue
            try:
                resp = self.session.get(
                    target,
                    timeout=min(req_timeout, 6),
                    verify=False,
                    allow_redirects=True
                )
                if resp.status_code in [200, 301, 302, 307, 308] and resp.text:
                    return resp.text, resp.url
            except Exception:
                continue

        return None, None

    def scan_raw_html_for_ehr(self, html: str):
        """
        Extracts URLs directly from HTML/JS text using regex (crucial for Single Page Apps & JS widgets).
        """
        urls_in_html = re.findall(r'https?://[^\s\"\'<>\)\(\]\}\;\,]+', html)
        for url in urls_in_html:
            clean_u = url.rstrip('.,;\\\'"')
            if should_ignore_url(clean_u):
                continue
            match = match_ehr_from_url(clean_u)
            if match:
                return {
                    "ehr_name": match["name"],
                    "portal_url": clean_u,
                    "anchor_text": "Embedded Page / Script Link",
                    "confidence": "High",
                    "detection_source": f"JS/HTML Payload ({match['name']})",
                    "category": match["category"],
                    "priority": 9
                }
        return None

    def scan_soup(self, soup: BeautifulSoup, base_url: str, domain: str):
        """
        Deep scans parsed DOM for EHR/Portal links, buttons, iframes, and widgets.
        """
        direct_ehr_matches = []
        candidate_portal_links = []
        parsed_base = urllib.parse.urlparse(base_url)
        clean_base_domain = clean_domain(parsed_base.netloc or domain)

        # 1. Inspect all <a> tags and clickable elements
        elements_to_check = soup.find_all(['a', 'button', 'div', 'span'])
        
        for elem in elements_to_check:
            href = elem.get('href', '').strip()
            if not href:
                href = extract_onclick_url(elem)

            if not href or href.startswith(('javascript:;', 'mailto:', 'tel:', '#')):
                continue

            full_url = urllib.parse.urljoin(base_url, href)
            if should_ignore_url(full_url):
                continue

            link_text = (elem.get_text() or '').strip()
            aria_label = (elem.get('aria-label') or '').strip()
            title = (elem.get('title') or '').strip()
            class_str = " ".join(elem.get('class', [])) if isinstance(elem.get('class'), list) else str(elem.get('class', ''))
            id_str = elem.get('id', '')
            combined_text = f"{link_text} {aria_label} {title} {class_str} {id_str}".strip()

            # Direct EHR URL match
            ehr_url_match = match_ehr_from_url(full_url)
            if ehr_url_match:
                direct_ehr_matches.append({
                    "ehr_name": ehr_url_match["name"],
                    "portal_url": full_url,
                    "anchor_text": link_text or ehr_url_match["name"],
                    "confidence": "High",
                    "detection_source": f"Direct URL ({ehr_url_match['name']})",
                    "category": ehr_url_match["category"],
                    "priority": 10
                })
                continue

            # Anchor text / aria / class match for EHR vendor
            ehr_text_match = match_ehr_from_text(combined_text)
            if ehr_text_match:
                direct_ehr_matches.append({
                    "ehr_name": ehr_text_match["name"],
                    "portal_url": full_url,
                    "anchor_text": link_text or ehr_text_match["name"],
                    "confidence": "High",
                    "detection_source": f"Anchor Text Match ({ehr_text_match['name']})",
                    "category": ehr_text_match["category"],
                    "priority": 8
                })
                continue

            # General patient portal intent match
            is_portal_intent = any(re.search(kw, combined_text, re.IGNORECASE) for kw in PORTAL_INTENT_KEYWORDS)
            href_has_portal_kw = any(kw in full_url.lower() for kw in [
                "/patient-portal", "/patient-login", "/portal", "mychart", "healow", "onpatient",
                "mycslink", "athenahealth", "ecwcloud", "mycw", "patientfusion"
            ])

            if is_portal_intent or href_has_portal_kw:
                parsed_target = urllib.parse.urlparse(full_url)
                target_domain = clean_domain(parsed_target.netloc)

                is_subdomain = target_domain.endswith(f".{clean_base_domain}") and target_domain != clean_base_domain
                is_external = target_domain and (target_domain != clean_base_domain) and not is_subdomain

                candidate_portal_links.append({
                    "portal_url": full_url,
                    "anchor_text": link_text or "Patient Portal",
                    "is_external": is_external,
                    "is_subdomain": is_subdomain,
                    "target_domain": target_domain
                })

        # 2. Check iframes (embedded portals/widgets)
        for iframe in soup.find_all('iframe', src=True):
            src = iframe.get('src', '').strip()
            if not src:
                continue
            full_src = urllib.parse.urljoin(base_url, src)
            ehr_match = match_ehr_from_url(full_src)
            if ehr_match:
                direct_ehr_matches.append({
                    "ehr_name": ehr_match["name"],
                    "portal_url": full_src,
                    "anchor_text": "Embedded iFrame Widget",
                    "confidence": "High",
                    "detection_source": f"Embedded iFrame ({ehr_match['name']})",
                    "category": ehr_match["category"],
                    "priority": 9
                })

        # Sort direct matches by priority
        direct_ehr_matches.sort(key=lambda x: x.get("priority", 0), reverse=True)
        return direct_ehr_matches, candidate_portal_links

    def detect_for_domain(self, domain_input: str) -> dict:
        """
        Deep multi-step entrypoint for single domain detection.
        """
        raw_input = str(domain_input or "").strip()
        cleaned_dom = clean_domain(raw_input)

        result = {
            "domain": cleaned_dom,
            "input_provided": raw_input,
            "is_healthcare": "Unknown",
            "website_url": "",
            "ehr_name": "Not Found",
            "ehr_category": "",
            "portal_url": "",
            "status": "Not Found",
            "confidence": "None",
            "detection_method": "",
            "portal_text": ""
        }

        if not cleaned_dom:
            result["status"] = "Invalid Domain"
            return result

        # Step 0: Probe Common Healthcare Portal Subdomains
        portal_subdomains = [
            f"https://mychart.{cleaned_dom}",
            f"https://portal.{cleaned_dom}",
            f"https://patientportal.{cleaned_dom}",
            f"https://mycslink.{cleaned_dom}",
            f"https://patients.{cleaned_dom}",
            f"https://myhealth.{cleaned_dom}"
        ]
        for sub_url in portal_subdomains:
            try:
                sub_r = self.session.get(sub_url, timeout=3.5, verify=False, allow_redirects=True)
                if sub_r.status_code == 200:
                    ehr_url_match = match_ehr_from_url(sub_r.url) or match_ehr_from_url(sub_url)
                    if ehr_url_match:
                        result["is_healthcare"] = "Yes"
                        result["ehr_name"] = ehr_url_match["name"]
                        result["ehr_category"] = ehr_url_match["category"]
                        result["portal_url"] = sub_r.url
                        result["status"] = "Found"
                        result["confidence"] = "High"
                        result["detection_method"] = f"Direct Subdomain ({sub_url})"
                        result["portal_text"] = "Portal Subdomain"
                        result["website_url"] = f"https://{cleaned_dom}"
                        return result
                    
                    # If subdomain page loaded, check its HTML content for EHR
                    sub_soup = BeautifulSoup(sub_r.text, 'html.parser')
                    sub_direct, _ = self.scan_soup(sub_soup, sub_r.url, cleaned_dom)
                    if sub_direct:
                        best = sub_direct[0]
                        result["is_healthcare"] = "Yes"
                        result["ehr_name"] = best["ehr_name"]
                        result["ehr_category"] = best.get("category", "")
                        result["portal_url"] = best["portal_url"]
                        result["status"] = "Found"
                        result["confidence"] = "High"
                        result["detection_method"] = f"Subdomain Scan ({sub_url}) -> {best['detection_source']}"
                        result["portal_text"] = best["anchor_text"]
                        result["website_url"] = f"https://{cleaned_dom}"
                        return result
            except Exception:
                pass

        # Step 1: Fetch Homepage
        target_url = f"https://{cleaned_dom}"
        html, final_url = self.fetch_page(target_url)

        if not html:
            hc_check = classify_healthcare(cleaned_dom)
            if not hc_check["is_healthcare"]:
                result["is_healthcare"] = "No"
                result["ehr_name"] = "Not related to health care or clinics"
                result["ehr_category"] = "Non-Healthcare"
                result["status"] = "Not related to health care or clinics"
                result["confidence"] = "High"
                result["detection_method"] = f"Unreachable ({hc_check['reason']})"
            else:
                result["is_healthcare"] = "Yes"
                result["status"] = "Site Unreachable"
                result["detection_method"] = "Connection Failed"
            return result

        result["website_url"] = final_url or target_url
        soup = BeautifulSoup(html, 'html.parser')

        # Step 2: Scan Homepage (Anchors, Buttons, Iframes)
        direct_matches, candidate_links = self.scan_soup(soup, result["website_url"], cleaned_dom)

        if direct_matches:
            best = direct_matches[0]
            result["is_healthcare"] = "Yes"
            result["ehr_name"] = best["ehr_name"]
            result["ehr_category"] = best.get("category", "")
            result["portal_url"] = best["portal_url"]
            result["status"] = "Found"
            result["confidence"] = best["confidence"]
            result["detection_method"] = best["detection_source"]
            result["portal_text"] = best["anchor_text"]
            return result

        # Step 2b: Scan Raw HTML for SPA/JS embedded URLs
        raw_match = self.scan_raw_html_for_ehr(html)
        if raw_match:
            result["is_healthcare"] = "Yes"
            result["ehr_name"] = raw_match["ehr_name"]
            result["ehr_category"] = raw_match.get("category", "")
            result["portal_url"] = raw_match["portal_url"]
            result["status"] = "Found"
            result["confidence"] = raw_match["confidence"]
            result["detection_method"] = raw_match["detection_source"]
            result["portal_text"] = raw_match["anchor_text"]
            return result

        # Step 3: Deep Subpage Crawling
        subpages_to_crawl = []
        for cand in candidate_links:
            p_url = cand["portal_url"]
            if cand.get("is_subdomain") or "portal" in p_url.lower() or "mychart" in p_url.lower() or "patient" in p_url.lower():
                subpages_to_crawl.append(p_url)
            elif not cand.get("is_external"):
                subpages_to_crawl.append(p_url)

        # Fallback to expanded common portal paths if nothing identified
        if not subpages_to_crawl and self.crawl_subpages:
            for path in EXPANDED_PORTAL_PATHS[:8]:
                subpages_to_crawl.append(urllib.parse.urljoin(result["website_url"], path))

        seen_crawls = set()
        for sub_url in subpages_to_crawl[:6]:  # Deep crawl top 6 candidate subpages
            if sub_url in seen_crawls or sub_url == result["website_url"]:
                continue
            seen_crawls.add(sub_url)

            sub_html, sub_final = self.fetch_page(sub_url)
            if not sub_html:
                continue

            sub_soup = BeautifulSoup(sub_html, 'html.parser')
            sub_direct, sub_candidates = self.scan_soup(sub_soup, sub_final or sub_url, cleaned_dom)

            if sub_direct:
                best = sub_direct[0]
                result["is_healthcare"] = "Yes"
                result["ehr_name"] = best["ehr_name"]
                result["ehr_category"] = best.get("category", "")
                result["portal_url"] = best["portal_url"]
                result["status"] = "Found"
                result["confidence"] = "High"
                result["detection_method"] = f"Subpage Crawl ({sub_url}) -> {best['detection_source']}"
                result["portal_text"] = best["anchor_text"]
                return result

            # Check raw html of subpage
            sub_raw_match = self.scan_raw_html_for_ehr(sub_html)
            if sub_raw_match:
                result["is_healthcare"] = "Yes"
                result["ehr_name"] = sub_raw_match["ehr_name"]
                result["ehr_category"] = sub_raw_match.get("category", "")
                result["portal_url"] = sub_raw_match["portal_url"]
                result["status"] = "Found"
                result["confidence"] = "High"
                result["detection_method"] = f"Subpage JS Payload ({sub_url}) -> {sub_raw_match['detection_source']}"
                result["portal_text"] = sub_raw_match["anchor_text"]
                return result

            # Check text on subpage
            sub_page_text = sub_soup.get_text(separator=' ', strip=True)
            text_ehr_match = match_ehr_from_text(sub_page_text)
            if text_ehr_match:
                result["is_healthcare"] = "Yes"
                result["ehr_name"] = text_ehr_match["name"]
                result["ehr_category"] = text_ehr_match.get("category", "")
                result["portal_url"] = sub_final or sub_url
                result["status"] = "Found"
                result["confidence"] = "Medium"
                result["detection_method"] = f"Subpage Content Match ({text_ehr_match['matched_pattern']})"
                return result

        # Step 4: Fallback to candidate portal link if generic/custom portal found
        if candidate_links:
            top_cand = candidate_links[0]
            result["is_healthcare"] = "Yes"
            result["ehr_name"] = "Custom / Practice Portal"
            result["portal_url"] = top_cand["portal_url"]
            result["status"] = "Generic Portal Found"
            result["confidence"] = "Medium"
            result["detection_method"] = f"Anchor Keyword: '{top_cand['anchor_text']}'"
            result["portal_text"] = top_cand["anchor_text"]
            return result

        # Nothing found - check whether the site is healthcare/clinic related
        hc_check = classify_healthcare(cleaned_dom, html=html, soup=soup)
        if not hc_check["is_healthcare"]:
            result["is_healthcare"] = "No"
            result["ehr_name"] = "Not related to health care or clinics"
            result["ehr_category"] = "Non-Healthcare"
            result["status"] = "Not related to health care or clinics"
            result["confidence"] = "High"
            result["detection_method"] = f"Non-Healthcare Detected ({hc_check['reason']})"
        else:
            result["is_healthcare"] = "Yes"
            result["status"] = "No Portal Detected"
            result["detection_method"] = "Healthcare Practice Verified (Homepage & Subpages Scanned)"
        return result
