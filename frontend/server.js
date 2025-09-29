import { createServer } from 'http';
import { parse } from 'url';
import { extname, join, dirname } from 'path';
import { createReadStream, existsSync, lstatSync } from 'fs';
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

function setCommonHeaders(res) {
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin-allow-popups');
  res.setHeader('Cross-Origin-Embedder-Policy', 'unsafe-none');
}

function sendFile(req, res, filePath, status = 200) {
  res.statusCode = status;
  res.setHeader('Content-Type', getContentType(filePath));
  setCommonHeaders(res);
  if (req.method === 'HEAD') {
    res.end();
    return;
  }
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
    setCommonHeaders(res);
    res.end();
    return;
  }

  if (safePath === '/admin') {
    sendFile(req, res, indexPath);
    return;
  }

  const decodedPath = decodeURIComponent(safePath);
  const normalized = decodedPath.replace(/^\/+/, '');
  const hasExtension = extname(normalized) !== '';
  const candidate = join(distDir, normalized || 'index.html');
  const fileExists = existsSync(candidate) && lstatSync(candidate).isFile();
  const acceptsHtml = (req.headers.accept ?? '').includes('text/html');

  try {
    if (hasExtension && fileExists) {
      sendFile(req, res, candidate);
      return;
    }

    if (!hasExtension || acceptsHtml) {
      sendFile(req, res, indexPath);
      return;
    }

    if (hasExtension) {
      setCommonHeaders(res);
      res.statusCode = 404;
      res.end('Not Found');
      return;
    }
  } catch (err) {
    res.statusCode = 500;
    setCommonHeaders(res);
    res.end('Internal Server Error');
    console.error('Failed to serve request', err);
  }
});

const port = Number(process.env.PORT ?? 4173);
server.listen(port, '0.0.0.0', () => {
  console.log(`Viewer portal running at http://0.0.0.0:${port}`);
});

