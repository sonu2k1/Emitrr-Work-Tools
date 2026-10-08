/**
 * Location Detection & Normalization Engine
 * Extracts physical and geographic locations (City, State, Country, Postal Code)
 * from HTML schema.org metadata, web snippets, search results, and company names.
 */

const US_STATES = {
  'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
  'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
  'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
  'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
  'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
  'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
  'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
  'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
  'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
  'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
  'DC': 'District of Columbia', 'PR': 'Puerto Rico'
};

const US_STATE_BY_NAME = {};
for (const [code, name] of Object.entries(US_STATES)) {
  US_STATE_BY_NAME[name.toLowerCase()] = code;
}

const MAJOR_US_CITIES = {
  'new york': 'NY', 'los angeles': 'CA', 'chicago': 'IL', 'houston': 'TX', 'phoenix': 'AZ',
  'philadelphia': 'PA', 'san antonio': 'TX', 'san diego': 'CA', 'dallas': 'TX', 'austin': 'TX',
  'san jose': 'CA', 'fort worth': 'TX', 'jacksonville': 'FL', 'columbus': 'OH', 'charlotte': 'NC',
  'indianapolis': 'IN', 'san francisco': 'CA', 'seattle': 'WA', 'denver': 'CO', 'oklahoma city': 'OK',
  'nashville': 'TN', 'el paso': 'TX', 'washington': 'DC', 'boston': 'MA', 'las vegas': 'NV',
  'portland': 'OR', 'detroit': 'MI', 'louisville': 'KY', 'memphis': 'TN', 'baltimore': 'MD',
  'milwaukee': 'WI', 'albuquerque': 'NM', 'tucson': 'AZ', 'fresno': 'CA', 'sacramento': 'CA',
  'mesa': 'AZ', 'kansas city': 'MO', 'atlanta': 'GA', 'omaha': 'NE', 'colorado springs': 'CO',
  'raleigh': 'NC', 'long beach': 'CA', 'virginia beach': 'VA', 'miami': 'FL', 'oakland': 'CA',
  'minneapolis': 'MN', 'tulsa': 'OK', 'bakersfield': 'CA', 'tampa': 'FL', 'wichita': 'KS',
  'arlington': 'TX', 'aurora': 'CO', 'new orleans': 'LA', 'cleveland': 'OH', 'anaheim': 'CA',
  'honolulu': 'HI', 'henderson': 'NV', 'stockton': 'CA', 'riverside': 'CA', 'lexington': 'KY',
  'corpus christi': 'TX', 'orlando': 'FL', 'irvine': 'CA', 'cincinnati': 'OH', 'pittsburgh': 'PA',
  'st. louis': 'MO', 'saint louis': 'MO', 'greensboro': 'NC', 'lincoln': 'NE', 'plano': 'TX',
  'durham': 'NC', 'boise': 'ID', 'scottsdale': 'AZ', 'birmingham': 'AL', 'rochester': 'NY',
  'spokane': 'WA', 'des moines': 'IA', 'richmond': 'VA', 'baton rouge': 'LA', 'salt lake city': 'UT'
};

const CANADIAN_PROVINCES = {
  'ON': 'Ontario', 'QC': 'Quebec', 'BC': 'British Columbia', 'AB': 'Alberta',
  'MB': 'Manitoba', 'SK': 'Saskatchewan', 'NS': 'Nova Scotia', 'NB': 'New Brunswick'
};

const COUNTRY_NAMES = [
  'united states', 'usa', 'united kingdom', 'uk', 'canada', 'australia', 'india',
  'germany', 'france', 'spain', 'italy', 'brazil', 'mexico', 'japan', 'singapore',
  'new zealand', 'netherlands', 'switzerland', 'sweden', 'ireland', 'south africa'
];

/**
 * Extract location from company name
 * e.g., "Austin Dental Spa" -> "Austin, TX, USA"
 */
