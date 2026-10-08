#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const csvParser = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const { processPracticeBatch, findPracticeDomain } = require('./lib/valentinEngine');

function printBanner() {
  console.log('\x1b[36m===============================================================\x1b[0m');
  console.log('\x1b[1m\x1b[32m  🏥 VALENTIN.APP PRACTICE & CLINIC DOMAIN FINDER (US & CA)\x1b[0m');
  console.log('\x1b[36m===============================================================\x1b[0m');
  console.log('\x1b[90m  Powered by Valentin.app Geocoding & Localized Google UULE Search\x1b[0m\n');
}

function printHelp() {
  printBanner();
  console.log(`Usage:
  node cli.js --input <input_csv_file> [options]
  node cli.js -i practices.csv -o output.csv -c US

Options:
  -i, --input <file>        Path to input CSV file (Required)
  -o, --output <file>       Path to output CSV file (Default: output_valentin_domains.csv)
  -c, --country <code>      Target Country: US (United States), CA (Canada), or ALL (Default: US)
  --concurrency <num>       Concurrent search threads (Default: 3)
  --delay <ms>              Delay between batch requests in ms (Default: 300)
  -s, --single <name>       Search single practice name directly
  -h, --help                Show this help menu

Examples:
  node cli.js -i sample_practices.csv -c US
  node cli.js -i sample_practices.csv -c CA -o canada_results.csv
  node cli.js -s "Aspen Dental" -c US
  node cli.js -s "Altima Dental" -c CA
`);
}

async function runSingleSearch(practiceName, country) {
  printBanner();
  console.log(`🔍 Searching domain for: "\x1b[1m\x1b[33m${practiceName}\x1b[0m" [Country: \x1b[35m${country}\x1b[0m]...\n`);
  
  const startTime = Date.now();
  const res = await findPracticeDomain(practiceName, { countryCode: country });
  const duration = ((Date.now() - startTime) / 1000).toFixed(2);

  if (res.status === 'Found') {
    console.log(`\x1b[32m✔ SUCCESS (${duration}s)\x1b[0m`);
    console.log(`  🏢 Practice:   ${res.practiceName}`);
    console.log(`  🧹 Cleaned:    ${res.cleanedName}`);
    console.log(`  🌐 Domain:     \x1b[1m\x1b[36m${res.domain}\x1b[0m`);
    console.log(`  🔗 URL:        ${res.websiteUrl}`);
    console.log(`  🎯 Confidence: ${res.confidence}`);
    console.log(`  📡 Source:     ${res.source}`);
  } else {
    console.log(`\x1b[31m✖ NOT FOUND (${duration}s)\x1b[0m`);
    console.log(`  🏢 Practice:   ${res.practiceName}`);
    console.log(`  🧹 Cleaned:    ${res.cleanedName}`);
    console.log(`  ⚠️ Status:     ${res.status}`);
  }
}

