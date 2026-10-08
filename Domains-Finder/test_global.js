const { findDomainForCompany } = require('./lib/domainFinder');

async function testGlobalCompanies() {
  console.log('====================================================');
  console.log('🌍 GLOBAL COUNTRY DOMAIN SEARCH ACCURACY TEST');
  console.log('====================================================\n');

  const globalCompanies = [
    { country: '🇬🇧 UK', name: 'BBC' },
    { country: '🇩🇪 Germany', name: 'BMW AG' },
    { country: '🇫🇷 France', name: 'L\'Oréal SA' },
    { country: '🇯🇵 Japan', name: 'Toyota Motor Corporation' },
    { country: '🇮🇳 India', name: 'Tata Consultancy Services Pvt Ltd' },
    { country: '🇦🇺 Australia', name: 'Atlassian Pty Ltd' },
    { country: '🇦🇪 UAE', name: 'Emirates Group' },
    { country: '🇺🇸 US', name: 'Salesforce Inc' },
    { country: '🇨🇦 Canada', name: 'Shopify Inc' },
    { country: '🇸🇪 Sweden', name: 'Spotify AB' }
  ];

  for (const item of globalCompanies) {
    const res = await findDomainForCompany(item.name);
    console.log(`${item.country.padEnd(15)} | "${item.name.padEnd(35)}" ➡️ Domain: ${(res.domain || 'NOT FOUND').padEnd(20)} [Source: ${res.source}]`);
  }

  console.log('\n====================================================');
}

testGlobalCompanies();
