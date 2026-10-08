const axios = require('axios');
const cheerio = require('cheerio');
const { URL } = require('url');

// Comprehensive list of social media, news, directories, registries, catalog, and aggregator domains to ignore
const IGNORED_DOMAINS = new Set([
  'linkedin.com',
  'facebook.com',
  'instagram.com',
  'twitter.com',
  'x.com',
  'youtube.com',
  'pinterest.com',
  'wikipedia.org',
  'wikimedia.org',
  'crunchbase.com',
  'glassdoor.com',
  'yelp.com',
  'bloomberg.com',
  'reuters.com',
  'github.com',
  'medium.com',
  'reddit.com',
  'quora.com',
  'zoominfo.com',
  'pitchbook.com',
  'trustpilot.com',
  'sec.gov',
  'dnb.com',
  'indeed.com',
  'bbb.org',
  'owler.com',
  'apollo.io',
  'tiktok.com',
  'threads.net',
  'scamadviser.com',
  'scam-detector.com',
  'opencorporates.com',
  'g2.com',
  'capterra.com',
  'trustradius.com',
  'ziprecruiter.com',
  'mapquest.com',
  'yellowpages.com',
  'indiamart.com',
  'justdial.com',
  'tradeindia.com',
  'forbes.com',
  'wsj.com',
  'nytimes.com',
  'yahoo.com',
  'bing.com',
  'duckduckgo.com',
  'slideshare.net',
  'play.google.com',
  'apps.apple.com'
]);

// Multi-second level ccTLDs e.g. .co.uk, .com.au, .co.in
const SECOND_LEVEL_TLDS = new Set([
  'co.uk', 'org.uk', 'gov.uk',
  'co.in', 'net.in', 'org.in', 'gov.in',
  'com.au', 'net.au', 'org.au',
  'co.jp', 'ne.jp', 'or.jp',
  'com.cn', 'net.cn', 'org.cn',
  'com.br', 'net.br', 'org.br',
  'co.nz', 'net.nz', 'org.nz',
  'com.sg', 'org.sg',
  'co.za', 'net.za',
  'com.mx', 'gob.mx',
  'co.kr', 'ne.kr',
  'com.tw', 'org.tw',
  'co.at', 'or.at',
  'com.tr', 'org.tr',
  'co.id', 'web.id',
  'com.my', 'net.my',
  'com.ar', 'org.ar',
  'com.co', 'co.co',
  'com.sa', 'pub.sa',
  'com.eg', 'edu.eg',
  'com.ua', 'org.ua',
  'com.vn', 'net.vn',
  'com.ph', 'org.ph',
  'com.pk', 'org.pk',
  'co.th', 'in.th'
]);

const BROWSER_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9'
};

const STOP_WORDS = new Set([
  'of', 'and', 'the', 'for', 'in', 'on', 'at', 'to', 'a', 'an', 'with', 'by',
  'de', 'la', 'le', 'del', 'der', 'van', 'von', '&', '+'
]);

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
    'buy domain', 'domain for purchase', 'domain name for sale', 'domain is listed'
  ];
  return patterns.some(p => text.includes(p));
}

/**
 * Remove accents, diacritics, and special quotes from international company names
 * e.g. "L'Oréal" -> "Loreal", "Nestlé" -> "Nestle"
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
 * Clean company name by removing ONLY actual legal entity registration suffixes
 */
function cleanCompanyName(name) {
  if (!name || typeof name !== 'string') return '';
  
  let cleaned = normalizeString(name);
  cleaned = cleaned.replace(/\(.*?\)/g, '');
  
  const legalSuffixes = [
    // India & Commonwealth
    'private limited', 'pvt ltd', 'pvt. ltd.', 'ltd.', 'ltd', 'limited', 'llp',
    'proprietorship', 'pvt',
    
    // US / UK / Global
    'inc.', 'inc', 'incorporated', 'llc', 'l.l.c.', 'corp.', 'corp', 'corporation',
    'co.', 'co', 'company', 'plc',
    
    // Europe
    'gmbh', 'gmbh & co. kg', 'gmbh & co kg', 'ag', 'kg', 'e.v.', 'ug', 'sarl', 'sas', 'sa', 'eurl',
    's.l.', 'sl', 's.a.', 's.l.u.', 's.a.b. de c.v.', 's.r.l.', 'srl', 's.p.a.', 'spa',
    'b.v.', 'bv', 'n.v.', 'nv', 'ab', 'as', 'aps', 'oy', 'oyj',
    
    // Asia & Middle East & Oceania
    'pty ltd', 'pty. ltd.', 'pty', 'k.k.', 'gk', 'kabushiki kaisha',
    'fze', 'fz-llc', 'wll', 'spc', 'co., ltd.', 'co.,ltd.'
  ];

  cleaned = cleaned.replace(/[,\.]+$|^\s+/g, '');

  for (const suffix of legalSuffixes) {
    const regex = new RegExp(`\\b${suffix.replace('.', '\\.')}\\b`, 'gi');
    cleaned = cleaned.replace(regex, '');
  }

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

    return hostname;
  } catch (err) {
    return null;
  }
}