async function runBatchSearch(inputFile, outputFile, country, concurrency, delay) {
  printBanner();

  if (!fs.existsSync(inputFile)) {
    console.error(`\x1b[31m❌ Error: Input file "${inputFile}" does not exist!\x1b[0m`);
    process.exit(1);
  }

  console.log(`📁 Input CSV:      \x1b[33m${inputFile}\x1b[0m`);
  console.log(`💾 Output CSV:     \x1b[33m${outputFile}\x1b[0m`);
  console.log(`🌎 Target Country: \x1b[35m${country.toUpperCase()}\x1b[0m`);
  console.log(`⚡ Concurrency:    \x1b[36m${concurrency}\x1b[0m`);
  console.log(`⏱️ Request Delay:  \x1b[36m${delay}ms\x1b[0m\n`);
  console.log('---------------------------------------------------------------');
  console.log('🚀 Reading records from CSV...');

  const records = [];
  await new Promise((resolve, reject) => {
    fs.createReadStream(inputFile)
      .pipe(csvParser())
      .on('data', (data) => records.push(data))
      .on('end', resolve)
      .on('error', reject);
  });

  if (records.length === 0) {
    console.error('\x1b[31m❌ Input CSV is empty!\x1b[0m');
    process.exit(1);
  }

  console.log(`📊 Loaded \x1b[1m${records.length}\x1b[0m practice records to process.\n`);

  let foundCount = 0;
  let notFoundCount = 0;
  let errorCount = 0;
  const startTime = Date.now();

  // Create initial CSV header
  const initialHeaders = ['Practice Name', 'practiceName', 'cleanedName', 'country', 'domain', 'websiteUrl', 'status', 'source', 'confidence'];
  if (!fs.existsSync(outputFile)) {
    fs.writeFileSync(outputFile, initialHeaders.join(',') + '\n', 'utf8');
  }

  const onProgress = (result, current, total) => {
    const percent = Math.round((current / total) * 100);
    const pName = (result.practiceName || result.Practice_Name || Object.values(result)[0] || '').substring(0, 32);
    
    if (result.status === 'Found') {
      foundCount++;
      console.log(`[\x1b[36m${current}/${total}\x1b[0m] (\x1b[32m${percent}%\x1b[0m) \x1b[32m✔ FOUND\x1b[0m  ${pName.padEnd(32)} ➜ \x1b[1m\x1b[36m${result.domain}\x1b[0m \x1b[90m(${result.source})\x1b[0m`);
    } else {
      notFoundCount++;
      console.log(`[\x1b[36m${current}/${total}\x1b[0m] (\x1b[33m${percent}%\x1b[0m) \x1b[31m✖ NOT FOUND\x1b[0m ${pName.padEnd(32)}`);
    }

    // Append to output CSV
    const escapeCsv = (val) => {
      if (val === null || val === undefined) return '';
      const str = String(val);
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    const rowLine = [
      escapeCsv(result['Practice Name'] || result.practiceName || ''),
      escapeCsv(result.practiceName || ''),
      escapeCsv(result.cleanedName || ''),
      escapeCsv(result.country || ''),
      escapeCsv(result.domain || ''),
      escapeCsv(result.websiteUrl || ''),
      escapeCsv(result.status || ''),
      escapeCsv(result.source || ''),
      escapeCsv(result.confidence || '')
    ].join(',') + '\n';

    fs.appendFileSync(outputFile, rowLine, 'utf8');
  };

  // Remove existing output file if starting fresh
  if (fs.existsSync(outputFile)) {
    fs.unlinkSync(outputFile);
    fs.writeFileSync(outputFile, initialHeaders.join(',') + '\n', 'utf8');
  }

  const results = await processPracticeBatch(records, onProgress, {
    country: country.toUpperCase(),
    concurrency,
    delayMs: delay
  });

  const totalTime = ((Date.now() - startTime) / 1000).toFixed(2);
  const successRate = Math.round((foundCount / records.length) * 100);

  console.log('\n===============================================================');
  console.log('\x1b[1m\x1b[32m🎉 BATCH PROCESSING COMPLETE!\x1b[0m');
  console.log('===============================================================');
  console.log(`📊 Total Processed: \x1b[1m${records.length}\x1b[0m`);
  console.log(`✔ Domains Found:   \x1b[32m\x1b[1m${foundCount}\x1b[0m (${successRate}%)`);
  console.log(`✖ Not Found:       \x1b[31m${notFoundCount}\x1b[0m`);
  console.log(`⏱️ Total Time:      \x1b[36m${totalTime}s\x1b[0m (Avg: ${(totalTime / records.length).toFixed(2)}s/record)`);
  console.log(`💾 Saved Output:    \x1b[1m\x1b[33m${path.resolve(outputFile)}\x1b[0m`);
  console.log('===============================================================\n');
}

// Parse Command Line Arguments
const args = process.argv.slice(2);
let inputFile = null;
let outputFile = 'output_valentin_domains.csv';
let country = 'US';
let concurrency = 3;
let delay = 300;
let singleSearchName = null;

for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === '-i' || arg === '--input') {
    inputFile = args[++i];
  } else if (arg === '-o' || arg === '--output') {
    outputFile = args[++i];
  } else if (arg === '-c' || arg === '--country') {
    country = args[++i];
  } else if (arg === '--concurrency') {
    concurrency = parseInt(args[++i], 10) || 3;
  } else if (arg === '--delay') {
    delay = parseInt(args[++i], 10) || 300;
  } else if (arg === '-s' || arg === '--single') {
    singleSearchName = args[++i];
  } else if (arg === '-h' || arg === '--help') {
    printHelp();
    process.exit(0);
  }
}

if (singleSearchName) {
  runSingleSearch(singleSearchName, country).catch(err => {
    console.error('Error during search:', err);
    process.exit(1);
  });
} else if (inputFile) {
  runBatchSearch(inputFile, outputFile, country, concurrency, delay).catch(err => {
    console.error('Error during batch search:', err);
    process.exit(1);
  });
} else {
  printHelp();
}
