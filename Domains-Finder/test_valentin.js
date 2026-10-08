const assert = require('assert');
const {
  generateUULEv1,
  generateUULEv2,
  searchValentinGoogle,
  findDomainForCompany
} = require('./lib/domainFinder');

async function testValentinIntegration() {
  console.log('==================================================');
  console.log('🧪 TESTING VALENTIN.APP UULE & SERP SEARCH');
  console.log('==================================================\n');

  // Test 1: UULE v1 Protobuf Generator Test
  console.log('1️⃣ Testing UULE v1 Canonical Name Encoder:');
  const uule1 = generateUULEv1('West New York,New Jersey,United States');
  console.log('    canonicalName: "West New York,New Jersey,United States"');
  console.log('    Generated UULE v1:', uule1);
  const expectedUULE1 = 'w+CAIQICImV2VzdCBOZXcgWW9yayxOZXcgSmVyc2V5LFVuaXRlZCBTdGF0ZXM=';
  assert.strictEqual(uule1, expectedUULE1, 'UULE v1 encoding failed to match expected valentin.app vector');
  console.log('   ✅ UULE v1 Protobuf Generator Passed!\n');

  // Test 2: UULE v2 Coordinate Encoder Test
  console.log('2️⃣ Testing UULE v2 Coordinate Encoder:');
  const uule2 = generateUULEv2(37.421, -122.084);
  console.log('    Coordinates: (37.421, -122.084)');
  console.log('    Generated UULE v2:', uule2);
  assert.strictEqual(typeof uule2, 'string', 'UULE v2 output should be a string');
  assert(uule2.startsWith('a+'), 'UULE v2 string must start with "a+"');
  console.log('   ✅ UULE v2 Coordinate Encoder Passed!\n');

  // Test 3: Valentin Google Search Strategy Test
  console.log('3️⃣ Testing Valentin Google Search Strategy:');
  const testCompany = 'Blinkit';
  console.log(`   Searching domain for "${testCompany}" with countryCode="IN" & location="India"...`);
  const valentinRes = await searchValentinGoogle(testCompany, {
    countryCode: 'IN',
    location: 'India'
  });
  console.log('   Valentin Result:', valentinRes);
  assert(valentinRes && valentinRes.domain, 'Should find domain for Blinkit via Valentin Localized Search');
  assert(valentinRes.domain.includes('blinkit.com'), `Domain should be blinkit.com, got: ${valentinRes.domain}`);
  console.log('   ✅ Valentin Search Strategy Passed!\n');

  // Test 4: findDomainForCompany End-to-End Test
  console.log('4️⃣ Testing findDomainForCompany with Valentin Options:');
  const fullRes = await findDomainForCompany('Zomato', {
    countryCode: 'IN',
    location: 'India'
  });
  console.log('   Full Domain Finder Result:', fullRes);
  assert.strictEqual(fullRes.status, 'Found', 'Status should be Found');
  assert(fullRes.domain.includes('zomato.com'), `Domain should be zomato.com, got: ${fullRes.domain}`);
  console.log('   ✅ findDomainForCompany Integration Passed!\n');

  console.log('==================================================');
  console.log('🎉 ALL VALENTIN.APP INTEGRATION TESTS PASSED!');
  console.log('==================================================');
}

testValentinIntegration().catch(err => {
  console.error('\n❌ Test Failure:', err);
  process.exit(1);
});
