# WebPT Practice & Domain Scraper

A fast, multi-threaded scraper to extract **Practice Names** and their **Website Domains** from WebPT appointment sites (`https://sites.webpt.com/{id}/request-an-appointment`).

---

## 🚀 Features

- **Practice Name Extraction**: Accurately extracts practice names from:
  - The `"Why <Practice Name>?"` headline (as shown in the WebPT appointment template)
  - Footer practice name & metadata
  - Page title & Next.js page properties
- **Domain Discovery**: Automatically discovers and resolves the official website **domain** for each practice (e.g., `atlantispt.com`, `txortho.com`, `fyzical.com`).
- **Error Filtering**: Automatically skips 404s, unconfigured sites, connection timeouts, and default uncustomized placeholder pages (e.g. `"Why get physical therapy?"`).
- **High Performance**: Multi-threaded with `ThreadPoolExecutor` and connection pooling (scans hundreds of pages per minute).
- **Auto-Save & Resume**:
  - Live auto-saving to both **CSV** (`webpt_practices.csv`) and **Excel** (`webpt_practices.xlsx`).
  - Progress checkpointing in `progress.json` allows pausing (`Ctrl+C`) and resuming anytime without re-scanning.
- **Rich Terminal UI**: Live progress bar, speed tracker, elapsed time, and color-coded results.

---

## 📦 Setup

Make sure you have Python 3 installed. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Usage

### 1. Run the default scan (IDs 20000 to 30000)
```bash
python3 scraper.py
```

### 2. Custom ID Range
```bash
# Scan from 20000 to 25000
python3 scraper.py --start 20000 --end 25000
```

### 3. Adjust Speed / Concurrency (Workers)
```bash
# Run with 50 concurrent threads
python3 scraper.py --start 20000 --end 30000 --workers 50
```

### 4. Custom Output Filename
```bash
python3 scraper.py --output my_webpt_results.csv
```

### 5. Resuming vs Starting Fresh
- **Resume (Default)**: Automatically resumes from where you left off if `progress.json` or `webpt_practices.csv` exists.
- **Fresh Scan**: Use `--no-resume` to ignore previous checkpoints:
  ```bash
  python3 scraper.py --no-resume
  ```

---

## 📊 Output Data Columns

| Column | Description | Example |
| :--- | :--- | :--- |
| `site_id` | WebPT site identifier | `22212` |
| `practice_name` | Extracted clinic / practice name | `Atlantis Physical and Occupational Therapy` |
| `domain` | Practice website domain | `atlantispt.com` |
| `page_title` | HTML page title | `Request an Appointment \| Atlantis Physical Therapy \| Torrance` |
| `footer_name` | Footer clinic name | `Atlantis Physical & Occupational Therapy` |
| `custom_domain` | Custom domain if configured in WebPT | `example.com` |
| `created_at` | Page creation timestamp | `2020-10-01T14:29:06.646-04:00` |
| `updated_at` | Page last update timestamp | `2025-08-11T14:51:04.854-04:00` |
| `url` | Direct URL to request appointment page | `https://sites.webpt.com/22212/request-an-appointment` |
