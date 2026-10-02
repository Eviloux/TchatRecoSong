import { createServer } from 'http';
import { createReadStream } from 'fs';
import { stat } from 'fs/promises';
import { dirname, extname, join, resolve, sep } from 'path';
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

const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};

function sendText(res, status, body) {
  res.writeHead(status, { ...SECURITY_HEADERS, 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(body);
}

function sendFile(req, res, filePath) {
  const isHashedAsset = filePath.startsWith(join(distDir, 'assets') + sep);
  res.writeHead(200, {
    ...SECURITY_HEADERS,
    'Content-Type': MIME_TYPES[extname(filePath).toLowerCase()] ?? 'application/octet-stream',
    // index.html doit toujours être revalidé, sinon les navigateurs gardent un
    // ancien bundle après un déploiement ; les assets hashés, eux, sont immuables.
    'Cache-Control': isHashedAsset ? 'public, max-age=31536000, immutable' : 'no-cache',
  });

  if (req.method === 'HEAD') {
    res.end();
    return;
  }
  createReadStream(filePath)
    .on('error', () => res.destroy())
    .pipe(res);
}

async function isFile(filePath) {
  try {
    return (await stat(filePath)).isFile();
  } catch {
    return false;
  }
}

async function handle(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendText(res, 405, 'Method Not Allowed');
    return;
  }

  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url ?? '/', 'http://localhost').pathname);
  } catch {
    // URL mal encodée (ex. /%E0) : sans ce garde-fou, l'exception tuait le serveur.
    sendText(res, 400, 'Bad Request');
    return;
  }

  // Routes de la SPA (sans extension) : toujours index.html, le routeur Vue décide.
  if (extname(pathname) === '') {
    sendFile(req, res, indexPath);
    return;
  }

  const candidatePath = resolve(distDir, `.${pathname}`);
  // Le séparateur final empêche aussi d'atteindre un dossier voisin comme `dist-old/`.
  if (!candidatePath.startsWith(distDir + sep)) {
    sendText(res, 403, 'Forbidden');
    return;
  }

  if (await isFile(candidatePath)) {
    sendFile(req, res, candidatePath);
    return;
  }

  sendText(res, 404, 'Not Found');
}

const server = createServer((req, res) => {
  handle(req, res).catch((error) => {
    console.error('Erreur inattendue du serveur front', error);
    if (!res.headersSent) {
      sendText(res, 500, 'Internal Server Error');
    } else {
      res.destroy();
    }
  });
});

const port = Number(process.env.PORT ?? 4173);
server.listen(port, '0.0.0.0', () => {
  console.log(`Viewer portal running at http://0.0.0.0:${port}`);
});
