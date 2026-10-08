const axios = require('axios');
const cheerio = require('cheerio');
const { URL } = require('url');

// Comprehensive list of social, directories, review sites, and healthcare aggregators to ignore
const IGNORED_DOMAINS = new Set([
  // Social Media & Search
  'linkedin.com',
  'facebook.com',
  'instagram.com',
  'twitter.com',
  'x.com',
  'youtube.com',
  'pinterest.com',
  'tiktok.com',
  'threads.net',
  'reddit.com',
  'quora.com',
  'google.com',
  'google.ca',
  'yahoo.com',
  'bing.com',
  'duckduckgo.com',
  'wikipedia.org',
  'wikimedia.org',
  
  // General Directories & Portals
  'yelp.com',
  'yelp.ca',
  'yellowpages.com',
  'yellowpages.ca',
  'whitepages.com',
  'mapquest.com',
  'bbb.org',
  'dnb.com',
  'bloomberg.com',
  'reuters.com',
  'crunchbase.com',
  'glassdoor.com',
  'indeed.com',
  'zoominfo.com',
  'apollo.io',
  'owler.com',
  'pitchbook.com',
  'trustpilot.com',
  'sec.gov',
  'opencorporates.com',
  'g2.com',
  'capterra.com',
  'scamadviser.com',
  'scam-detector.com',
  'chamberofcommerce.com',
  'manta.com',
  'superpages.com',
  'citysearch.com',
  'localdatabase.com',
  'foursquare.com',
  'patch.com',
  'merchantcircle.com',
  'ezlocal.com',
  'alignable.com',
  'nextdoor.com',
  
  // Healthcare / Dental / Medical Directory Aggregators
  'healthgrades.com',
  'zocdoc.com',
  'vitals.com',
  'doximity.com',
  'webmd.com',
  'sharecare.com',
  'ratemds.com',
  'opencare.com',
  '1800dentist.com',
  'emergencydentistsusa.com',
  'dentistnearme.com',
  'doctor.webmd.com',
  'findatopdoc.com',
  'topnpi.com',
  'npino.com',
  'npiprofile.com',
  'npidb.org',
  'hipaspace.com',
  'caredash.com',
  'docspot.com',
  'drchrono.com',
  'castleconnolly.com',
  'wellness.com',
  'usnews.com',
  'health.usnews.com',
  'dentalplans.com',
  'delta-dental.com',
  'deltadental.com',
  'cigna.com',
  'aetna.com',
  'humana.com',
  'metlife.com',
  'unitedhealthcare.com',
  'uhc.com',
  'anthem.com',
  'bluecross.ca',
  'sunlife.ca',
  'manulife.ca',
  'threebestrated.com',
  'threebestrated.ca',
  'canadapages.com',
  'canadapost.ca',
  'homestars.com',
  'psychologytoday.com',
  'therapist.com',
  'goodtherapy.org',
  'chirodirectory.com',
  'optometrystudents.com',
  'allaboutvision.com'
]);

// Multi-second level ccTLDs e.g. .co.uk, .com.au, .gc.ca, .on.ca
const SECOND_LEVEL_TLDS = new Set([
  'co.uk', 'org.uk', 'gov.uk',
  'com.au', 'net.au', 'org.au',
  'co.in', 'net.in', 'org.in',
  'gc.ca', 'on.ca', 'qc.ca', 'bc.ca', 'ab.ca', 'mb.ca', 'sk.ca', 'ns.ca', 'nb.ca', 'nl.ca', 'pe.ca',
  'co.nz', 'net.nz', 'org.nz',
  'co.za', 'net.za',
  'com.mx', 'gob.mx',
  'com.br', 'net.br'
]);

const BROWSER_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9',
  'sec-ch-ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"macOS"',
  'Upgrade-Insecure-Requests': '1'
};

const STOP_WORDS = new Set([
  'of', 'and', 'the', 'for', 'in', 'on', 'at', 'to', 'a', 'an', 'with', 'by',
  'de', 'la', 'le', 'et', '&', '+'
]);

