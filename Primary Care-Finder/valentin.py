import time
import base64
import requests
from urllib.parse import quote_plus

# Popular US Metro areas for default bulk searches
TOP_US_METROS = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Phoenix, AZ",
    "Philadelphia, PA",
    "San Antonio, TX",
    "San Diego, CA",
    "Dallas, TX",
    "Austin, TX",
    "Miami, FL",
    "Atlanta, GA",
    "Denver, CO",
    "Seattle, WA",
    "Boston, MA",
    "Tampa, FL",
    "Charlotte, NC",
    "Nashville, TN",
    "Indianapolis, IN",
    "Columbus, OH"
]

def geocode_location(address: str) -> dict:
    """
    Uses valentin.app geocode endpoint to fetch exact lat/lng and formatted address.
    """
    url = f"https://valentin.app/geocode?address={quote_plus(address)}&hl=en&gl=US"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
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
    except Exception as e:
        pass

    # Fallback to default US center (or approximate coordinates)
    return {
        "lat": 39.8283,
        "lng": -98.5795,
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
    radius = 150 * 620  # 93000

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

def get_valentin_search_params(keyword: str, location: str) -> dict:
    """
    Generates all necessary Valentin.app localized search parameters.
    """
    geo = geocode_location(location)
    uule = generate_uule(geo["lat"], geo["lng"])
    search_url = (
        f"https://www.google.com/search?q={quote_plus(keyword)}&hl=en&gl=US&pws=0&uule={quote_plus(uule)}"
    )
    return {
        "keyword": keyword,
        "location": geo["address"],
        "lat": geo["lat"],
        "lng": geo["lng"],
        "uule": uule,
        "search_url": search_url
    }
