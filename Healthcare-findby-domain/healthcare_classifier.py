"""
Healthcare & Clinic Classification Engine
Provides highly accurate multi-layer classification with specialty detection,
negative keyword filtering, and domain-fallback heuristics.
"""

import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

# Specific Healthcare Specialties & Categories
SPECIALTY_PATTERNS = {
    "Dental & Orthodontics": [
        r"\b(dentist|dentistry|dental|orthodontics|orthodontist|periodontist|periodontics|endodontics|oral\s+surgery|teeth\s+whitening|dental\s+implants|invisalign|veneers|root\s+canal|cavity|pediatric\s+dentist)\b"
    ],
    "Hospital & Health System": [
        r"\b(hospital|health\s+system|medical\s+center|emergency\s+room|emergency\s+department|level\s+1\s+trauma|trauma\s+center|inpatient|surgical\s+hospital|children\'?s\s+hospital|general\s+hospital)\b"
    ],
    "Urgent Care & Walk-in Clinic": [
        r"\b(urgent\s+care|walk-in\s+clinic|immediate\s+care|express\s+care|after\s+hours\s+clinic|same-day\s+care|minute\s+clinic)\b"
    ],
    "Primary Care & Family Medicine": [
        r"\b(primary\s+care|family\s+medicine|family\s+practice|family\s+physicians?|internal\s+medicine|general\s+practitioner|preventive\s+care|annual\s+wellness\s+exam)\b"
    ],
    "Dermatology & Skin Care": [
        r"\b(dermatology|dermatologist|skin\s+cancer|mohs\s+surgery|botox|cosmetic\s+dermatology|psoriasis|eczema|acne\s+treatment|laser\s+skin)\b"
    ],
    "Orthopedics & Sports Medicine": [
        r"\b(orthopedic|orthopaedics|orthopedist|orthopedic\s+surgery|joint\s+replacement|sports\s+medicine|arthroscopy|knee\s+replacement|hip\s+replacement|fracture\s+care)\b"
    ],
    "Chiropractic & Physical Therapy": [
        r"\b(chiropractic|chiropractor|subluxation|spinal\s+adjustment|physical\s+therapy|physical\s+therapist|physiotherapy|rehabilitation|kinesiology|manual\s+therapy)\b"
    ],
    "Eye Care & Ophthalmology": [
        r"\b(optometry|optometrist|ophthalmology|ophthalmologist|lasik|cataract|glaucoma|retina|cornea|eye\s+exam|vision\s+care|contact\s+lenses)\b"
    ],
    "Mental Health & Psychiatry": [
        r"\b(psychiatry|psychiatrist|psychology|psychologist|psychotherapy|mental\s+health|counseling|therapist|behavioral\s+health|depression|anxiety|addiction\s+treatment|rehab\s+center)\b"
    ],
    "Women's Health & OB/GYN": [
        r"\b(obstetrics|gynecology|ob/gyn|obgyn|women\'?s\s+health|maternity|prenatal|fertility|ivf|gynecologist|mammogram|pelvic\s+health)\b"
    ],
    "Pediatrics": [
        r"\b(pediatric|pediatrics|pediatrician|child\s+health|adolescent\s+medicine|newborn\s+care|pediatric\s+care)\b"
    ],
    "Cardiology & Heart Care": [
        r"\b(cardiology|cardiologist|heart\s+center|cardiovascular|electrocardio|echocardiogram|cardiac\s+care|heart\s+failure)\b"
    ],
    "Gastroenterology": [
        r"\b(gastroenterology|gastroenterologist|colonoscopy|endoscopy|digestive\s+health|gi\s+clinic|hepatology)\b"
    ],
    "Oncology & Cancer Care": [
        r"\b(oncology|oncologist|cancer\s+center|chemotherapy|radiation\s+oncology|infusion\s+center|hematology|tumor\s+care)\b"
    ],
    "Neurology & Neurosurgery": [
        r"\b(neurology|neurologist|neurosurgery|neurosurgeon|stroke\s+care|epilepsy|neuropathy|brain\s+and\s+spine)\b"
    ],
    "Urology": [
        r"\b(urology|urologist|prostate|kidney\s+stones|bladder\s+health|vasectomy|urological)\b"
    ],
    "Ear, Nose & Throat (ENT) & Audiology": [
        r"\b(ent|otolaryngology|otolaryngologist|audiology|audiologist|hearing\s+aids|sinus|tinnitus|hearing\s+test)\b"
    ],
    "Podiatry": [
        r"\b(podiatry|podiatrist|foot\s+and\s+ankle|foot\s+doctor|bunion|heel\s+pain|orthotics|diabetic\s+foot)\b"
    ],
    "Pain Management & Spine": [
        r"\b(pain\s+management|chronic\s+pain|spine\s+center|epidural\s+injection|nerve\s+block|interventional\s+pain)\b"
    ],
    "Senior Care & Home Health": [
        r"\b(home\s+health|hospice|palliative\s+care|senior\s+care|assisted\s+living|memory\s+care|nursing\s+home|skilled\s+nursing|elder\s+care)\b"
    ],
    "Veterinary / Animal Care": [
        r"\b(veterinary|veterinarian|vet\s+clinic|animal\s+hospital|pet\s+clinic|canine|feline|vet\s+care)\b"
    ],
    "Plastic & Cosmetic Surgery": [
        r"\b(plastic\s+surgery|cosmetic\s+surgery|plastic\s+surgeon|rhinoplasty|liposuction|breast\s+augmentation|facelift)\b"
    ],
    "General / Other Medical Specialty": [
        r"\b(allergy|immunology|endocrinology|diabetes|nephrology|dialysis|pulmonology|sleep\s+medicine|rheumatology|pathology|radiology|imaging|mri|ct\s+scan|x-ray|ultrasound|pharmacy|rx)\b"
    ]
}