// Memory cache for geocoded locations to minimize Valentin.app API queries
const geocodeCache = new Map();

/**
 * Remove accents, diacritics, and special characters
 */
function normalizeString(str) {
  if (!str) return '';
  return str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/['`’]/g, '')
    .trim();
}

/**
 * Healthcare and Practice Name Cleaner
 * Strips doctor titles, credentials, legal suffixes, etc.
 */
function cleanPracticeName(name) {
  if (!name || typeof name !== 'string') return '';
  
  let cleaned = normalizeString(name);
  // Remove parenthesized notes e.g. "Smile Dental (Downtown Branch)" -> "Smile Dental"
  cleaned = cleaned.replace(/\(.*?\)/g, ' ');
  cleaned = cleaned.replace(/\[.*?\]/g, ' ');

  // Strip leading site IDs e.g. "FL048 ", "FL003 ", "AL001 ", "043 "
  cleaned = cleaned.replace(/^[A-Z]{2}\d{2,4}\s+/i, ' ');
  cleaned = cleaned.replace(/^\d{2,4}\s+/i, ' ');

  // Strip leading titles
  cleaned = cleaned.replace(/^\s*(dr\.|dr|doctor)\s+/i, '');

  const healthcareSuffixes = [
    'd\\.d\\.s\\.', 'dds', 'd\\.m\\.d\\.', 'dmd', 'm\\.d\\.', 'md', 'd\\.o\\.', 'do',
    'd\\.c\\.', 'dc', 'd\\.p\\.m\\.', 'dpm', 'o\\.d\\.', 'od', 'f\\.a\\.c\\.s\\.', 'facs',
    'f\\.a\\.c\\.o\\.g\\.', 'facog', 'p\\.a\\.-c', 'pa-c', 'p\\.a\\.', 'np', 'aprn', 'crna',
    'p\\.l\\.l\\.c\\.', 'pllc', 'p\\.c\\.', 'pc', 'l\\.l\\.c\\.', 'llc', 'l\\.l\\.p\\.', 'llp',
    'incorporated', 'inc\\.', 'inc', 'corporation', 'corp\\.', 'corp',
    'company', 'co\\.', 'co', 'limited', 'ltd\\.', 'ltd', 's\\.c\\.', 'sc'
  ];

  for (const suffix of healthcareSuffixes) {
    const regex = new RegExp(`\\b${suffix}\\b`, 'gi');
    cleaned = cleaned.replace(regex, ' ');
  }

  // Clean trailing and separated punctuation
  cleaned = cleaned.replace(/[,;:\.\|/]+/g, ' ');
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  return cleaned.length > 0 ? cleaned : normalizeString(name);
}

/**
 * Extract clean root domain from URL string
 */
function extractCleanDomain(urlString) {
  if (!urlString) return null;
  try {
    let raw = urlString.trim();
    if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
      raw = 'http://' + raw;
    }
    const parsed = new URL(raw);
    let hostname = parsed.hostname.toLowerCase();

    if (hostname.startsWith('www.')) {
      hostname = hostname.slice(4);
    }

    if (!/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(hostname)) {
      return null;
    }

    const parts = hostname.split('.');
    if (parts.length < 2) return null;

    let mainDomain = parts.slice(-2).join('.');
    if (parts.length >= 3) {
      const possibleSubTld = parts.slice(-2).join('.');
      if (SECOND_LEVEL_TLDS.has(possibleSubTld)) {
        mainDomain = parts.slice(-3).join('.');
      }
    }
    
    if (IGNORED_DOMAINS.has(hostname) || IGNORED_DOMAINS.has(mainDomain)) {
      return null;
    }

    // Ignore image/asset CDNs or generic storage domains
    if (hostname.endsWith('.cloudfront.net') || hostname.endsWith('.azureedge.net') || hostname.endsWith('.s3.amazonaws.com')) {
      return null;
    }

    return hostname;
  } catch (err) {
    return null;
  }
}

