/**
 * Search Engine & Web Metadata Scraper
 * Queries search engines (Google Suggest, DuckDuckGo HTML, SERP) to find company domains,
 * knowledge graph snippets, and crawls landing pages for Schema.org JSON-LD data.
 */

const axios = require('axios');
const cheerio = require('cheerio');
const { URL } = require('url');

const BROWSER_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9'
};

const IGNORED_DOMAINS = new Set([
  'linkedin.com', 'facebook.com', 'instagram.com', 'twitter.com', 'x.com',
  'youtube.com', 'pinterest.com', 'wikipedia.org', 'crunchbase.com', 'glassdoor.com',
  'yelp.com', 'bloomberg.com', 'reuters.com', 'github.com', 'medium.com',
  'reddit.com', 'quora.com', 'zoominfo.com', 'pitchbook.com', 'trustpilot.com',
  'sec.gov', 'dnb.com', 'indeed.com', 'bbb.org', 'owler.com', 'apollo.io',
  'tiktok.com', 'mapquest.com', 'yellowpages.com', 'yahoo.com', 'bing.com',
  'duckduckgo.com', 'google.com'
]);

/**
 * Clean and extract domain from URL string
 */
function extractDomain(urlStr) {
  if (!urlStr) return null;
  let cleanUrl = urlStr.trim();
  if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
    cleanUrl = 'https://' + cleanUrl;
  }
  try {
    const parsed = new URL(cleanUrl);
    let hostname = parsed.hostname.toLowerCase();
    if (hostname.startsWith('www.')) {
      hostname = hostname.slice(4);
    }
    if (IGNORED_DOMAINS.has(hostname)) {
      return null;
    }
    return hostname;
  } catch (e) {
    return null;
  }
}

/**
 * Search DuckDuckGo HTML for snippets, title, and website domain
 */
async function searchDuckDuckGo(query) {
  try {
    const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    const response = await axios.get(url, {
      headers: BROWSER_HEADERS,
      timeout: 5000
    });

    const $ = cheerio.load(response.data);
    const results = [];

    $('.result').each((i, el) => {
      if (i >= 5) return;
      const title = $(el).find('.result__title a').text().trim();
      let rawHref = $(el).find('.result__title a').attr('href');
      const snippet = $(el).find('.result__snippet').text().trim();

      let targetUrl = rawHref;
      if (rawHref && rawHref.includes('uddg=')) {
        try {
          const match = rawHref.match(/uddg=([^&]+)/);
          if (match) {
            targetUrl = decodeURIComponent(match[1]);
          }
        } catch (e) {}
      }

      const domain = extractDomain(targetUrl);
      if (title || snippet) {
        results.push({
          title,
          snippet,
          url: targetUrl,
          domain
        });
      }
    });

    return results;
  } catch (err) {
    return [];
  }
}

/**
 * Query Google Suggest for autocomplete queries
 */
async function queryGoogleSuggest(companyName) {
  try {
    const url = `https://suggestqueries.google.com/complete/search?client=chrome&q=${encodeURIComponent(companyName + ' clinic healthcare')}&gl=us&hl=en`;
    const response = await axios.get(url, {
      headers: BROWSER_HEADERS,
      timeout: 3500
    });

    if (Array.isArray(response.data) && Array.isArray(response.data[1])) {
      return response.data[1];
    }
    return [];
  } catch (err) {
    return [];
  }
}

/**
 * Fetch and scrape company landing page for schema.org, titles, and body content
 */
async function scrapeWebsite(domain) {
  if (!domain) return null;
  const targetUrl = `https://${domain}`;

  try {
    const response = await axios.get(targetUrl, {
      headers: BROWSER_HEADERS,
      timeout: 5000,
      maxRedirects: 3,
      validateStatus: (status) => status < 400
    });

    const html = response.data;
    if (typeof html !== 'string') return null;

    const $ = cheerio.load(html);

    // 1. Extract Schema.org JSON-LD
    const schemaObjects = [];
    const schemaTypes = [];
    $('script[type="application/ld+json"]').each((_, el) => {
      try {
        const raw = $(el).html();
        if (raw) {
          const parsed = JSON.parse(raw.trim());
          schemaObjects.push(parsed);

          if (parsed['@type']) {
            if (Array.isArray(parsed['@type'])) {
              schemaTypes.push(...parsed['@type']);
            } else {
              schemaTypes.push(parsed['@type']);
            }
          }
          if (Array.isArray(parsed['@graph'])) {
            for (const item of parsed['@graph']) {
              if (item['@type']) {
                schemaTypes.push(item['@type']);
              }
            }
          }
        }
      } catch (e) {}
    });

    // 2. Extract Meta tags
    let metaText = '';
    $('meta').each((_, el) => {
      const name = $(el).attr('name') || $(el).attr('property') || '';
      const content = $(el).attr('content') || '';
      if (name && content) {
        metaText += ` ${name}: ${content}`;
      }
    });

    // 3. Extract title and body text
    const titleText = $('title').text().trim();
    $('script, style, noscript, svg, path').remove();
    const bodyText = $('body').text().replace(/\s+/g, ' ').trim().slice(0, 5000);

    return {
      domain,
      url: targetUrl,
      titleText,
      metaText,
      bodyText,
      schemaObjects,
      schemaTypes
    };
  } catch (err) {
    // Return minimal domain context if website is unreachable
    return {
      domain,
      url: targetUrl,
      titleText: '',
      metaText: '',
      bodyText: '',
      schemaObjects: [],
      schemaTypes: []
    };
  }
}

module.exports = {
  searchDuckDuckGo,
  queryGoogleSuggest,
  scrapeWebsite,
  extractDomain
};
