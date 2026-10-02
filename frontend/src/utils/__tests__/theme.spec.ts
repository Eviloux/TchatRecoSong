import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  THEME_STORAGE_KEY,
  initTheme,
  resetThemeForTests,
  resolveInitialTheme,
  toggleTheme,
  useTheme,
} from '../theme';

function mockSystemPrefersLight(prefersLight: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({ matches: prefersLight, addEventListener: vi.fn() }),
  );
}

describe('thème', () => {
  beforeEach(() => {
    localStorage.clear();
    resetThemeForTests();
    delete document.documentElement.dataset.theme;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('suit le réglage de l’appareil sans choix mémorisé', () => {
    mockSystemPrefersLight(true);
    expect(resolveInitialTheme()).toBe('light');

    mockSystemPrefersLight(false);
    expect(resolveInitialTheme()).toBe('dark');
  });

  it('privilégie le choix mémorisé du viewer', () => {
    mockSystemPrefersLight(true);
    localStorage.setItem(THEME_STORAGE_KEY, 'dark');
    expect(resolveInitialTheme()).toBe('dark');
  });

  it('ignore une valeur mémorisée invalide', () => {
    mockSystemPrefersLight(false);
    localStorage.setItem(THEME_STORAGE_KEY, 'rose');
    expect(resolveInitialTheme()).toBe('dark');
  });

  it('bascule, applique et mémorise le thème', () => {
    mockSystemPrefersLight(false);
    initTheme();
    const { theme } = useTheme();
    expect(document.documentElement.dataset.theme).toBe('dark');

    toggleTheme();

    expect(theme.value).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');
  });

  it('reste utilisable si le stockage est bloqué', () => {
    mockSystemPrefersLight(false);
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('bloqué', 'SecurityError');
    });
    initTheme();

    expect(() => toggleTheme()).not.toThrow();
    expect(document.documentElement.dataset.theme).toBe('light');
  });
});