/**
 * Detect parked or domain-for-sale landing pages
 */
function isParkedOrForSalePage(htmlContent, titleContent) {
  if (!htmlContent && !titleContent) return false;
  const text = ((htmlContent || '') + ' ' + (titleContent || '')).toLowerCase();
  const patterns = [
    'is for sale', 'domain for sale', 'buy this domain', 'domain is available',
    'hugedomains', 'sedo.com', 'dan.com', 'afternic', 'godaddy.com/domain-search',
    'this domain name is', 'parked free', 'domainpark', 'namecheap.com/domains',
    'under construction', 'domain has expired', 'purchase this domain', 'this domain is for sale',
    'buy domain', 'domain for purchase', 'domain name for sale', 'domain is listed',
    'renewal reminder', 'registered at namecheap'
  ];
  return patterns.some(p => text.includes(p));
}

/**
 * Domain relevance score for Practice / Healthcare matching
 */
function calculatePracticeRelevanceScore(domain, practiceName, locationContext = '') {
  if (!domain || !practiceName) return -1;

  const cleanName = cleanPracticeName(practiceName).toLowerCase().replace(/[^a-z0-9]/g, '');
  const domainSlug = domain.split('.')[0].toLowerCase().replace(/[^a-z0-9]/g, '');

  if (!cleanName || !domainSlug) return -1;

  let baseScore = 0;

  if (cleanName === domainSlug) {
    baseScore = 130;
  } else if (domainSlug.startsWith(cleanName)) {
    baseScore = 95;
  } else if (cleanName.startsWith(domainSlug)) {
    const ratio = domainSlug.length / cleanName.length;
    if (ratio >= 0.55 || (cleanName.length - domainSlug.length) <= 6) {
      baseScore = 90;
    } else {
      baseScore = 40;
    }
  } else if (cleanName.includes(domainSlug) && domainSlug.length >= 6) {
    const ratio = domainSlug.length / cleanName.length;
    baseScore = ratio >= 0.5 ? 75 : 45;
  } else {
    const cleaned = cleanPracticeName(practiceName);
    const words = cleaned.toLowerCase().split(/[\s,-]+/).filter(w => w.length >= 2);
    const meaningfulWords = words.filter(w => !STOP_WORDS.has(w));

    const initialsWithStop = words.map(w => w[0]).join('');
    const initialsNoStop = meaningfulWords.map(w => w[0]).join('');

    if ((words.length >= 3 && initialsWithStop.length >= 3 && domainSlug === initialsWithStop) ||
        (meaningfulWords.length >= 3 && initialsNoStop.length >= 3 && domainSlug === initialsNoStop)) {
      baseScore = 95;
    } else {
      let matchCount = 0;
      for (const word of meaningfulWords) {
        if (word.length >= 4 && domainSlug.includes(word)) matchCount++;
      }
      if (matchCount >= 2) baseScore = 60 + (matchCount * 10);
    }
  }

  if (baseScore <= 0) return 0;

  // Bonus for country-specific top-level domains (.ca for Canada, .com for US/Global)
  if (domain.endsWith('.ca') || domain.endsWith('.com')) {
    baseScore += 20;
  } else if (domain.endsWith('.org') || domain.endsWith('.net') || domain.endsWith('.clinic') || domain.endsWith('.dental') || domain.endsWith('.health')) {
    baseScore += 15;
  }

  // Bonus if location keyword (city/state) is present in domain
  if (locationContext) {
    const cleanLoc = locationContext.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (cleanLoc.length >= 3 && domainSlug.includes(cleanLoc)) {
      baseScore += 15;
    }
  }

  return baseScore;
}

/**
 * Valentin.app UULE v1 Protobuf Generator
 * Encodes canonical name (e.g. "New York, NY, USA" or "Toronto, ON, Canada")
 * into Google UULE format: "w+CAIQICI..."
 */
