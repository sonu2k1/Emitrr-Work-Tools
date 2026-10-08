# 🏥 US Primary Care Finder (Company Name & Domain Scraper)

A targeted Python-based terminal scraper that extracts **Company Name** (1st Column) and official **Domain** (2nd Column) across 6 US Primary Care specialties using **Valentin.app** geocoding and localized search targeting.

---

## 🎯 6 Primary Care Categories Supported
1. **Family Medicine**
2. **Internal Medicine**
3. **Pediatrics**
4. **Geriatrics**
5. **Direct Primary Care**
6. **Concierge Medicine**
*(Plus options for **All 6 Categories** or **Custom Multi-select**)*

---

## ⚙️ Key Features
- **Clean Simple File Naming**: 
  - Output files are cleanly named by category and scrape run counter (e.g., `Family Medicine - 1.csv`, `Family Medicine - 2.csv`, `Pediatrics - 1.csv`, `All Primary Care - 1.csv`).
- **Interactive Terminal Prompts**:
  1. Prompts for Primary Care category selection first (`1-6`, `7` for All, `M` for custom).
  2. Prompts for target US location (single city/state, top 5 metros, top 20 nationwide metros, or custom list).
  3. Prompts for maximum records target (or 'all' for unlimited).
- **250 Records Checkpoint Prompt**:
  - Automatically pauses every **250 records** and asks if you want to **Continue** scraping the next batch or **Stop and generate the output CSV**.
- **Valentin.app Geolocation**: Uses `valentin.app` to resolve exact US geocodes and calculate precise Google UULE geo-targeting parameters.
- **Practice & Domain Filtering**: Extracts clean practice names and root official website domains (e.g. `familymedicineaustin.com`, `euphorahealth.com`), while automatically filtering out generic directories (Yelp, Healthgrades, ZocDoc, etc.).
- **Automatic Deduplication & Safe Export**: Prevents duplicate domains and ensures safe export even on `Ctrl+C` interrupt.

---

## 🚀 Installation & Setup

1. Open your terminal and navigate to the project directory:
   ```bash
   cd "/Users/sonusingh/Emitrr-Works-Tools/Primary Care-Finder"
   ```

2. Install dependencies (if not already installed):
   ```bash
   python3 -m pip install -r requirements.txt
   playwright install chromium
   ```

---

## 💻 How to Run

Run the scraper directly in your terminal:
```bash
python3 main.py
```

---

## 📁 Output CSV Format

Sample CSV output (`output/Family Medicine - 1.csv`):

| Company Name | Domain | Category | Location |
| :--- | :--- | :--- | :--- |
| Family Medicine Austin | familymedicineaustin.com | Family Medicine | Austin, TX, USA |
| Rosedale Family Care Partners, PA | rosedalefamilycare.com | Family Medicine | Austin, TX, USA |
| Premier Family Physicians @ Southwest Medical Village | pfpdocs.com | Family Medicine | Austin, TX, USA |

---

## 📂 Project Structure
```
Primary Care-Finder/
├── main.py              # Interactive CLI Entry Point (with 250-record prompt & simple naming)
├── scraper.py           # Playwright & Localized Scraping Engine
├── valentin.py          # Valentin.app Geocoding & UULE Generator
├── requirements.txt     # Python Dependencies
├── README.md            # Documentation
└── output/              # Clean CSV & JSON files (e.g. Family Medicine - 1.csv)
```
