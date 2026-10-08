import warnings
warnings.filterwarnings("ignore")
import re
from typing import Dict, Any, Optional, Tuple, List

# Generic/role-based email mailboxes that do not belong to an individual
ROLE_BASED_PREFIXES = {
    "info", "contact", "admin", "administrator", "support", "help", "billing", 
    "frontdesk", "front_desk", "reception", "office", "officeadmin", "appointments", 
    "scheduling", "schedule", "care", "service", "customerservice", "sales", 
    "marketing", "team", "hello", "hi", "inquiries", "inquiry", "general", 
    "staff", "careers", "jobs", "accounting", "feedback", "manager", "operations",
    "patientcare", "patients", "records", "insurance", "intake"
}

# Honorifics and titles to strip or extract
HONORIFICS = {"dr", "doctor", "prof", "professor", "mr", "mrs", "ms", "dentist"}

# Comprehensive Healthcare and Corporate Job Titles
HEALTHCARE_TITLES = [
    # ABA & Behavioral Health
    "Board Certified Behavior Analyst", "Behavior Analyst", "BCBA-D", "BCBA", 
    "Registered Behavior Technician", "RBT", "Behavior Therapist", "ABA Therapist", 
    "Clinical Supervisor", "Behavior Interventionist", "Behavior Consultant",
    
    # Dental & Specialty
    "General Dentist", "Cosmetic Dentist", "Family Dentist", "Pediatric Dentist", 
    "Orthodontist", "Periodontist", "Endodontist", "Oral and Maxillofacial Surgeon", 
    "Oral Surgeon", "Prosthodontist", "Implantologist", "Dentist", "Dental Surgeon",
    
    # Medical Specialists
    "Primary Care Physician", "Family Physician", "Internal Medicine Physician", 
    "Pediatrician", "Chiropractor", "Optometrist", "Ophthalmologist", "Dermatologist", 
    "Cardiologist", "Neurologist", "Oncologist", "Gynecologist", "Obstetrician", 
    "OB-GYN", "OBGYN", "Orthopedic Surgeon", "Plastic Surgeon", "Anesthesiologist", 
    "Psychiatrist", "Psychologist", "Physical Therapist", "Occupational Therapist", 
    "Speech-Language Pathologist", "Audiologist", "Podiatrist", "Physician", "Doctor", "Surgeon",
    
    # Clinical Leadership
    "Medical Director", "Clinical Director", "Dental Director", "Chief Medical Officer", 
    "Chief Dental Officer", "Chief Clinical Officer", "Director of Nursing", 
    "Director of Operations", "Director of Clinical Operations", "Managing Clinical Director",
    
    # Practice Management & Admin
    "Practice Manager", "Office Manager", "Practice Administrator", "Dental Office Manager", 
    "Clinic Manager", "Healthcare Administrator", "Practice Owner", "Clinic Director", 
    "Director of Patient Experience", "Office Administrator", "Operations Manager", 
    "Operations Director", "Regional Manager", "General Manager",
    
    # Nursing & Support Providers
    "Nurse Practitioner", "Family Nurse Practitioner", "Physician Assistant", 
    "Registered Nurse", "Clinical Nurse Specialist", "Registered Dental Hygienist", 
    "Dental Hygienist", "Certified Dental Assistant", "Dental Assistant", "Lead Dental Assistant", 
    "Medical Assistant", "Surgical Assistant", "Phlebotomist",
    
    # Front Office & Coordinators
    "Treatment Coordinator", "Patient Care Coordinator", "Financial Coordinator", 
    "Insurance Coordinator", "Billing Specialist", "Billing Manager", "Patient Coordinator", 
    "Front Desk Coordinator", "Receptionist", "Intake Specialist", "Scheduling Coordinator"
]

CORPORATE_TITLES = [
    # C-Suite / Executive
    "Chief Executive Officer", "CEO", "President", "Founder", "Co-Founder", "Owner", 
    "Co-Owner", "Managing Partner", "Partner", "Principal", "Chief Operating Officer", 
    "COO", "Chief Financial Officer", "CFO", "Chief Technology Officer", "CTO", 
    "Chief Information Officer", "CIO", "Chief Revenue Officer", "CRO", "Chief Marketing Officer", "CMO",
    
    # VP / Executive Leadership
    "Executive Vice President", "Senior Vice President", "Vice President of Operations", 
    "Vice President of Sales", "Vice President of Marketing", "Vice President", "VP", 
    "SVP", "EVP", "AVP",
    
    # Director / Head of
    "Director of Operations", "Director of Business Development", "Director of Sales", 
    "Director of Marketing", "Director of Finance", "Director of HR", "Director of Human Resources", 
    "Director", "Head of Operations", "Head of Sales", "Head of Growth", "Head of People",
    
    # Managers & Leads
    "Account Executive", "Business Development Manager", "Sales Manager", "Marketing Manager", 
    "Product Manager", "Project Manager", "Customer Success Manager", "HR Manager", 
    "Office Manager", "Team Lead", "Supervisor",
    
    # Specialists & Associates
    "Senior Consultant", "Consultant", "Specialist", "Coordinator", "Analyst", "Associate"
]