# Strong General Healthcare Indicators
GENERAL_HEALTHCARE_PATTERNS = [
    r"\b(patient|patients|patient\s+portal|patient\s+forms|new\s+patient|book\s+appointment|schedule\s+appointment|request\s+an\s+appointment)\b",
    r"\b(physician|physicians|doctor|doctors|dr\.|m\.d\.|d\.o\.|d\.d\.s\.|d\.m\.d\.|d\.p\.m\.|d\.c\.|f\.a\.c\.s\.)\b",
    r"\b(medical|medicine|clinical|clinic|clinics|healthcare|health\s+care|telehealth|telemedicine|medical\s+practice)\b",
    r"\b(diagnosis|treatment|treatments|symptoms|insurance\s+accepted|accepting\s+new\s+patients|board\s+certified)\b",
    r"\b(prescription|refill|hipaa|health\s+services|medical\s+group)\b"
]

# Non-Healthcare Industry Patterns (Negative Filters)
NON_HEALTHCARE_PATTERNS = [
    (r"\b(roofing|roof\s+repair|roof\s+replacement|shingles|gutters|siding|metal\s+roof)\b", "Roofing & Siding"),
    (r"\b(auto\s+repair|car\s+dealership|used\s+cars|oil\s+change|towing\s+service|collision\s+center|tire\s+shop|auto\s+body|transmission\s+repair|car\s+wash|auto\s+parts)\b", "Automotive"),
    (r"\b(plumbing|plumber|drain\s+cleaning|water\s+heater|pipe\s+repair|hvac|air\s+conditioning|furnace|heating\s+and\s+cooling)\b", "Home Services / HVAC / Plumbing"),
    (r"\b(pest\s+control|exterminator|termite|bed\s+bugs|lawn\s+care|landscaping|tree\s+service|locksmith|flooring|carpet\s+cleaning)\b", "Home Improvement"),
    (r"\b(real\s+estate|realtor|homes\s+for\s+sale|property\s+management|mortgage|escrow|title\s+company|vacation\s+rentals?|airbnb)\b", "Real Estate"),
    (r"\b(law\s+firm|attorneys?\s+at\s+law|personal\s+injury\s+lawyer|criminal\s+defense|divorce\s+attorney|litigation|legal\s+counsel|legal\s+services)\b", "Legal Services"),
    (r"\b(restaurant|bakery|catering|brewery|winery|menu|pizza|coffee\s+shop|diner|cocktail|bistro|bar\s+and\s+grill)\b", "Food & Beverage"),
    (r"\b(seo\s+agency|digital\s+marketing|web\s+design\s+agency|software\s+development|it\s+support|cloud\s+solutions|saas|cybersecurity)\b", "Technology / Marketing"),
    (r"\b(furniture|mattress|jewelry|diamonds|apparel|clothing\s+store|boutique|online\s+shop|e-commerce|shoe\s+store)\b", "Retail & Shopping"),
    (r"\b(hotel|resort|vacation\s+package|car\s+rental|tour\s+guide|sightseeing|yacht\s+charter|travel\s+agency)\b", "Travel & Hospitality"),
    (r"\b(accounting|cpa|tax\s+preparation|bookkeeping|financial\s+advisor|wealth\s+management|insurance\s+agency)\b", "Financial / Accounting")
]

