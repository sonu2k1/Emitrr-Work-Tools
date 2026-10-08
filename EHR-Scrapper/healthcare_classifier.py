"""
Healthcare & Clinic Classification Module
Accurately identifies whether a domain / website belongs to healthcare, clinics, medical practices, or non-healthcare industries.
"""

import re
from bs4 import BeautifulSoup

# Strong domain keywords indicating healthcare
HEALTHCARE_DOMAIN_KEYWORDS = [
    r"health", r"med", r"clinic", r"care", r"doctor", r"dr[a-z0-9]", r"pediatric",
    r"dental", r"dentist", r"dent", r"ortho", r"derm", r"surg", r"eye", r"retina",
    r"optom", r"chiro", r"psych", r"therapy", r"wellness", r"neuro", r"cardio",
    r"gastro", r"obgyn", r"gyn", r"physician", r"podiat", r"foot", r"spine",
    r"pain", r"rehab", r"hospice", r"urgent", r"fammed", r"familypractice",
    r"allergy", r"asthma", r"vein", r"vascular", r"urology", r"hearing", r"sleep",
    r"imaging", r"mri", r"xray", r"dialysis", r"nephro", r"oncol", r"cancer",
    r"fertility", r"embryo", r"prenatal", r"midwife", r"midwifery", r"birth",
    r"infusion", r"rx", r"pharm", r"apothecary", r"vet", r"animalhospital",
    r"homecare", r"seniorcare", r"assistedliving", r"mobility", r"audiol",
    r"endocrin", r"rheumatol", r"physicaltherap", r"acupuncture", r"endoscopy"
]

# Non-healthcare domain keywords
NON_HEALTHCARE_DOMAIN_KEYWORDS = [
    r"roof", r"roofing", r"auto", r"automall", r"car", r"hitch", r"towing", r"tire",
    r"plumb", r"hvac", r"electric", r"pest", r"appliance", r"furniture", r"mattress",
    r"jewel", r"wine", r"wines", r"brewery", r"bakery", r"pie", r"pies", r"restaurant",
    r"realty", r"realestate", r"title", r"escrow", r"rental", r"rentals", r"getaway",
    r"law", r"legal", r"attorney", r"lawyer", r"finance", r"financial", r"loan",
    r"broadband", r"isp", r"marketing", r"agency", r"seo", r"transfer", r"logistics",
    r"stair", r"window", r"windows", r"flooring"
]

# Strong regex patterns for medical & clinical content
HEALTHCARE_CONTENT_PATTERNS = [
    r"\b(patient|patients|patient\s+care|patient\s+portal|patient\s+forms|new\s+patient)\b",
    r"\b(physician|physicians|doctor|doctors|dr\.|m\.d\.|d\.o\.|d\.d\.s\.|d\.m\.d\.|d\.p\.m\.|d\.c\.)\b",
    r"\b(medical|medicine|clinical|clinic|clinics|hospital|health\s+system|healthcare)\b",
    r"\b(appointment|book\s+an\s+appointment|schedule\s+appointment|request\s+appointment)\b",
    r"\b(treatment|treatments|diagnosis|symptoms|therapy|therapist|counseling)\b",
    r"\b(cardiology|dermatology|pediatric|pediatrics|orthopedic|orthopaedics|gastroenterology)\b",
    r"\b(neurology|oncology|urology|gynecology|obstetrics|ob/gyn|obgyn|maternity|fertility|ivf)\b",
    r"\b(optometry|ophthalmology|eye\s+care|chiropractic|chiropractor|physical\s+therapy|physiotherapy)\b",
    r"\b(podiatry|podiatrist|dentistry|dental|dentist|oral\s+surgery|periodontics|endodontics)\b",
    r"\b(psychiatry|psychologist|mental\s+health|behavioral\s+health|substance\s+abuse)\b",
    r"\b(primary\s+care|urgent\s+care|family\s+medicine|internal\s+medicine|integrative\s+medicine)\b",
    r"\b(pain\s+management|rheumatology|endocrinology|nephrology|pulmonology|allergy|asthma)\b",
    r"\b(radiology|imaging|mri|ct\s+scan|x-ray|ultrasound|mammography|pathology)\b",
    r"\b(hospice|palliative\s+care|home\s+health|senior\s+care|assisted\s+living|home\s+care)\b",
    r"\b(telehealth|telemedicine|prescription|refill|pharmacy|insurance\s+accepted)\b",
    r"\b(veterinary|vet\s+clinic|animal\s+hospital|veterinarian)\b"
]

