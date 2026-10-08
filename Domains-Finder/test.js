const { findDomainForCompany, processCompanyBatch } = require('./lib/domainFinder');

async function test() {
  console.log('--- Single Lookup Test ---');
  const testCompanies = ['Stripe', 'Google Inc.', 'Reliance Industries', 'Notion', 'NonExistentCompanyX12938'];

  for (const comp of testCompanies) {
    const res = await findDomainForCompany(comp);
    console.log(`Company: "${comp}" -> Domain: "${res.domain}" [Status: ${res.status}, Source: ${res.source}]`);
  }

  console.log('\n--- Batch Processing Test ---');
  const batch = ['Microsoft Corporation', 'AirBnb', 'Zomato India', 'Adobe Systems'];
  const results = await processCompanyBatch(batch, (item, current, total) => {
    console.log(`Progress (${current}/${total}): ${item.company} -> ${item.domain || 'NOT FOUND'}`);
  }, { concurrency: 2, delayMs: 200 });

  console.log('\nBatch finished. Total items processed:', results.length);
}

test();