# Domain Keyword Lists
HEALTHCARE_DOMAIN_KEYWORDS = [
    r"health", r"med", r"clinic", r"care", r"doctor", r"dr[a-z0-9]", r"dental",
    r"dentist", r"dent", r"ortho", r"derm", r"surg", r"eye", r"retina", r"optom",
    r"chiro", r"psych", r"therapy", r"wellness", r"neuro", r"cardio", r"gastro",
    r"obgyn", r"gyn", r"physician", r"podiat", r"foot", r"spine", r"pain",
    r"rehab", r"hospice", r"urgent", r"fammed", r"familypractice", r"allergy",
    r"asthma", r"vein", r"vascular", r"urology", r"hearing", r"sleep", r"imaging",
    r"mri", r"xray", r"dialysis", r"nephro", r"oncol", r"cancer", r"fertility",
    r"pediatric", r"prenatal", r"midwife", r"infusion", r"rx", r"pharm", r"vet",
    r"animalhospital", r"homecare", r"seniorcare", r"audiol", r"hospital", r"doc",
    r"zocdoc", r"practitioner"
]

NON_HEALTHCARE_DOMAIN_KEYWORDS = [
    r"roof", r"roofing", r"auto", r"automall", r"car", r"towing", r"tire",
    r"plumb", r"hvac", r"electric", r"pest", r"appliance", r"furniture", r"mattress",
    r"jewel", r"wine", r"brewery", r"bakery", r"restaurant", r"realty", r"realestate",
    r"title", r"escrow", r"rental", r"law", r"legal", r"attorney", r"lawyer",
    r"finance", r"loan", r"marketing", r"agency", r"seo", r"logistics", r"flooring"
]


def clean_domain_string(raw: str) -> str:
    """Cleans a URL or domain string into a clean hostname."""
    if not raw or not isinstance(raw, str):
        return ""
    d = raw.strip().lower()
    # Remove protocol
    d = re.sub(r"^https?://", "", d)
    # Remove www
    d = re.sub(r"^www\.", "", d)
    # Remove path, query params, hash
    d = d.split("/")[0].split("?")[0].split("#")[0].strip()
    return d