/**
 * Domain relevance score (higher is better match)
 */
function calculateRelevanceScore(domain, companyName) {
  if (!domain || !companyName) return -1;

  const cleanName = cleanCompanyName(companyName).toLowerCase().replace(/[^a-z0-9]/g, '');
  const domainSlug = domain.split('.')[0].toLowerCase().replace(/[^a-z0-9]/g, '');

  if (!cleanName || !domainSlug) return -1;

  let baseScore = 0;

  if (cleanName === domainSlug) {
    baseScore = 120;
  } else if (domainSlug.startsWith(cleanName) || cleanName.startsWith(domainSlug)) {
    baseScore = 80;
  } else if (cleanName.includes(domainSlug) || domainSlug.includes(cleanName)) {
    baseScore = 65;
  } else {
    const cleaned = cleanCompanyName(companyName);
    const words = cleaned.toLowerCase().split(/[\s,-]+/).filter(w => w.length >= 2);
    const meaningfulWords = words.filter(w => !STOP_WORDS.has(w));

    const initialsWithStop = words.map(w => w[0]).join('');
    const initialsNoStop = meaningfulWords.map(w => w[0]).join('');

    if ((words.length >= 2 && initialsWithStop.length >= 2 && domainSlug === initialsWithStop) ||
        (meaningfulWords.length >= 2 && initialsNoStop.length >= 2 && domainSlug === initialsNoStop)) {
      baseScore = 95;
    } else {
      let matchCount = 0;
      for (const word of meaningfulWords) {
        if (word.length >= 3 && domainSlug.includes(word)) matchCount++;
      }
      if (matchCount > 0) baseScore = 45 + (matchCount * 5);
    }
  }

  if (baseScore <= 0) return 0;

  if (domain.endsWith('.com')) {
    baseScore += 20;
  } else if (domain.endsWith('.org') || domain.endsWith('.net') || domain.endsWith('.io') || domain.endsWith('.co')) {
    baseScore += 15;
  } else if (!SECOND_LEVEL_TLDS.has(domain.split('.').slice(-2).join('.'))) {
    baseScore += 5;
  }

  return baseScore;
}

/**
 * Direct Root Domain Verification with robust parallel HTTP/HTTPS fallback & content verification
 */
