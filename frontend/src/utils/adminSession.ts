import { getApiUrl } from './api';

export interface AdminProfile {
  name: string;
  provider: string;
  subject?: string;
}

const TOKEN_STORAGE_KEY = 'admin_token';
const PROFILE_STORAGE_KEY = 'admin_profile';

type SessionCache = { token: string; profile: AdminProfile };

let cachedSession: SessionCache | null = null;
let lastValidatedToken: string | null = null;
let validationPromise: Promise<AdminSessionValidation> | null = null;

export type AdminSessionValidation =
  | { status: 'valid'; token: string; profile: AdminProfile }
  | { status: 'invalid' }
  | { status: 'error'; error: unknown };

function parseStoredProfile(raw: string | null): AdminProfile | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed === 'object' &&
      typeof (parsed as Record<string, unknown>).name === 'string' &&
      typeof (parsed as Record<string, unknown>).provider === 'string'
    ) {
      const result: AdminProfile = {
        name: (parsed as Record<string, unknown>).name as string,
        provider: (parsed as Record<string, unknown>).provider as string,
      };
      if (typeof (parsed as Record<string, unknown>).subject === 'string') {
        result.subject = (parsed as Record<string, unknown>).subject as string;
      }
      return result;
    }
  } catch (error) {
    console.warn('Profil administrateur invalide dans le stockage local', error);
  }
  return null;
}

export function loadStoredAdminSession(): { token: string | null; profile: AdminProfile | null } {
  if (cachedSession) {
    return { token: cachedSession.token, profile: cachedSession.profile };
  }

  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (!token) {
    return { token: null, profile: null };
  }

  const profile = parseStoredProfile(localStorage.getItem(PROFILE_STORAGE_KEY));
  if (profile) {
    cachedSession = { token, profile };
  }

  return { token, profile };
}

export function persistAdminSession(token: string, profile: AdminProfile): void {
  cachedSession = { token, profile };
  lastValidatedToken = token;
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
}

export function clearAdminSession(): void {
  cachedSession = null;
  lastValidatedToken = null;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(PROFILE_STORAGE_KEY);
}

async function requestSessionValidation(token: string): Promise<AdminSessionValidation> {
  let apiUrl: string;
  try {
    apiUrl = getApiUrl();
  } catch (error) {
    console.error("Impossible d'obtenir l'URL de l'API pour valider la session admin", error);
    return { status: 'error', error };
  }

  try {
    const response = await fetch(`${apiUrl}/auth/session`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const data = await response.json();
      const profile: AdminProfile = {
        name: data.name ?? '',
        provider: data.provider ?? '',
      };
      if (typeof data.subject === 'string' && data.subject) {
        profile.subject = data.subject;
      }
      persistAdminSession(token, profile);
      return { status: 'valid', token, profile };
    }

    if (response.status === 401 || response.status === 403) {
      clearAdminSession();
      return { status: 'invalid' };
    }

    const error = new Error(`Réponse inattendue lors de la validation de session (${response.status})`);
    console.error(error);
    return { status: 'error', error };
  } catch (error) {
    console.error('Impossible de vérifier la session administrateur', error);
    return { status: 'error', error };
  }
}

export async function ensureValidStoredAdminSession(options: { force?: boolean } = {}): Promise<AdminSessionValidation> {
  const { force = false } = options;
  const stored = loadStoredAdminSession();

  if (!stored.token) {
    clearAdminSession();
    return { status: 'invalid' };
  }

  if (!force && cachedSession && cachedSession.token === stored.token && lastValidatedToken === stored.token) {
    return { status: 'valid', token: cachedSession.token, profile: cachedSession.profile };
  }

  if (!force && validationPromise) {
    return validationPromise;
  }

  validationPromise = requestSessionValidation(stored.token);
  const result = await validationPromise;
  validationPromise = null;
  return result;
}
