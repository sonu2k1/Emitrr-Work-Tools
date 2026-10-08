const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const csvParser = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const xlsx = require('xlsx');
const { processPracticeBatch, findPracticeDomain, geocodeAddress } = require('./lib/valentinEngine');

const app = express();
const PORT = process.env.PORT || 3000;

// Setup directories
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// Multer upload config
const upload = multer({
  dest: uploadsDir,
  limits: { fileSize: 50 * 1024 * 1024 } // 50MB
});

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Active scraping jobs storage
const jobs = new Map();

/**
 * API: Single Practice Domain Search
 */
app.post('/api/search-single', async (req, res) => {
  try {
    const { practiceName, country = 'US', city = '', state = '', address = '' } = req.body;
    if (!practiceName) {
      return res.status(400).json({ error: 'Practice name is required' });
    }

    const result = await findPracticeDomain(practiceName, {
      countryCode: country,
      city,
      state,
      address
    });

    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * API: Upload CSV / Excel and Start Batch Job
 */
app.post('/api/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const country = req.body.country || 'US';
    const concurrency = parseInt(req.body.concurrency, 10) || 3;
    const delay = parseInt(req.body.delay, 10) || 300;
    const filePath = req.file.path;
    const originalName = req.file.originalname;
    const ext = path.extname(originalName).toLowerCase();

    let records = [];

    if (ext === '.xlsx' || ext === '.xls') {
      const workbook = xlsx.readFile(filePath);
      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      records = xlsx.utils.sheet_to_json(sheet, { defval: '' });
    } else {
      // Parse CSV
      records = await new Promise((resolve, reject) => {
        const rows = [];
        fs.createReadStream(filePath)
          .pipe(csvParser())
          .on('data', (data) => rows.push(data))
          .on('end', () => resolve(rows))
          .on('error', reject);
      });
    }

    // Clean up uploaded temp file
    try { fs.unlinkSync(filePath); } catch (e) {}

    if (records.length === 0) {
      return res.status(400).json({ error: 'Uploaded file contains no data rows.' });
    }

    const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);
    const jobData = {
      id: jobId,
      fileName: originalName,
      country,
      concurrency,
      delay,
      total: records.length,
      processed: 0,
      found: 0,
      notFound: 0,
      status: 'running',
      startTime: Date.now(),
      records: records,
      results: [],
      clients: []
    };

    jobs.set(jobId, jobData);

    // Start background processing
    startJobProcessing(jobId);

    res.json({
      jobId,
      totalRecords: records.length,
      fileName: originalName,
      country
    });

  } catch (err) {
    res.status(500).json({ error: 'Failed to process file: ' + err.message });
  }
});

/**
 * Background Job Runner
 */
async function startJobProcessing(jobId) {
  const job = jobs.get(jobId);
  if (!job) return;

  const onProgress = (result, current, total) => {
    job.processed = current;
    if (result.status === 'Found') {
      job.found++;
    } else {
      job.notFound++;
    }

    // Broadcast SSE update
    const updateEvent = {
      type: 'progress',
      current,
      total,
      found: job.found,
      notFound: job.notFound,
      latest: result
    };

    job.clients.forEach(client => {
      client.write(`data: ${JSON.stringify(updateEvent)}\n\n`);
    });
  };

  try {
    const enrichedResults = await processPracticeBatch(job.records, onProgress, {
      country: job.country,
      concurrency: job.concurrency,
      delayMs: job.delay
    });

    job.results = enrichedResults;
    job.status = 'completed';
    job.endTime = Date.now();

    const completeEvent = {
      type: 'complete',
      total: job.total,
      found: job.found,
      notFound: job.notFound,
      durationSeconds: ((job.endTime - job.startTime) / 1000).toFixed(1)
    };

    job.clients.forEach(client => {
      client.write(`data: ${JSON.stringify(completeEvent)}\n\n`);
      client.end();
    });

  } catch (err) {
    job.status = 'error';
    job.error = err.message;
    job.clients.forEach(client => {
      client.write(`data: ${JSON.stringify({ type: 'error', error: err.message })}\n\n`);
      client.end();
    });
  }
}

/**
 * SSE Stream endpoint for live job updates
 */
app.get('/api/stream/:jobId', (req, res) => {
  const jobId = req.params.jobId;
  const job = jobs.get(jobId);

  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  job.clients.push(res);

  // Send initial state
  res.write(`data: ${JSON.stringify({
    type: 'init',
    total: job.total,
    processed: job.processed,
    found: job.found,
    notFound: job.notFound,
    status: job.status
  })}\n\n`);

  req.on('close', () => {
    job.clients = job.clients.filter(c => c !== res);
  });
});

/**
 * API: Download Enriched CSV
 */
app.get('/api/export/:jobId/csv', async (req, res) => {
  const jobId = req.params.jobId;
  const job = jobs.get(jobId);

  if (!job || !job.results || job.results.length === 0) {
    return res.status(404).json({ error: 'No results available for download' });
  }

  const exportPath = path.join(uploadsDir, `valentin_practices_${jobId}.csv`);
  const headerKeys = new Set();
  job.results.forEach(row => {
    Object.keys(row).forEach(k => headerKeys.add(k));
  });

  const csvHeaders = Array.from(headerKeys).map(k => ({ id: k, title: k }));
  const csvWriter = createCsvWriter({
    path: exportPath,
    header: csvHeaders
  });

  await csvWriter.writeRecords(job.results);

  res.download(exportPath, `valentin_practices_${job.country}_enriched.csv`, (err) => {
    try { fs.unlinkSync(exportPath); } catch (e) {}
  });
});

/**
 * API: Download Enriched Excel (.xlsx)
 */
app.get('/api/export/:jobId/excel', (req, res) => {
  const jobId = req.params.jobId;
  const job = jobs.get(jobId);

  if (!job || !job.results || job.results.length === 0) {
    return res.status(404).json({ error: 'No results available for download' });
  }

  const worksheet = xlsx.utils.json_to_sheet(job.results);
  const workbook = xlsx.utils.book_new();
  xlsx.utils.book_append_sheet(workbook, worksheet, 'Enriched Practices');

  const exportPath = path.join(uploadsDir, `valentin_practices_${jobId}.xlsx`);
  xlsx.writeFile(workbook, exportPath);

  res.download(exportPath, `valentin_practices_${job.country}_enriched.xlsx`, (err) => {
    try { fs.unlinkSync(exportPath); } catch (e) {}
  });
});

/**
 * API: Download Sample CSVs
 */
app.get('/api/sample/us', (req, res) => {
  res.download(path.join(__dirname, 'sample_us_practices.csv'), 'sample_us_practices.csv');
});

app.get('/api/sample/ca', (req, res) => {
  res.download(path.join(__dirname, 'sample_canada_practices.csv'), 'sample_canada_practices.csv');
});

app.listen(PORT, () => {
  console.log('=================================================');
  console.log(`🚀 Valentin.app Practice Search Web App is running!`);
  console.log(`🌐 Open in Browser: http://localhost:${PORT}`);
  console.log('=================================================');
});
