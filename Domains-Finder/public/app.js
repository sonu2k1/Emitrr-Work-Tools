// Global State Variables
let currentJobId = null;
let parsedHeaders = [];
let allResults = [];
let eventSource = null;
let totalRowCount = 0;
let foundCount = 0;
let notFoundCount = 0;
let isJobPaused = false;
let isJobStopped = false;

// Tab Switcher
function switchTab(tabName) {
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));

  if (tabName === 'bulk') {
    document.getElementById('tabBulkBtn').classList.add('active');
    document.getElementById('bulkSection').classList.add('active');
  } else {
    document.getElementById('tabSingleBtn').classList.add('active');
    document.getElementById('singleSection').classList.add('active');
  }
}

// Drag and Drop Upload Handler
const dropZone = document.getElementById('dropZone');
const csvFileInput = document.getElementById('csvFileInput');

['dragenter', 'dragover'].forEach(eventName => {
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(eventName => {
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
  });
});

dropZone.addEventListener('drop', (e) => {
  const dt = e.dataTransfer;
  const files = dt.files;
  if (files && files.length > 0) {
    handleFileUpload(files[0]);
  }
});

csvFileInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) {
    handleFileUpload(e.target.files[0]);
  }
});

// Upload CSV file to server
async function handleFileUpload(file) {
  if (!file.name.endsWith('.csv')) {
    alert('Please select a valid .csv file');
    return;
  }

  const formData = new FormData();
  formData.append('csvFile', file);

  try {
    const res = await fetch('/api/upload-csv', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Failed to upload CSV');
      return;
    }

    currentJobId = data.jobId;
    totalRowCount = data.totalRows;
    parsedHeaders = data.headers;

    // Display File Setup Card
    document.getElementById('dropZone').classList.add('hidden');
    document.getElementById('configCard').classList.remove('hidden');
    document.getElementById('fileInfoText').textContent = `File "${file.name}" loaded with ${totalRowCount.toLocaleString()} rows`;

    // Populate Column Dropdown
    const columnSelect = document.getElementById('columnSelect');
    columnSelect.innerHTML = '';
    parsedHeaders.forEach(h => {
      const opt = document.createElement('option');
      opt.value = h;
      opt.textContent = h;
      if (h === data.autoDetectedColumn) {
        opt.selected = true;
      }
      columnSelect.appendChild(opt);
    });

  } catch (err) {
    alert('Upload error: ' + err.message);
  }
}

function resetUpload() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  currentJobId = null;
  allResults = [];
  isJobPaused = false;
  isJobStopped = false;
  document.getElementById('dropZone').classList.remove('hidden');
  document.getElementById('configCard').classList.add('hidden');
  document.getElementById('resultsWrapper').classList.add('hidden');
  document.getElementById('csvFileInput').value = '';
}

function toggleCustomLocationInput(selectId, groupId) {
  const select = document.getElementById(selectId);
  const group = document.getElementById(groupId);
  if (select && group) {
    if (select.value === 'custom') {
      group.classList.remove('hidden');
    } else {
      group.classList.add('hidden');
    }
  }
}

