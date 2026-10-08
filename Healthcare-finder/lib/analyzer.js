/**
 * Master Analyzer Pipeline
 * Coordinates web search, website scraping, healthcare classification,
 * and location detection for single companies and CSV batch rows.
 */

const { classifyHealthcare } = require('./healthcareClassifier');
const { detectLocation, extractLocationFromCompanyName } = require('./locationDetector');
const { searchDuckDuckGo, queryGoogleSuggest, scrapeWebsite } = require('./searchEngine');

/**
 * Analyze a single company name
 * @param {string} companyName - Name of the company
 * @param {object} options - Optional hints (e.g. location, website)
 * @returns {Promise<object>} Detailed analysis result
 */
async function analyzeCompany(companyName, options = {}) {
  if (!companyName || typeof companyName !== 'string' || !companyName.trim()) {
    return {
      companyName: '',
      isHealthcare: 'No',
      category: 'Unknown',
      detectedLocation: 'Not Detected',
      confidence: 'Low',
      reason: 'Empty company name provided',
      websiteDomain: '',
      signals: []
    };
  }

  const cleanName = companyName.trim();
  let domain = options.website || options.domain || '';
  let snippetText = '';
  let titleText = '';
  let metaText = '';
  let bodyText = '';
  let schemaObjects = [];
  let schemaTypes = [];

  // Step 1: Perform Web & DuckDuckGo Search if no domain or to gather snippets
  try {
    const searchResults = await searchDuckDuckGo(`"${cleanName}"`);
    if (searchResults && searchResults.length > 0) {
      // Gather snippets from top 3 results
      snippetText = searchResults.map(r => `${r.title}. ${r.snippet}`).join(' ');
      
      if (!domain) {
        const topWithDomain = searchResults.find(r => r.domain);
        if (topWithDomain) {
          domain = topWithDomain.domain;
        }
      }
    }
  } catch (err) {}

  // Step 2: If domain is available, scrape website for rich JSON-LD & body text
  if (domain) {
    try {
      const siteData = await scrapeWebsite(domain);
      if (siteData) {
        titleText = siteData.titleText || '';
        metaText = siteData.metaText || '';
        bodyText = siteData.bodyText || '';
        schemaObjects = siteData.schemaObjects || [];
        schemaTypes = siteData.schemaTypes || [];
      }
    } catch (err) {}
  }

  // Step 3: Run Healthcare Classification
  const contextData = {
    domain,
    snippetText,
    titleText,
    metaText,
    bodyText,
    schemaObjects,
    schemaTypes
  };

  const classification = classifyHealthcare(cleanName, contextData);

  // Step 4: Run Location Detection
  const locationResult = detectLocation(cleanName, contextData);

  // Fallback: If user provided a location hint or column
  let finalLocation = locationResult.formatted;
  if ((!finalLocation || finalLocation === 'Not Detected') && options.location) {
    finalLocation = options.location;
  }

  return {
    companyName: cleanName,
    isHealthcare: classification.isHealthcare,
    category: classification.category,
    detectedLocation: finalLocation || 'Not Detected',
    confidence: classification.confidence,
    reason: classification.reason,
    websiteDomain: domain || 'N/A',
    signals: classification.signals || [],
    locationSource: locationResult.source || 'None'
  };
}

/**
 * Process a batch of rows with controlled concurrency
 * @param {Array<object>} rows - Array of CSV row objects
 * @param {string} companyColumn - Name of the company column
 * @param {object} options - Configuration options (concurrency, etc.)
 * @param {function} onProgress - Callback fired after each processed item
 * @param {function} isCancelled - Function to check if processing was cancelled/paused
 * @returns {Promise<Array<object>>} Enriched rows
 */
async function processBatch(rows, companyColumn, options = {}, onProgress = () => {}, isCancelled = () => false) {
  const concurrency = options.concurrency || 4;
  const results = new Array(rows.length);
  let currentIndex = 0;

  async function worker() {
    while (currentIndex < rows.length) {
      if (isCancelled && isCancelled()) {
        break;
      }

      const index = currentIndex++;
      const row = rows[index];
      const companyName = row[companyColumn] || row['Company'] || row['company'] || Object.values(row)[0] || '';

      // Check for possible existing location or website columns in the row
      const locationHint = row['Location'] || row['City'] || row['State'] || row['Address'] || '';
      const websiteHint = row['Website'] || row['Domain'] || row['URL'] || '';

      try {
        const analysis = await analyzeCompany(companyName, {
          location: locationHint,
          website: websiteHint
        });

        const enrichedRow = {
          ...row,
          'Is_Healthcare': analysis.isHealthcare,
          'Healthcare_Category': analysis.category,
          'Detected_Location': analysis.detectedLocation,
          'Confidence_Score': analysis.confidence,
          'Analysis_Reason': analysis.reason,
          'Website_Domain': analysis.websiteDomain
        };

        results[index] = enrichedRow;
        onProgress(index, enrichedRow, analysis);
      } catch (err) {
        const fallbackRow = {
          ...row,
          'Is_Healthcare': 'No',
          'Healthcare_Category': 'Error / Unknown',
          'Detected_Location': locationHint || 'Not Detected',
          'Confidence_Score': 'Low',
          'Analysis_Reason': `Analysis failed: ${err.message}`,
          'Website_Domain': websiteHint || 'N/A'
        };
        results[index] = fallbackRow;
        onProgress(index, fallbackRow, null);
      }
    }
  }

  const workers = Array.from({ length: Math.min(concurrency, rows.length) }, () => worker());
  await Promise.all(workers);

  return results.filter(Boolean);
}

module.exports = {
  analyzeCompany,
  processBatch
};