function extractLocationFromCompanyName(companyName) {
  if (!companyName) return null;
  const nameLower = companyName.toLowerCase();

  // Check major cities in company name
  for (const [city, stateCode] of Object.entries(MAJOR_US_CITIES)) {
    const cityRegex = new RegExp(`\\b${city.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (cityRegex.test(nameLower)) {
      const formattedCity = city.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
      return {
        city: formattedCity,
        state: stateCode,
        country: 'USA',
        formatted: `${formattedCity}, ${stateCode}, USA`,
        source: 'Company Name Analysis'
      };
    }
  }

  // Check full state names
  for (const [stateName, stateCode] of Object.entries(US_STATE_BY_NAME)) {
    const stateRegex = new RegExp(`\\b${stateName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (stateRegex.test(nameLower)) {
      const formattedState = stateName.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
      return {
        city: '',
        state: stateCode,
        country: 'USA',
        formatted: `${formattedState}, USA`,
        source: 'Company Name Analysis'
      };
    }
  }

  return null;
}

/**
 * Extract structured PostalAddress from Schema.org JSON-LD objects
 */
function extractLocationFromSchema(schemaObjects) {
  if (!schemaObjects || !Array.isArray(schemaObjects)) return null;

  for (const item of schemaObjects) {
    if (!item) continue;

    // Check direct PostalAddress or nested address in LocalBusiness / Organization / MedicalBusiness
    let addressObj = null;
    if (item['@type'] === 'PostalAddress') {
      addressObj = item;
    } else if (item.address) {
      addressObj = item.address;
    } else if (Array.isArray(item['@graph'])) {
      for (const node of item['@graph']) {
        if (node['@type'] === 'PostalAddress' || node.address) {
          addressObj = node.address || node;
          break;
        }
      }
    }

    if (addressObj) {
      const street = addressObj.streetAddress || '';
      const city = addressObj.addressLocality || '';
      const state = addressObj.addressRegion || '';
      const postalCode = addressObj.postalCode || '';
      const country = addressObj.addressCountry || 'USA';

      const parts = [street, city, state, postalCode].filter(p => p && typeof p === 'string' && p.trim() !== '');
      if (parts.length >= 2) {
        let countryCode = (typeof country === 'object' && country.name) ? country.name : country;
        if (!countryCode || countryCode === 'US') countryCode = 'USA';
        
        let formatted = `${city ? city + ', ' : ''}${state ? state + ' ' : ''}${postalCode}`.trim();
        if (formatted) {
          formatted += `, ${countryCode}`;
        } else {
          formatted = parts.join(', ') + `, ${countryCode}`;
        }

        return {
          street,
          city,
          state,
          postalCode,
          country: countryCode,
          formatted: formatted.replace(/^,\s*/, ''),
          source: 'Schema.org JSON-LD'
        };
      }
    }
  }

  return null;
}

/**
 * Extract location from text/snippet using high-precision address regexes
 */
function extractLocationFromText(text) {
  if (!text || typeof text !== 'string') return null;

  // Pattern 1: City, State 5-digit ZIP (e.g., "Austin, TX 78701" or "Miami, Florida 33101")
  const usCityStateZip = /([A-Z][a-zA-Z\s.-]{2,25}),\s*([A-Z]{2}|[A-Za-z\s]{4,15})\s+(\d{5}(?:-\d{4})?)/g;
  let match = usCityStateZip.exec(text);
  if (match) {
    const city = match[1].trim();
    let state = match[2].trim();
    const zip = match[3].trim();

    if (state.length > 2 && US_STATE_BY_NAME[state.toLowerCase()]) {
      state = US_STATE_BY_NAME[state.toLowerCase()];
    }

    if (US_STATES[state.toUpperCase()] || state.length === 2) {
      return {
        city,
        state: state.toUpperCase(),
        postalCode: zip,
        country: 'USA',
        formatted: `${city}, ${state.toUpperCase()} ${zip}, USA`,
        source: 'Address RegEx Match'
      };
    }
  }

  // Pattern 2: Street Address + City + State (e.g., "123 Main St, Austin, TX")
  const usStreetAddress = /\b\d{1,5}\s+[\w\s.-]+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Hwy|Highway|Way|Suite|Ste)\b[,\s]+([A-Za-z\s.-]+),\s*([A-Z]{2})\b/i;
  match = usStreetAddress.exec(text);
  if (match) {
    const city = match[1].trim();
    const state = match[2].trim().toUpperCase();
    if (US_STATES[state]) {
      return {
        city,
        state,
        country: 'USA',
        formatted: `${city}, ${state}, USA`,
        source: 'Street Address Pattern'
      };
    }
  }

  // Pattern 3: City, 2-Letter State Code (e.g. "Dallas, TX" or "Chicago, IL")
  const cityStatePattern = /\b([A-Z][a-zA-Z\s]{2,20}),\s*([A-Z]{2})\b/g;
  while ((match = cityStatePattern.exec(text)) !== null) {
    const city = match[1].trim();
    const state = match[2].trim().toUpperCase();
    if (US_STATES[state] && !['AN', 'AS', 'AT', 'BY', 'DO', 'IF', 'IN', 'IS', 'IT', 'MY', 'NO', 'OF', 'ON', 'OR', 'SO', 'TO', 'UP', 'US'].includes(state)) {
      return {
        city,
        state,
        country: 'USA',
        formatted: `${city}, ${state}, USA`,
        source: 'City & State Match'
      };
    }
  }

  // Pattern 4: Check if any major city appears in snippet text
  const textLower = text.toLowerCase();
  for (const [city, stateCode] of Object.entries(MAJOR_US_CITIES)) {
    const cityRegex = new RegExp(`\\b${city.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (cityRegex.test(textLower)) {
      const formattedCity = city.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
      return {
        city: formattedCity,
        state: stateCode,
        country: 'USA',
        formatted: `${formattedCity}, ${stateCode}, USA`,
        source: 'Context City Analysis'
      };
    }
  }

  return null;
}

/**
 * Detect location from all available sources in priority order:
 * 1. Schema.org JSON-LD
 * 2. Company Name embedded location
 * 3. Search snippets / HTML Text
 * 4. Meta tags (geo.placename, og:locality)
 */
function detectLocation(companyName, contextData = {}) {
  // 1. Try Schema.org
  if (contextData.schemaObjects) {
    const schemaLoc = extractLocationFromSchema(contextData.schemaObjects);
    if (schemaLoc) return schemaLoc;
  }

  // 2. Try Company Name
  const nameLoc = extractLocationFromCompanyName(companyName);
  if (nameLoc) return nameLoc;

  // 3. Try Meta tags
  if (contextData.metaText) {
    const metaLoc = extractLocationFromText(contextData.metaText);
    if (metaLoc) return metaLoc;
  }

  // 4. Try Search Snippets & Page Body
  const combinedContext = `${contextData.snippetText || ''} ${contextData.bodyText || ''}`;
  if (combinedContext) {
    const textLoc = extractLocationFromText(combinedContext);
    if (textLoc) return textLoc;
  }

  return {
    city: '',
    state: '',
    country: '',
    formatted: 'Not Detected',
    source: 'None'
  };
}

module.exports = {
  detectLocation,
  extractLocationFromCompanyName,
  extractLocationFromSchema,
  extractLocationFromText,
  US_STATES,
  MAJOR_US_CITIES
};
