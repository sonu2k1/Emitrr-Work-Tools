# 💼 Email Job Title & Seniority Finder (Python CLI)

A Python CLI tool that takes a CSV containing email addresses and enriches each row with:
- **Detected Full Name** (First Name, Last Name)
- **Job Title** (e.g., *General Dentist, Practice Manager, CEO, Orthodontist, Clinical Director*)
- **Seniority Tier** (e.g., *Owner / Executive, Director / VP, Manager / Admin, Practitioner / Doctor, Staff*)
- **Company / Practice Name**
- **LinkedIn Profile URL** (when found)
- **Confidence Score & Data Source**

---

## 🚀 Features

- **100% Free Multi-Engine Search**: Searches Google, DuckDuckGo, and Bing with LinkedIn dorking to discover public designations.
- **Smart Email Parsing**: Extracts names from emails like `john.smith@domain.com`, `dr.smith@domain.com`, `jdoe@domain.com`.
- **Role-Based Inbox Detection**: Automatically flags generic mailboxes (`info@`, `contact@`, `admin@`, `frontdesk@`, `billing@`).
- **Company Website Team Page Scraper**: Fallback crawler for `/team`, `/about`, `/providers`, `/doctors` pages.
- **Optional B2B API Key (Apollo.io)**: Connect your Apollo API key for instant 95%+ precision enrichment.
- **Real-Time Checkpointing**: Output CSV is continuously saved every few rows — no lost work if interrupted.
- **Interactive Rich Terminal UI**: Live progress bars, speed stats, and colored tables.

---

## 📦 Installation & Setup

1. Open your terminal and navigate to the directory:
```bash
cd "/Users/sonusingh/Emitrr-Works-Tools/Title FInder"
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

---

## 🛠️ How to Use (Commands)

### 1. Test a Single Email (Quick Check)
Test any email directly in your terminal to see the live breakdown:
```bash
python3 title_finder.py -e "satya.nadella@microsoft.com"
```
```bash
python3 title_finder.py -e "dr.smith@austindental.com"
```

### 2. Process a CSV File (Batch Mode)
Provide your input CSV file (email column is auto-detected):
```bash
python3 title_finder.py -i sample_emails.csv -o output_enriched.csv
```

### 3. Custom Concurrency & Speed
Adjust thread count (`-t`) and delay (`-d`):
```bash
python3 title_finder.py -i your_leads.csv -o results.csv -t 5 -d 0.5
```

### 4. Use with Apollo API Key (Optional for 10x Boost)
Either pass it as a flag:
```bash
python3 title_finder.py -i leads.csv --apollo-key "YOUR_APOLLO_KEY"
```
Or create a `.env` file:
```bash
APOLLO_API_KEY=your_key_here
```

---

## 📊 Output Columns Added to CSV

| Column Name | Example Value | Description |
|---|---|---|
| `Detected_First_Name` | `Satya` | Inferred or discovered first name |
| `Detected_Last_Name` | `Nadella` | Inferred or discovered last name |
| `Detected_Full_Name` | `Satya Nadella` | Full name of the contact |
| `Job_Title` | `Chief Executive Officer (CEO)` | Exact job title found |
| `Seniority` | `Owner / Executive (C-Suite)` | Seniority hierarchy level |
| `Company_Name` | `Microsoft` | Formatted company or practice |
| `LinkedIn_URL` | `https://www.linkedin.com/in/...` | Matched LinkedIn profile link |
| `Confidence_Score` | `High` / `Medium` / `Low` | Confidence of the match |
| `Data_Source` | `LinkedIn / Web Search` | Search / Scraper / API / Website |
| `Status` | `Found` / `Not Found` | Status indicator |
