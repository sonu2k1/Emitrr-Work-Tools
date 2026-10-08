/**
 * Unit & Integration Test Suite for Healthcare & Location Finder
 */

const { classifyHealthcare } = require('./lib/healthcareClassifier');
const { detectLocation, extractLocationFromCompanyName, extractLocationFromText } = require('./lib/locationDetector');
const { analyzeCompany } = require('./lib/analyzer');

async function runTests() {
  console.log('🧪 Starting Healthcare & Location Finder Tests...\n');

  // Test 1: Healthcare Classifier direct tests
  console.log('--- Test Group 1: Healthcare Classifier ---');
  const testCases = [
    { name: 'Austin Smile Dental Spa', expectedHc: 'Yes', category: 'Dental & Oral Health' },
    { name: 'Apex Roofing & Siding LLC', expectedHc: 'No', category: 'Non-Healthcare' },
    { name: 'Pacific Coast Chiropractic & Rehab', expectedHc: 'Yes', category: 'Chiropractic & Spine' },
    { name: 'John Doe Law Offices', expectedHc: 'No', category: 'Non-Healthcare' },
    { name: 'Memorial Sloan Kettering Cancer Center', expectedHc: 'Yes', category: 'Hospital & Health System' },
    { name: 'Denver Auto Collision Specialists', expectedHc: 'No', category: 'Non-Healthcare' }
  ];

  let passedHc = 0;
  for (const tc of testCases) {
    const res = classifyHealthcare(tc.name);
    const passed = res.isHealthcare === tc.expectedHc;
    if (passed) passedHc++;
    console.log(`[${passed ? 'PASS' : 'FAIL'}] "${tc.name}" -> IsHc: ${res.isHealthcare} (${res.category}) [Conf: ${res.confidence}]`);
  }

  // Test 2: Location Extraction tests
  console.log('\n--- Test Group 2: Location Extraction ---');
  const locationCases = [
    { name: 'Austin Dental Clinic', text: '', expectedLocContains: 'Austin' },
    { name: 'General Dental Group', text: 'Visit our office at 123 Main St, Miami, FL 33101', expectedLocContains: 'Miami' },
    { name: 'Family Health Center', text: 'Serving patients throughout Chicago, IL and surrounding suburbs', expectedLocContains: 'Chicago' },
    { name: 'Seattle Eye Care', text: '', expectedLocContains: 'Seattle' }
  ];

  let passedLoc = 0;
  for (const tc of locationCases) {
    const res = detectLocation(tc.name, { snippetText: tc.text });
    const passed = res.formatted && res.formatted.includes(tc.expectedLocContains);
    if (passed) passedLoc++;
    console.log(`[${passed ? 'PASS' : 'FAIL'}] "${tc.name}" -> Detected: "${res.formatted}" (Source: ${res.source})`);
  }

  // Test 3: Master Analyzer Integration test
  console.log('\n--- Test Group 3: Master Analyzer End-to-End ---');
  const sampleCompany = 'Austin Heart Hospital';
  const fullAnalysis = await analyzeCompany(sampleCompany);
  console.log(`Analyzed: "${sampleCompany}"`);
  console.log(`  - Is Healthcare:     ${fullAnalysis.isHealthcare}`);
  console.log(`  - Category:          ${fullAnalysis.category}`);
  console.log(`  - Detected Location: ${fullAnalysis.detectedLocation}`);
  console.log(`  - Confidence:        ${fullAnalysis.confidence}`);
  console.log(`  - Reason:            ${fullAnalysis.reason}`);

  console.log(`\n==============================================`);
  console.log(`Classifier: ${passedHc}/${testCases.length} Passed`);
  console.log(`Location:   ${passedLoc}/${locationCases.length} Passed`);
  console.log(`==============================================\n`);
}

runTests().catch(err => {
  console.error('Test Error:', err);
  process.exit(1);
});
