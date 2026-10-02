import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchWithTimeout } from '../api';

describe('fetchWithTimeout', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('abandonne une requête qui ne répond pas', async () => {
    vi.useFakeTimers();
    // fetch qui ne se résout jamais, sauf annulation par le signal.
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
          }),
      ),
    );

    const pending = fetchWithTimeout('https://api.example.com/auth/config', {}, 1000);
    const assertion = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;
  });

  it('renvoie la réponse quand elle arrive à temps', async () => {
    const response = new Response('{}', { status: 200 });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));

    await expect(fetchWithTimeout('https://api.example.com/health')).resolves.toBe(response);
  });
});
