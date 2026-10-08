import re
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional, Callable
from playwright.sync_api import sync_playwright

from master_manager import clean_practice_name, clean_official_website, normalize_domain, is_valid_practice_domain
from domain_resolver import DomainResolver

# Core Healthcare Categories targeted by Weave
WEAVE_HEALTHCARE_VERTICALS = {
    "dentistry": "Dental & Oral Healthcare",
    "optometry": "Optometry & Eyecare",
    "ophthalmology": "Ophthalmology & Eye Surgery",
    "veterinary": "Veterinary & Animal Health",
    "physical-therapy": "Physical Therapy & Rehab",
    "plastic-surgery": "Plastic Surgery & Aesthetics",
    "medical-spas": "Medical Spas & Dermatology",
    "podiatry": "Podiatry & Foot Specialists",
    "mental-health": "Mental & Behavioral Health",
    "audiology": "Audiology & Hearing",
    "orthodontics": "Orthodontics",
    "primary-care": "Primary Care & Family Medicine",
    "medical": "General Medical Practice"
}

# Curated high-confidence customer case studies directly featured by Weave
CURATED_WEAVE_CASE_STUDIES = [
    {
        "name": "Let's Go Dental",
        "location": "Florida",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Case Study - Call Intelligence"
    },
    {
        "name": "Enclave Vision Associates",
        "location": "Houston, TX",
        "category": "Optometry & Eyecare",
        "source": "Weave Case Study - Patient Communication"
    },
    {
        "name": "Animal Hospital of Lake Villa",
        "location": "Lake Villa, IL",
        "category": "Veterinary & Animal Health",
        "source": "Weave Case Study - Practice Management"
    },
    {
        "name": "Riverfront Dental",
        "location": "Salem, OR",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Case Study - Patient Experience"
    },
    {
        "name": "Children's Clear Vision",
        "location": "Round Rock, TX",
        "category": "Optometry & Eyecare",
        "source": "Weave Case Study - Payment Processing"
    },
    {
        "name": "Cercek Dental",
        "location": "Reno, NV",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Case Study - Practice Growth"
    },
    {
        "name": "Berdy Dental Group",
        "location": "Jacksonville, FL",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Case Study - Patient Communication"
    },
    {
        "name": "Gerlecz Dentistry",
        "location": "Panama City, FL",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Case Study - Disaster Recovery"
    },
    {
        "name": "Palisades Dentists",
        "location": "Pacific Palisades, CA",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Customer Story"
    },
    {
        "name": "Align Therapy",
        "location": "Lehi, UT",
        "category": "Physical Therapy & Rehab",
        "source": "Weave Customer Spotlight - David Butler"
    },
    {
        "name": "Periodontal & Implant Associates",
        "location": "Pelham, AL",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Customer Spotlight - Dr. Jennifer Doobrow"
    },
    {
        "name": "Beaches Facial Plastic & Nasal Surgery",
        "location": "Jacksonville Beach, FL",
        "category": "Plastic Surgery & Aesthetics",
        "source": "Weave Customer Spotlight - Scott Trimas"
    },
    {
        "name": "Marion Plastic Surgery & Medical Spa",
        "location": "Dallas, TX",
        "category": "Plastic Surgery & Aesthetics",
        "source": "Weave Customer Spotlight - Dr. Michael Marion"
    },
    {
        "name": "Whole Mind Mental Health Clinic",
        "location": "Salt Lake City, UT",
        "category": "Mental & Behavioral Health",
        "source": "Weave Customer Spotlight - Dr. Tom Rayner MD"
    },
    {
        "name": "Beach Dental Center",
        "location": "San Diego, CA",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Customer Spotlight - Dr. Dan Barton"
    },
    {
        "name": "Riverside Pet Care",
        "location": "Ludlow, MA",
        "category": "Veterinary & Animal Health",
        "source": "Weave Customer Spotlight - Dr. Ian Kolbaba"
    },
    {
        "name": "The Eye Vets",
        "location": "Riverton, UT",
        "category": "Veterinary & Animal Health",
        "source": "Weave Customer Spotlight - Dr. Ben Bergstrom"
    },
    {
        "name": "Philadelphia Dental Associates",
        "location": "Philadelphia, PA",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Verified Customer Review"
    },
    {
        "name": "Dana Point Smiles",
        "location": "Dana Point, CA",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Verified Customer Review"
    },
    {
        "name": "Admire Your Smile",
        "location": "Jefferson City, MO",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Customer Review - Dr. Corey Mack"
    },
    {
        "name": "Aliso Kids Dental",
        "location": "Aliso Viejo, CA",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Customer Review - Pediatric Dental"
    },
    {
        "name": "Olive Family Dentistry",
        "location": "Olive Branch, MS",
        "category": "Dental & Oral Healthcare",
        "source": "Weave Customer Review"
    },
    {
        "name": "Eye Docs",
        "location": "US",
        "category": "Optometry & Eyecare",
        "source": "Weave Customer Review"
    }
]

