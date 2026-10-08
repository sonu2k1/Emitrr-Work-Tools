# 🩺 EHR & Patient Portal Scraper

An intelligent, multi-threaded Python scraper designed to accurately identify **EHR Providers** and **Patient Portal URLs** for healthcare practices and domains from CSV/Excel files.

---

## ⚡ Key Features

- **50+ Healthcare EHR & Portal Signatures Supported**:
  - **Epic** (*MyChart, Patient Gateway, My CS-Link*)
  - **AthenaHealth** (*AthenaPatient, AthenaCommunicator, AthenaNet*)
  - **eClinicalWorks** (*Healow, mycw.net*)
  - **ModMed** (*EMA, Modernizing Medicine, myehr.com*)
  - **NextGen Healthcare** (*NextMD*)
  - **Cerner / Oracle Health** (*HealtheLife, Cerner Health*)
  - **Allscripts / Veradigm** (*FollowMyHealth*)
  - **Greenway Health** (*MyHealthRecord, PrimeSuite, Intergy*)
  - **Kareo / Tebra** (*Portal / Patient Portal*)
  - **AdvancedMD** (*Patient Portal*)
  - **DrChrono** (*OnPatient*)
  - **ChiroTouch**, **WebPT**, **Jane App**, **SimplePractice**, **TherapyNotes**
  - **Phreesia**, **NexHealth**, **Solutionreach**, **CharmHealth**, **PrognoCIS**
  - **Dental Practice Portals**: Dentrix, Eaglesoft, Open Dental, Curve Dental, etc.
- **Smart Multi-Step Detection**:
  1. Probes common patient subdomains (`mychart.domain.com`, `portal.domain.com`, etc.)
  2. Scans Homepage HTML (`<a>`, `<button>`, `<iframe>`, and `<script>` widgets)
  3. Inspects JavaScript / Single Page App (SPA) data payloads
  4. Crawls patient-specific sub-pages (`/patient-portal`, `/portal`, `/patients`, `/patient-login`)
- **High Concurrency & Speed**: Multi-threaded with `ThreadPoolExecutor` and live `tqdm` progress tracking.
- **Flexible Formats**: Reads & writes both `.csv` and `.xlsx` (Excel) formats.
- **Auto-Detection**: Automatically identifies domain columns (`domain`, `website`, `url`, etc.).

---

## 📦 Installation

```bash
cd EHR-Scrapper
pip install -r requirements.txt
```

---

## 🚀 Usage

### 1. Interactive Mode
Run without arguments for an interactive guide:
```bash
python3 scraper.py
```

### 2. Process a CSV File
```bash
python3 scraper.py -i sample_domains.csv -o output_results.csv
```

### 3. Specify Domain Column & Concurrency
```bash
python3 scraper.py -i input.csv -o enriched.csv -c "Company Website" -t 15 --excel
```

### 4. Test a Single Domain
```bash
python3 scraper.py --single hopkinsmedicine.org
```

---

## 🛠️ CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `-i, --input` | Input CSV or Excel file path | None |
| `-o, --output` | Output CSV filename | `enriched_ehr_portals.csv` |
| `-c, --column` | Specific column containing the domain | Auto-detected |
| `-t, --threads`| Number of concurrent threads | `10` |
| `--timeout` | HTTP request timeout in seconds | `12` |
| `--excel` | Also save results as an Excel (`.xlsx`) file | `False` |
| `--no-subpages`| Disable subpage crawling (faster, homepage-only) | `False` |
| `--single` | Test a single domain directly from CLI | None |
| `--sample` | Run verification test on preloaded test domains | None |

---

## 📊 Output Schema

The resulting CSV/Excel file contains:
- `practice_name` (original input columns preserved)
- `domain` (original input domain)
- `Detected_Domain` (normalized domain)
- `EHR_Name` (e.g. `Epic (MyChart)`, `AthenaHealth`, `eClinicalWorks (Healow)`, etc.)
- `EHR_Category` (e.g. `Cloud EHR`, `Hospital System`, `Specialty EHR`)
- `Patient_Portal_URL` (Direct link to the practice's portal login)
- `Portal_Status` (`Found`, `Generic Portal Found`, `No Portal Detected`, `Site Unreachable`)
- `Confidence` (`High`, `Medium`, `None`)
- `Detection_Method` (e.g. `Direct Subdomain`, `Direct URL`, `Subpage Crawl`, `Anchor Text Match`)
