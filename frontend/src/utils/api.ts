const LOCAL_BACKEND_URL = 'http://localhost:8000';

export function getApiUrl(): string {
  const configured = import.meta.env.VITE_API_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  if (typeof window === 'undefined') {
    throw new Error('VITE_API_URL doit être défini lorsque window est indisponible.');
  }

  const { hostname } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1' || hostname === '[::1]') {
    return LOCAL_BACKEND_URL;
  }

  try {
    const url = new URL(window.location.origin);
    if (url.hostname.includes('-front')) {
      url.hostname = url.hostname.replace('-front', '');
    }
    return `${url.protocol}//${url.hostname}${url.port ? `:${url.port}` : ''}`.replace(/\/$/, '');
  } catch (error) {
    throw new Error('Impossible de déduire automatiquement VITE_API_URL. Définissez VITE_API_URL pour votre déploiement.');
  }
}

const DEFAULT_TIMEOUT_MS = 10_000;

/**
 * `fetch` avec délai maximal : sans lui, une requête vers un backend Render
 * en train de se réveiller peut rester en attente plusieurs minutes et bloquer
 * l'interface. Lève une `DOMException` (`TimeoutError`/`AbortError`) à l'expiration.
 */
export async function fetchWithTimeout(
  input: string,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}
