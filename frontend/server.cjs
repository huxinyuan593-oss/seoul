/**
 * Production Static Server — serves the Vite-built frontend.
 * Much more stable than `vite dev` for long-running use.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const DIST = path.join(__dirname, 'dist');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

const server = http.createServer((req, res) => {
  let filePath = path.join(DIST, req.url === '/' ? 'index.html' : req.url.split('?')[0]);

  // SPA fallback: if file not found, serve index.html
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(DIST, 'index.html');
  }

  const ext = path.extname(filePath);
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
  fs.createReadStream(filePath).pipe(res);
});

server.listen(PORT, () => {
  console.log(`[Frontend] Production server running at http://localhost:${PORT}`);
  console.log(`[Frontend] Serving static files from: ${DIST}`);
});
