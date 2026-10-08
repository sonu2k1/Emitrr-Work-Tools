const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const csvParser = require('csv-parser');
const { findDomainForCompany, processCompanyBatch } = require('./lib/domainFinder');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

const os = require('os');
const uploadDir = process.env.VERCEL ? os.tmpdir() : path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}
const upload = multer({ dest: uploadDir });

// Store active job sessions
const activeJobs = new Map();

/**
 * Single Company Lookup Endpoint
 */
app.post('/api/lookup', async (req, res) => {
  try {
    const { companyName, location, countryCode, languageCode } = req.body;
    if (!companyName) {
      return res.status(400).json({ error: 'Company name is required' });
    }
    const result = await findDomainForCompany(companyName, { location, countryCode, languageCode });
    return res.json(result);
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

/**
 * Upload & Parse CSV File
 */
app.post('/api/upload-csv', upload.single('csvFile'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No CSV file uploaded' });
    }

    const filePath = req.file.path;
    const rows = [];

    await new Promise((resolve, reject) => {
      fs.createReadStream(filePath)
        .pipe(csvParser())
        .on('data', (row) => rows.push(row))
        .on('end', resolve)
        .on('error', reject);
    });

    fs.unlinkSync(filePath);

    if (rows.length === 0) {
      return res.status(400).json({ error: 'Uploaded CSV file is empty' });
    }

    const headers = Object.keys(rows[0]).filter(h => h.trim() !== '');
    const candidateColumns = ['company', 'company name', 'company_name', 'organization', 'name', 'account name'];
    const autoDetectedColumn = headers.find(h => candidateColumns.includes(h.trim().toLowerCase())) || headers[0];

    const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    activeJobs.set(jobId, {
      rows,
      headers,
      autoDetectedColumn,
      status: 'idle', // idle, running, paused, stopped, completed
      createdAt: Date.now()
    });

    return res.json({
      jobId,
      totalRows: rows.length,
      headers,
      autoDetectedColumn,
      sampleData: rows.slice(0, 5)
    });
  } catch (err) {
    return res.status(500).json({ error: 'Failed to process CSV file: ' + err.message });
  }
});

/**
 * Control Job Endpoint (Pause, Resume, Stop)
 */
app.post('/api/job-control', (req, res) => {
  const { jobId, action } = req.body;
  if (!jobId || !activeJobs.has(jobId)) {
    return res.status(404).json({ error: 'Job not found' });
  }

  const job = activeJobs.get(jobId);

  if (action === 'pause') {
    job.status = 'paused';
  } else if (action === 'resume') {
    job.status = 'running';
  } else if (action === 'stop') {
    job.status = 'stopped';
  } else {
    return res.status(400).json({ error: 'Invalid action' });
  }

  return res.json({ jobId, status: job.status });
});

/**
 * SSE Stream endpoint for live batch processing progress
 */
app.get('/api/process-stream', async (req, res) => {
  const { jobId, companyColumn, concurrency = 3, delayMs = 200, location, countryCode, languageCode } = req.query;

  if (!jobId || !activeJobs.has(jobId)) {
    return res.status(404).json({ error: 'Job not found or expired' });
  }

  const job = activeJobs.get(jobId);
  job.status = 'running';

  const rows = job.rows;
  const colName = companyColumn || job.autoDetectedColumn;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const sendEvent = (event, data) => {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  sendEvent('start', { totalRows: rows.length, companyColumn: colName });

  const companyList = rows.map((row, index) => ({
    rowIndex: index,
    originalRow: row,
    companyName: row[colName] || ''
  }));

  // Periodic keep-alive ping to prevent proxy / browser timeout on large CSVs (43k+ rows)
  const pingInterval = setInterval(() => {
    try {
      res.write(': keep-alive\n\n');
    } catch (e) {}
  }, 15000);

  try {
    const queue = [...companyList];
    const results = [];
    let completedCount = 0;
    const workerCount = Math.min(parseInt(concurrency, 10) || 5, companyList.length);

    async function worker() {
      while (queue.length > 0) {
        // Handle stop signal
        if (job.status === 'stopped') break;

        // Handle pause signal
        while (job.status === 'paused') {
          sendEvent('status_change', { status: 'paused' });
          await new Promise(r => setTimeout(r, 400));
          if (job.status === 'stopped') break;
        }

        if (job.status === 'stopped') break;

        const item = queue.shift();
        if (!item) break;

        let itemResult;
        try {
          itemResult = await findDomainForCompany(item.companyName, { location, countryCode, languageCode });
        } catch (err) {
          itemResult = {
            company: item.companyName,
            domain: '',
            logo: '',
            status: 'Error',
            error: err.message
          };
        }

        itemResult = { ...item.originalRow, ...itemResult };
        results.push(itemResult);
        completedCount++;

        sendEvent('progress', {
          item: itemResult,
          completed: completedCount,
          total: companyList.length,
          percent: (completedCount / companyList.length) * 100,
          status: job.status
        });

        if (delayMs > 0 && queue.length > 0) {
          await new Promise(r => setTimeout(r, parseInt(delayMs, 10) || 200));
        }
      }
    }

    const workers = Array.from({ length: workerCount }, () => worker());
    await Promise.all(workers);

    if (job.status === 'stopped') {
      sendEvent('stopped', { message: 'Processing stopped by user', completed: completedCount });
    } else {
      job.status = 'completed';
      sendEvent('complete', { message: 'All domains processed successfully!', completed: completedCount });
    }
  } catch (err) {
    sendEvent('error', { message: err.message });
  } finally {
    clearInterval(pingInterval);
    res.end();
  }
});

/**
 * Export Enriched CSV
 */
app.post('/api/export-csv', (req, res) => {
  try {
    const { headers, rows } = req.body;
    if (!rows || !Array.isArray(rows) || rows.length === 0) {
      return res.status(400).json({ error: 'No row data provided for CSV export' });
    }

    const fieldSet = new Set(headers || []);
    rows.forEach(r => Object.keys(r).forEach(k => {
      if (k !== 'originalRow' && k !== 'rowIndex') {
        fieldSet.add(k);
      }
    }));

    const allHeaders = Array.from(fieldSet);

    function escapeCsvField(val) {
      if (val === null || val === undefined) return '""';
      const str = String(val);
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    }

    const csvLines = [];
    csvLines.push(allHeaders.map(escapeCsvField).join(','));

    for (const rowObj of rows) {
      const orig = rowObj.originalRow || {};
      const lineValues = allHeaders.map(h => {
        if (rowObj[h] !== undefined) return rowObj[h];
        if (orig[h] !== undefined) return orig[h];
        return '';
      });
      csvLines.push(lineValues.map(escapeCsvField).join(','));
    }

    const csvContent = csvLines.join('\n');

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="enriched_company_domains.csv"');
    return res.send(csvContent);
  } catch (err) {
    return res.status(500).json({ error: 'Export failed: ' + err.message });
  }
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`\n=================================================`);
    console.log(`🚀 Company Domain Finder Web App is running!`);
    console.log(`🌐 Open in Browser: http://localhost:${PORT}`);
    console.log(`=================================================\n`);
  });
}

module.exports = app;
