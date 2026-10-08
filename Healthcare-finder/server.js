const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const csvParser = require('csv-parser');
const { format } = require('fast-csv');
const { analyzeCompany, processBatch } = require('./lib/analyzer');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}
const upload = multer({ dest: uploadDir });

// Active jobs cache
const activeJobs = new Map();

/**
 * 1. Single Company Quick Analysis Endpoint
 */
app.post('/api/analyze-single', async (req, res) => {
  try {
    const { companyName, locationHint, websiteHint } = req.body;
    if (!companyName || !companyName.trim()) {
      return res.status(400).json({ error: 'Company name is required' });
    }

    const result = await analyzeCompany(companyName.trim(), {
      location: locationHint,
      website: websiteHint
    });

    return res.json(result);
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

/**
 * 2. Upload CSV File
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

    try {
      fs.unlinkSync(filePath);
    } catch (e) {}

    if (rows.length === 0) {
      return res.status(400).json({ error: 'Uploaded CSV file is empty' });
    }

    const headers = Object.keys(rows[0]).filter(h => h.trim() !== '');
    const candidateColumns = ['company', 'company name', 'company_name', 'organization', 'name', 'account name', 'business name', 'clinic name', 'practice name'];
    const autoDetectedColumn = headers.find(h => candidateColumns.includes(h.trim().toLowerCase())) || headers[0];

    const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    activeJobs.set(jobId, {
      id: jobId,
      rows,
      headers,
      autoDetectedColumn,
      selectedColumn: autoDetectedColumn,
      status: 'idle', // idle, running, paused, cancelled, completed
      processedCount: 0,
      healthcareCount: 0,
      nonHealthcareCount: 0,
      locationsCount: 0,
      results: [],
      clients: [],
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
 * 3. SSE Endpoint for Real-time Progress Streaming
 */
app.get('/api/job-stream/:jobId', (req, res) => {
  const { jobId } = req.params;
  const job = activeJobs.get(jobId);

  if (!job) {
    return res.status(404).send('Job not found');
  }

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  job.clients.push(res);

  // Send initial state
  res.write(`data: ${JSON.stringify({
    type: 'init',
    status: job.status,
    totalRows: job.rows.length,
    processedCount: job.processedCount,
    healthcareCount: job.healthcareCount,
    nonHealthcareCount: job.nonHealthcareCount,
    locationsCount: job.locationsCount
  })}\n\n`);

  req.on('close', () => {
    job.clients = job.clients.filter(c => c !== res);
  });
});

/**
 * Broadcast SSE event to all connected clients for a job
 */
function broadcastJobEvent(job, eventType, data) {
  const message = `data: ${JSON.stringify({ type: eventType, ...data })}\n\n`;
  for (const client of job.clients) {
    try {
      client.write(message);
    } catch (e) {}
  }
}

/**
 * 4. Start Batch Analysis Job
 */
app.post('/api/start-job', async (req, res) => {
  const { jobId, selectedColumn, concurrency } = req.body;
  const job = activeJobs.get(jobId);

  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  if (job.status === 'running') {
    return res.status(400).json({ error: 'Job is already running' });
  }

  job.status = 'running';
  job.selectedColumn = selectedColumn || job.autoDetectedColumn;
  const conc = parseInt(concurrency) || 4;

  res.json({ success: true, message: 'Job started' });

  broadcastJobEvent(job, 'status_change', { status: 'running' });

  // Run in background
  const startTime = Date.now();

  try {
    const finalResults = await processBatch(
      job.rows,
      job.selectedColumn,
      { concurrency: conc },
      (index, enrichedRow, analysis) => {
        job.processedCount++;
        if (enrichedRow['Is_Healthcare'] === 'Yes') {
          job.healthcareCount++;
        } else {
          job.nonHealthcareCount++;
        }
        if (enrichedRow['Detected_Location'] && enrichedRow['Detected_Location'] !== 'Not Detected') {
          job.locationsCount++;
        }

        job.results[index] = enrichedRow;

        broadcastJobEvent(job, 'progress', {
          index,
          total: job.rows.length,
          processed: job.processedCount,
          healthcareCount: job.healthcareCount,
          nonHealthcareCount: job.nonHealthcareCount,
          locationsCount: job.locationsCount,
          row: enrichedRow,
          analysis
        });
      },
      () => job.status === 'cancelled' || job.status === 'paused'
    );

    if (job.status !== 'cancelled') {
      job.status = 'completed';
      job.results = finalResults;
      broadcastJobEvent(job, 'completed', {
        totalProcessed: job.processedCount,
        healthcareCount: job.healthcareCount,
        nonHealthcareCount: job.nonHealthcareCount,
        locationsCount: job.locationsCount,
        durationMs: Date.now() - startTime
      });
    }
  } catch (err) {
    job.status = 'error';
    broadcastJobEvent(job, 'error', { message: err.message });
  }
});

/**
 * 5. Job Controls (Pause, Resume, Cancel)
 */
app.post('/api/job-control', (req, res) => {
  const { jobId, action } = req.body;
  const job = activeJobs.get(jobId);

  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  if (action === 'cancel') {
    job.status = 'cancelled';
    broadcastJobEvent(job, 'status_change', { status: 'cancelled' });
    return res.json({ success: true, status: 'cancelled' });
  } else if (action === 'pause') {
    job.status = 'paused';
    broadcastJobEvent(job, 'status_change', { status: 'paused' });
    return res.json({ success: true, status: 'paused' });
  }

  return res.status(400).json({ error: 'Invalid action' });
});

/**
 * 6. Export Enriched CSV
 */
app.get('/api/export-csv/:jobId', (req, res) => {
  const { jobId } = req.params;
  const job = activeJobs.get(jobId);

  if (!job || !job.results || job.results.length === 0) {
    return res.status(404).json({ error: 'No enriched results found for this job' });
  }

  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', `attachment; filename="healthcare_enriched_${Date.now()}.csv"`);

  const csvStream = format({ headers: true });
  csvStream.pipe(res);

  for (const row of job.results) {
    if (row) {
      csvStream.write(row);
    }
  }

  csvStream.end();
});

/**
 * 7. Provide Sample CSV Download
 */
app.get('/api/sample-csv', (req, res) => {
  const sampleFilePath = path.join(__dirname, 'sample_companies.csv');
  if (fs.existsSync(sampleFilePath)) {
    res.download(sampleFilePath, 'sample_companies.csv');
  } else {
    res.status(404).send('Sample CSV not found');
  }
});

app.listen(PORT, () => {
  console.log(`\n=================================================`);
  console.log(`🏥 Healthcare & Clinic Finder + Location Detector`);
  console.log(`🌐 Web App running at: http://localhost:${PORT}`);
  console.log(`=================================================\n`);
});
