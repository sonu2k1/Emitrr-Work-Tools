# 🏥 Healthcare Domain Finder & Classifier (Terminal Tool)

Ek fast, multi-threaded CLI tool jo CSV file se domains read karta hai aur classify karta hai ki wo **Healthcare / Clinics / Hospitals / Dental / Mental Health** etc. se related hai ya **Non-Healthcare** (Automotive, Real Estate, Legal, Roofing, Food, etc.) hai.

---

## 🚀 Kaise Use Karein (How to Run)

### 1. Simple Run (Default `input.csv` ke sath):
Apne domains ko `input.csv` me daalein aur terminal me run karein:
```bash
cd /Users/sonusingh/Emitrr-Works-Tools/Healthcare-findby-domain
python3 main.py
```

### 2. Custom Input / Output Files ke sath:
Agar aapke paas koi dusri CSV file hai:
```bash
python3 main.py -i my_leads.csv -o my_results.csv
```

### 3. Concurrency (Speed) & Timeout Badhane ke liye:
Badi files (1000+ domains) ke liye threads badha sakte hain:
```bash
python3 main.py -i input.csv -o output.csv --threads 25 --timeout 10
```

---

## 📊 Features & Capabilities

1. **Auto Domain Detection**:
   - Aapke CSV me column ka naam chahe `domain`, `website`, `url`, `Company Domain`, `link` kuch bhi ho, ye automatically detect kar leta hai.
   - Domain se `http://`, `https://`, `www.` aur trailing slashes automatically clean ho jate hain.

2. **Accurate Multi-Specialty Detection**:
   - **Hospitals & Health Systems**
   - **Dental & Orthodontics**
   - **Urgent Care & Walk-in Clinics**
   - **Primary Care & Family Medicine**
   - **Dermatology & Skin Clinics**
   - **Orthopedics & Spine**
   - **Chiropractic & Physical Therapy**
   - **Eye Care / Optometry / Ophthalmology**
   - **Mental Health, Psychiatry & Therapy**
   - **Women's Health & OB/GYN / Fertility**
   - **Pediatrics**
   - **Cardiology, Oncology, Urology, ENT, Podiatry, Senior Care, etc.**

3. **Negative Industry Filters (Prevents False Positives)**:
   - Roofing, HVAC, Plumbing, Construction
   - Automotive, Mechanics, Towing
   - Real Estate, Mortgages, Rentals
   - Law Firms, Lawyers
   - Food, Restaurants, Bakeries
   - Tech, Marketing Agencies, E-commerce

4. **Detailed Output Columns Generated**:
   - `Cleaned_Domain`: Clean domain name
   - `Is_Healthcare`: `YES` / `NO`
   - `Healthcare_Category`: e.g. *Dental & Orthodontics*, *Hospital & Health System*, *Non-Healthcare (Roofing)*
   - `Confidence`: *High*, *Medium*, *Low*
   - `Reason`: Detailed explanation for the classification
   - `Page_Title`: Extracted website title
   - `Site_Status`: Live status / HTTP code / error details
   - `Detected_Specialties`: Any specific medical tags matched

5. **Offline / Fallback Intelligence**:
   - Agar kisi domain ki website temporarily down ho ya timeout ho jaye, to domain keywords ke base par smart heuristic classification karta hai.
