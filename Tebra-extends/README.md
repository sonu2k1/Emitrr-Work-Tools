# 🏥 Tebra Care Provider & Practice Domain Scraper

High-performance, interactive Python scraper jo **Tebra Provider Profiles** se metadata extract karta hai aur unke **Practice Names** ke according unka official **Practice Domain** discover karta hai.

---

## 📋 Output CSV Columns

Script output CSV me exactly yeh columns extract karke save karta hai:

1. **`URL`** - Provider ka Tebra profile URL
2. **`Name`** - Doctor / Provider ka pura naam (titles jaise MD, FNP, DO ke sath)
3. **`Specialties`** - Medical specialty (e.g. Cardiologist, Cardiovascular Disease Physician)
4. **`Practice Name`** - Clinic ya hospital group ka naam
5. **`NPI Number`** - 10-digit National Provider Identifier (profile data ya URL slug se)
6. **`Location`** - Complete clinic address (Street, City, State, ZIP)
7. **`Phone`** - Clinic ka contact telephone number
8. **`Practice Domian(According to practice Name column)`** - Practice ka official website domain

---

## ✨ Key Features

- 🖥️ **Visually Stunning Terminal UI**: `rich` library par built live animated dashboard, real-time stats panel, colored progress bars, aur sliding table jo har scraped record ko live display karti hai.
- 💬 **Interactive Prompts**: Terminal me chalate hi aapse input file, output file, concurrency (threads), domain lookup on/off, aur test limits puchhega.
- ⚡ **Multi-Threaded Concurrency**: Configurable worker threads (default: 8 threads) ke sath high-speed scraping.
- 🌐 **Practice Domain Intelligence**:
  - **Tier 1: Persistent Cache** (`practice_domains_cache.json`) - Ek clinic ka domain milne ke baad usi clinic ke baaki sabhi doctors ke liye 0ms me cache se reuse hota hai.
  - **Tier 2: Clearbit Autocomplete API** - Instant enterprise domain lookup.
  - **Tier 3: Yahoo Search** - High-accuracy search without rate-limits or 202 challenge blocks.
- 🔄 **Auto-Resume Protection**: Agar scraping kisi bhi reason se pause/stop hoti hai, dobara chalane par pehle se scraped URLs automatically skip ho jaate hain. Zero duplicate requests.
- 💾 **Real-Time Disk Flushing**: Har ek scraped row immediately CSV me write aur disk par flush hoti hai. Terminal band karne par bhi koi data loss nahi hota.

---

## 🚀 How to Run

### Option 1: Interactive Mode (Recommended)
Sirf script run karein, terminal me interactive prompts open honge:

```bash
cd /Users/sonusingh/Emitrr-Works-Tools/Tebra-extends
python3 tebra_scraper.py
```
*(ya `./run.sh`)*

Aapko options select karne ka mauka milega:
1. Input CSV (Default: `Tebra-Browse - Profile URL.csv`)
2. Output CSV (Default: `tebra_providers_scraped.csv`)
3. Find Practice Domains? (Y/n)
4. Worker Threads (Default: `8`)
5. Limit (e.g. `50` for quick test, ya `all` pure 9,856 profiles ke liye)

---

### Option 2: CLI Flags Mode (Automated / Headless)

Aap directly arguments pass karke bhi chala sakte hain:

```bash
# Pure 9,856 URLs ko background me run karein:
python3 tebra_scraper.py -y

# Custom input/output aur 12 threads ke sath:
python3 tebra_scraper.py -i "Tebra-Browse - Profile URL.csv" -o "tebra_full_output.csv" -t 12 -y

# Quick test sirf first 25 records par:
python3 tebra_scraper.py -l 25 -o "sample_output.csv" -y

# Superfast mode (Practice Domain lookup disable karke):
python3 tebra_scraper.py --no-domain -t 15 -y
```

---

## 🛠️ CLI Options Reference

| Flag | Description | Default |
|---|---|---|
| `-i, --input` | Input CSV path jisme Profile URLs hain | `Tebra-Browse - Profile URL.csv` |
| `-o, --output` | Output CSV path | `tebra_providers_scraped.csv` |
| `-t, --threads` | Number of concurrent worker threads | `8` |
| `-l, --limit` | Limit number of URLs to scrape (0 = All) | `0` |
| `--no-domain` | Practice domain resolution disable karein (extra fast) | `False` |
| `--no-resume` | Output file overwrite karein | `False` |
| `-y, --yes` | Prompts skip karke direct execute karein | `False` |
| `-h, --help` | Help message show karein | - |

---

## 🛑 Safe Interruption (Ctrl+C)
Scraping ke dauran kabhi bhi `Ctrl + C` daba kar pause kar sakte hain. Script in-flight requests safely complete karegi, cache save karegi aur summary display karegi. Dobara script run karne par ye wahi se continue karegi!