async function probeDirectRootDomain(companyName) {
  const cleaned = cleanCompanyName(companyName);
  const cleanSlug = cleaned.toLowerCase().replace(/[^a-z0-9]/g, '');
  if (!cleanSlug || cleanSlug.length < 2) return null;

  const candidateDomains = [
    `${cleanSlug}.com`,
    `${cleanSlug}.org`
  ];

  const words = cleaned.toLowerCase().split(/[\s,-]+/).filter(w => w.length >= 2);
  const meaningfulWords = words.filter(w => !STOP_WORDS.has(w));
  const primaryBrandWord = meaningfulWords.find(w => w.length >= 3) || words.find(w => w.length >= 3);

  const acronyms = [];
  if (words.length >= 3) {
    const init1 = words.map(w => w[0]).join('');
    if (init1.length >= 3 && init1 !== cleanSlug) acronyms.push(init1);
  }
  if (meaningfulWords.length >= 3) {
    const init2 = meaningfulWords.map(w => w[0]).join('');
    if (init2.length >= 3 && init2 !== cleanSlug && !acronyms.includes(init2)) acronyms.push(init2);
  }

  for (const acr of acronyms) {
    candidateDomains.push(`${acr}.org`);
    candidateDomains.push(`${acr}.com`);
  }

  async function checkCandidate(candidate) {
    const candidateSlug = candidate.split('.')[0].toLowerCase();
    const isAcronym = acronyms.includes(candidateSlug);
    const protocols = [`https://www.${candidate}`, `https://${candidate}`];

    for (const testUrl of protocols) {
      try {
        const res = await axios.get(testUrl, {
          headers: { 'User-Agent': BROWSER_HEADERS['User-Agent'] },
          timeout: 2000,
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

          if (isParkedOrForSalePage(htmlContent, title)) {
            return null;
          }

          if (isAcronym) {
            const lowerHtml = (htmlContent + ' ' + title).toLowerCase();
            const hasPrimaryKeyword = primaryBrandWord && lowerHtml.includes(primaryBrandWord);
            if (!hasPrimaryKeyword) {
              return null;
            }
          }

          const score = calculateRelevanceScore(candidate, companyName);
          if (score >= 60) {
            return {
              domain: candidate,
              logo: `https://logo.clearbit.com/${candidate}`,
              source: 'Direct Domain Verification',
              confidence: 'High'
            };
          }
        }
      } catch (e) {}
    }
    return null;
  }

  const results = await Promise.all(candidateDomains.map(d => checkCandidate(d)));
  return results.find(r => r !== null) || null;
}

/**
 * Strategy 1: Clearbit Autocomplete API
 */
async function searchClearbit(companyName) {
  const clean = cleanCompanyName(companyName);
  const rawClean = normalizeString(companyName);
  const queriesToTry = [clean, rawClean, companyName].filter((v, i, a) => v && a.indexOf(v) === i);

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
              const score = calculateRelevanceScore(cleanedDomain, companyName);
              if (score > maxScore && score >= 40) {
                maxScore = score;
                bestMatch = {
                  domain: cleanedDomain,
                  logo: item.logo || `https://logo.clearbit.com/${cleanedDomain}`,
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
 * Strategy 2: DuckDuckGo HTML Search Scraper (Multi-Region / Multi-Language)
 */
async function searchDuckDuckGo(companyName) {
  try {
    const cleanName = cleanCompanyName(companyName);
    const query = `"${cleanName}" official website`;

    const response = await axios.get(`https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`, {
      headers: BROWSER_HEADERS,
      timeout: 6000
    });

    const $ = cheerio.load(response.data);
    const candidateDomains = [];

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

    let bestDomain = null;
    let maxScore = -1;

    for (const domain of candidateDomains) {
      const score = calculateRelevanceScore(domain, companyName);
      if (score > maxScore) {
        maxScore = score;
        bestDomain = domain;
      }
    }

    if (bestDomain && maxScore >= 30) {
      return {
        domain: bestDomain,
        logo: `https://logo.clearbit.com/${bestDomain}`,
        source: 'DuckDuckGo Global Search',
        confidence: maxScore >= 70 ? 'High' : 'Medium'
      };
    }
  } catch (err) {}
  return null;
}

/**
 * Valentin.app UULE v1 Protobuf Generator
 * Encodes canonical name (e.g. "West New York,New Jersey,United States" or "India")
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
 * Encodes latitude, longitude and optional radius into Google UULE text format: "a+..."
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
 * Strategy 3: Valentin.app Localized Google Search with UULE + HL + GL
 */
async function searchValentinGoogle(companyName, options = {}) {
  try {
    const cleanName = cleanCompanyName(companyName);
    if (!cleanName) return null;

    const hl = options.languageCode || options.hl || 'en';
    const gl = options.countryCode || options.gl || 'US';

    let uule = options.uule;
    if (!uule && options.location) {
      uule = generateUULEv1(options.location);
    } else if (!uule && options.lat && options.lng) {
      uule = generateUULEv2(options.lat, options.lng);
    }

    const candidateDomains = [];

    // Step 1: Query Google Localized Autocomplete API with UULE, GL, HL
    const suggestQueries = [cleanName, `${cleanName} website`];
    for (const q of suggestQueries) {
      try {
        let suggestUrl = `https://suggestqueries.google.com/complete/search?client=chrome&q=${encodeURIComponent(q)}&gl=${gl}&hl=${hl}`;
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
    }

    // Step 2: Query Google Localized SERP HTML Search
    if (candidateDomains.length === 0) {
      const query = `"${cleanName}" official website`;
      const queryParams = new URLSearchParams();
      queryParams.set('q', query);
      queryParams.set('hl', hl);
      queryParams.set('gl', gl);
      if (uule) {
        queryParams.set('uule', uule);
      }

      const searchUrl = `https://www.google.com/search?${queryParams.toString()}`;

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
    }

    let bestDomain = null;
    let maxScore = -1;

    for (const domain of candidateDomains) {
      const score = calculateRelevanceScore(domain, companyName);
      if (score > maxScore) {
        maxScore = score;
        bestDomain = domain;
      }
    }

    if (bestDomain && maxScore >= 30) {
      const locLabel = options.location ? options.location : (options.countryCode ? options.countryCode.toUpperCase() : 'Valentin UULE');
      return {
        domain: bestDomain,
        logo: `https://logo.clearbit.com/${bestDomain}`,
        source: `Valentin Localized Search (${locLabel})`,
        confidence: maxScore >= 70 ? 'High' : 'Medium'
      };
    }
  } catch (err) {}
  return null;
}

/**
 * Strategy 4: Google Global Search Fallback
 */
async function searchGoogle(companyName) {
  try {
    const cleanName = cleanCompanyName(companyName);
    const query = `${cleanName} website`;

    const response = await axios.get(`https://www.google.com/search?q=${encodeURIComponent(query)}`, {
      headers: BROWSER_HEADERS,
      timeout: 6000
    });

    const $ = cheerio.load(response.data);
    const candidateDomains = [];

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

    let bestDomain = null;
    let maxScore = -1;

    for (const domain of candidateDomains) {
      const score = calculateRelevanceScore(domain, companyName);
      if (score > maxScore) {
        maxScore = score;
        bestDomain = domain;
      }
    }

    if (bestDomain && maxScore >= 30) {
      return {
        domain: bestDomain,
        logo: `https://logo.clearbit.com/${bestDomain}`,
        source: 'Google Global Search',
        confidence: maxScore >= 70 ? 'High' : 'Medium'
      };
    }
  } catch (err) {}
  return null;
}

/**
 * Strategy: Yahoo Search Engine Scraper
 */
async function searchYahoo(companyName) {
  try {
    const cleanName = cleanCompanyName(companyName);
    const query = `${cleanName} official website`;
    const response = await axios.get(`https://search.yahoo.com/search?p=${encodeURIComponent(query)}`, {
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
      const score = calculateRelevanceScore(domain, companyName);
      if (score > maxScore) {
        maxScore = score;
        bestDomain = domain;
      }
    }

    if (bestDomain && maxScore >= 30) {
      return {
        domain: bestDomain,
        logo: `https://logo.clearbit.com/${bestDomain}`,
        source: 'Yahoo Global Search',
        confidence: maxScore >= 70 ? 'High' : 'Medium'
      };
    }
  } catch (err) {}
  return null;
}

/**
 * Main Domain Finder function
 */
async function findDomainForCompany(companyName, options = {}) {
  if (!companyName || typeof companyName !== 'string' || !companyName.trim()) {
    return {
      company: companyName,
      domain: '',
      logo: '',
      status: 'Failed',
      source: 'N/A',
      confidence: 'None',
      error: 'Empty company name'
    };
  }

  const name = companyName.trim();

  // 0. Direct Root Domain Verification
  let result = await probeDirectRootDomain(name);

  // 1. Clearbit Autocomplete (Global)
  if (!result) {
    result = await searchClearbit(name);
  }

  // 2. Valentin Localized Search (if location, country, or uule specified in options)
  if (!result && (options.location || options.countryCode || options.uule || options.lat)) {
    result = await searchValentinGoogle(name, options);
  }

  // 3. Yahoo Global Search Engine
  if (!result) {
    result = await searchYahoo(name);
  }

  // 4. DuckDuckGo Global Search
  if (!result) {
    result = await searchDuckDuckGo(name);
  }

  // 5. Valentin Search fallback (default parameters) if no results from DuckDuckGo
  if (!result) {
    result = await searchValentinGoogle(name, options);
  }

  // 6. Google Global Search Fallback
  if (!result) {
    result = await searchGoogle(name);
  }

  if (result) {
    return {
      company: name,
      domain: result.domain,
      logo: result.logo,
      status: 'Found',
      source: result.source,
      confidence: result.confidence
    };
  }

  return {
    company: name,
    domain: '',
    logo: '',
    status: 'Not Found',
    source: 'N/A',
    confidence: 'None'
  };
}

/**
 * Process a batch of company names with concurrency limit and delay
 */
async function processCompanyBatch(companyList, onProgress, options = {}) {
  const concurrency = options.concurrency || 3;
  const delayMs = options.delayMs || 300;
  const results = [];
  
  let completedCount = 0;
  const queue = [...companyList];

  async function worker() {
    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) break;

      const companyName = typeof item === 'string' ? item : (item.companyName || item.company || Object.values(item)[0]);
      
      let res;
      try {
        res = await findDomainForCompany(companyName, options);
      } catch (err) {
        res = {
          company: companyName,
          domain: '',
          logo: '',
          status: 'Error',
          error: err.message
        };
      }

      if (typeof item === 'object' && item !== null) {
        res = { ...item, ...res };
      }

      results.push(res);
      completedCount++;

      if (typeof onProgress === 'function') {
        onProgress(res, completedCount, companyList.length);
      }

      if (delayMs > 0 && queue.length > 0) {
        await new Promise(r => setTimeout(r, delayMs));
      }
    }
  }

  const workers = Array.from({ length: Math.min(concurrency, companyList.length) }, () => worker());
  await Promise.all(workers);

  return results;
}

module.exports = {
  findDomainForCompany,
  processCompanyBatch,
  cleanCompanyName,
  extractCleanDomain,
  calculateRelevanceScore,
  normalizeString,
  generateUULEv1,
  generateUULEv2,
  searchValentinGoogle
};

