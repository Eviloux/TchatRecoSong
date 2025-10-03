import { getApiUrl } from '../utils/api';

type AuthEndpoint = 'google' | 'twitch';

export interface AuthResponse {
  token: string;
  provider: string;
  name: string;
}

export interface AuthConfig {
  google_client_id?: string;
  twitch_client_id?: string;
}

export async function exchangeAdminAuth(endpoint: AuthEndpoint, payload: Record<string, string>): Promise<AuthResponse> {
  const apiUrl = getApiUrl();
  if (!apiUrl) {
    throw new Error('API non configurée.');
  }

  const response = await fetch(`${apiUrl}/auth/${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = 'Erreur inconnue';
    try {
      const data = await response.json();
      if (typeof data?.detail === 'string') {
        detail = data.detail;
      }
    } catch (err) {
      console.error("Impossible de lire la réponse d'erreur.", err);
    }
    throw new Error(detail);
  }

  return response.json();
}

export async function fetchAuthConfigFromApi(): Promise<AuthConfig | null> {
  const apiUrl = getApiUrl();
  if (!apiUrl) {
    return null;
  }

  try {
    const response = await fetch(`${apiUrl}/auth/config`);
    if (!response.ok) {
      return null;
    }
    return response.json();
  } catch (err) {
    console.error('Impossible de récupérer la configuration auth', err);
    return null;
  }
}
