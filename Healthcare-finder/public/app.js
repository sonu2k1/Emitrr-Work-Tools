/**
 * Healthcare & Clinic Analyzer - Frontend Logic
 */

let currentJobId = null;
let currentEventSource = null;
let currentFilter = 'all';
let allResults = [];

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('csv-file-input');
const uploadSection = document.getElementById('upload-section');
const configSection = document.getElementById('config-section');
const progressSection = document.getElementById('progress-section');

const columnSelect = document.getElementById('column-select');
const concurrencySelect = document.getElementById('concurrency-select');
const previewThead = document.getElementById('preview-thead');
const previewTbody = document.getElementById('preview-tbody');
const previewRowCount = document.getElementById('preview-row-count');

const statProcessed = document.getElementById('stat-processed');
const statHealthcare = document.getElementById('stat-healthcare');
const statLocations = document.getElementById('stat-locations');
const statNonHealthcare = document.getElementById('stat-non-healthcare');

const progressFill = document.getElementById('progress-fill');
const progressPercentage = document.getElementById('progress-percentage');
const progressStatusText = document.getElementById('progress-status-text');

const liveTbody = document.getElementById('live-tbody');
const btnExportCsv = document.getElementById('btn-export-csv');
const btnCancelJob = document.getElementById('btn-cancel-job');

const countAll = document.getElementById('count-all');
const countHc = document.getElementById('count-hc');
const countNonHc = document.getElementById('count-non-hc');

/**
 * Tab Switching
 */
function switchTab(tabId) {
  document.getElementById('tab-batch').classList.toggle('active', tabId === 'batch');
  document.getElementById('tab-single').classList.toggle('active', tabId === 'single');

  document.getElementById('view-batch').style.display = tabId === 'batch' ? 'block' : 'none';
  document.getElementById('view-single').style.display = tabId === 'single' ? 'block' : 'none';
}

/**
 * Drag & Drop Event Listeners
 */
if (dropzone) {
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  });
}

/**
 * Upload & Parse CSV
 */
async function handleFileUpload(file) {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    alert('Please upload a valid .csv file');
    return;
  }

  const formData = new FormData();
  formData.append('csvFile', file);

  try {
    dropzone.innerHTML = `
      <div class="dropzone-icon"><i class="fa-solid fa-spinner fa-spin"></i></div>
      <h3>Parsing CSV File...</h3>
      <p>${file.name}</p>
    `;

    const res = await fetch('/api/upload-csv', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Failed to upload CSV');
    }

    currentJobId = data.jobId;
    renderConfigSection(data);
  } catch (err) {
    alert('Upload Error: ' + err.message);
    resetUpload();
  }
}

/**
 * Render Configuration & Preview
 */
function renderConfigSection(data) {
  uploadSection.style.display = 'none';
  configSection.style.display = 'block';

  // Populate Columns
  columnSelect.innerHTML = '';
  data.headers.forEach(h => {
    const opt = document.createElement('option');
    opt.value = h;
    opt.textContent = h;
    if (h === data.autoDetectedColumn) {
      opt.selected = true;
    }
    columnSelect.appendChild(opt);
  });

  previewRowCount.textContent = `${data.totalRows} total rows`;

  // Populate Preview Table
  previewThead.innerHTML = '';
  const headerRow = document.createElement('tr');
  data.headers.forEach(h => {
    const th = document.createElement('th');
    th.textContent = h;
    headerRow.appendChild(th);
  });
  previewThead.appendChild(headerRow);

  previewTbody.innerHTML = '';
  data.sampleData.forEach(row => {
    const tr = document.createElement('tr');
    data.headers.forEach(h => {
      const td = document.createElement('td');
      td.textContent = row[h] || '';
      tr.appendChild(td);
    });
    previewTbody.appendChild(tr);
  });
}

/**
 * Reset Upload
 */
function resetUpload() {
  if (currentEventSource) {
    currentEventSource.close();
    currentEventSource = null;
  }
  currentJobId = null;
  allResults = [];
  fileInput.value = '';

  uploadSection.style.display = 'block';
  configSection.style.display = 'none';
  progressSection.style.display = 'none';

  dropzone.innerHTML = `
    <div class="dropzone-icon"><i class="fa-solid fa-cloud-arrow-up"></i></div>
    <h3>Drag & Drop your CSV file here</h3>
    <p>Upload any CSV containing company or organization names</p>
    <div class="upload-actions">
      <button class="btn btn-primary" onclick="document.getElementById('csv-file-input').click()">
        <i class="fa-solid fa-folder-open"></i> Browse CSV File
      </button>
      <a href="/api/sample-csv" class="btn btn-outline" download>
        <i class="fa-solid fa-download"></i> Download Sample CSV
      </a>
    </div>
  `;
}