ALL_KNOWN_TITLES = HEALTHCARE_TITLES + CORPORATE_TITLES


def clean_string(text: str) -> str:
    """Cleans invisible chars, HTML entities, and whitespace."""
    if not text:
        return ""
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00a0\r\n\t]+", " ", str(text))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_email(raw_email: str) -> Dict[str, Any]:
    """
    Parses email address to extract name components, domain, and company heuristics.
    """
    if not raw_email or not isinstance(raw_email, str):
        return {
            "email": "",
            "is_valid": False,
            "is_role_based": False,
            "first_name": "",
            "last_name": "",
            "full_name": "",
            "domain": "",
            "company_name": ""
        }

    email = clean_string(raw_email).lower()
    # Match standard email pattern
    match = re.search(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", email)
    if not match:
        return {
            "email": raw_email,
            "is_valid": False,
            "is_role_based": False,
            "first_name": "",
            "last_name": "",
            "full_name": "",
            "domain": "",
            "company_name": ""
        }

    local_part, domain = match.groups()
    
    # Clean domain from subdomains like mail. or smtp.
    domain_clean = re.sub(r"^(?:mail|webmail|smtp|mx|pop|email)\.", "", domain)
    
    # Check if role-based
    clean_local = re.sub(r"[0-9_.-]+", "", local_part).lower()
    is_role_based = local_part.lower() in ROLE_BASED_PREFIXES or clean_local in ROLE_BASED_PREFIXES

    first_name, last_name, full_name = extract_name_from_local_part(local_part)
    company_name = infer_company_from_domain(domain_clean)

    return {
        "email": f"{local_part}@{domain}",
        "is_valid": True,
        "is_role_based": is_role_based,
        "first_name": first_name.title() if first_name else "",
        "last_name": last_name.title() if last_name else "",
        "full_name": full_name.title() if full_name else "",
        "domain": domain_clean,
        "company_name": company_name
    }


def extract_name_from_local_part(local: str) -> Tuple[str, str, str]:
    """
    Extracts First Name, Last Name, and Full Name from email username.
    Handles formats:
    - john.smith -> John Smith
    - john_smith -> John Smith
    - john-smith -> John Smith
    - dr.john.smith -> John Smith (with Dr. honorific noted)
    - jsmith -> John/J Smith
    - johnsmith -> Johnsmith (attempted)
    """
    # Remove trailing digits e.g. john.smith12 -> john.smith
    clean_local = re.sub(r"\d+$", "", local.lower())
    
    # Split on common separators: dot, underscore, hyphen, plus
    parts = [p for p in re.split(r"[._\-+]+", clean_local) if p]
    
    if not parts:
        return ("", "", "")

    # Check for honorifics as first part
    if parts[0] in HONORIFICS and len(parts) > 1:
        parts = parts[1:]

    if len(parts) == 1:
        single = parts[0]
        # Check if single has Dr prefix attached e.g., drsmith
        for hon in HONORIFICS:
            if single.startswith(hon) and len(single) > len(hon) + 2:
                single = single[len(hon):]
                break
        return (single, "", single)

    if len(parts) == 2:
        return (parts[0], parts[1], f"{parts[0]} {parts[1]}")

    if len(parts) >= 3:
        # e.g. john.m.smith -> first: john, last: smith, full: john m smith
        return (parts[0], parts[-1], " ".join(parts))

    return ("", "", "")


# Common Medical & Academic Institutions mapping
INSTITUTION_MAP = {
    "umich.edu": "Michigan Medicine (University of Michigan)",
    "med.umich.edu": "Michigan Medicine",
    "uthscsa.edu": "UT Health San Antonio",
    "ucla.edu": "UCLA Health",
    "mednet.ucla.edu": "UCLA Health",
    "downstate.edu": "SUNY Downstate Health Sciences",
    "utmck.edu": "UT Medical Center Knoxville",
    "utsouthwestern.edu": "UT Southwestern Medical Center",
    "rush.edu": "Rush University Medical Center",
    "stonybrookmedicine.edu": "Stony Brook Medicine",
    "pennmedicine.upenn.edu": "Penn Medicine",
    "upenn.edu": "Penn Medicine / UPenn",
    "uphs.upenn.edu": "Penn Medicine (UPHS)",
    "harvard.edu": "Harvard Medical School / BIDMC",
    "bidmc.harvard.edu": "Beth Israel Deaconess Medical Center (Harvard)",
    "miami.edu": "University of Miami Health",
    "med.miami.edu": "UHealth (University of Miami)",
    "health.southalabama.edu": "USA Health (South Alabama)",
    "uchicagomedicine.org": "UChicago Medicine",
    "ohsu.edu": "OHSU Health",
    "nyulangone.org": "NYU Langone Health",
    "musc.edu": "MUSC Health",
    "vcuhealth.org": "VCU Health",
    "jhmi.edu": "Johns Hopkins Medicine",
    "mayo.edu": "Mayo Clinic",
    "mayoclinic.org": "Mayo Clinic",
    "vumc.org": "Vanderbilt University Medical Center",
    "emoryhealthcare.org": "Emory Healthcare",
    "jefferson.edu": "Thomas Jefferson University Hospitals",
    "stanfordhealthcare.org": "Stanford Health Care"
}

TITLE_KEYWORDS_REGEX = re.compile(
    r"\b(?:ceo|cfo|coo|cto|cmo|cro|cio|president|director|vp|vice president|"
    r"manager|administrator|dentist|doctor|physician|surgeon|orthodontist|periodontist|"
    r"endodontist|chiropractor|optometrist|ophthalmologist|therapist|hygienist|"
    r"assistant|specialist|coordinator|founder|co-founder|owner|partner|principal|"
    r"managing partner|professor|associate professor|assistant professor|chair|"
    r"fellow|resident|chief|nurse|practitioner)\b",
    re.IGNORECASE
)


def infer_company_from_domain(domain: str) -> str:
    """
    Infers formatted company or practice name from domain.
    """
    if not domain:
        return ""

    low_domain = domain.lower()

    # Check direct institution mapping
    for k, v in INSTITUTION_MAP.items():
        if low_domain == k or low_domain.endswith("." + k):
            return v

    # Exclude public free email providers
    free_providers = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", 
        "aol.com", "comcast.net", "sbcglobal.net", "verizon.net", "mail.com", "zoho.com"
    }
    if low_domain in free_providers:
        return ""

    # Strip TLD and prefixes like med., health., mail.
    parts = low_domain.split(".")
    if len(parts) >= 3 and parts[0] in ["med", "health", "mail", "clinic", "hospital", "hsc"]:
        name_part = parts[1]
    else:
        name_part = parts[0]

    # Replace hyphens with spaces
    words = re.split(r"[-_]+", name_part)
    
    # If single word, try heuristic word split
    split_words = []
    common_break_terms = [
        "dental", "orthodontics", "ortho", "pediatric", "family", "care", 
        "health", "clinic", "chiro", "eye", "vision", "partners", "associates", 
        "group", "practice", "center", "medical", "surgery", "smiles", "smile",
        "behavior", "success", "aba"
    ]
    
    for w in words:
        current = w
        for term in common_break_terms:
            if term in current and current != term:
                current = current.replace(term, f" {term} ")
        split_words.extend(current.strip().split())

    formatted_company = " ".join([w.capitalize() for w in split_words if w])
    return formatted_company