// Start Batch Processing via SSE Stream
function startBatchProcessing() {
  if (!currentJobId) return;

  const companyColumn = document.getElementById('columnSelect').value;
  const concurrency = document.getElementById('concurrencySelect').value;
  const regionVal = document.getElementById('regionSelect').value;

  let countryCode = '';
  let location = '';
  if (regionVal === 'custom') {
    location = document.getElementById('customLocationInput').value.trim();
  } else if (regionVal !== 'global') {
    countryCode = regionVal;
  }

  // Show Results Dashboard
  document.getElementById('configCard').classList.add('hidden');
  document.getElementById('resultsWrapper').classList.remove('hidden');

  // Reset Controls & Stats
  foundCount = 0;
  notFoundCount = 0;
  allResults = [];
  isJobPaused = false;
  isJobStopped = false;
  updateStats();

  // Reset Control Buttons UI
  const pauseBtn = document.getElementById('pauseBtn');
  const stopBtn = document.getElementById('stopBtn');
  pauseBtn.disabled = false;
  pauseBtn.className = 'btn btn-warning btn-sm';
  pauseBtn.innerHTML = `<i class="fa-solid fa-pause"></i> Pause`;

  stopBtn.disabled = false;
  document.getElementById('exportBtn').disabled = false;

  document.getElementById('tableBody').innerHTML = '';
  document.getElementById('progressStatusText').textContent = 'Finding domains...';
  document.getElementById('progressBarFill').style.width = '0%';
  document.getElementById('progressPctText').textContent = `0% (0 / ${totalRowCount.toLocaleString()})`;

  // Initiate SSE Stream with Valentin UULE parameters if selected
  let sseUrl = `/api/process-stream?jobId=${encodeURIComponent(currentJobId)}&companyColumn=${encodeURIComponent(companyColumn)}&concurrency=${concurrency}`;
  if (countryCode) sseUrl += `&countryCode=${encodeURIComponent(countryCode)}`;
  if (location) sseUrl += `&location=${encodeURIComponent(location)}`;

  eventSource = new EventSource(sseUrl);

  eventSource.addEventListener('start', (e) => {
    const data = JSON.parse(e.data);
    totalRowCount = data.totalRows;
    updateStats();
  });

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    const item = data.item;
    allResults.push(item);

    if (item.domain) {
      foundCount++;
    } else {
      notFoundCount++;
    }

    updateStats();

    const completed = data.completed || (foundCount + notFoundCount);
    const total = data.total || totalRowCount;
    const rawPct = total > 0 ? (completed / total) * 100 : 0;

    let pctDisplay;
    if (completed === 0) {
      pctDisplay = '0%';
    } else if (rawPct < 0.01) {
      pctDisplay = '< 0.01%';
    } else if (rawPct < 1) {
      pctDisplay = `${rawPct.toFixed(2)}%`;
    } else if (rawPct < 10) {
      pctDisplay = `${rawPct.toFixed(1)}%`;
    } else {
      pctDisplay = `${Math.round(rawPct)}%`;
    }

    const barWidth = completed > 0 ? Math.max(rawPct, 0.5) : 0;
    document.getElementById('progressBarFill').style.width = `${barWidth.toFixed(2)}%`;
    document.getElementById('progressPctText').textContent = `${pctDisplay} (${completed.toLocaleString()} / ${total.toLocaleString()})`;

    // Append to Table
    appendTableRow(item, data.completed);
  });

  eventSource.addEventListener('stopped', (e) => {
    const data = JSON.parse(e.data);
    document.getElementById('progressStatusText').textContent = '🛑 Stopped by user';
    disableControlsOnEnd();
  });

  eventSource.addEventListener('complete', () => {
    document.getElementById('progressStatusText').textContent = '✅ Completed!';
    document.getElementById('progressBarFill').style.width = '100%';
    document.getElementById('progressPctText').textContent = '100%';
    disableControlsOnEnd();
  });

  eventSource.addEventListener('error', (e) => {
    if (!isJobStopped && !isJobPaused) {
      document.getElementById('progressStatusText').textContent = '⚠️ Connection ended';
      disableControlsOnEnd();
    }
  });
}

// Pause / Resume Toggle
async function togglePauseJob() {
  if (!currentJobId || isJobStopped) return;

  const pauseBtn = document.getElementById('pauseBtn');
  const action = isJobPaused ? 'resume' : 'pause';

  try {
    const res = await fetch('/api/job-control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jobId: currentJobId, action })
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Failed to update job state');
      return;
    }

    if (action === 'pause') {
      isJobPaused = true;
      pauseBtn.className = 'btn btn-success btn-sm';
      pauseBtn.innerHTML = `<i class="fa-solid fa-play"></i> Resume`;
      document.getElementById('progressStatusText').textContent = '⏸️ Paused';
    } else {
      isJobPaused = false;
      pauseBtn.className = 'btn btn-warning btn-sm';
      pauseBtn.innerHTML = `<i class="fa-solid fa-pause"></i> Pause`;
      document.getElementById('progressStatusText').textContent = 'Finding domains...';
    }

  } catch (err) {
    alert('Control error: ' + err.message);
  }
}

// Stop Job
async function stopJob() {
  if (!currentJobId || isJobStopped) return;

  if (!confirm('Are you sure you want to stop processing? You can still export the domains found so far.')) {
    return;
  }

  isJobStopped = true;

  try {
    await fetch('/api/job-control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jobId: currentJobId, action: 'stop' })
    });

    document.getElementById('progressStatusText').textContent = '🛑 Stopped by user';
    disableControlsOnEnd();

  } catch (err) {
    alert('Stop error: ' + err.message);
  }
}

