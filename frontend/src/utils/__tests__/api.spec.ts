import { afterEach, describe, expect, it, vi } from 'vitest';
import { getApiUrl } from '../api';

describe('getApiUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('utilise VITE_API_URL sans barre oblique finale', () => {
    vi.stubEnv('VITE_API_URL', 'https://api.example.com/');
    expect(getApiUrl()).toBe('https://api.example.com');
  });

  it('pointe vers le backend local en développement', () => {
    vi.stubEnv('VITE_API_URL', '');
    expect(getApiUrl()).toBe('http://localhost:8000');
  });
});
