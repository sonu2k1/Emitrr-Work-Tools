# 🏥 Valentin.app Practice & Clinic Domain Scraper (US & Canada)

A high-accuracy localized Practice & Clinic Domain Finder built for **United States (US)** and **Canada (CA)** healthcare datasets, powered by **Valentin.app** Geocoding and Google UULE Localized Search.

---

## 🌟 Key Features

- 🎯 **Valentin.app Geocoding & UULE Precision**: Generates exact Google UULE tokens (v1 Canonical Protobuf & v2 Coordinate lat/lng) via `valentin.app/geocode` for localized SERP extraction.
- 🇺🇸 **United States & 🇨🇦 Canada Support**: Fully configured with `gl=US, hl=en` and `gl=CA, hl=en, google.ca`.
- 🩺 **Healthcare & Practice Name Normalizer**: Automatically handles doctor titles (`Dr.`, `MD`, `DDS`, `DMD`, `DO`, `DC`, `OD`, `DPM`), credentials, parenthesized location notes, and corporate legal suffixes (`PLLC`, `PC`, `Inc`, `LLC`).
- ⚡ **Multi-Tier Cascade Strategy**:
  1. Direct Domain Health & Parked-Page Verification (`.com`, `.ca`, `.org`)
  2. Valentin.app Localized Google Autocomplete & SERP
  3. Localized DuckDuckGo (US / CA)
  4. Localized Yahoo (US / CA)
  5. Clearbit Healthcare Directory
- 🖥️ **Modern Web Dashboard**: Real-time progress streaming (SSE), drag-and-drop CSV/Excel upload, instant filtering, 1-click CSV & Excel export.
- 💻 **High-Speed CLI & Python Scraper**: Support for both Node.js CLI (`node cli.js`) and Python script (`python3 scraper.py`).

---

## 🚀 Quick Start

### 1. Modern Web Dashboard (Recommended)

```bash
cd /Users/sonusingh/Emitrr-Works-Tools/Valentin-Search
npm start
```
Then open **[http://localhost:3000](http://localhost:3000)** in your browser.

- Select target country (**United States 🇺🇸** or **Canada 🇨🇦**)
- Drag and drop your practice CSV/Excel file
- Watch real-time streaming results and download enriched CSV / Excel!

---

### 2. Node.js Command Line Interface (CLI)

```bash
# Run on US practices
node cli.js -i sample_us_practices.csv -c US -o output_us.csv

# Run on Canada practices
node cli.js -i sample_canada_practices.csv -c CA -o output_canada.csv

# Single practice quick search
node cli.js -s "Aspen Dental" -c US
node cli.js -s "Altima Dental" -c CA
```

#### CLI Options:
| Flag | Description | Default |
|------|-------------|---------|
| `-i, --input` | Path to input CSV or Excel file | Required |
| `-o, --output` | Path to output CSV file | `output_valentin_domains.csv` |
| `-c, --country` | Target country (`US` or `CA`) | `US` |
| `--concurrency` | Number of concurrent search threads | `3` |
| `--delay` | Delay between batch requests in ms | `300` |
| `-s, --single` | Quick single practice domain lookup | - |

---

### 3. Python Scraper

```bash
pip install -r requirements.txt

# Run on US practices
python3 scraper.py -i sample_us_practices.csv -c US -o output_us.csv

# Run on Canada practices
python3 scraper.py -i sample_canada_practices.csv -c CA -o output_canada.csv

# Single search
python3 scraper.py -s "Smile Doctors Orthodontics" -c US
```

---

## 📊 CSV Format Supported

The scraper automatically detects standard practice name column headers:
- `Practice Name`, `Practice`, `Clinic Name`, `Clinic`, `Doctor Name`, `Hospital`, `Company Name`, `Name`, etc.
- Optional location columns: `Address`, `City`, `State` / `Province`, `Country` (`US` or `CA`).

---

## 🧪 Running Automated Tests

```bash
npm test
```
Verifies Valentin geocoding, UULE generation, practice name normalization, and end-to-end domain detection for US and Canada.
