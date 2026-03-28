const fs = require('fs');
const path = require('path');
const https = require('https');

const API_HOST = 'ai-native-ip-production.up.railway.app';
const IP_ID = '1';
const DOCS_DIR = 'F:/AI-Native IP/docs/IP知识库';
const ALLOWED_EXT = ['.txt', '.md', '.doc', '.docx', '.pdf'];

function getFiles() {
  const items = fs.readdirSync(DOCS_DIR);
  return items.filter(f => {
    const ext = path.extname(f).toLowerCase();
    return ALLOWED_EXT.includes(ext);
  });
}

function uploadFile(filename) {
  return new Promise((resolve) => {
    const filePath = path.join(DOCS_DIR, filename);
    const fileSize = fs.statSync(filePath).size;
    
    if (fileSize > 20 * 1024 * 1024) {
      console.log('SKIP (too large):', filename);
      resolve({ ok: true, file_id: null });
      return;
    }
    
    const boundary = '----FormBoundary' + Date.now();
    const header = Buffer.from(
      `--${boundary}\r\n` +
      `Content-Disposition: form-data; name="ip_id"\r\n\r\n` +
      `${IP_ID}\r\n` +
      `--${boundary}\r\n` +
      `Content-Disposition: form-data; name="file"; filename="${filename}"\r\n` +
      `Content-Type: application/octet-stream\r\n\r\n`
    );
    const footer = Buffer.from(`\r\n--${boundary}--\r\n`);
    const fileData = fs.readFileSync(filePath);
    
    const options = {
      hostname: API_HOST,
      port: 443,
      path: '/api/v1/memory/upload',
      method: 'POST',
      headers: {
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': header.length + fileData.length + footer.length
      },
      timeout: 180000
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const ok = res.statusCode === 200 && json.file_id;
          console.log(ok ? 'UPLOAD OK' : 'UPLOAD FAIL', filename, json.file_id || '', 'status:', res.statusCode);
          resolve({ ok, file_id: json.file_id });
        } catch(e) {
          console.log('PARSE ERROR', filename, data.slice(0,100));
          resolve({ ok: false, file_id: null });
        }
      });
    });
    
    req.on('error', (e) => {
      console.log('ERROR', filename, e.message);
      resolve({ ok: false, file_id: null });
    });
    
    req.on('timeout', () => {
      console.log('TIMEOUT', filename);
      req.destroy();
      resolve({ ok: false, file_id: null });
    });
    
    req.write(header);
    req.write(fileData);
    req.write(footer);
    req.end();
  });
}

function ingestFile(fileId) {
  return new Promise((resolve) => {
    const postData = JSON.stringify({
      ip_id: IP_ID,
      source_type: 'file',
      local_file_id: fileId
    });
    
    const options = {
      hostname: API_HOST,
      port: 443,
      path: '/api/v1/memory/ingest',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': postData.length
      },
      timeout: 30000
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const ok = json.ingest_task_id;
          console.log(ok ? 'INGEST OK' : 'INGEST FAIL', fileId);
          resolve({ ok, task_id: json.ingest_task_id });
        } catch(e) {
          console.log('INGEST PARSE ERROR', fileId);
          resolve({ ok: false, task_id: null });
        }
      });
    });
    
    req.on('error', (e) => {
      console.log('INGEST ERROR', fileId, e.message);
      resolve({ ok: false, task_id: null });
    });
    
    req.write(postData);
    req.end();
  });
}

function warmup() {
  return new Promise((resolve) => {
    let done = 0;
    console.log('Warming up...');
    for (let i = 0; i < 5; i++) {
      https.get('https://ai-native-ip-production.up.railway.app/health', (r) => {
        done++;
        if (done >= 5) {
          console.log('Warmup done');
          resolve();
        }
      }).on('error', () => {
        done++;
        if (done >= 5) resolve();
      });
    }
    // Wait longer for warmup
    setTimeout(resolve, 15000);
  });
}

async function main() {
  console.log('Warming up Railway (this may take a minute)...');
  await warmup();
  
  const files = getFiles();
  console.log('Found', files.length, 'files\n');
  
  let uploadSuccess = 0;
  
  for (let i = 0; i < files.length; i++) {
    const f = files[i];
    console.log('Processing:', i+1 + '/' + files.length, f);
    
    // Upload
    const result = await uploadFile(f);
    
    if (result.ok && result.file_id) {
      uploadSuccess++;
      // Wait a bit then ingest
      await new Promise(r => setTimeout(r, 1000));
      await ingestFile(result.file_id);
    }
    
    // Wait between files
    await new Promise(r => setTimeout(r, 2000));
  }
  
  console.log('\n=== DONE ===');
  console.log('Uploaded:', uploadSuccess, '/', files.length);
}

main();
