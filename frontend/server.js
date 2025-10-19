import { createServer } from 'http';
import { extname, join, dirname, resolve } from 'path';
import { createReadStream } from 'fs';
import { access, stat } from 'fs/promises';
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

async function fileExists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function wantsSpaFallback(pathname, req) {
  if (pathname === '/' || pathname === '') {
    return true;
  }

  const hasExtension = extname(pathname) !== '';
  if (hasExtension) {
    return false;
  }

  const acceptHeader = req.headers['accept'];
  if (acceptHeader && acceptHeader.includes('text/html')) {
    return true;
  }

  return true;
}

const server = createServer(async (req, res) => {
  if (!req.url) {
    res.statusCode = 400;
    res.end('Bad Request');
    return;
  }

  const requestUrl = new URL(req.url, `http://${req.headers.host ?? 'localhost'}`);
  let pathname = decodeURIComponent(requestUrl.pathname);

  const methodAllowsSpaFallback = req.method === 'GET' || req.method === 'HEAD';

  if (methodAllowsSpaFallback) {
    const looksLikeStaticAsset = extname(pathname) !== '';
    if (!looksLikeStaticAsset) {
      sendFile(req, res, indexPath);
      return;
    }
  }


  // Prevent path traversal and normalise the request path relative to the dist directory
  const sanitizedPath = pathname.replace(/\.\.+/g, '.').replace(/^\/+/, '');
  const candidatePath = resolve(distDir, sanitizedPath);

  if (!candidatePath.startsWith(distDir)) {
    res.statusCode = 403;
    setCommonHeaders(res);
    res.end('Forbidden');
    return;
  }

  try {
    const stats = await stat(candidatePath);

    if (stats.isFile()) {
      sendFile(req, res, candidatePath);
      return;
    }

    if (stats.isDirectory()) {
      const nestedIndex = join(candidatePath, 'index.html');
      if (await fileExists(nestedIndex)) {
        sendFile(req, res, nestedIndex);
        return;
      }
    }
  } catch (error) {
    if (!wantsSpaFallback(sanitizedPath, req)) {
      res.statusCode = 404;
      setCommonHeaders(res);
      res.end('Not Found');
      return;
    }

  }

  sendFile(req, res, indexPath);
});

const port = Number(process.env.PORT ?? 4173);
server.listen(port, '0.0.0.0', () => {
  console.log(`Viewer portal running at http://0.0.0.0:${port}`);
});

