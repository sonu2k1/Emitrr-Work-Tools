# 🏥 Healthcare & Clinic Analyzer + Location Finder

An intelligent company enrichment tool that processes CSV files with company names to detect whether they belong to **Healthcare / Clinics / Medical Practices**, classifies their medical specialties, detects their **Physical & Geographic Location** (City, State, Country), and exports enriched CSV datasets.

---

## 🌟 Key Features

1. **Healthcare & Clinic Classifier**:
   - Detects **Healthcare / Clinic / Medical** businesses vs Non-Healthcare (Roofing, Legal, Automotive, HVAC, Food, Tech, etc.).
   - Categorizes into 20+ specialized medical domains: *Dental & Oral Health, Chiropractic & Spine, Dermatology, Primary Care & Family Medicine, Orthopedics, Pediatrics, Physical Therapy & Rehab, Ophthalmology & Optometry, Mental Health, Cardiology, Women's Health & OB/GYN, Urgent Care, Hospital & Health System, Veterinary, Podiatry, Gastroenterology, Allergy & Immunology, Medical Aesthetics / Med Spa, etc.*
   - Provides confidence scores (`High`, `Medium`, `Low`) and exact reason / signals.

2. **Geographic Location Detection**:
   - Extracts City, State, Country, and Street addresses using:
     - Embedded company name locations (e.g., *"Austin Smile Clinic"* -> `Austin, TX, USA`)
     - Schema.org JSON-LD structured `PostalAddress`
     - Address RegEx parsing (`City, State ZIP`, `Street, City, State`)
     - Search snippets and knowledge graph data

3. **Modern Glassmorphism Web App**:
   - Live drag-and-drop CSV upload with smart column auto-detection.
   - Real-time Server-Sent Events (SSE) progress streaming.
   - Interactive data table with live filters (*All*, *Healthcare Only*, *Non-Healthcare*).
   - Single Company Deep Inspector tab for on-the-fly testing.
   - One-click Enriched CSV download.

4. **Command-Line Interface (CLI)**:
   - Run batch processing directly from terminal with configurable concurrency.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd Healthcare-finder
npm install
```

### 2. Start the Web Dashboard
```bash
npm run dev
# Or: node server.js
```
Open your browser and navigate to: **`http://localhost:3000`**

### 3. Run via Terminal CLI
```bash
node cli.js sample_companies.csv enriched_output.csv --concurrency 4
```

### 4. Run Automated Tests
```bash
npm test
# Or: node test.js
```

---

## 📊 Enriched CSV Columns

The output CSV retains all your original columns and appends the following:
| Column | Description | Example |
| :--- | :--- | :--- |
| `Is_Healthcare` | `Yes` or `No` | `Yes` |
| `Healthcare_Category` | Medical specialty or industry category | `Dental & Oral Health` |
| `Detected_Location` | Physical location / City, State | `Austin, TX, USA` |
| `Confidence_Score` | Confidence level | `High` |
| `Analysis_Reason` | Concise evidence & signals | `Confirmed Healthcare entity (Dental)` |
| `Website_Domain` | Official website domain | `austinsmile.com` |

---

## 📁 Project Structure

```
Healthcare-finder/
├── lib/
│   ├── analyzer.js              # Master analysis & batch processing pipeline
│   ├── healthcareClassifier.js  # Medical specialty & negative classifier
│   ├── locationDetector.js      # Geo and address extraction engine
│   └── searchEngine.js          # Web search & landing page scraper
├── public/
│   ├── index.html               # Web UI template
│   ├── style.css                # Dark glassmorphism styling
│   └── app.js                   # Frontend controller & SSE streaming
├── cli.js                       # Command-line interface
├── server.js                    # Express server & API endpoints
├── sample_companies.csv         # Sample dataset
├── test.js                      # Unit and integration test suite
└── package.json
```