function disableControlsOnEnd() {
  document.getElementById('pauseBtn').disabled = true;
  document.getElementById('stopBtn').disabled = true;
  document.getElementById('exportBtn').disabled = false;
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function updateStats() {
  document.getElementById('statTotal').textContent = totalRowCount.toLocaleString();
  document.getElementById('statFound').textContent = foundCount.toLocaleString();
  document.getElementById('statNotFound').textContent = notFoundCount.toLocaleString();
  
  const processedTotal = foundCount + notFoundCount;
  const pct = processedTotal > 0 ? Math.round((foundCount / processedTotal) * 100) : 0;
  document.getElementById('statAccuracy').textContent = `${pct}%`;
}

function appendTableRow(item, rowNum) {
  const tbody = document.getElementById('tableBody');
  const tr = document.createElement('tr');

  const statusBadge = item.domain 
    ? `<span class="badge badge-found"><i class="fa-solid fa-check"></i> Found</span>`
    : `<span class="badge badge-notfound"><i class="fa-solid fa-xmark"></i> Not Found</span>`;

  const domainCell = item.domain
    ? `<a href="https://${item.domain}" target="_blank" class="domain-link">
         <img src="${item.logo}" class="company-logo-img" onerror="this.src='https://cdn-icons-png.flaticon.com/512/1006/1006771.png'">
         ${item.domain}
       </a>`
    : `<span style="color: var(--text-muted);">N/A</span>`;

  tr.innerHTML = `
    <td>${rowNum}</td>
    <td style="font-weight: 700;">${escapeHtml(item.company || '')}</td>
    <td>${domainCell}</td>
    <td>${statusBadge}</td>
    <td><span style="font-size: 13px; color: var(--text-muted);">${item.source || 'N/A'}</span></td>
    <td><span class="badge badge-pending">${item.confidence || 'N/A'}</span></td>
  `;

  tbody.appendChild(tr);

  // Keep live feed DOM lightweight for massive datasets (e.g. 43,000+ rows)
  if (tbody.children.length > 200) {
    tbody.removeChild(tbody.firstElementChild);
  }

  const container = tbody.closest('.table-responsive');
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function filterTable() {
  const filter = document.getElementById('tableFilterInput').value.toLowerCase();
  const rows = document.querySelectorAll('#tableBody tr');

  rows.forEach(tr => {
    const text = tr.textContent.toLowerCase();
    tr.style.display = text.includes(filter) ? '' : 'none';
  });
}

// Export Enriched CSV
async function exportEnrichedCSV() {
  if (allResults.length === 0) return;

  try {
    const res = await fetch('/api/export-csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        headers: parsedHeaders,
        rows: allResults
      })
    });

    if (!res.ok) {
      alert('Failed to export CSV');
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'enriched_company_domains.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (err) {
    alert('Export error: ' + err.message);
  }
}

// Single Lookup Search
async function performSingleLookup() {
  const companyInput = document.getElementById('singleCompanyInput');
  const searchBtn = document.getElementById('singleSearchBtn');
  const resultBox = document.getElementById('singleResultContainer');
  const companyName = companyInput.value.trim();

  if (!companyName) return;

  const regionVal = document.getElementById('singleRegionSelect').value;
  let countryCode = '';
  let location = '';
  if (regionVal === 'custom') {
    location = document.getElementById('singleCustomLocationInput').value.trim();
  } else if (regionVal !== 'global') {
    countryCode = regionVal;
  }

  searchBtn.disabled = true;
  searchBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Searching...`;
  resultBox.classList.add('hidden');

  try {
    const res = await fetch('/api/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ companyName, countryCode, location })
    });

    const data = await res.json();
    resultBox.classList.remove('hidden');

    if (data.domain) {
      resultBox.innerHTML = `
        <div class="single-result-header">
          <img src="${data.logo}" onerror="this.src='https://cdn-icons-png.flaticon.com/512/1006/1006771.png'">
          <div>
            <h2 style="font-size: 22px; font-weight: 800;">${escapeHtml(data.company)}</h2>
            <a href="https://${data.domain}" target="_blank" class="domain-link" style="font-size: 18px; margin-top: 4px;">
              ${data.domain} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 12px;"></i>
            </a>
          </div>
        </div>
        <div style="display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap;">
          <span class="badge badge-found"><i class="fa-solid fa-check"></i> Found</span>
          <span class="badge badge-pending">Source: ${data.source}</span>
          <span class="badge badge-pending">Confidence: ${data.confidence}</span>
        </div>
      `;
    } else {
      resultBox.innerHTML = `
        <div class="single-result-header">
          <div style="width: 48px; height: 48px; border-radius: 10px; background: rgba(239, 68, 68, 0.15); display: flex; align-items: center; justify-content: center; color: var(--danger); font-size: 24px;">
            <i class="fa-solid fa-circle-xmark"></i>
          </div>
          <div>
            <h2 style="font-size: 20px; font-weight: 800;">${escapeHtml(data.company)}</h2>
            <p style="color: var(--text-muted); font-size: 14px;">No website domain could be confidently found for this company.</p>
          </div>
        </div>
      `;
    }

  } catch (err) {
    alert('Lookup error: ' + err.message);
  } finally {
    searchBtn.disabled = false;
    searchBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Search`;
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

