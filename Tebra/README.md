# Tebra Care Provider Scraper

Yeh scraper `https://www.tebra.com/care/` ke Navbar ke **Browse** button ko click karke popup ke sabhi 12 specialties aur unke corresponding locations ke provider profile links aur details ko scrape karke CSV file me save karta hai.

---

### Target Specialties (from Browse Popup)
1. **Cardiologists**
2. **Chiropractors**
3. **Dentists**
4. **Dermatologists**
5. **Family Physicians**
6. **OB-GYNs**
7. **Ophthalmologists**
8. **Orthopedic Surgeons**
9. **Pediatricians**
10. **Physical Therapists**
11. **Podiatrists**
12. **Psychiatrists**

---

### CSV Output Format
CSV file me following columns save hote hain:
- **Specialty Category**: Jaise `Family Physicians`, `Cardiologists`, etc.
- **Location**: City & State (jaise `Atlanta, GA`, `Dallas, TX`)
- **Provider Name**: Doctor / Clinic ka naam (jaise `C. Sainvil`)
- **Provider Specialty**: Specific specialty (jaise `Family Physician`, `Internist`)
- **Distance**: Distance (jaise `2.2 mi`)
- **Address**: Address / Telehealth (jaise `Telehealth Visits Atlanta, GA 30308`)
- **Profile URL**: Provider ka profile link (jaise `https://www.tebra.com/care/provider/c-sainvil-1609312909`)
- **Location Page URL**: Jis search results page se doctor mila

---

### Installation

```bash
cd /Users/sonusingh/Emitrr-Works-Tools/Tebra
pip install -r requirements.txt
playwright install chromium
```

---

### How to Run

#### 1. Sabhi 12 Specialties aur Sabhi Locations scrape karne ke liye (Full Run):
```bash
python3 tebra_scraper.py
```
*(Yeh by default `tebra_providers.csv` me sara data realtime save karega)*

#### 2. Specific Specialty scrape karne ke liye:
```bash
# Sirf Family Physicians ke liye:
python3 tebra_scraper.py --specialty "Family Physicians"

# Multiple specialties ke liye:
python3 tebra_scraper.py --specialty "Cardiologists" "Dentists" "Dermatologists"
```

#### 3. Test run (Per Location sirf first page scrape karega):
```bash
python3 tebra_scraper.py --max-pages 1 --output test_sample.csv
```

#### 4. Live Browser UI dekhne ke liye (`--headed`):
```bash
python3 tebra_scraper.py --specialty "Family Physicians" --headed
```

#### 5. Custom Output file name:
```bash
python3 tebra_scraper.py --output my_doctors_list.csv
```

---

### Key Features
- **Real-time CSV Streaming**: Data continuous write hota hai (`flush=True`), script beech me band hone par bhi saved data lose nahi hota.
- **Duplicate Prevention**: Same profile link ko dubara add nahi karta.
- **Automatic Pagination**: `a.rel-next` ke through har location ke sabhi pages (jaise 89 providers) automatically scrape karta hai.
- **Auto-Resume**: Agar script dubara chalaoge toh existing CSV ko read karke duplicate entries skip karega.
