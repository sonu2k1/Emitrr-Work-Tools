# 🌸 US Women's Health & OB-GYN / FQHC Practice Scraper

A high-performance Python terminal scraper designed to find, extract, verify, and auto-append US-based **OB-GYN, Women's Health, Maternal-Fetal Medicine (MFM), Fertility Clinics, Midwifery Centers, and FQHCs** with their **Official Practice Names and Verified Website Domains**.

Directly connected with `Master Data Sheet - Women’s Health _ OB-GYNFQHC.csv`.

---

## ✨ Features

- 🎯 **Targeted Categories**:
  1. OB-GYN & Gynecology Practices
  2. Women's Health Clinics
  3. Maternal-Fetal Medicine (MFM) & High-Risk Pregnancy
  4. Reproductive Endocrinology & Fertility Clinics
  5. Midwifery & Birth Centers
  6. FQHC & Community Health Centers (Women's Health)
  7. Gynecological Surgery & Urogynecology
  8. Full Spectrum Women's Health Sweep (All 7)

- 📍 **Target US Locations**:
  - Specific City / State (e.g., Dallas TX, Miami FL, Chicago IL)
  - Specific State (e.g., Texas, California, Florida, Ohio, New York)
  - Top 5 / 20 / 50 Nationwide US Metros
  - Custom comma-separated cities

- 🛡️ **Zero Duplicates Guarantee**:
  - Automatically loads and indexes all existing records in `Master Data Sheet - Women’s Health _ OB-GYNFQHC.csv`.
  - Normalizes domains (stripping `www.`, tracking parameters like `?utm_source=chatgpt.com`).
  - Skips any provider already present in your master sheet or captured during the run.

- 🌐 **Multi-Engine Extraction**:
  - **Valentin.app Localized Coordinates**: Hyper-accurate US local search parameters (UULE).
  - **Playwright Google Maps**: Extracts verified practice cards, official domains, and metadata.
  - **Secondary Web Search Fallback**: DuckDuckGo HTML scraping for broader coverage.
  - Filters out directories like Yelp, Healthgrades, Zocdoc, Doximity, WebMD, Facebook, LinkedIn, etc.

- 💾 **Export & Auto-Append**:
  - Automatically appends unique verified records directly into `Master Data Sheet - Women’s Health _ OB-GYNFQHC.csv`.
  - Optionally exports a timestamped backup CSV to `output/`.

---

## 🚀 How to Run in Terminal

### 1. Navigate to the Directory
```bash
cd "/Users/sonusingh/Emitrr-Works-Tools/OBGYN_Scraper"
```

### 2. Run the Interactive Scraper
```bash
python3 main.py
```

---

## 🛠️ Step-by-Step Terminal Workflow

1. **Category Selection**: Choose one specialty or press `8` for full spectrum Women's Health & FQHC.
2. **Location Selection**: Choose specific city, state, top 5/20/50 metros, or custom list.
3. **Limit**: Choose records limit per query (e.g., 20, 50, or `all`).
4. **Live Scraping**: Watch unique verified practices appear in green in your terminal in real-time.
5. **Export**: Choose `1` (Direct Append to Master Sheet), `2` (Save standalone CSV), or `3` (Both).

---

## 📁 File Structure

```
OBGYN_Scraper/
├── Master Data Sheet - Women’s Health _ OB-GYNFQHC.csv   # Main data sheet
├── main.py                                             # Terminal interactive CLI
├── scraper.py                                          # Multi-engine scraper
├── valentin.py                                         # Valentin.app geocoding & US metros
├── master_manager.py                                   # Deduplication & CSV manager
├── requirements.txt                                    # Dependencies
└── output/                                             # Timestamped export backups
```
