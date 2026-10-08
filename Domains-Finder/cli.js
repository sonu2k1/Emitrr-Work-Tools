const fs = require('fs');
const path = require('path');
const csvParser = require('csv-parser');
const { processCompanyBatch } = require('./lib/domainFinder');

function parseArgs() {
  const args = process.argv.slice(2);
  const params = {
    input: null,
    output: null,
    column: null,
    concurrency: 3,
    delay: 300,
    location: null,
    country: null
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '-i' || arg === '--input') {
      params.input = args[++i];
    } else if (arg === '-o' || arg === '--output') {
      params.output = args[++i];
    } else if (arg === '-c' || arg === '--column') {
      params.column = args[++i];
    } else if (arg === '--concurrency') {
      params.concurrency = parseInt(args[++i], 10) || 3;
    } else if (arg === '--delay') {
      params.delay = parseInt(args[++i], 10) || 300;
    } else if (arg === '-l' || arg === '--location') {
      params.location = args[++i];
    } else if (arg === '--country') {
      params.country = args[++i];
    }
  }

  return params;
}

function escapeCsvField(val) {
  if (val === null || val === undefined) return '""';
  const str = String(val);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

async function runCLI() {
  const params = parseArgs();

  console.log('==============================================');
  console.log('       🔍 CSV COMPANY DOMAIN FINDER           ');
  console.log('==============================================');

  if (!params.input) {
    console.log('\nUsage:');
    console.log('  node cli.js -i <input.csv> [-o <output.csv>] [-c <column_name>] [-l <location>] [--country <US|IN|GB>]');
    console.log('\nOptions:');
    console.log('  -i, --input        Path to input CSV file (Required)');
    console.log('  -o, --output       Path to output CSV file (Default: <input>_domains.csv)');
    console.log('  -c, --column       Header name for company names (Default: Auto-detected)');
    console.log('  -l, --location     Canonical location for Valentin.app UULE (e.g. "India", "London,England,United Kingdom")');
    console.log('  --country          Two-letter ISO country code for Valentin SERP search (e.g. US, IN, GB)');
    console.log('  --concurrency      Concurrent search requests (Default: 3)');
    console.log('  --delay            Delay in ms between requests (Default: 300)');
    console.log('\nExample:');
    console.log('  node cli.js -i companies.csv -o output.csv -c "Company Name" -l "India" --country IN');
    process.exit(1);
  }

  const inputPath = path.resolve(params.input);
  if (!fs.existsSync(inputPath)) {
    console.error(`\n❌ Error: Input file not found at ${inputPath}`);
    process.exit(1);
  }

  const outputPath = params.output
    ? path.resolve(params.output)
    : inputPath.replace(/\.csv$/i, '_domains.csv');

  console.log(`\n📄 Reading CSV: ${inputPath}`);

  const rows = [];
  let detectedColumn = params.column;

  await new Promise((resolve, reject) => {
    fs.createReadStream(inputPath)
      .pipe(csvParser())
      .on('data', (row) => rows.push(row))
      .on('end', resolve)
      .on('error', reject);
  });

  if (rows.length === 0) {
    console.error('❌ Error: CSV file is empty.');
    process.exit(1);
  }

  const headers = Object.keys(rows[0]).filter(h => h.trim() !== '');
  console.log(`📊 Found ${rows.length} rows. Headers: [ ${headers.join(', ')} ]`);

  if (!detectedColumn) {
    const candidateNames = ['company', 'company name', 'company_name', 'organization', 'name', 'account name'];
    detectedColumn = headers.find(h => candidateNames.includes(h.trim().toLowerCase())) || headers[0];
    console.log(`💡 Auto-selected company name column: "${detectedColumn}"`);
  } else {
    if (!headers.includes(detectedColumn)) {
      console.warn(`⚠️ Warning: Column "${detectedColumn}" not found in CSV. Using "${headers[0]}".`);
      detectedColumn = headers[0];
    }
  }

  if (params.location || params.country) {
    console.log(`🎯 Valentin.app UULE Localized Search Enabled: Location="${params.location || 'N/A'}", Country="${params.country || 'N/A'}"`);
  }

  console.log(`🚀 Starting Domain Search with concurrency=${params.concurrency}...\n`);

  const startTime = Date.now();
  let foundCount = 0;

  const companyList = rows.map(r => ({
    originalRow: r,
    companyName: r[detectedColumn] || ''
  }));

  const processedResults = await processCompanyBatch(
    companyList,
    (res, current, total) => {
      const pct = Math.round((current / total) * 100);
      if (res.domain) foundCount++;
      const statusSymbol = res.domain ? '✅' : '❌';
      const companyStr = String(res.company || '').padEnd(30);
      const domainStr = String(res.domain ? res.domain : 'NOT FOUND').padEnd(25);
      console.log(`[${current}/${total}] (${pct}%) ${statusSymbol} ${companyStr} -> ${domainStr} [${res.source || 'N/A'}]`);
    },
    {
      concurrency: params.concurrency,
      delayMs: params.delay,
      location: params.location,
      countryCode: params.country
    }
  );

  const allHeaders = [...headers];
  if (!allHeaders.includes('Found Domain')) allHeaders.push('Found Domain');
  if (!allHeaders.includes('Domain Status')) allHeaders.push('Domain Status');
  if (!allHeaders.includes('Domain Source')) allHeaders.push('Domain Source');
  if (!allHeaders.includes('Company Logo')) allHeaders.push('Company Logo');

  const csvRows = [];
  csvRows.push(allHeaders.map(escapeCsvField).join(','));

  for (const item of processedResults) {
    const orig = item.originalRow || {};
    const rowValues = headers.map(h => orig[h] !== undefined ? orig[h] : '');
    
    rowValues.push(item.domain || '');
    rowValues.push(item.status || 'Not Found');
    rowValues.push(item.source || 'N/A');
    rowValues.push(item.logo || '');

    csvRows.push(rowValues.map(escapeCsvField).join(','));
  }

  fs.writeFileSync(outputPath, csvRows.join('\n'), 'utf8');

  const durationSec = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log('\n==============================================');
  console.log(`✨ Processing Complete in ${durationSec}s!`);
  console.log(`📊 Total: ${rows.length} | Found: ${foundCount} (${Math.round((foundCount/rows.length)*100)}%)`);
  console.log(`💾 Saved Enriched CSV to: ${outputPath}`);
  console.log('==============================================\n');
}

runCLI().catch(err => {
  console.error('Fatal CLI Error:', err);
  process.exit(1);
});