# Strong regex patterns for non-healthcare industries
NON_HEALTHCARE_CONTENT_PATTERNS = [
    r"\b(roofing|roof\s+repair|roof\s+replacement|shingles|gutters|siding)\b",
    r"\b(auto\s+parts|automotive|car\s+repair|auto\s+repair|dealership|used\s+cars|collision\s+center|towing|tire\s+shop|oil\s+change|detailing|car\s+wash)\b",
    r"\b(furniture|mattress|sofa|dining\s+table|home\s+decor|bedding)\b",
    r"\b(bakery|pies|cakes|pastries|catering|restaurant|brewery|winery|vineyard|wine\s+tasting)\b",
    r"\b(jewelry|jewellery|diamonds|gemstones|engagement\s+rings|necklaces)\b",
    r"\b(real\s+estate|realtor|property\s+management|vacation\s+rental|airbnb|title\s+company|escrow|mortgage)\b",
    r"\b(plumbing|hvac|air\s+conditioning|furnace|pest\s+control|exterminator|lawn\s+care|landscaping|locksmith|flooring|appliance\s+repair)\b",
    r"\b(law\s+firm|attorneys?\s+at\s+law|personal\s+injury\s+lawyer|criminal\s+defense|divorce\s+attorney|estate\s+planning\s+attorney)\b",
    r"\b(seo\s+services|digital\s+marketing|web\s+design\s+agency|software\s+development|it\s+services)\b",
    r"\b(boat\s+tour|jet\s+ski|sightseeing|yacht\s+charter)\b"
]


def classify_healthcare(domain: str, html: str = None, soup: BeautifulSoup = None) -> dict:
    """
    Evaluates domain and web page content to determine if it is related to healthcare/clinics.
    Returns:
        {
            "is_healthcare": bool,
            "reason": str,
            "healthcare_score": int,
            "non_healthcare_score": int
        }
    """
    domain_clean = (domain or "").lower().strip()
    
    # 1. Evaluate domain name
    domain_hc_hits = sum(1 for kw in HEALTHCARE_DOMAIN_KEYWORDS if re.search(kw, domain_clean))
    domain_non_hc_hits = sum(1 for kw in NON_HEALTHCARE_DOMAIN_KEYWORDS if re.search(kw, domain_clean))
    
    # If no html provided (e.g. site unreachable), base strictly on domain
    if not html and not soup:
        if domain_hc_hits > 0 and domain_non_hc_hits == 0:
            return {
                "is_healthcare": True,
                "reason": "Healthcare domain name",
                "healthcare_score": domain_hc_hits * 3,
                "non_healthcare_score": 0
            }
        elif domain_non_hc_hits > 0 and domain_hc_hits == 0:
            return {
                "is_healthcare": False,
                "reason": "Non-healthcare domain name",
                "healthcare_score": 0,
                "non_healthcare_score": domain_non_hc_hits * 3
            }
        else:
            return {
                "is_healthcare": False,
                "reason": "Unreachable domain without strong healthcare indicator",
                "healthcare_score": domain_hc_hits,
                "non_healthcare_score": domain_non_hc_hits
            }

    if not soup and html:
        soup = BeautifulSoup(html, 'html.parser')

    # Extract text components
    title_text = ""
    if soup.title and soup.title.string:
        title_text = str(soup.title.string).lower()

    meta_text = ""
    for meta in soup.find_all('meta'):
        name = meta.get('name', '').lower()
        prop = meta.get('property', '').lower()
        if name in ['description', 'keywords'] or prop in ['og:description', 'og:title']:
            meta_text += " " + (meta.get('content', '') or '').lower()

    # Get sample visible body text (first 5000 chars is sufficient for classification)
    body_elem = soup.find('body')
    body_text = (body_elem.get_text(separator=' ', strip=True) if body_elem else soup.get_text(separator=' ', strip=True))[:6000].lower()

    combined_text = f"{title_text} {meta_text} {body_text}"

    # Score content
    hc_matches = 0
    for pat in HEALTHCARE_CONTENT_PATTERNS:
        matches = re.findall(pat, combined_text, flags=re.IGNORECASE)
        if matches:
            # Add weight based on count
            hc_matches += min(len(matches), 3)

    non_hc_matches = 0
    for pat in NON_HEALTHCARE_CONTENT_PATTERNS:
        matches = re.findall(pat, combined_text, flags=re.IGNORECASE)
        if matches:
            non_hc_matches += min(len(matches), 3)

    # Title & Domain weight
    for kw in HEALTHCARE_DOMAIN_KEYWORDS:
        if re.search(kw, title_text):
            hc_matches += 3
        if re.search(kw, domain_clean):
            hc_matches += 2

    for kw in NON_HEALTHCARE_DOMAIN_KEYWORDS:
        if re.search(kw, title_text):
            non_hc_matches += 4
        if re.search(kw, domain_clean):
            non_hc_matches += 3

    # Decision logic
    if hc_matches >= 3 and hc_matches > non_hc_matches:
        return {
            "is_healthcare": True,
            "reason": f"Healthcare content verified (score: {hc_matches} vs {non_hc_matches})",
            "healthcare_score": hc_matches,
            "non_healthcare_score": non_hc_matches
        }
    elif non_hc_matches >= 2 and non_hc_matches >= hc_matches:
        return {
            "is_healthcare": False,
            "reason": f"Non-healthcare industry detected (score: {non_hc_matches} vs {hc_matches})",
            "healthcare_score": hc_matches,
            "non_healthcare_score": non_hc_matches
        }
    elif hc_matches > 0 and non_hc_matches == 0:
        return {
            "is_healthcare": True,
            "reason": f"Healthcare indicators present (score: {hc_matches})",
            "healthcare_score": hc_matches,
            "non_healthcare_score": 0
        }
    else:
        return {
            "is_healthcare": False,
            "reason": f"Insufficient healthcare relevance (score: {hc_matches})",
            "healthcare_score": hc_matches,
            "non_healthcare_score": non_hc_matches
        }
