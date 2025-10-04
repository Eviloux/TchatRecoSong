import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AdminView from '../src/views/AdminView.vue';

const TWITCH_STATE_KEY = 'twitch_oauth_state';

describe('AdminView Twitch hash fallback', () => {
  const originalHref = window.location.href;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();

    fetchMock = vi.fn((input: RequestInfo, init?: RequestInit) => {
      if (typeof input === 'string' && input.endsWith('/auth/twitch')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ token: 'server-token', provider: 'twitch', name: 'Admin' }),
            {
              status: 200,
              headers: { 'Content-Type': 'application/json' }
            }
          )
        );
      }

      if (typeof input === 'string' && input.endsWith('/auth/config')) {
        return Promise.resolve(
          new Response(JSON.stringify({}), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          })
        );
      }

      return Promise.resolve(
        new Response(JSON.stringify({ detail: 'not found' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });

    vi.stubGlobal('fetch', fetchMock);
    window.history.replaceState(null, '', originalHref);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    window.history.replaceState(null, '', originalHref);
  });

  it('processes a Twitch access token from the URL hash when mounting', async () => {
    const stateValue = 'expected-state';
    sessionStorage.setItem(TWITCH_STATE_KEY, stateValue);
    window.history.replaceState(
      null,
      '',
      `http://localhost/admin#access_token=test-token&state=${stateValue}`
    );

    const wrapper = mount(AdminView);

    await flushPromises();
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/auth/twitch',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: 'test-token' })
      })
    );
    expect(localStorage.getItem('admin_token')).toBe('server-token');
    expect(localStorage.getItem('admin_profile')).toBe(
      JSON.stringify({ name: 'Admin', provider: 'twitch' })
    );
    expect(sessionStorage.getItem(TWITCH_STATE_KEY)).toBeNull();
    expect(window.location.hash).toBe('');

    await wrapper.unmount();
  });
});
