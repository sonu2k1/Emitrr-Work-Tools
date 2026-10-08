import time
import base64
import requests
from urllib.parse import quote_plus
from typing import Dict, List

# Top US Metros for healthcare practices scraping
TOP_US_METROS = [
    "Dallas, TX",
    "Houston, TX",
    "Austin, TX",
    "San Antonio, TX",
    "Los Angeles, CA",
    "San Diego, CA",
    "San Francisco, CA",
    "Sacramento, CA",
    "Phoenix, AZ",
    "Miami, FL",
    "Tampa, FL",
    "Orlando, FL",
    "Jacksonville, FL",
    "Atlanta, GA",
    "Chicago, IL",
    "New York, NY",
    "Philadelphia, PA",
    "Charlotte, NC",
    "Raleigh, NC",
    "Nashville, TN",
    "Indianapolis, IN",
    "Columbus, OH",
    "Cleveland, OH",
    "Seattle, WA",
    "Denver, CO",
    "Salt Lake City, UT",
    "Las Vegas, NV",
    "Portland, OR",
    "Boston, MA",
    "Detroit, MI",
    "Minneapolis, MN",
    "Kansas City, MO",
    "St. Louis, MO",
    "Baltimore, MD",
    "Milwaukee, WI",
    "Albuquerque, NM",
    "Tucson, AZ",
    "Oklahoma City, OK",
    "Tulsa, OK",
    "New Orleans, LA",
    "Louisville, KY",
    "Memphis, TN",
    "Richmond, VA",
    "Virginia Beach, VA",
    "Omaha, NE",
    "Fresno, CA",
    "Long Beach, CA",
    "Fort Worth, TX",
    "El Paso, TX",
    "Colorado Springs, CO"
]

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming"
]

def geocode_location(address: str) -> Dict[str, any]:
    """
    Uses valentin.app geocode endpoint or fallback to fetch exact lat/lng and formatted address.
    """
    url = f"https://valentin.app/geocode?address={quote_plus(address)}&hl=en&gl=US"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "OK" and data.get("results"):
                res = data["results"][0]
                lat = res["geometry"]["location"]["lat"]
                lng = res["geometry"]["location"]["lng"]
                formatted = res.get("formatted_address", address)
                return {
                    "lat": lat,
                    "lng": lng,
                    "address": formatted,
                    "success": True
                }
    except Exception:
        pass

    # US geographic centroid default fallback
    return {
        "lat": 37.0902,
        "lng": -95.7129,
        "address": address,
        "success": False
    }

def generate_uule(lat: float, lng: float) -> str:
    """
    Replicates Valentin.app's UULE generation algorithm for precise Google SERP localization.
    """
    lat_e7 = round(1e7 * lat)
    lng_e7 = round(1e7 * lng)
    now_ms = int(time.time() * 1000)
    timestamp_us = str(1000 * now_ms)
    radius = 150 * 620  # ~93km

    payload = (
        f"role:1\n"
        f"producer:12\n"
        f"provenance:6\n"
        f"timestamp:{timestamp_us}\n"
        f"latlng{{\n"
        f"latitude_e7:{lat_e7}\n"
        f"longitude_e7:{lng_e7}\n"
        f"}}\n"
        f"radius:{radius}"
    )

    encoded = base64.b64encode(payload.encode("utf-8")).decode("utf-8")
    uule = "a " + encoded.replace("+", "-").replace("/", "_").rstrip("=")
    return uule

def get_valentin_search_params(keyword: str, location: str) -> Dict[str, any]:
    """
    Generates localized search parameters for targeted maps / web queries.
    """
    geo = geocode_location(location)
    uule = generate_uule(geo["lat"], geo["lng"])
    search_url = (
        f"https://www.google.com/search?q={quote_plus(keyword)}&hl=en&gl=US&pws=0&uule={quote_plus(uule)}"
    )
    return {
        "search_url": search_url,
        "lat": geo["lat"],
        "lng": geo["lng"],
        "location": geo["address"],
        "uule": uule,
        "keyword": keyword
    }
