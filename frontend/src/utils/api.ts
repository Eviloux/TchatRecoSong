export function getApiUrl(): string | null {
  const configured = import.meta.env.VITE_API_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const url = new URL(window.location.origin);
    if (url.hostname.includes('-front')) {
      url.hostname = url.hostname.replace('-front', '');
    }
    return `${url.protocol}//${url.hostname}${url.port ? `:${url.port}` : ''}`.replace(/\/$/, '');
  } catch (error) {
    console.warn('Impossible de déduire automatiquement VITE_API_URL', error);
    return null;
  }
}