function generateUULEv1(canonicalName) {
  if (!canonicalName || typeof canonicalName !== 'string') return null;
  const str = canonicalName.trim();
  if (!str) return null;

  const strBytes = Buffer.from(str, 'utf8');
  const strLen = strBytes.length;

  const lenVarint = [];
  let l = strLen;
  while (l > 127) {
    lenVarint.push((l & 0x7f) | 0x80);
    l >>>= 7;
  }
  lenVarint.push(l & 0x7f);

  const header = Buffer.from([0x08, 0x02, 0x10, 0x20, 0x22, ...lenVarint]);
  const pbBuffer = Buffer.concat([header, strBytes]);

  return 'w+' + pbBuffer.toString('base64');
}

/**
 * Valentin.app UULE v2 Coordinate Text Generator
 * Encodes latitude, longitude and radius into Google UULE text format: "a+..."
 */
function generateUULEv2(lat, lng, radius = 93000) {
  const latitude = parseFloat(lat);
  const longitude = parseFloat(lng);
  if (isNaN(latitude) || isNaN(longitude)) return null;

  const latE7 = Math.round(latitude * 1e7);
  const lngE7 = Math.round(longitude * 1e7);
  const ts = Date.now() * 1000;

  const rawText = `role:1\nproducer:12\nprovenance:6\ntimestamp:${ts}\nlatlng{\nlatitude_e7:${latE7}\nlongitude_e7:${lngE7}\n}\nradius:${radius}`;
  const base64Str = Buffer.from(rawText, 'utf8').toString('base64');
  return 'a+' + base64Str;
}

/**
 * Valentin.app Geocoding API integration
 * Calls https://valentin.app/geocode?address=...&hl=en&gl=US/CA
 */
async function geocodeAddress(address, countryCode = 'US') {
  if (!address || typeof address !== 'string' || !address.trim()) return null;
  const key = `${countryCode.toUpperCase()}_${address.trim().toLowerCase()}`;

  if (geocodeCache.has(key)) {
    return geocodeCache.get(key);
  }

  try {
    const gl = countryCode.toUpperCase() === 'CA' ? 'CA' : 'US';
    const url = `https://valentin.app/geocode?address=${encodeURIComponent(address.trim())}&hl=en&gl=${gl}`;
    
    const response = await axios.get(url, {
      headers: {
        'User-Agent': BROWSER_HEADERS['User-Agent'],
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://valentin.app/'
      },
      timeout: 5000
    });

    if (response.data && response.data.status === 'OK' && Array.isArray(response.data.results) && response.data.results.length > 0) {
      const top = response.data.results[0];
      const locData = {
        formattedAddress: top.formatted_address,
        lat: top.geometry.location.lat,
        lng: top.geometry.location.lng,
        placeId: top.place_id
      };
      geocodeCache.set(key, locData);
      return locData;
    }
  } catch (err) {}
  return null;
}

/**
 * Direct Domain Verification with HTTP/HTTPS check
 */
async function probeDirectPracticeDomain(practiceName, countryCode = 'US') {
  const cleaned = cleanPracticeName(practiceName);
  const cleanSlug = cleaned.toLowerCase().replace(/[^a-z0-9]/g, '');
  if (!cleanSlug || cleanSlug.length < 3) return null;

  const candidateDomains = [];
  if (countryCode.toUpperCase() === 'CA') {
    candidateDomains.push(`${cleanSlug}.ca`, `${cleanSlug}.com`);
  } else {
    candidateDomains.push(`${cleanSlug}.com`, `${cleanSlug}.org`, `${cleanSlug}.net`);
  }

  // Strip generic healthcare tokens to find core brand (e.g. "CityMD Urgent Care" -> "citymd")
  const strippedBrand = cleanSlug
    .replace(/(urgentcare|medicalcenter|familymedicine|pediatrics|specialists|healthcare|pediatriccenter|familycare|medicalgroup|clinic|associates)$/g, '');
  
  if (strippedBrand.length >= 5 && strippedBrand !== cleanSlug && (strippedBrand.length / cleanSlug.length) >= 0.5) {
    if (countryCode.toUpperCase() === 'CA') {
      candidateDomains.push(`${strippedBrand}.ca`, `${strippedBrand}.com`);
    } else {
      candidateDomains.push(`${strippedBrand}.com`, `${strippedBrand}.org`);
    }
  }

  for (const candidate of candidateDomains) {
    const testUrl = `https://www.${candidate}`;
    try {
      const res = await axios.get(testUrl, {
        headers: { 'User-Agent': BROWSER_HEADERS['User-Agent'] },
        timeout: 2500,
        maxRedirects: 2,
        validateStatus: (status) => status < 400
      });

      if (res.status >= 200 && res.status < 400 && res.data) {
        const htmlContent = typeof res.data === 'string' ? res.data : '';
        let title = '';
        try {
          const $ = cheerio.load(htmlContent);
          title = $('title').text() || '';
        } catch (e) {}

        if (!isParkedOrForSalePage(htmlContent, title)) {
          const score = calculatePracticeRelevanceScore(candidate, practiceName);
          if (score >= 70) {
            return {
              domain: candidate,
              url: `https://${candidate}`,
              source: 'Direct Practice Verification',
              confidence: 'High'
            };
          }
        }
      }
    } catch (e) {}
  }
}