class WeaveSiteScraper:
    def __init__(
        self,
        headless: bool = True,
        existing_domains: Optional[Set[str]] = None,
        existing_names: Optional[Set[str]] = None
    ):
        self.headless = headless
        self.existing_domains = existing_domains if existing_domains is not None else set()
        self.existing_names = existing_names if existing_names is not None else set()
        self.session_domains: Set[str] = set()
        self.session_names: Set[str] = set()
        self.resolver = DomainResolver(headless=headless)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def is_new(self, name: str, domain: str) -> bool:
        if not domain or not is_valid_practice_domain(domain):
            return False
        dom = normalize_domain(domain)
        if not dom or dom in self.existing_domains or dom in self.session_domains:
            return False
        norm_name = re.sub(r"[^a-zA-Z0-9]", "", name.lower()) if name else ""
        if norm_name and (norm_name in self.existing_names or norm_name in self.session_names):
            return False
        return True

    def register(self, name: str, domain: str):
        dom = normalize_domain(domain)
        if dom:
            self.session_domains.add(dom)
        norm_name = re.sub(r"[^a-zA-Z0-9]", "", name.lower()) if name else ""
        if norm_name:
            self.session_names.add(norm_name)

    def scrape_all_weave_sources(
        self,
        progress_callback: Optional[Callable[[any], None]] = None
    ) -> List[Dict[str, str]]:
        extracted_practices: List[Dict[str, str]] = []
        seen_practice_names: Set[str] = set()

        def add_raw(name: str, loc: str, cat: str, src: str):
            cname = clean_practice_name(name)
            if not cname or len(cname) < 3:
                return
            n_key = re.sub(r"[^a-zA-Z0-9]", "", cname.lower())
            if n_key and n_key not in seen_practice_names:
                seen_practice_names.add(n_key)
                extracted_practices.append({
                    "name": cname,
                    "location": loc,
                    "category": cat,
                    "source": src
                })

        # 1. Add Core Case Studies
        for cs in CURATED_WEAVE_CASE_STUDIES:
            add_raw(cs["name"], cs["location"], cs["category"], cs["source"])

        if progress_callback:
            progress_callback({
                "type": "log",
                "message": f"Loaded [bold green]{len(extracted_practices)}[/] core case studies & customer stories from Weave..."
            })

        # 2. Extract from Senja Verified Customer Reviews
        if progress_callback:
            progress_callback({
                "type": "log",
                "message": "Connecting to [bold cyan]Weave Senja Customer Feed[/] to extract verified clinic reviews..."
            })

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                page.goto("https://senja.io/p/weave/qk15kH", wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(2000)

                body_text = page.inner_text("body")
                lines = [l.strip() for l in body_text.split("\n") if l.strip()]

                for line in lines:
                    if len(line) > 3 and len(line) < 60:
                        is_health = any(w in line.lower() for w in [
                            "dental", "dentist", "smile", "ortho", "vision", "eye", "care",
                            "clinic", "health", "pet", "animal", "vet", "therapy", "surgery",
                            "chiro", "pediatric", "family", "medical", "spa", "doctor", "dr."
                        ])
                        if is_health and not any(ex in line.lower() for ex in ["weave", "review", "testimonial", "demo", "cookie", "learn more"]):
                            cat = "Healthcare Practice"
                            ll = line.lower()
                            if "dental" in ll or "smile" in ll or "ortho" in ll or "teeth" in ll:
                                cat = "Dental & Oral Healthcare"
                            elif "vision" in ll or "eye" in ll or "optom" in ll:
                                cat = "Optometry & Eyecare"
                            elif "vet" in ll or "pet" in ll or "animal" in ll:
                                cat = "Veterinary & Animal Health"
                            elif "therapy" in ll or "rehab" in ll:
                                cat = "Physical Therapy & Rehab"
                            elif "plastic" in ll or "cosmetic" in ll or "spa" in ll:
                                cat = "Plastic Surgery & Aesthetics"
                            elif "mental" in ll or "psych" in ll:
                                cat = "Mental & Behavioral Health"
                            
                            add_raw(line, "US", cat, "Weave Senja Verified Review")

                browser.close()
        except Exception as e:
            if progress_callback:
                progress_callback({
                    "type": "log",
                    "message": f"[yellow]Senja parser notice:[/] {str(e)[:80]}"
                })

        # 3. Extract from Industry Pages
        if progress_callback:
            progress_callback({
                "type": "log",
                "message": f"Scanning [bold cyan]{len(WEAVE_HEALTHCARE_VERTICALS)}[/] Weave Industry Landing Pages for customer quotes..."
            })

        for slug, cat_name in WEAVE_HEALTHCARE_VERTICALS.items():
            url = f"https://www.getweave.com/industry/{slug}/"
            try:
                r = requests.get(url, headers=self.headers, timeout=8)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    for q in soup.find_all(["blockquote", "cite"]):
                        txt = q.get_text(strip=True)
                        m = re.search(r"—?\s*([A-Za-z0-9\s\,\.\'\-]{4,50})", txt)
                        if m:
                            p_name = m.group(1).strip()
                            if any(w in p_name.lower() for w in ["dr.", "dental", "clinic", "center", "care", "eye", "vet", "associates"]):
                                add_raw(p_name, "US", cat_name, f"Weave Industry Spotlight - {cat_name}")
            except Exception:
                pass

        if progress_callback:
            progress_callback({
                "type": "log",
                "message": f"Total candidate Weave healthcare customers identified: [bold green]{len(extracted_practices)}[/]"
            })

        # 4. Resolve Official Websites & Domains
        self.resolver.start_browser()
        verified_records: List[Dict[str, str]] = []

        try:
            for idx, item in enumerate(extracted_practices, start=1):
                name = item["name"]
                loc = item["location"]
                cat = item["category"]
                src = item["source"]

                if progress_callback:
                    progress_callback({
                        "type": "resolving",
                        "current": idx,
                        "total": len(extracted_practices),
                        "practice": name,
                        "location": loc
                    })

                resolved_url = self.resolver.resolve(name, loc)
                if resolved_url and is_valid_practice_domain(resolved_url):
                    clean_site = clean_official_website(resolved_url)
                    dom = normalize_domain(clean_site)

                    if self.is_new(name, dom):
                        self.register(name, dom)
                        rec = {
                            "practice_name": name,
                            "official_website": clean_site,
                            "category": cat,
                            "location": loc,
                            "source": src
                        }
                        verified_records.append(rec)
                        if progress_callback:
                            progress_callback({"type": "record", "data": rec})
                
                time.sleep(0.3)
        finally:
            self.resolver.close_browser()

        return verified_records