def classify_seniority(title: str) -> str:
    """
    Classifies a job title into standard Seniority Tiers.
    """
    if not title:
        return "Unknown"
        
    t = title.lower()
    
    # C-Suite / Executive / Ownership
    if any(k in t for k in ["ceo", "chief", "founder", "owner", "co-owner", "president", "partner", "principal", "managing partner", "proprietor"]):
        return "Owner / Executive (C-Suite)"
        
    # Director / VP
    if any(k in t for k in ["vice president", "vp", "director", "head of", "svp", "evp", "chair"]):
        return "Director / VP"
        
    # Healthcare Providers / Practitioners / Faculty
    if any(k in t for k in ["dentist", "doctor", "dr.", "physician", "surgeon", "orthodontist", "periodontist", "endodontist", "chiropractor", "optometrist", "practitioner", "therapist", "professor", "fellow", "resident"]):
        return "Practitioner / Doctor / Faculty"

    # Practice / Operations Management
    if any(k in t for k in ["manager", "administrator", "supervisor", "lead", "coordinator of"]):
        return "Manager / Admin"
        
    # Staff / Clinical Support
    if any(k in t for k in ["hygienist", "assistant", "coordinator", "specialist", "front desk", "receptionist", "intake", "billing", "associate"]):
        return "Staff / Coordinator"
        
    return "Professional"