/**
 * Strategy 1: Valentin.app Localized Google Search (US & Canada)
 */
async function searchValentinGoogle(practiceName, options = {}) {
  try {
    const cleaned = cleanPracticeName(practiceName);
    if (!cleaned) return null;

    const country = (options.countryCode || options.country || 'US').toUpperCase();
    const gl = country === 'CA' ? 'CA' : 'US';
    const hl = 'en';
    const googleHost = gl === 'CA' ? 'https://www.google.ca/search' : 'https://www.google.com/search';

    let uule = options.uule;
    let locationLabel = options.location || (gl === 'CA' ? 'Canada' : 'United States');

    // If address/city/state provided, geocode via Valentin.app or encode into UULE
    if (!uule) {
      if (options.lat && options.lng) {
        uule = generateUULEv2(options.lat, options.lng);
      } else if (options.address || options.city || options.state) {
        const fullAddr = [options.address, options.city, options.state, gl === 'CA' ? 'Canada' : 'USA'].filter(Boolean).join(', ');
        const geocoded = await geocodeAddress(fullAddr, gl);
        if (geocoded) {
          uule = generateUULEv2(geocoded.lat, geocoded.lng);
          locationLabel = geocoded.formattedAddress;
        } else {
          uule = generateUULEv1(fullAddr);
          locationLabel = fullAddr;
        }
      } else if (options.location) {
        uule = generateUULEv1(options.location);
      } else {
        uule = gl === 'CA' ? generateUULEv1('Canada') : generateUULEv1('United States');
      }
    }

    const candidateDomains = [];

    // Step A: Localized Autocomplete Query
    try {
      let suggestUrl = `https://suggestqueries.google.com/complete/search?client=chrome&q=${encodeURIComponent(cleaned)}&gl=${gl}&hl=${hl}`;
      if (uule) {
        suggestUrl += `&uule=${encodeURIComponent(uule)}`;
      }
      const suggRes = await axios.get(suggestUrl, {
        headers: BROWSER_HEADERS,
        timeout: 4000
      });

      if (Array.isArray(suggRes.data) && Array.isArray(suggRes.data[1])) {
        for (const item of suggRes.data[1]) {
          if (typeof item === 'string') {
            const domain = extractCleanDomain(item);
            if (domain && !candidateDomains.includes(domain)) {
              candidateDomains.push(domain);
            }
          }
        }
      }
    } catch (e) {}

    // Step B: Valentin Localized Google SERP
    if (candidateDomains.length === 0) {
      const queriesToTry = [
        `"${cleaned}" official website`,
        `${cleaned} practice ${options.city || ''} ${options.state || ''}`.trim()
      ];

      for (const query of queriesToTry) {
        if (candidateDomains.length > 0) break;
        try {
          const queryParams = new URLSearchParams();
          queryParams.set('q', query);
          queryParams.set('hl', hl);
          queryParams.set('gl', gl);
          queryParams.set('pws', '0');
          if (uule) {
            queryParams.set('uule', uule);
          }

          const searchUrl = `${googleHost}?${queryParams.toString()}`;
          const response = await axios.get(searchUrl, {
            headers: BROWSER_HEADERS,
            timeout: 6000
          });

          const $ = cheerio.load(response.data);
          $('a').each((_, el) => {
            let href = $(el).attr('href');
            if (href) {
              let rawUrl = href;
              if (href.startsWith('/url?q=')) {
                try {
                  rawUrl = href.split('/url?q=')[1].split('&')[0];
                } catch (e) {}
              }
              const domain = extractCleanDomain(rawUrl);
              if (domain && !candidateDomains.includes(domain)) {
                candidateDomains.push(domain);
              }
            }
          });
        } catch (e) {}
      }
    }

    let bestDomain = null;
    let maxScore = -1;

    for (const domain of candidateDomains) {
      const score = calculatePracticeRelevanceScore(domain, practiceName, options.city || options.state);
      if (score > maxScore) {
        maxScore = score;
        bestDomain = domain;
      }
    }

    if (bestDomain && maxScore >= 35) {
      return {
        domain: bestDomain,
        url: `https://${bestDomain}`,
        source: `Valentin Google Localized (${gl === 'CA' ? 'Canada' : 'US'})`,
        confidence: maxScore >= 75 ? 'High' : 'Medium'
      };
    }
  } catch (err) {}
  return null;
}

