"""
Comprehensive Geographic Matrix for US + Canada Healthcare Practices
"""

# All 50 US States + DC
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming", "District of Columbia"
]

# All Canadian Provinces & Territories
CANADA_PROVINCES = [
    "Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba",
    "Saskatchewan", "Nova Scotia", "New Brunswick", "Newfoundland and Labrador",
    "Prince Edward Island", "Yukon", "Northwest Territories", "Nunavut"
]

# Top 100 Major US & Canadian Metro Hubs
TOP_US_CANADA_METROS = [
    # Top US Metros
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
    "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "Austin, TX",
    "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC", "Indianapolis, IN",
    "San Francisco, CA", "Seattle, WA", "Denver, CO", "Nashville, TN", "Oklahoma City, OK",
    "El Paso, TX", "Boston, MA", "Portland, OR", "Las Vegas, NV", "Detroit, MI",
    "Memphis, TN", "Louisville, KY", "Baltimore, MD", "Milwaukee, WI", "Albuquerque, NM",
    "Tucson, AZ", "Fresno, CA", "Sacramento, CA", "Atlanta, GA", "Kansas City, MO",
    "Miami, FL", "Raleigh, NC", "Omaha, NE", "Long Beach, CA", "Virginia Beach, VA",
    "Oakland, CA", "Minneapolis, MN", "Tampa, FL", "Tulsa, OK", "Arlington, TX",
    "New Orleans, LA", "Wichita, KS", "Cleveland, OH", "Orlando, FL", "Salt Lake City, UT",
    "Honolulu, HI", "Boise, ID", "Birmingham, AL", "Anchorage, AK", "Little Rock, AR",
    "Des Moines, IA", "Richmond, VA", "Spokane, WA", "Baton Rouge, LA", "Tacoma, WA",
    
    # Top Canadian Metros
    "Toronto, ON", "Montreal, QC", "Vancouver, BC", "Calgary, AB", "Edmonton, AB",
    "Ottawa, ON", "Winnipeg, MB", "Quebec City, QC", "Hamilton, ON", "Kitchener, ON",
    "London, ON", "Victoria, BC", "Halifax, NS", "Oshawa, ON", "Windsor, ON",
    "Saskatoon, SK", "Regina, SK", "St. John's, NL", "Kelowna, BC", "Barrie, ON",
    "Sherbrooke, QC", "Guelph, ON", "Kanata, ON", "Abbotsford, BC", "Kingston, ON",
    "Trois-Rivieres, QC", "Moncton, NB", "Chicoutimi, QC", "Milton, ON", "Red Deer, AB"
]

# Healthcare Categories Heavily Using Weave
HEALTHCARE_SECTORS = {
    "Dental": [
        "dental clinic", "family dentistry", "orthodontics", "pediatric dentist",
        "periodontics", "endodontics", "cosmetic dentistry", "oral surgery"
    ],
    "Optometry & Vision": [
        "optometry clinic", "eye care center", "family eye doctor", "optometrist",
        "ophthalmology", "vision clinic", "contact lens center"
    ],
    "Veterinary": [
        "veterinary hospital", "animal clinic", "pet care hospital",
        "veterinarian", "animal hospital", "vet clinic", "emergency vet"
    ],
    "Physical Therapy & Rehab": [
        "physical therapy clinic", "sports rehabilitation", "physiotherapy clinic",
        "occupational therapy", "spine and sports therapy"
    ],
    "Plastic Surgery & MedSpas": [
        "plastic surgery", "medical spa", "aesthetic clinic",
        "facial plastic surgery", "dermatology clinic", "cosmetic surgery"
    ],
    "Podiatry": [
        "podiatry clinic", "foot and ankle specialist", "podiatric medicine", "foot clinic"
    ],
    "Mental Health": [
        "mental health clinic", "psychiatry practice", "psychology clinic",
        "behavioral health", "counseling and wellness center"
    ],
    "Primary Care & Medical": [
        "primary care clinic", "family medicine", "internal medicine clinic",
        "urgent care clinic", "integrative health center", "audiology clinic"
    ],
    "Chiropractic": [
        "chiropractic clinic", "family chiropractor", "wellness chiropractic"
    ]
}
