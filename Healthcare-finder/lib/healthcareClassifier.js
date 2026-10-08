/**
 * Healthcare & Clinic Classification Engine
 * Analyzes company names, website snippets, metadata, and HTML content
 * to identify whether an entity is a Healthcare provider / Clinic and categorize its specialty.
 */

const SPECIALTY_DEFINITIONS = [
  {
    category: 'Dental & Oral Health',
    keywords: [
      'dental', 'dentist', 'dentistry', 'orthodontics', 'orthodontist', 'periodontics',
      'endodontics', 'oral surgery', 'prosthodontics', 'teeth whitening', 'implants',
      'pediatric dentist', 'smile studio', 'dental care', 'dds', 'dmd', 'oral health'
    ],
    patterns: [
      /\b(dental|dentist|dentistry|orthodontist|periodontist|endodontist|invisalign|dds|dmd)\b/i,
      /\b(tooth|teeth|cavity|root canal|dental hygiene|oral care)\b/i
    ]
  },
  {
    category: 'Chiropractic & Spine',
    keywords: [
      'chiropractic', 'chiropractor', 'spine care', 'spinal', 'subluxation', 'back pain',
      'chiro', 'spinal adjustment', 'dc', 'chiropractic clinic', 'wellness chiropractic'
    ],
    patterns: [
      /\b(chiro|chiropractic|chiropractor|spine\s+clinic|spinal\s+care|subluxation|d\.c\.)\b/i
    ]
  },
  {
    category: 'Dermatology & Skin Care',
    keywords: [
      'dermatology', 'dermatologist', 'skin cancer', 'mohs surgery', 'acne treatment',
      'skin care clinic', 'cosmetic dermatology', 'dermatologic', 'aesthetic medicine'
    ],
    patterns: [
      /\b(dermatolog(y|ist|ical)|skin\s+clinic|mohs|eczema|psoriasis|skin\s+cancer)\b/i
    ]
  },
  {
    category: 'Primary Care & Family Medicine',
    keywords: [
      'primary care', 'family medicine', 'family practice', 'internal medicine',
      'general practice', 'general practitioner', 'family health', 'preventive care',
      'annual checkup', 'pcp', 'wellness clinic', 'community health center'
    ],
    patterns: [
      /\b(primary\s+care|family\s+medicine|family\s+practice|internal\s+medicine|general\s+practitioner|fammed)\b/i
    ]
  },
  {
    category: 'Orthopedics & Sports Medicine',
    keywords: [
      'orthopedic', 'orthopedics', 'orthopaedics', 'sports medicine', 'joint replacement',
      'knee replacement', 'hip replacement', 'bone and joint', 'arthroscopy', 'ortho'
    ],
    patterns: [
      /\b(orthopedic|orthopaedics|orthopaedic|sports\s+medicine|joint\s+replacement|bone\s+and\s+joint)\b/i
    ]
  },
  {
    category: 'Pediatrics',
    keywords: [
      'pediatric', 'pediatrics', 'pediatrician', 'childrens clinic', 'kids health',
      'child healthcare', 'adolescent medicine', 'pediatric care'
    ],
    patterns: [
      /\b(pediatric|pediatrics|pediatrician|children'?s\s+health|children'?s\s+clinic)\b/i
    ]
  },
  {
    category: 'Physical Therapy & Rehab',
    keywords: [
      'physical therapy', 'physiotherapy', 'physical therapist', 'occupational therapy',
      'rehabilitation', 'speech therapy', 'rehab clinic', 'kinesiology', 'dpt', 'pt clinic'
    ],
    patterns: [
      /\b(physical\s+therapy|physiotherapy|physical\s+therapist|occupational\s+therapy|rehab(ilitation)?|dpt)\b/i
    ]
  },
  {
    category: 'Ophthalmology & Optometry',
    keywords: [
      'optometry', 'optometrist', 'ophthalmology', 'ophthalmologist', 'eye care',
      'eye clinic', 'lasik', 'cataract surgery', 'vision center', 'retina specialist',
      'glaucoma', 'cornea'
    ],
    patterns: [
      /\b(optometr(y|ist)|ophthalmolog(y|ist)|eye\s+care|eye\s+clinic|vision\s+center|lasik|retina)\b/i
    ]
  },
  {
    category: 'Mental Health & Psychology',
    keywords: [
      'psychiatry', 'psychiatrist', 'psychology', 'psychologist', 'mental health',
      'behavioral health', 'counseling', 'psychotherapy', 'therapist', 'addiction treatment',
      'substance abuse', 'lcsw', 'lmft'
    ],
    patterns: [
      /\b(psychiatr(y|ist)|psycholog(y|ist)|mental\s+health|behavioral\s+health|counseling|psychotherapy|therapist|lcsw|lmft)\b/i
    ]
  },
  {
    category: 'Urgent Care & Walk-in Clinic',
    keywords: [
      'urgent care', 'walk-in clinic', 'immediate care', 'express care', 'after hours clinic',
      'minor emergency', 'convenient care'
    ],
    patterns: [
      /\b(urgent\s+care|walk-?in\s+clinic|immediate\s+care|express\s+care|after\s+hours\s+clinic)\b/i
    ]
  },
  {
    category: 'Hospital & Health System',
    keywords: [
      'hospital', 'medical center', 'health system', 'healthcare system', 'regional medical center',
      'memorial hospital', 'general hospital', 'infirmary', 'emergency room'
    ],
    patterns: [
      /\b(hospital|medical\s+center|health\s+system|healthcare\s+system|regional\s+medical)\b/i
    ]
  },
  {
    category: 'Cardiology & Heart Health',
    keywords: [
      'cardiology', 'cardiologist', 'heart institute', 'cardiovascular', 'heart care',
      'arrhythmia', 'cardiac', 'echocardiogram'
    ],
    patterns: [
      /\b(cardiolog(y|ist)|cardiovascular|heart\s+center|heart\s+institute|cardiac)\b/i
    ]
  },
  {
    category: 'Women\'s Health & OB/GYN',
    keywords: [
      'ob/gyn', 'obgyn', 'gynecology', 'obstetrics', 'maternity', 'fertility', 'womens health',
      'prenatal care', 'midwifery', 'reproductive medicine', 'ivf'
    ],
    patterns: [
      /\b(ob\/gyn|obgyn|gynecolog(y|ist)|obstetric(s|ian)|maternity|fertility\s+clinic|women'?s\s+health|ivf)\b/i
    ]
  },
  {
    category: 'Veterinary & Animal Clinic',
    keywords: [
      'veterinary', 'veterinarian', 'vet clinic', 'animal hospital', 'pet hospital',
      'pet clinic', 'dvm', 'animal care'
    ],
    patterns: [
      /\b(veterinar(y|ian)|vet\s+clinic|animal\s+hospital|pet\s+hospital|dvm)\b/i
    ]
  },
  {
    category: 'Podiatry & Foot Care',
    keywords: [
      'podiatry', 'podiatrist', 'foot and ankle', 'foot clinic', 'dpm', 'bunion surgery'
    ],
    patterns: [
      /\b(podiatr(y|ist)|foot\s+and\s+ankle|foot\s+clinic|dpm)\b/i
    ]
  },
  {
    category: 'Gastroenterology & Digestive',
    keywords: [
      'gastroenterology', 'gastroenterologist', 'endoscopy', 'colonoscopy', 'digestive health',
      'gi clinic', 'digestive disease'
    ],
    patterns: [
      /\b(gastroenterolog(y|ist)|endoscopy|colonoscopy|digestive\s+health|gi\s+clinic)\b/i
    ]
  },
  {
    category: 'Oncology & Cancer Care',
    keywords: [
      'cancer', 'oncology', 'oncologist', 'cancer center', 'cancer institute',
      'chemotherapy', 'radiation oncology', 'infusion center', 'hematology', 'tumor'
    ],
    patterns: [
      /\b(oncolog(y|ist)|cancer\s+center|cancer\s+institute|chemotherapy|hematolog(y|ist)|radiation\s+oncology)\b/i
    ]
  },
  {
    category: 'Allergy & Immunology',
    keywords: [
      'allergy', 'allergist', 'immunology', 'asthma clinic', 'allergy and asthma',
      'immunotherapy', 'sinus and allergy'
    ],
    patterns: [
      /\b(allerg(y|ist)|immunolog(y|ist)|asthma\s+clinic)\b/i
    ]
  },
  {
    category: 'Medical Aesthetics & Med Spa',
    keywords: [
      'med spa', 'medspa', 'medical spa', 'botox clinic', 'aesthetic clinic',
      'laser clinic', 'cosmetic clinic', 'wellness spa'
    ],
    patterns: [
      /\b(med\s*spa|medical\s+spa|botox|aesthetic\s+clinic|cosmetic\s+laser)\b/i
    ]
  },
  {
    category: 'General Healthcare & Clinic',
    keywords: [
      'health', 'healthcare', 'clinic', 'medical', 'medicine', 'doctor', 'physicians',
      'care center', 'wellness center', 'treatment center', 'specialists'
    ],
    patterns: [
      /\b(healthcare|medical\s+group|medical\s+associates|physicians?|clinic|wellness\s+center)\b/i
    ]
  }
];

// Healthcare indicator keywords for domain or company name matching
const HEALTHCARE_NAME_KEYWORDS = [
  'health', 'healthcare', 'medical', 'medicine', 'clinic', 'clinics', 'doctor', 'doctors', 'dr',
  'dent', 'dental', 'dentist', 'dentistry', 'ortho', 'orthodont', 'orthopedic', 'chiro', 'chiropractic',
  'derm', 'dermatology', 'pediatric', 'pediatrics', 'optom', 'optometry', 'ophthalmology', 'eye',
  'vision', 'rehab', 'therapy', 'therapies', 'physio', 'physiotherapy', 'cardio', 'cardiology',
  'obgyn', 'gyn', 'fertility', 'podiatry', 'foot', 'spine', 'pain', 'urgent', 'urgentcare',
  'hospice', 'radiology', 'imaging', 'mri', 'dialysis', 'rx', 'pharm', 'pharmacy', 'vet',
  'veterinary', 'wellness', 'physician', 'physicians', 'md', 'dds', 'dmd', 'dpm', 'dc',
  'surgery', 'surgical', 'hospital', 'hospitals', 'infirmary', 'urology', 'neurology',
  'oncology', 'cancer', 'gastro', 'allergy', 'asthma', 'ent', 'audiology', 'hearing', 'sleep', 'vein'
];

// Strong non-healthcare industry keywords
const NON_HEALTHCARE_PATTERNS = [
  {
    category: 'Roofing & Construction',
    patterns: [/\b(roofing|roofs?|gutters?|shingles?|siding|general\s+contractor|construction|builder|framing|remodeling|drywall|decking)\b/i]
  },
  {
    category: 'Automotive',
    patterns: [/\b(auto\s+repair|mechanic|car\s+wash|dealership|auto\s+body|towing|tire\s+shop|oil\s+change|detailing|motors|automotive|used\s+cars|collision)\b/i]
  },
  {
    category: 'Plumbing & HVAC',
    patterns: [/\b(plumbing|plumber|hvac|air\s+conditioning|furnace|heating\s+and\s+cooling|drain\s+cleaning|septic)\b/i]
  },
  {
    category: 'Legal & Law Firm',
    patterns: [/\b(law\s+firm|law\s+offices?|attorneys?|lawyers?|legal\s+services|personal\s+injury|criminal\s+defense|litigation|paralegal|counsel)\b/i]
  },
  {
    category: 'Real Estate & Property',
    patterns: [/\b(real\s+estate|realtor|realty|property\s+management|vacation\s+rentals?|mortgage|escrow|title\s+company)\b/i]
  },
  {
    category: 'Food, Beverage & Hospitality',
    patterns: [/\b(restaurant|bakery|café|cafe|brewery|winery|catering|pizza|bar\s+and\s+grill|food\s+truck|hotel|motel|resort)\b/i]
  },
  {
    category: 'Tech, Software & Marketing',
    patterns: [/\b(software\s+development|saas|digital\s+marketing|seo\s+agency|web\s+design|it\s+support|cloud\s+services)\b/i]
  },
  {
    category: 'Home & Commercial Services',
    patterns: [/\b(pest\s+control|landscaping|lawn\s+care|locksmith|flooring|carpet\s+cleaning|tree\s+service|cleaning\s+service|maid\s+service|electrician|electrical)\b/i]
  },
  {
    category: 'Financial & Insurance',
    patterns: [/\b(accounting|cpa|bookkeeping|tax\s+services|financial\s+advisor|wealth\s+management|insurance\s+agency)\b/i]
  },
  {
    category: 'Retail & Jewelry',
    patterns: [/\b(jewelry|jeweller|boutique|clothing\s+store|furniture\s+store|mattress|appliance\s+store)\b/i]
  }
];

/**
 * Classify company based on combined text (name, website text, meta description, search snippets)
 * @param {string} companyName 
 * @param {object} contextData - { snippetText, metaText, titleText, bodyText, domain, schemaTypes }
 * @returns {object} Classification result
 */
function classifyHealthcare(companyName, contextData = {}) {
  const nameClean = (companyName || '').toLowerCase().trim();
  const domain = (contextData.domain || '').toLowerCase().trim();
  const title = (contextData.titleText || '').toLowerCase();
  const meta = (contextData.metaText || '').toLowerCase();
  const snippet = (contextData.snippetText || '').toLowerCase();
  const body = (contextData.bodyText || '').toLowerCase();
  const schemaTypes = Array.isArray(contextData.schemaTypes) ? contextData.schemaTypes : [];

  const combinedText = `${nameClean} ${domain} ${title} ${meta} ${snippet} ${body}`.trim();

  let healthcareScore = 0;
  let nonHealthcareScore = 0;
  let detectedSpecialty = null;
  let matchedHealthcareSignals = [];
  let matchedNonHealthcareSignals = [];

  // 1. Schema.org verification (High Trust Signal)
  const healthcareSchemaTypes = [
    'medicalbusiness', 'dentist', 'physician', 'hospital', 'medicalclinic',
    'chiropractor', 'pharmacy', 'optician', 'veterinarycare', 'diagnosticlab'
  ];
  for (const st of schemaTypes) {
    const stLower = st.toLowerCase();
    if (healthcareSchemaTypes.some(h => stLower.includes(h))) {
      healthcareScore += 25;
      matchedHealthcareSignals.push(`Schema.org type: ${st}`);
    }
  }

  // 2. Check Name direct indicators
  for (const kw of HEALTHCARE_NAME_KEYWORDS) {
    const reg = new RegExp(`\\b${kw}\\b`, 'i');
    if (reg.test(nameClean)) {
      healthcareScore += 8;
      matchedHealthcareSignals.push(`Name keyword: "${kw}"`);
    }
  }

  // 3. Check Specialty Matching across text
  let bestSpecialtyScore = 0;
  for (const spec of SPECIALTY_DEFINITIONS) {
    let specScore = 0;
    
    // Check keywords in company name
    for (const kw of spec.keywords) {
      const reg = new RegExp(`\\b${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
      if (reg.test(nameClean)) {
        specScore += 10;
        matchedHealthcareSignals.push(`Company name specialty match: "${kw}"`);
      }
      if (domain.includes(kw.replace(/\s+/g, ''))) {
        specScore += 5;
      }
    }

    // Check patterns in combined text
    for (const pat of spec.patterns) {
      const matches = combinedText.match(pat);
      if (matches) {
        specScore += 4;
      }
    }

    if (specScore > bestSpecialtyScore) {
      bestSpecialtyScore = specScore;
      detectedSpecialty = spec.category;
    }
  }

  healthcareScore += bestSpecialtyScore;

  // 4. Clinical & Patient Services Signals
  const clinicalSignals = [
    { pattern: /\b(patient\s+portal|book\s+an\s+appointment|request\s+appointment|schedule\s+visit|new\s+patients?\s+welcome)\b/i, weight: 6, label: 'Patient Appointment / Booking portal' },
    { pattern: /\b(m\.d\.|d\.o\.|d\.d\.s\.|d\.m\.d\.|d\.p\.m\.|d\.c\.|fnp-c|pa-c|board\s+certified)\b/i, weight: 6, label: 'Medical Credentials (MD, DDS, DO, Board Certified)' },
    { pattern: /\b(health\s+insurance\s+accepted|medicare|medicaid|copay|telehealth|telemedicine)\b/i, weight: 5, label: 'Insurance / Telehealth signals' },
    { pattern: /\b(clinic\s+hours|treatments?|diagnosis|symptoms|patient\s+forms|medical\s+records)\b/i, weight: 4, label: 'Clinical treatments & medical records' }
  ];

  for (const sig of clinicalSignals) {
    if (sig.pattern.test(combinedText)) {
      healthcareScore += sig.weight;
      matchedHealthcareSignals.push(sig.label);
    }
  }

  // 5. Non-Healthcare Signals Check
  for (const nonHc of NON_HEALTHCARE_PATTERNS) {
    for (const pat of nonHc.patterns) {
      if (pat.test(nameClean)) {
        nonHealthcareScore += 15;
        matchedNonHealthcareSignals.push(`Name matches ${nonHc.category}`);
      } else if (pat.test(combinedText)) {
        nonHealthcareScore += 6;
        matchedNonHealthcareSignals.push(`Text indicates ${nonHc.category}`);
      }
    }
  }

  // 6. Final Decision & Confidence Resolution
  let isHealthcare = false;
  let confidence = 'Low';
  let reason = '';

  if (healthcareScore >= 12 && healthcareScore > (nonHealthcareScore * 1.5)) {
    isHealthcare = true;
    confidence = (healthcareScore >= 22 || matchedHealthcareSignals.length >= 3) ? 'High' : 'Medium';
    const specLabel = detectedSpecialty || 'General Healthcare / Clinic';
    reason = `Confirmed Healthcare/Clinic entity (${specLabel}). Key signals: ${matchedHealthcareSignals.slice(0, 3).join(', ')}`;
  } else if (nonHealthcareScore >= 10 && nonHealthcareScore > healthcareScore) {
    isHealthcare = false;
    confidence = nonHealthcareScore >= 15 ? 'High' : 'Medium';
    detectedSpecialty = 'Non-Healthcare';
    reason = `Identified as non-healthcare industry. Signals: ${matchedNonHealthcareSignals.slice(0, 2).join(', ')}`;
  } else if (healthcareScore > nonHealthcareScore && healthcareScore >= 6) {
    isHealthcare = true;
    confidence = 'Medium';
    detectedSpecialty = detectedSpecialty || 'Healthcare & Wellness';
    reason = `Healthcare indicators detected: ${matchedHealthcareSignals.slice(0, 2).join(', ')}`;
  } else if (nonHealthcareScore > 0) {
    isHealthcare = false;
    confidence = 'Medium';
    detectedSpecialty = 'Non-Healthcare';
    reason = `Industry signals indicate non-medical business (${matchedNonHealthcareSignals.slice(0, 2).join(', ')})`;
  } else {
    // Ambiguous
    isHealthcare = false;
    confidence = 'Low';
    detectedSpecialty = 'Unknown / Non-Healthcare';
    reason = 'Insufficient clinical or healthcare evidence found for this company.';
  }

  return {
    isHealthcare: isHealthcare ? 'Yes' : 'No',
    isHealthcareBoolean: isHealthcare,
    category: isHealthcare ? (detectedSpecialty || 'General Healthcare') : (detectedSpecialty || 'Non-Healthcare'),
    confidence,
    healthcareScore,
    nonHealthcareScore,
    reason,
    signals: isHealthcare ? matchedHealthcareSignals : matchedNonHealthcareSignals
  };
}

module.exports = {
  classifyHealthcare,
  SPECIALTY_DEFINITIONS,
  HEALTHCARE_NAME_KEYWORDS,
  NON_HEALTHCARE_PATTERNS
};