/**
 * Strategy 2: Localized DuckDuckGo Search (Fallback)
 */
async function searchDuckDuckGoPractice(practiceName, options = {}) {
  try {
    const cleaned = cleanPracticeName(practiceName);
    const country = (options.countryCode || options.country || 'US').toUpperCase();
    const locPart = options.city || options.state || (country === 'CA' ? 'Canada' : 'USA');
    
    const queries = [
      `"${cleaned}" official website`,
      `${cleaned} official website`,
      `${cleaned} ${locPart}`
    ];

    const kl = country === 'CA' ? 'ca-en' : 'us-en';
    const candidateDomains = [];

    for (const query of queries) {
      if (candidateDomains.length > 0) break;
      try {
        const response = await axios.get(`https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}&kl=${kl}`, {
          headers: BROWSER_HEADERS,
          timeout: 5000
        });

        const $ = cheerio.load(response.data);
        $('a.result__url, a.result__snippet, .results_links a').each((_, el) => {
          let href = $(el).attr('href');
          if (href) {
            if (href.includes('uddg=')) {
              try {
                const urlObj = new URL('https:' + href);
                href = urlObj.searchParams.get('uddg');
              } catch (e) {}
            }
            if (href) {
              const domain = extractCleanDomain(href);
              if (domain && !candidateDomains.includes(domain)) {
                candidateDomains.push(domain);
              }
            }
          }
        });
      } catch (e) {}
    }

    let bestDomain = null;
    let maxScore = -1;

    for (const domain of candidateDomains) {
      const score = calculatePracticeRelevanceScore(domain, practiceName, options.city || options.state);
      if (score > maxScore) {
        maxScore = score;
        bestDomain = domain;
      }
    }

    if (bestDomain && maxScore >= 35) {
      return {
        domain: bestDomain,
        url: `https://${bestDomain}`,
        source: `DuckDuckGo Localized (${country})`,
        confidence: maxScore >= 70 ? 'High' : 'Medium'
      };
    }
  } catch (err) {}
  return null;
}

/**
 * Strategy 3: Yahoo Localized Search (Fallback)
 */