/**
 * Start Batch Processing Job
 */
async function startBatchProcessing() {
  if (!currentJobId) return;

  const selectedCol = columnSelect.value;
  const conc = concurrencySelect.value;

  configSection.style.display = 'none';
  progressSection.style.display = 'block';

  liveTbody.innerHTML = '';
  allResults = [];
  btnExportCsv.disabled = true;

  // Listen to SSE Stream
  subscribeToJobStream(currentJobId);

  // Trigger start
  try {
    const res = await fetch('/api/start-job', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobId: currentJobId,
        selectedColumn: selectedCol,
        concurrency: conc
      })
    });
    const data = await res.json();
    if (!res.ok) {
      alert('Error starting job: ' + data.error);
    }
  } catch (err) {
    alert('Failed to trigger job: ' + err.message);
  }
}

/**
 * SSE Subscription
 */
function subscribeToJobStream(jobId) {
  if (currentEventSource) {
    currentEventSource.close();
  }

  currentEventSource = new EventSource(`/api/job-stream/${jobId}`);

  currentEventSource.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.type === 'init' || msg.type === 'progress') {
      const total = msg.total || msg.totalRows || 1;
      const processed = msg.processed || msg.processedCount || 0;
      const pct = Math.round((processed / total) * 100);

      statProcessed.textContent = `${processed} / ${total}`;
      statHealthcare.textContent = msg.healthcareCount || 0;
      statLocations.textContent = msg.locationsCount || 0;
      statNonHealthcare.textContent = msg.nonHealthcareCount || 0;

      progressFill.style.width = `${pct}%`;
      progressPercentage.textContent = `${pct}%`;

      if (msg.row) {
        allResults.push(msg.row);
        appendLiveTableRow(msg.row, processed);
        updateFilterCounts();
      }
    } else if (msg.type === 'completed') {
      progressStatusText.innerHTML = `<i class="fa-solid fa-circle-check text-green"></i> Processing Completed!`;
      progressFill.style.width = '100%';
      progressPercentage.textContent = '100%';
      btnExportCsv.disabled = false;
      btnCancelJob.style.display = 'none';
      if (currentEventSource) {
        currentEventSource.close();
      }
    } else if (msg.type === 'status_change') {
      if (msg.status === 'cancelled') {
        progressStatusText.innerHTML = `<i class="fa-solid fa-ban text-red"></i> Job Stopped by User`;
        btnExportCsv.disabled = allResults.length === 0;
        if (currentEventSource) {
          currentEventSource.close();
        }
      }
    }
  };

  currentEventSource.onerror = () => {
    // Attempt auto-reconnect or ignore if completed
  };
}

/**
 * Append Row to Real-Time Table
 */
function appendLiveTableRow(row, index) {
  const tr = document.createElement('tr');
  tr.dataset.healthcare = row['Is_Healthcare'];

  const isHc = row['Is_Healthcare'] === 'Yes';
  const pillClass = isHc ? 'pill-yes' : 'pill-no';
  const pillIcon = isHc ? 'fa-check' : 'fa-xmark';

  const conf = (row['Confidence_Score'] || 'Low').toLowerCase();
  let confClass = 'pill-low';
  if (conf === 'high') confClass = 'pill-high';
  else if (conf === 'medium' || conf === 'med') confClass = 'pill-med';

  const domain = row['Website_Domain'] && row['Website_Domain'] !== 'N/A' 
    ? `<a href="https://${row['Website_Domain']}" target="_blank" class="text-cyan" style="text-decoration:none;"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${row['Website_Domain']}</a>`
    : '<span style="color:var(--text-dim)">N/A</span>';

  const locationText = row['Detected_Location'] && row['Detected_Location'] !== 'Not Detected'
    ? `<span style="color:#f8fafc;"><i class="fa-solid fa-location-dot text-amber" style="margin-right:4px;"></i>${row['Detected_Location']}</span>`
    : '<span style="color:var(--text-dim)">Not Detected</span>';

  const companyNameVal = row['Company'] || row['company'] || row['Company Name'] || Object.values(row)[0] || '';

  tr.innerHTML = `
    <td style="color:var(--text-dim);">${index}</td>
    <td><strong>${companyNameVal}</strong></td>
    <td><span class="pill ${pillClass}"><i class="fa-solid ${pillIcon}"></i> ${row['Is_Healthcare']}</span></td>
    <td><span style="font-weight:600; color:${isHc ? '#34d399' : 'var(--text-muted)'}">${row['Healthcare_Category']}</span></td>
    <td>${locationText}</td>
    <td><span class="pill ${confClass}">${row['Confidence_Score']}</span></td>
    <td style="font-size:0.82rem; color:var(--text-muted); max-width:280px;">${row['Analysis_Reason']}</td>
    <td>${domain}</td>
  `;

  // Apply current filter visibility
  if (currentFilter === 'healthcare' && !isHc) {
    tr.style.display = 'none';
  } else if (currentFilter === 'non-healthcare' && isHc) {
    tr.style.display = 'none';
  }

  liveTbody.insertBefore(tr, liveTbody.firstChild);
}

