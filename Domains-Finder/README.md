# 🔍 CSV Company Domain Finder

A fast, accurate, and full-featured tool to discover official website domains and logos for company names in any CSV file.

![Dashboard Preview](https://img.shields.io/badge/Status-Active-brightgreen) ![Node Version](https://img.shields.io/badge/Node.js-v18+-blue)

---

## ✨ Features

- **🎯 High Accuracy**: Uses multi-tier search engine strategy (Clearbit Autocomplete API + DuckDuckGo/Google search fallback + Social noise filter).
- **🚀 Ultra Fast**: Parallel batch processing with configurable concurrency and rate limiting.
- **🖥️ Web Visual Dashboard**: Modern, sleek browser UI with drag-and-drop CSV upload, column auto-detection, live progress streaming (SSE), and 1-click CSV download.
- **💻 CLI Terminal Tool**: Execute direct terminal commands for bulk CSV files.
- **🖼️ Logo Enrichment**: Includes company favicon / logo URLs in the output CSV.
- **🛡️ Noise & Social Filtering**: Automatically filters out irrelevant sites like LinkedIn, Facebook, Wikipedia, Twitter, Crunchbase, Glassdoor, etc.

---

## 🚀 Quick Start Guide

### 1. Installation

Navigate to the project folder and install dependencies:

```bash
cd /Users/sonusingh/Emitrr-Works-Tools/Domains-Finder
npm install
```

---

### 🌐 Mode A: Web Visual Dashboard (Browser Interface)

Start the Web Application server:

```bash
npm start
```

Open your browser at:
👉 **[http://localhost:3000](http://localhost:3000)**

**How to use Web UI:**
1. Drag & drop your `.csv` file onto the upload zone.
2. Select the column containing company names (auto-detected by default).
3. Click **"Start Finding Domains"**.
4. Watch the live progress dashboard, found domains, and confidence badges.
5. Click **"Export Enriched CSV"** to download your updated CSV file.

---

### 💻 Mode B: CLI Command Tool (Terminal Interface)

Run direct terminal commands on any CSV file:

```bash
node cli.js -i sample_companies.csv -o output_domains.csv
```

#### CLI Options:
| Flag | Description | Default |
|------|-------------|---------|
| `-i, --input` | Path to input CSV file (Required) | - |
| `-o, --output` | Path for enriched CSV output | `<input>_domains.csv` |
| `-c, --column` | Header name for company names | Auto-detected |
| `--concurrency` | Number of parallel search requests | `3` |
| `--delay` | Delay in ms between requests | `300` |

#### Example Command:
```bash
node cli.js -i leads.csv -o enriched_leads.csv -c "Organization Name" --concurrency 5
```

---

## 📊 Sample Output Format

| Company Name | Found Domain | Domain Status | Domain Source | Company Logo |
|--------------|--------------|---------------|---------------|--------------|
| Microsoft Corporation | `microsoft.com` | Found | Clearbit Autocomplete | `https://logo.clearbit.com/microsoft.com` |
| Stripe Inc. | `stripe.com` | Found | Clearbit Autocomplete | `https://logo.clearbit.com/stripe.com` |
| Google LLC | `google.com` | Found | Clearbit Autocomplete | `https://logo.clearbit.com/google.com` |
| Notion Labs | `notion.so` | Found | Clearbit Autocomplete | `https://logo.clearbit.com/notion.so` |
| Airbnb Inc | `airbnb.com` | Found | Clearbit Autocomplete | `https://logo.clearbit.com/airbnb.com` |
| Zomato India | `zomato.com` | Found | Clearbit Autocomplete | `https://logo.clearbit.com/zomato.com` |

---

## 🛠️ Project Architecture

```
Domains-Finder/
├── lib/
│   └── domainFinder.js    # Core multi-strategy domain search engine & scoring
├── public/
│   ├── index.html         # Web Dashboard UI layout
│   ├── style.css          # Glassmorphism dark mode styles
│   └── app.js             # Client JS (SSE streaming, drag-and-drop, export)
├── server.js              # Express REST & SSE server
├── cli.js                 # Command-line utility tool
├── test.js                # Search engine test script
├── sample_companies.csv   # Sample CSV file for testing
└── package.json           # Node dependencies
```
