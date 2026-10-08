#!/usr/bin/env node

/**
 * Healthcare & Clinic Finder CLI
 * Usage: node cli.js <input.csv> [output.csv] [--column "Company Name"] [--concurrency 4]
 */

const fs = require('fs');
const path = require('path');
const csvParser = require('csv-parser');
const { format } = require('fast-csv');
const { processBatch } = require('./lib/analyzer');

const args = process.argv.slice(2);

if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log(`
🏥 Healthcare & Clinic Analyzer CLI
======================================
Usage:
  node cli.js <input.csv> [output.csv] [options]

Options:
  --column <name>       Column name containing the company name (auto-detected if omitted)
  --concurrency <num>   Number of concurrent analyses (default: 4)
  --help, -h            Show this help message

Example:
  node cli.js sample_companies.csv enriched_output.csv
  `);
  process.exit(0);
}

const inputFile = args[0];
let outputFile = args[1] && !args[1].startsWith('--') ? args[1] : `enriched_${path.basename(inputFile)}`;

let customColumn = null;
let concurrency = 4;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--column' && args[i + 1]) {
    customColumn = args[i + 1];
  }
  if (args[i] === '--concurrency' && args[i + 1]) {
    concurrency = parseInt(args[i + 1], 10) || 4;
  }
}

if (!fs.existsSync(inputFile)) {
  console.error(`❌ Error: Input file "${inputFile}" does not exist.`);
  process.exit(1);
}

async function run() {
  console.log(`\n=================================================`);
  console.log(`🏥 Healthcare & Clinic Finder CLI`);
  console.log(`📁 Input File:       ${inputFile}`);
  console.log(`💾 Output File:      ${outputFile}`);
  console.log(`⚡ Concurrency:      ${concurrency}`);
  console.log(`=================================================\n`);

  // Read CSV
  const rows = [];
  await new Promise((resolve, reject) => {
    fs.createReadStream(inputFile)
      .pipe(csvParser())
      .on('data', (row) => rows.push(row))
      .on('end', resolve)
      .on('error', reject);
  });

  if (rows.length === 0) {
    console.error('❌ Error: Input CSV is empty.');
    process.exit(1);
  }

  const headers = Object.keys(rows[0]).filter(h => h.trim() !== '');
  const candidateColumns = ['company', 'company name', 'company_name', 'organization', 'name', 'account name'];
  const targetColumn = customColumn || headers.find(h => candidateColumns.includes(h.trim().toLowerCase())) || headers[0];

  console.log(`🎯 Using column: "${targetColumn}" (${rows.length} rows to process)\n`);

  const startTime = Date.now();
  let completed = 0;
  let hcCount = 0;
  let locCount = 0;

  const enrichedRows = await processBatch(
    rows,
    targetColumn,
    { concurrency },
    (index, enrichedRow, analysis) => {
      completed++;
      const isHc = enrichedRow['Is_Healthcare'] === 'Yes';
      if (isHc) hcCount++;
      if (enrichedRow['Detected_Location'] && enrichedRow['Detected_Location'] !== 'Not Detected') locCount++;

      const hcBadge = isHc ? '✅ [HEALTHCARE]' : '❌ [NON-HC]    ';
      const locBadge = enrichedRow['Detected_Location'] || 'No Location';
      const compName = enrichedRow[targetColumn] || `Row #${index + 1}`;

      console.log(
        `[${completed}/${rows.length}] ${hcBadge} ${compName.padEnd(30).slice(0, 30)} | ` +
        `${enrichedRow['Healthcare_Category'].padEnd(25).slice(0, 25)} | ` +
        `📍 ${locBadge.slice(0, 25)}`
      );
    }
  );

  // Write enriched CSV
  const writeStream = fs.createWriteStream(outputFile);
  const csvStream = format({ headers: true });
  csvStream.pipe(writeStream);

  for (const r of enrichedRows) {
    csvStream.write(r);
  }
  csvStream.end();

  await new Promise((resolve) => writeStream.on('finish', resolve));

  const totalTimeSec = ((Date.now() - startTime) / 1000).toFixed(1);

  console.log(`\n=================================================`);
  console.log(`🎉 Enrichment Complete in ${totalTimeSec}s!`);
  console.log(`📊 Total Processed:      ${completed}`);
  console.log(`🏥 Healthcare Entities:  ${hcCount} (${Math.round((hcCount / completed) * 100)}%)`);
  console.log(`📍 Locations Detected:   ${locCount} (${Math.round((locCount / completed) * 100)}%)`);
  console.log(`💾 Saved to:             ${outputFile}`);
  console.log(`=================================================\n`);
}

run().catch(err => {
  console.error('Fatal Error:', err);
  process.exit(1);
});
