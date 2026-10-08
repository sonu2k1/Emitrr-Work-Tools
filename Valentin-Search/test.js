const assert = require('assert');
const {
  generateUULEv1,
  generateUULEv2,
  geocodeAddress,
  findPracticeDomain,
  cleanPracticeName
} = require('./lib/valentinEngine');

async function runTests() {
  console.log('===============================================================');
  console.log('🧪 RUNNING VALENTIN PRACTICE SEARCH VALIDATION SUITE');
  console.log('===============================================================\n');

  // Test 1: UULE v1 Protobuf Generator
  console.log('1️⃣ Testing UULE v1 Canonical Name Generator:');
  const uuleUS = generateUULEv1('New York, NY, USA');
  console.log('   Location: "New York, NY, USA" -> UULE:', uuleUS);
  assert(uuleUS.startsWith('w+'), 'UULE v1 must start with w+');

  const uuleCA = generateUULEv1('Toronto, ON, Canada');
  console.log('   Location: "Toronto, ON, Canada" -> UULE:', uuleCA);
  assert(uuleCA.startsWith('w+'), 'UULE v1 Canada must start with w+');
  console.log('   ✅ UULE v1 Passed!\n');

  // Test 2: UULE v2 Coordinate Encoder
  console.log('2️⃣ Testing UULE v2 Coordinate Encoder:');
  const uuleCoord = generateUULEv2(40.7128, -74.0060);
  console.log('   Coords: (40.7128, -74.0060) -> UULE:', uuleCoord);
  assert(uuleCoord.startsWith('a+'), 'UULE v2 must start with a+');
  console.log('   ✅ UULE v2 Passed!\n');

  // Test 3: Valentin Geocoding API
  console.log('3️⃣ Testing Valentin.app Geocoding API:');
  const geoRes = await geocodeAddress('Chicago, IL', 'US');
  console.log('   Geocoded Chicago:', geoRes);
  assert(geoRes && geoRes.lat && geoRes.lng, 'Valentin geocode should return lat and lng');
  console.log('   ✅ Valentin Geocoding Passed!\n');

  // Test 4: Practice Name Cleaner
  console.log('4️⃣ Testing Practice Name Normalization:');
  const raw1 = 'Aspen Dental Management, Inc.';
  const clean1 = cleanPracticeName(raw1);
  console.log(`   "${raw1}" ➜ "${clean1}"`);
  assert.strictEqual(clean1, 'Aspen Dental Management', 'Should strip legal suffix');

  const raw2 = 'Dr. John Smith, DDS, PLLC (Downtown)';
  const clean2 = cleanPracticeName(raw2);
  console.log(`   "${raw2}" ➜ "${clean2}"`);
  assert.strictEqual(clean2, 'John Smith', 'Should strip titles, credentials and brackets');
  console.log('   ✅ Name Normalization Passed!\n');

  // Test 5: US Practice Domain Finding
  console.log('5️⃣ Testing US Practice Domain Finding:');
  const usTest1 = await findPracticeDomain('Aspen Dental', { countryCode: 'US', city: 'Chicago', state: 'IL' });
  console.log('   US Practice 1 (Aspen Dental):', usTest1);
  assert.strictEqual(usTest1.status, 'Found', 'Aspen Dental should be found');
  assert(usTest1.domain.includes('aspendental.com'), `Domain should be aspendental.com, got: ${usTest1.domain}`);

  const usTest2 = await findPracticeDomain('One Medical', { countryCode: 'US', city: 'San Francisco', state: 'CA' });
  console.log('   US Practice 2 (One Medical):', usTest2);
  assert.strictEqual(usTest2.status, 'Found', 'One Medical should be found');
  assert(usTest2.domain.includes('onemedical.com'), `Domain should be onemedical.com, got: ${usTest2.domain}`);
  console.log('   ✅ US Practice Search Passed!\n');

  // Test 6: Canada Practice Domain Finding
  console.log('6️⃣ Testing Canada Practice Domain Finding:');
  const caTest1 = await findPracticeDomain('Altima Dental', { countryCode: 'CA', city: 'Toronto', state: 'ON' });
  console.log('   Canada Practice 1 (Altima Dental):', caTest1);
  assert.strictEqual(caTest1.status, 'Found', 'Altima Dental should be found');
  assert(caTest1.domain.includes('altimadental.com'), `Domain should be altimadental.com, got: ${caTest1.domain}`);

  const caTest2 = await findPracticeDomain('123Dentist', { countryCode: 'CA', city: 'Vancouver', state: 'BC' });
  console.log('   Canada Practice 2 (123Dentist):', caTest2);
  assert.strictEqual(caTest2.status, 'Found', '123Dentist should be found');
  assert(caTest2.domain.includes('123dentist'), `Domain should contain 123dentist, got: ${caTest2.domain}`);
  console.log('   ✅ Canada Practice Search Passed!\n');

  console.log('===============================================================');
  console.log('🎉 ALL TESTS PASSED SUCCESSFULLY!');
  console.log('===============================================================');
}

runTests().catch(err => {
  console.error('\n❌ Test Failure:', err);
  process.exit(1);
});
