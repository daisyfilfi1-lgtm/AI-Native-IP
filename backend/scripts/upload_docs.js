const fs = require('fs');
const path = require('path');
const https = require('https');

const API_HOST = 'ai-native-ip.netlify.app';
const API_PATH = '/api/v1/memory/upload';
const IP_ID = '1';
const DOCS_DIR = 'F:/AI-Native IP/docs/IP知识库';

// Only upload small files (docx, txt, md) - skip large PDFs
const ALLOWED_EXT = ['.txt', '.md', '.doc', '.docx'];

function getFiles() {
  const items = fs.readdirSync(DOCS_DIR);
  return items.filter(f => {
    const ext = path.extname(f).toLowerCase();
    // Skip PDFs - they are too large
    return ALLOWED_EXT.includes(ext);
  });
}

function uploadFile(filename) {
  return new Promise((resolve) => {
    const filePath = path.join(DOCS_DIR, filename);
    const fileSize = fs.statSync(filePath).size;
    
    // Skip files > 10MB
    if (fileSize > 10 * 1024 * 1024) {
      console.log('SKIP (too large):', filename, (fileSize/1024/1024).toFixed(1) + 'MB');
      resolve(true); // Count as success to skip
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
      path: API_PATH,
      method: 'POST',
      headers: {
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': header.length + fileData.length + footer.length
      },
      timeout: 60000
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        const ok = res.statusCode === 200;
        console.log(ok ? 'OK' : 'FAIL', filename, res.statusCode);
        resolve(ok);
      });
    });
    
    req.on('error', (e) => {
      console.log('ERROR', filename, e.message);
      resolve(false);
    });
    
    req.on('timeout', () => {
      console.log('TIMEOUT', filename);
      req.destroy();
      resolve(false);
    });
    
    req.write(header);
    req.write(fileData);
    req.write(footer);
    req.end();
  });
}

async function main() {
  // Warm up Railway first
  console.log('Warming up Railway...');
  https.get('https://ai-native-ip.netlify.app/health', (r) => {
    console.log('Railway ready');
    
    const files = getFiles();
    console.log('Found', files.length, 'small files');
    
    let success = 0, fail = 0;
    let index = 0;
    
    function uploadNext() {
      if (index >= files.length) {
        console.log('Done! Success:', success, 'Failed:', fail);
        return;
      }
      
      const f = files[index++];
      uploadFile(f).then(ok => {
        if (ok) success++; else fail++;
        // Small delay between uploads
        setTimeout(uploadNext, 300);
      });
    }
    
    uploadNext();
  }).on('error', (e) => {
    console.log('Warmup failed:', e.message);
  });
}

main();