async function searchYahooPractice(practiceName, options = {}) {
  try {
    const cleaned = cleanPracticeName(practiceName);
    const country = (options.countryCode || options.country || 'US').toUpperCase();
    const locPart = options.city || options.state || (country === 'CA' ? 'Canada' : 'USA');
    const query = `${cleaned} ${locPart} official website`;

    const yahooHost = country === 'CA' ? 'https://ca.search.yahoo.com/search' : 'https://search.yahoo.com/search';
    const response = await axios.get(`${yahooHost}?p=${encodeURIComponent(query)}`, {
      headers: BROWSER_HEADERS,
      timeout: 6000
    });

    const $ = cheerio.load(response.data);
    const candidateDomains = [];

    $('a').each((_, el) => {
      let href = $(el).attr('href');
      if (href && href.includes('r.search.yahoo.com')) {
        try {
          const match = href.match(/\/RU=([^/]+)\//);
          if (match && match[1]) {
            href = decodeURIComponent(match[1]);
          }
        } catch (e) {}
      }
      if (href) {
        const domain = extractCleanDomain(href);
        if (domain && !candidateDomains.includes(domain) && !domain.includes('yahoo.com')) {
          candidateDomains.push(domain);
        }
      }
    });

    let bestDomain = null;
    let maxScore = -1;

    for (const domain of candidateDomains) {
      const score = calculatePracticeRelevanceScore(domain, practiceName, options.city || options.state);
      if (score > maxScore) {
        maxScore = score;
        bestDomain = domain;
      }
    }

    if (bestDomain && maxScore >= 35) {
      return {
        domain: bestDomain,
        url: `https://${bestDomain}`,
        source: `Yahoo Search (${country})`,
        confidence: maxScore >= 70 ? 'High' : 'Medium'
      };
    }
  } catch (err) {}
  return null;
}

/**
 * Strategy 4: Clearbit Healthcare / Company Autocomplete (Fallback)
 */
async function searchClearbitPractice(practiceName) {
  const cleaned = cleanPracticeName(practiceName);
  const queriesToTry = [cleaned, practiceName].filter((v, i, a) => v && a.indexOf(v) === i);

  for (const q of queriesToTry) {
    try {
      const response = await axios.get(`https://autocomplete.clearbit.com/v1/companies/suggest?query=${encodeURIComponent(q)}`, {
        headers: { 'User-Agent': BROWSER_HEADERS['User-Agent'] },
        timeout: 4000
      });

      if (Array.isArray(response.data) && response.data.length > 0) {
        let bestMatch = null;
        let maxScore = -1;

        for (const item of response.data) {
          if (item && item.domain) {
            const cleanedDomain = extractCleanDomain(item.domain);
            if (cleanedDomain) {
              const score = calculatePracticeRelevanceScore(cleanedDomain, practiceName);
              if (score > maxScore && score >= 45) {
                maxScore = score;
                bestMatch = {
                  domain: cleanedDomain,
                  url: `https://${cleanedDomain}`,
                  source: 'Clearbit Autocomplete',
                  confidence: score >= 80 ? 'High' : 'Medium'
                };
              }
            }
          }
        }

        if (bestMatch) return bestMatch;
      }
    } catch (err) {}
  }
  return null;
}

/**
 * Main Practice Domain Finder function
 */
async function findPracticeDomain(practiceName, options = {}) {
  if (!practiceName || typeof practiceName !== 'string' || !practiceName.trim()) {
    return {
      practiceName: practiceName || '',
      cleanedName: '',
      country: options.countryCode || options.country || 'US',
      domain: '',
      websiteUrl: '',
      status: 'Failed',
      source: 'N/A',
      confidence: 'None',
      error: 'Empty practice name'
    };
  }

  const name = practiceName.trim();
  const cleaned = cleanPracticeName(name);
  const country = (options.countryCode || options.country || 'US').toUpperCase();

  // 1. Direct Domain Verification Probe
  let result = await probeDirectPracticeDomain(name, country);

  // 2. Valentin.app Localized Google Search (US / CA with UULE)
  if (!result) {
    result = await searchValentinGoogle(name, { ...options, countryCode: country });
  }

  // 3. DuckDuckGo Localized Search
  if (!result) {
    result = await searchDuckDuckGoPractice(name, { ...options, countryCode: country });
  }

  // 4. Yahoo Localized Search
  if (!result) {
    result = await searchYahooPractice(name, { ...options, countryCode: country });
  }

  // 5. Clearbit Autocomplete
  if (!result) {
    result = await searchClearbitPractice(name);
  }

  if (result) {
    return {
      practiceName: name,
      cleanedName: cleaned,
      country: country,
      domain: result.domain,
      websiteUrl: result.url || `https://${result.domain}`,
      status: 'Found',
      source: result.source,
      confidence: result.confidence
    };
  }

  return {
    practiceName: name,
    cleanedName: cleaned,
    country: country,
    domain: '',
    websiteUrl: '',
    status: 'Not Found',
    source: 'N/A',
    confidence: 'None'
  };
}

/**
 * Process a batch of practice records with concurrency control and progress callback
 */
async function processPracticeBatch(practiceList, onProgress, options = {}) {
  const concurrency = options.concurrency || 3;
  const delayMs = options.delayMs || 300;
  const results = [];
  
  let completedCount = 0;
  const queue = [...practiceList];

  async function worker() {
    while (queue.length > 0) {
      const row = queue.shift();
      if (!row) break;

      let practiceName = '';
      let country = options.country || 'US';
      let city = '';
      let state = '';
      let address = '';

      if (typeof row === 'string') {
        practiceName = row;
      } else if (typeof row === 'object' && row !== null) {
        // Auto-detect fields from diverse CSV column names
        const keys = Object.keys(row);
        const nameKey = keys.find(k => /^(practice_?name|practice|clinic_?name|clinic|doctor_?name|doctor|hospital_?name|hospital|company_?name|company|name|business_?name)$/i.test(k.trim())) || keys[0];
        practiceName = row[nameKey] || '';

        const countryKey = keys.find(k => /^(country|country_?code|nation)$/i.test(k.trim()));
        if (countryKey && row[countryKey]) {
          const rawCountry = row[countryKey].trim().toUpperCase();
          if (rawCountry === 'CA' || rawCountry.includes('CANADA')) country = 'CA';
          else if (rawCountry === 'US' || rawCountry.includes('USA') || rawCountry.includes('UNITED STATES')) country = 'US';
        }

        const cityKey = keys.find(k => /^(city|town)$/i.test(k.trim()));
        if (cityKey) city = row[cityKey];

        const stateKey = keys.find(k => /^(state|province|region)$/i.test(k.trim()));
        if (stateKey) state = row[stateKey];

        const addrKey = keys.find(k => /^(address|street|location)$/i.test(k.trim()));
        if (addrKey) address = row[addrKey];
      }

      let res;
      try {
        res = await findPracticeDomain(practiceName, {
          ...options,
          countryCode: country,
          city,
          state,
          address
        });
      } catch (err) {
        res = {
          practiceName,
          cleanedName: cleanPracticeName(practiceName),
          country,
          domain: '',
          websiteUrl: '',
          status: 'Error',
          source: 'Error',
          confidence: 'None',
          error: err.message
        };
      }

      // Preserve original input row metadata
      const enrichedResult = {
        ...(typeof row === 'object' ? row : { inputPracticeName: row }),
        ...res
      };

      results.push(enrichedResult);
      completedCount++;

      if (typeof onProgress === 'function') {
        onProgress(enrichedResult, completedCount, practiceList.length);
      }

      if (delayMs > 0 && queue.length > 0) {
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }

  const workers = [];
  for (let i = 0; i < Math.min(concurrency, practiceList.length); i++) {
    workers.push(worker());
  }

  await Promise.all(workers);
  return results;
}

module.exports = {
  findPracticeDomain,
  processPracticeBatch,
  cleanPracticeName,
  extractCleanDomain,
  calculatePracticeRelevanceScore,
  generateUULEv1,
  generateUULEv2,
  geocodeAddress,
  searchValentinGoogle,
  searchDuckDuckGoPractice,
  searchYahooPractice,
  searchClearbitPractice,
  probeDirectPracticeDomain
};