def classify_domain_content(
    domain: str,
    html: Optional[str] = None,
    soup: Optional[BeautifulSoup] = None,
    page_title: str = "",
    meta_description: str = "",
    status_msg: str = "Live"
) -> Dict[str, Any]:
    """
    Classifies a domain based on page content, meta tags, and domain heuristics.
    Returns:
        is_healthcare: bool (True/False)
        category: str (e.g. 'Dental & Orthodontics', 'Non-Healthcare: Roofing', 'General Healthcare')
        confidence: str ('High', 'Medium', 'Low')
        reason: str
        detected_specialties: list
    """
    clean_domain = clean_domain_string(domain)
    
    # 1. Check Domain Name Keywords
    domain_hc_hits = [kw for kw in HEALTHCARE_DOMAIN_KEYWORDS if re.search(kw, clean_domain)]
    domain_non_hc_hits = [kw for kw in NON_HEALTHCARE_DOMAIN_KEYWORDS if re.search(kw, clean_domain)]
    
    # If no webpage content available (offline / error fallback)
    if not html and not soup:
        if domain_hc_hits and not domain_non_hc_hits:
            category = "Healthcare (Inferred from Domain)"
            for spec, patterns in SPECIALTY_PATTERNS.items():
                if any(re.search(pat, clean_domain, flags=re.IGNORECASE) for pat in patterns):
                    category = spec
                    break
            return {
                "is_healthcare": True,
                "category": category,
                "confidence": "Medium",
                "reason": f"Site unreachable ({status_msg}), but domain contains strong healthcare keyword(s): {', '.join(domain_hc_hits)}",
                "detected_specialties": [category] if category != "Healthcare (Inferred from Domain)" else [],
                "score_hc": len(domain_hc_hits) * 3,
                "score_non_hc": 0
            }
        elif domain_non_hc_hits:
            return {
                "is_healthcare": False,
                "category": "Non-Healthcare Domain",
                "confidence": "Medium",
                "reason": f"Site unreachable ({status_msg}), domain keyword indicates non-healthcare: {', '.join(domain_non_hc_hits)}",
                "detected_specialties": [],
                "score_hc": 0,
                "score_non_hc": len(domain_non_hc_hits) * 3
            }
        else:
            return {
                "is_healthcare": False,
                "category": "Unreachable / Unknown",
                "confidence": "Low",
                "reason": f"Site unreachable ({status_msg}) and domain name lacks clear healthcare indicators",
                "detected_specialties": [],
                "score_hc": 0,
                "score_non_hc": 0
            }

    # If HTML provided, parse and analyze
    if not soup and html:
        soup = BeautifulSoup(html, "html.parser")

    # Extract text segments
    extracted_title = page_title.lower() if page_title else ""
    if not extracted_title and soup.title and soup.title.string:
        extracted_title = str(soup.title.string).strip().lower()

    meta_text = meta_description.lower() if meta_description else ""
    if soup:
        for meta in soup.find_all("meta"):
            name = (meta.get("name") or "").lower()
            prop = (meta.get("property") or "").lower()
            if name in ["description", "keywords"] or prop in ["og:description", "og:title"]:
                meta_text += " " + (meta.get("content") or "").lower()

        # Headings text (h1, h2, h3)
        headings = " ".join([h.get_text(separator=" ", strip=True).lower() for h in soup.find_all(["h1", "h2", "h3"])])
        
        # Body text (first 8000 chars)
        body_elem = soup.find("body")
        body_text = (body_elem.get_text(separator=" ", strip=True) if body_elem else soup.get_text(separator=" ", strip=True))[:8000].lower()
    else:
        headings = ""
        body_text = (html or "")[:8000].lower()

    # Prioritized text blocks
    high_priority_text = f"{clean_domain} {extracted_title} {meta_text} {headings}"
    full_text = f"{high_priority_text} {body_text}"

    # 2. Check Negative / Non-Healthcare Filters
    non_hc_scores = {}
    total_non_hc_score = 0
    for pat, ind_name in NON_HEALTHCARE_PATTERNS:
        matches_hp = re.findall(pat, high_priority_text, flags=re.IGNORECASE)
        matches_body = re.findall(pat, body_text, flags=re.IGNORECASE)
        weight = (len(matches_hp) * 4) + min(len(matches_body), 4)
        if weight > 0:
            non_hc_scores[ind_name] = non_hc_scores.get(ind_name, 0) + weight
            total_non_hc_score += weight

    if domain_non_hc_hits:
        total_non_hc_score += len(domain_non_hc_hits) * 3

    # 3. Check Specialty Match & General Healthcare
    specialty_hits = {}
    total_hc_score = 0

    for spec_name, patterns in SPECIALTY_PATTERNS.items():
        spec_score = 0
        for pat in patterns:
            hp_m = re.findall(pat, high_priority_text, flags=re.IGNORECASE)
            body_m = re.findall(pat, body_text, flags=re.IGNORECASE)
            spec_score += (len(hp_m) * 3) + min(len(body_m), 3)
        if spec_score > 0:
            specialty_hits[spec_name] = spec_score
            total_hc_score += spec_score

    # General Healthcare terms
    for pat in GENERAL_HEALTHCARE_PATTERNS:
        hp_m = re.findall(pat, high_priority_text, flags=re.IGNORECASE)
        body_m = re.findall(pat, body_text, flags=re.IGNORECASE)
        total_hc_score += (len(hp_m) * 2) + min(len(body_m), 2)

    if domain_hc_hits:
        total_hc_score += len(domain_hc_hits) * 3

    # Rank detected specialties
    sorted_specialties = sorted(specialty_hits.items(), key=lambda x: x[1], reverse=True)
    top_specialty = sorted_specialties[0][0] if sorted_specialties else "General Healthcare"

    # 4. Final Classification Decision
    if total_hc_score >= 4 and total_hc_score > total_non_hc_score:
        confidence = "High" if total_hc_score >= 7 else "Medium"
        reason = f"Verified healthcare practice ({top_specialty}). Content & keywords score: {total_hc_score}"
        return {
            "is_healthcare": True,
            "category": top_specialty,
            "confidence": confidence,
            "reason": reason,
            "detected_specialties": [s[0] for s in sorted_specialties[:3]],
            "score_hc": total_hc_score,
            "score_non_hc": total_non_hc_score
        }
    
    elif total_non_hc_score >= 4 and total_non_hc_score >= total_hc_score:
        top_non_hc = sorted(non_hc_scores.items(), key=lambda x: x[1], reverse=True)[0][0] if non_hc_scores else "Non-Healthcare"
        confidence = "High" if total_non_hc_score >= 6 else "Medium"
        return {
            "is_healthcare": False,
            "category": f"Non-Healthcare ({top_non_hc})",
            "confidence": confidence,
            "reason": f"Identified as {top_non_hc} industry (score: {total_non_hc_score} vs hc: {total_hc_score})",
            "detected_specialties": [],
            "score_hc": total_hc_score,
            "score_non_hc": total_non_hc_score
        }
    
    elif total_hc_score >= 2 and total_non_hc_score == 0:
        return {
            "is_healthcare": True,
            "category": top_specialty,
            "confidence": "Medium",
            "reason": f"Healthcare indicators found ({top_specialty}, score: {total_hc_score})",
            "detected_specialties": [s[0] for s in sorted_specialties[:2]],
            "score_hc": total_hc_score,
            "score_non_hc": total_non_hc_score
        }
    
    else:
        return {
            "is_healthcare": False,
            "category": "Non-Healthcare / General",
            "confidence": "Low" if total_hc_score == 0 and total_non_hc_score == 0 else "Medium",
            "reason": f"Insufficient healthcare relevance (hc_score: {total_hc_score}, non_hc_score: {total_non_hc_score})",
            "detected_specialties": [],
            "score_hc": total_hc_score,
            "score_non_hc": total_non_hc_score
        }
