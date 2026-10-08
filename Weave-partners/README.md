# 🌐 Weave (getweave.com) Healthcare Partners & Customer Domains Scraper

A high-performance, interactive Python scraper and intelligence extractor designed to discover and extract verified **Official Websites & Root Domains** of healthcare practices using or partnering with **Weave** ([getweave.com](https://www.getweave.com/)).

---

## 🌟 Key Features

1. **Direct Weave Customer Extraction**:
   - Scrapes official Weave Case Studies (`/case-studies/`)
   - Scrapes customer video spotlights & success stories (`/stories/`)
   - Connects to Weave's verified Senja customer review platform (`senja.io/p/weave/qk15kH`)
   - Scrapes quotes across all 13 Weave Healthcare Industry verticals.

2. **Automated Authority Domain Resolution**:
   - Resolves exact official practice websites and root domains.
   - Cleans tracking parameters, UTM codes, session IDs, and fragments.
   - Excludes directories and social aggregators (`yelp.com`, `healthgrades.com`, `zocdoc.com`, `facebook.com`, etc.).

3. **Multi-Vertical Localized Search**:
   - **Dental & Orthodontics**
   - **Optometry & Vision Care**
   - **Veterinary Medicine & Animal Hospitals**
   - **Physical Therapy & Sports Rehab**
   - **Plastic Surgery & Medical Spas**
   - **Podiatry & Foot Specialists**
   - **Mental & Behavioral Health**
   - **Primary Care & Family Practice**
   - **Audiology & Hearing Specialists**

4. **Zero-Loss Live Auto-Save**:
   - Discovered practices are saved immediately to `output/weave_healthcare_customers.csv`.
   - Real-time deduplication prevents duplicate entries.

5. **Rich Terminal CLI Experience**:
   - Interactive terminal UI powered by `rich`
   - Real-time progress bars, live spinner, color-coded discovered practice logs, and database statistics table.

---

## 📁 File Structure

```
Weave-partners/
├── weave_verified_extractor.py # 🎯 100% Verified Weave Customer Harvester (UUID & API)
├── main.py                     # Interactive Rich CLI application
├── weave_site_scraper.py       # Direct Weave customer & Senja review scraper
├── vertical_finder.py          # Targeted localized healthcare search scanner
├── domain_resolver.py          # Multi-engine official website resolver
├── master_manager.py           # CSV storage, deduplication & domain normalizer
├── valentin.py                 # Geocoding & US Metro Coordinates generator
├── requirements.txt            # Python package dependencies
├── output/
│   ├── weave_verified_customers_master.csv  # 🎯 100% Verified Weave Customer Domains
│   ├── weave_discovered_uuids.txt           # Cached Weave Location UUIDs
│   ├── weave_healthcare_customers.csv       # Scraped Healthcare Practices
│   └── weave_us_canada_customers.csv        # North American Harvester CSV
└── README.md
```

---

## 🚀 Quick Start & Usage

### 1. Run the 100% Verified Customer Harvester (Recommended)
```bash
python3 weave_verified_extractor.py
```
Or launch via the interactive menu:
```bash
python3 main.py
```

---

## 📊 Verified CSV Output Schema (`weave_verified_customers_master.csv`)

| Field Name | Description | Example |
| :--- | :--- | :--- |
| **Practice Name** | Cleaned official name of practice | `Santa Clarita Animal Hospital` |
| **Official Website** | Direct verified website URL | `https://santaclaritaanimalhospital.com` |
| **Clean Domain** | Clean root domain | `santaclaritaanimalhospital.com` |
| **Healthcare Vertical** | Specialty vertical | `Vet` / `Dental` / `Optometry` |
| **Weave Location UUID** | Authoritative Weave Location ID | `a90eb683-c94e-4005-a0ad-42e8a2607505` |
| **Notification Email** | Practice contact / admin email | `charles@santaclaritaanimalhospital.com` |
| **Timezone / Region** | US / Canadian practice timezone | `US/Pacific` |
| **Weave Verified Evidence** | Extracted HTML integration proof | `<a href="https://book2.getweave.com/a90eb...` |
| **Verification Status** | Live integration vs active account | `Verified (Live Weave Integration)` |
| **Date Verified** | Timestamp of verification | `2026-09-08 11:10:27` |

---

## 🛠️ CLI Menu Options (`main.py`)

1. **`[1] 🎯 100% Verified Weave Customer Harvester`**: Authoritative extraction via Weave booking UUIDs, metadata API, and live integration verifier.
2. **`[2] 🌐 Official Weave Case Studies & Reviews Scraper`**: Scrapes Weave case studies, customer stories, and Senja verified reviews.
3. **`[3] 🌎 US + Canada 40,000 Mass Healthcare Harvester`**: Sweeps Google Maps across North American metros and states.
4. **`[4] 🩺 Targeted Healthcare Vertical Scraper`**: Custom search by specific vertical and US cities.
5. **`[5] 🔍 Single Practice Domain Resolver`**: Instantly resolve and verify any practice domain.
6. **`[6] 📊 View Master Database & Analytics`**: Real-time breakdown table showing practices and percentages per category.
7. **`[7] 🚪 Exit`**
