document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const btnBrowse = document.getElementById('btnBrowse');
  const selectedFileInfo = document.getElementById('selectedFileInfo');
  const fileNameDisplay = document.getElementById('fileNameDisplay');
  const fileRemoveBtn = document.getElementById('fileRemoveBtn');
  const btnStartScraping = document.getElementById('btnStartScraping');
  const countryOptions = document.querySelectorAll('.country-option');
  
  const toggleAdvanced = document.getElementById('toggleAdvanced');
  const advancedBox = document.getElementById('advancedBox');
  const concurrencyInput = document.getElementById('concurrencyInput');
  const delayInput = document.getElementById('delayInput');

  const statTotal = document.getElementById('statTotal');
  const statProcessed = document.getElementById('statProcessed');
  const statFound = document.getElementById('statFound');
  const statRate = document.getElementById('statRate');
  
  const progressSec = document.getElementById('progressSec');
  const progressFill = document.getElementById('progressFill');
  const progressPercent = document.getElementById('progressPercent');
  const progressText = document.getElementById('progressText');

  const tableBody = document.getElementById('tableBody');
  const tableFilterInput = document.getElementById('tableFilterInput');
  const btnExportCsv = document.getElementById('btnExportCsv');
  const btnExportExcel = document.getElementById('btnExportExcel');

  const singleSearchForm = document.getElementById('singleSearchForm');
  const singlePracticeInput = document.getElementById('singlePracticeInput');
  const btnSingleSearch = document.getElementById('btnSingleSearch');
  const singleResultContainer = document.getElementById('singleResultContainer');
  const toastContainer = document.getElementById('toastContainer');

  // State
  let selectedFile = null;
  let selectedCountry = 'US';
  let currentJobId = null;
  let activeEventSource = null;
  let allResults = [];

  // 1. Country Selection Handler
  countryOptions.forEach(option => {
    option.addEventListener('click', () => {
      countryOptions.forEach(o => o.classList.remove('active'));
      option.classList.add('active');
      const radio = option.querySelector('input[type="radio"]');
      radio.checked = true;
      selectedCountry = radio.value;
    });
  });

  // 2. File Upload & Drag-and-Drop
  btnBrowse.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener('click', () => {
    fileInput.click();
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    const validExts = ['.csv', '.xlsx', '.xls'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validExts.includes(ext)) {
      showToast('Please upload a valid CSV or Excel file', 'danger');
      return;
    }

    selectedFile = file;
    fileNameDisplay.textContent = file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
    selectedFileInfo.style.display = 'inline-flex';
    btnStartScraping.disabled = false;
    showToast(`File selected: ${file.name}`, 'success');
  }

  fileRemoveBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = '';
    selectedFileInfo.style.display = 'none';
    btnStartScraping.disabled = true;
  });

  // 3. Advanced Toggle
  toggleAdvanced.addEventListener('click', () => {
    if (advancedBox.style.display === 'none') {
      advancedBox.style.display = 'flex';
      toggleAdvanced.textContent = '⚙️ Advanced Settings ▴';
    } else {
      advancedBox.style.display = 'none';
      toggleAdvanced.textContent = '⚙️ Advanced Settings ▾';
    }
  });

  // 4. Start Batch Scraping
  btnStartScraping.addEventListener('click', async () => {
    if (!selectedFile) return;

    btnStartScraping.disabled = true;
    btnStartScraping.innerHTML = '<span class="btn-icon">⏳</span> Initializing Valentin Scraper...';
    
    // Reset stats & table
    allResults = [];
    tableBody.innerHTML = '';
    statTotal.textContent = '0';
    statProcessed.textContent = '0';
    statFound.textContent = '0';
    statRate.textContent = '0%';
    progressSec.style.display = 'block';
    progressFill.style.width = '0%';
    progressPercent.textContent = '0%';
    btnExportCsv.disabled = true;
    btnExportExcel.disabled = true;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('country', selectedCountry);
    formData.append('concurrency', concurrencyInput.value || '3');
    formData.append('delay', delayInput.value || '300');

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Upload failed');
      }

      currentJobId = data.jobId;
      statTotal.textContent = data.totalRecords;
      showToast(`Started scraping ${data.totalRecords} practices via Valentin.app!`, 'success');
      btnStartScraping.innerHTML = '<span class="btn-icon">⚡</span> Scraping in Progress...';

      // Connect SSE stream
      connectEventStream(currentJobId);

    } catch (err) {
      showToast(err.message, 'danger');
      btnStartScraping.disabled = false;
      btnStartScraping.innerHTML = '<span class="btn-icon">⚡</span> Start Finding Practice Domains';
    }
  });

  function connectEventStream(jobId) {
    if (activeEventSource) {
      activeEventSource.close();
    }

    activeEventSource = new EventSource(`/api/stream/${jobId}`);

    activeEventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'progress') {
        const { current, total, found, notFound, latest } = data;
        
        statProcessed.textContent = current;
        statFound.textContent = found;
        const rate = Math.round((found / current) * 100) || 0;
        statRate.textContent = `${rate}%`;

        const pct = Math.round((current / total) * 100);
        progressFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;
        progressText.textContent = `Scraped ${current} of ${total} practices (${found} domains found)`;

        allResults.push(latest);
        appendResultRow(latest, allResults.length);

        btnExportCsv.disabled = false;
        btnExportExcel.disabled = false;
      }

      if (data.type === 'complete') {
        activeEventSource.close();
        progressText.textContent = `Completed in ${data.durationSeconds}s! Found ${data.found} of ${data.total} domains.`;
        btnStartScraping.disabled = false;
        btnStartScraping.innerHTML = '<span class="btn-icon">⚡</span> Start New Batch';
        showToast('Batch domain finding completed successfully!', 'success');
      }

      if (data.type === 'error') {
        activeEventSource.close();
        showToast('Error during scraping: ' + data.error, 'danger');
        btnStartScraping.disabled = false;
        btnStartScraping.innerHTML = '<span class="btn-icon">⚡</span> Start Finding Practice Domains';
      }
    };

    activeEventSource.onerror = () => {
      activeEventSource.close();
    };
  }

  function appendResultRow(item, index) {
    const tr = document.createElement('tr');
    const isFound = item.status === 'Found';

    const domainDisplay = isFound && item.domain ? `
      <div class="domain-cell">
        <span>${item.domain}</span>
        <button class="btn-copy-domain" title="Copy domain" onclick="copyText('${item.domain}')">📋</button>
      </div>
    ` : '<span style="color:var(--text-dim);">-</span>';

    const urlDisplay = isFound && item.websiteUrl ? `
      <a href="${item.websiteUrl}" target="_blank" rel="noopener noreferrer" class="link-website">${item.websiteUrl.replace(/^https?:\/\//, '')} ↗</a>
    ` : '<span style="color:var(--text-dim);">-</span>';

    const statusBadge = isFound ? 
      `<span class="status-badge status-found">Found</span>` : 
      `<span class="status-badge status-notfound">Not Found</span>`;

    const confClass = item.confidence === 'High' ? 'confidence-high' : 'confidence-medium';

    tr.innerHTML = `
      <td>${index}</td>
      <td><strong>${escapeHtml(item.practiceName || item.inputPracticeName || 'N/A')}</strong></td>
      <td>${item.country === 'CA' ? '🇨🇦 CA' : '🇺🇸 US'}</td>
      <td style="color:var(--text-muted);">${escapeHtml(item.cleanedName || '-')}</td>
      <td>${domainDisplay}</td>
      <td>${urlDisplay}</td>
      <td class="${confClass}">${item.confidence || '-'}</td>
      <td style="font-size:0.75rem; color:var(--text-dim);">${escapeHtml(item.source || '-')}</td>
      <td>${statusBadge}</td>
    `;

    tableBody.appendChild(tr);
  }

  // 5. Table Filter Search
  tableFilterInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const rows = tableBody.querySelectorAll('tr');

    rows.forEach(row => {
      if (row.classList.contains('empty-row')) return;
      const text = row.innerText.toLowerCase();
      row.style.display = text.includes(query) ? '' : 'none';
    });
  });

  // 6. Export Handlers
  btnExportCsv.addEventListener('click', () => {
    if (!currentJobId) return;
    window.location.href = `/api/export/${currentJobId}/csv`;
    showToast('Downloading enriched CSV...', 'success');
  });

  btnExportExcel.addEventListener('click', () => {
    if (!currentJobId) return;
    window.location.href = `/api/export/${currentJobId}/excel`;
    showToast('Downloading enriched Excel file...', 'success');
  });

  // 7. Single Practice Search
  singleSearchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pName = singlePracticeInput.value.trim();
    if (!pName) return;

    btnSingleSearch.disabled = true;
    btnSingleSearch.textContent = 'Searching...';
    singleResultContainer.style.display = 'block';
    singleResultContainer.innerHTML = '<p style="color:var(--text-muted);">Querying Valentin.app localized search...</p>';

    try {
      const res = await fetch('/api/search-single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          practiceName: pName,
          country: selectedCountry
        })
      });

      const data = await res.json();
      btnSingleSearch.disabled = false;
      btnSingleSearch.textContent = 'Search';

      if (data.status === 'Found') {
        singleResultContainer.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="color:#fff;">${escapeHtml(data.practiceName)}</strong>
            <span class="status-badge status-found">Found</span>
          </div>
          <p style="margin:4px 0;">Domain: <strong style="color:#38bdf8; font-family:var(--font-mono);">${data.domain}</strong></p>
          <p style="margin:4px 0;">URL: <a href="${data.websiteUrl}" target="_blank" class="link-website">${data.websiteUrl}</a></p>
          <p style="margin:4px 0; font-size:0.75rem; color:var(--text-dim);">Source: ${data.source} | Confidence: ${data.confidence}</p>
        `;
        showToast(`Domain found for ${pName}: ${data.domain}`, 'success');
      } else {
        singleResultContainer.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:#fff;">${escapeHtml(data.practiceName)}</strong>
            <span class="status-badge status-notfound">Not Found</span>
          </div>
          <p style="color:var(--text-dim); font-size:0.78rem; margin-top:4px;">Could not locate official practice domain.</p>
        `;
        showToast(`No domain found for ${pName}`, 'danger');
      }

    } catch (err) {
      btnSingleSearch.disabled = false;
      btnSingleSearch.textContent = 'Search';
      singleResultContainer.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
  });

  // Helpers
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    if (type === 'success') toast.style.borderLeftColor = 'var(--success)';
    if (type === 'danger') toast.style.borderLeftColor = 'var(--danger)';
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 4000);
  }

  window.copyText = function(text) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(`Copied domain "${text}" to clipboard!`, 'success');
    });
  };

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
});
