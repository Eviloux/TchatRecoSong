import { readonly, ref } from 'vue';

export type Theme = 'dark' | 'light';

// Même clé que le script anti-flash de index.html : les garder synchronisés.
export const THEME_STORAGE_KEY = 'tchatreco:theme';

const THEME_COLORS: Record<Theme, string> = { dark: '#1a1526', light: '#f8f6fd' };

function readStoredTheme(): Theme | null {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return stored === 'dark' || stored === 'light' ? stored : null;
  } catch {
    // Stockage bloqué (navigation privée stricte…) : pas de préférence mémorisée.
    return null;
  }
}

function systemTheme(): Theme {
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

/** Thème à appliquer : choix mémorisé du viewer, sinon réglage de l'appareil. */
export function resolveInitialTheme(): Theme {
  return readStoredTheme() ?? systemTheme();
}

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[theme]);
}

const currentTheme = ref<Theme>('dark');
let initialized = false;

/** À appeler une fois au démarrage de l'application. */
export function initTheme(): void {
  if (initialized) return;
  initialized = true;
  currentTheme.value = resolveInitialTheme();
  applyTheme(currentTheme.value);

  // Tant que le viewer n'a rien choisi, on suit les changements de l'appareil.
  window.matchMedia?.('(prefers-color-scheme: light)').addEventListener?.('change', () => {
    if (readStoredTheme() === null) {
      currentTheme.value = systemTheme();
      applyTheme(currentTheme.value);
    }
  });
}

export function setTheme(theme: Theme): void {
  currentTheme.value = theme;
  applyTheme(theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Le thème s'applique quand même, il ne sera simplement pas mémorisé.
  }
}

export function toggleTheme(): void {
  setTheme(currentTheme.value === 'dark' ? 'light' : 'dark');
}

export function useTheme() {
  return { theme: readonly(currentTheme), toggleTheme, setTheme };
}

/** Réservé aux tests. */
export function resetThemeForTests(): void {
  initialized = false;
  currentTheme.value = 'dark';
}
