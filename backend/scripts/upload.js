const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const API_HOST = 'ai-native-ip-production.up.railway.app';
const API_PATH = '/api/v1/memory/upload';
const IP_ID = '1';
const DOCS_DIR = 'F:/AI-Native IP/docs/IP知识库';

function getFiles() {
  const items = fs.readdirSync(DOCS_DIR);
  return items.filter(f => {
    const ext = path.extname(f).toLowerCase();
    return ['.txt', '.md', '.doc', '.docx', '.pdf'].includes(ext);
  });
}

function uploadFile(filename) {
  return new Promise((resolve) => {
    const filePath = path.join(DOCS_DIR, filename);
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
      path: API_PATH,
      method: 'POST',
      headers: {
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': header.length + fileData.length + footer.length
      }
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          console.log('OK: ' + filename);
          resolve(true);
        } else {
          console.log('FAIL: ' + filename + ' (' + res.statusCode + ')');
          resolve(false);
        }
      });
    });
    
    req.on('error', (e) => {
      console.log('ERROR: ' + filename + ' - ' + e.message);
      resolve(false);
    });
    
    req.write(header);
    req.write(fileData);
    req.write(footer);
    req.end();
  });
}

async function main() {
  const files = getFiles();
  console.log('Found ' + files.length + ' files');
  
  let success = 0, fail = 0;
  for (const f of files) {
    const ok = await uploadFile(f);
    if (ok) success++; else fail++;
  }
  console.log('Done! Success: ' + success + ', Failed: ' + fail);
}

main();