def extract_title_from_text(text: str, name: str = "", company: str = "") -> Optional[str]:
    """
    Extracts high-confidence Job Title from search snippet, LinkedIn/Apollo title or website text.
    """
    if not text:
        return None
        
    cleaned = clean_string(text)

    # Filter out junk questions, e-commerce listings, and blog headlines
    if "?" in cleaned or any(junk in cleaned.lower() for junk in ["what does", "how to", "who is", "buy online", "price in", "lights for"]):
        return None

    # 1. High-precision Structured Title Parser (LinkedIn, Apollo.io, ZoomInfo, RocketReach):
    # Examples:
    # - "Kenneth Gow, MD - Professor and Surgeon - Stony Brook Medicine | LinkedIn"
    # - "Sarah Jenkins - Dentist & Owner - Family Dentistry | Apollo.io"
    # - "Mark Zuckerberg - Founder, Chairman and CEO at Meta | Apollo"
    if any(k in cleaned.lower() for k in ["linkedin", "apollo", "zoominfo", "rocketreach", "leadiq"]) or " - " in cleaned or " | " in cleaned:
        segments = [s.strip() for s in re.split(r"\s+[-–—|]\s+", cleaned) if s.strip()]
        for seg in segments:
            low = seg.lower()
            if any(junk in low for junk in ["linkedin", "apollo", "apollo.io", "zoominfo", "rocketreach", "leadiq", "connection", "follower", "experience", "see full profile", "location", "overview"]):
                continue
            if name and low == name.lower():
                continue
            if company and low == company.lower():
                continue
            # Must match word boundary title keywords
            if TITLE_KEYWORDS_REGEX.search(low):
                cleaned_seg = re.sub(r"\s+at\s+.*$", "", seg, flags=re.IGNORECASE).strip()
                if 2 <= len(cleaned_seg) <= 60:
                    return clean_title_candidate(cleaned_seg)

    # 2. Apollo & B2B Directory Specific Snippet Patterns:
    # Example: "Title: Chief Executive Officer. Company: Acme Corp"
    title_field_match = re.search(r"\b(?:Title|Job Title|Role|Current Title)\s*:\s*([A-Za-z\s,/&-]+?)(?:\.|\s+Company:|\s+Location:|\s+Email:|$)", cleaned, re.IGNORECASE)
    if title_field_match:
        cand = title_field_match.group(1).strip()
        if 2 <= len(cand) <= 60 and TITLE_KEYWORDS_REGEX.search(cand.lower()):
            return clean_title_candidate(cand)

    # Example: "... is the Owner & Dentist at Family Dental..."
    is_a_match = re.search(r"\b(?:is the|works as|serves as|working as|currently a|currently serving as|position of)\s+(?:a|an|the)?\s*([A-Za-z\s,/&-]+?)\s+(?:at|for|with)\b", cleaned, re.IGNORECASE)
    if is_a_match:
        cand = is_a_match.group(1).strip()
        if 2 <= len(cand) <= 60 and TITLE_KEYWORDS_REGEX.search(cand.lower()):
            return clean_title_candidate(cand)

    # 3. Direct match with Known Titles Dictionary (prioritize longest matching phrases)
    sorted_known = sorted(ALL_KNOWN_TITLES, key=len, reverse=True)
    for known in sorted_known:
        pattern = rf"\b{re.escape(known)}\b"
        if re.search(pattern, cleaned, re.IGNORECASE):
            return known

    # 4. Pattern: "Job Title at [Company]"
    at_match = re.search(r"\b([A-Za-z\s]+?)\s+at\s+([A-Za-z0-9\s]+)", cleaned, re.IGNORECASE)
    if at_match:
        cand = at_match.group(1).strip()
        if len(cand) > 3 and len(cand) < 50:
            if TITLE_KEYWORDS_REGEX.search(cand.lower()):
                return clean_title_candidate(cand)

    return None


def clean_title_candidate(title: str) -> str:
    """Cleans junk characters, trailing delimiters from extracted job title."""
    t = title.strip(" -–—|•·,:")
    # Remove leading honorifics if only title
    t = re.sub(r"^(?:dr\.?|doctor|mr\.?|mrs\.?|ms\.?)\s+", "", t, flags=re.IGNORECASE)
    # Remove trailing company if present e.g. "Dentist at Smiles"
    t = re.sub(r"\s+(?:at|@)\s+.*$", "", t, flags=re.IGNORECASE)
    # Capitalize words properly
    return " ".join([word.capitalize() if not word.isupper() and word.lower() not in ["and", "of", "the", "for"] else word for word in t.split()])
