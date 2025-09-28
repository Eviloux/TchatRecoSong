import { createServer } from 'http';
import { parse } from 'url';
import { extname, join, dirname } from 'path';
import { createReadStream, existsSync } from 'fs';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const distDir = join(__dirname, 'dist');
const indexPath = join(distDir, 'index.html');

const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
};

function getContentType(filePath) {
  return MIME_TYPES[extname(filePath).toLowerCase()] ?? 'application/octet-stream';
}

function sendFile(res, filePath, status = 200) {
  res.statusCode = status;
  res.setHeader('Content-Type', getContentType(filePath));
  createReadStream(filePath).pipe(res);
}

const server = createServer(async (req, res) => {
  if (!req.url) {
    res.statusCode = 400;
    res.end('Bad Request');
    return;
  }

  const { pathname } = parse(req.url);
  const safePath = pathname?.replace(/\.\./g, '') || '/';

  if (safePath === '/') {
    res.statusCode = 302;
    res.setHeader('Location', '/submit');
    res.end();
    return;
  }

  const decodedPath = decodeURIComponent(safePath);
  const normalized = decodedPath.replace(/^\/+/, '');
  const hasExtension = extname(normalized) !== '';
  const candidate = join(distDir, normalized || 'index.html');

  try {
    if (hasExtension && existsSync(candidate)) {
      sendFile(res, candidate);
      return;
    }

    if (hasExtension) {
      res.statusCode = 404;
      res.end('Not Found');
      return;
    }

    sendFile(res, indexPath);
  } catch (err) {
    res.statusCode = 500;
    res.end('Internal Server Error');
    console.error('Failed to serve request', err);
  }
});

const port = Number(process.env.PORT ?? 4173);
server.listen(port, '0.0.0.0', () => {
  console.log(`Viewer portal running at http://0.0.0.0:${port}`);
});