/**
 * Filter Table
 */
function filterTable(filter) {
  currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');

  const rows = liveTbody.querySelectorAll('tr');
  rows.forEach(tr => {
    const isHc = tr.dataset.healthcare === 'Yes';
    if (filter === 'all') {
      tr.style.display = '';
    } else if (filter === 'healthcare') {
      tr.style.display = isHc ? '' : 'none';
    } else if (filter === 'non-healthcare') {
      tr.style.display = !isHc ? '' : 'none';
    }
  });
}

function updateFilterCounts() {
  countAll.textContent = allResults.length;
  countHc.textContent = allResults.filter(r => r['Is_Healthcare'] === 'Yes').length;
  countNonHc.textContent = allResults.filter(r => r['Is_Healthcare'] === 'No').length;
}

/**
 * Cancel Job
 */
async function cancelJob() {
  if (!currentJobId) return;
  if (confirm('Are you sure you want to stop the analysis?')) {
    await fetch('/api/job-control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jobId: currentJobId, action: 'cancel' })
    });
  }
}

/**
 * Export Enriched CSV
 */
function exportEnrichedCSV() {
  if (!currentJobId) return;
  window.location.href = `/api/export-csv/${currentJobId}`;
}

/**
 * Single Company Inspector Handler
 */
async function handleSingleLookup(e) {
  e.preventDefault();
  const companyName = document.getElementById('single-company-name').value.trim();
  const locationHint = document.getElementById('single-location-hint').value.trim();
  const websiteHint = document.getElementById('single-website-hint').value.trim();

  if (!companyName) return;

  const btn = document.getElementById('btn-inspect');
  const originalBtnContent = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...`;

  const resultBox = document.getElementById('single-result-box');
  resultBox.style.display = 'none';

  try {
    const res = await fetch('/api/analyze-single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ companyName, locationHint, websiteHint })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to inspect');

    renderSingleResult(data);
  } catch (err) {
    alert('Inspection Error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalBtnContent;
  }
}

function renderSingleResult(data) {
  const resultBox = document.getElementById('single-result-box');
  resultBox.style.display = 'block';

  document.getElementById('res-company-name').textContent = data.companyName;

  const isHc = data.isHealthcare === 'Yes';
  const pillClass = isHc ? 'pill-yes' : 'pill-no';
  const pillIcon = isHc ? 'fa-check' : 'fa-xmark';

  document.getElementById('res-badges').innerHTML = `
    <span class="pill ${pillClass}"><i class="fa-solid ${pillIcon}"></i> ${data.isHealthcare}</span>
    <span class="badge badge-sm">${data.category}</span>
  `;

  document.getElementById('res-confidence-meter').innerHTML = `
    <span class="pill ${data.confidence.toLowerCase() === 'high' ? 'pill-high' : 'pill-med'}">
      <i class="fa-solid fa-shield-halved"></i> ${data.confidence} Confidence
    </span>
  `;

  document.getElementById('res-is-healthcare').innerHTML = `
    <span style="color:${isHc ? '#34d399' : '#fb7185'}; font-size:1.2rem;">${isHc ? 'Yes (Healthcare Provider / Clinic)' : 'No (Non-Healthcare)'}</span>
  `;

  document.getElementById('res-category').textContent = data.category;
  document.getElementById('res-location').innerHTML = data.detectedLocation && data.detectedLocation !== 'Not Detected'
    ? `<i class="fa-solid fa-location-dot text-amber"></i> ${data.detectedLocation}`
    : 'Not Detected';

  document.getElementById('res-domain').innerHTML = data.websiteDomain && data.websiteDomain !== 'N/A'
    ? `<a href="https://${data.websiteDomain}" target="_blank" class="text-cyan" style="text-decoration:none;"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${data.websiteDomain}</a>`
    : 'N/A';

  document.getElementById('res-reason').textContent = data.reason;

  const signalsDiv = document.getElementById('res-signals');
  signalsDiv.innerHTML = '';
  if (data.signals && data.signals.length > 0) {
    data.signals.forEach(s => {
      const span = document.createElement('span');
      span.className = 'signal-tag';
      span.innerHTML = `<i class="fa-solid fa-check-double"></i> ${s}`;
      signalsDiv.appendChild(span);
    });
  }
}
