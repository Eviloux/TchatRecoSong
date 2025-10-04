export interface AdminProfile {
  name: string;
  provider: string;
}

export interface AdminSession {
  token: string;
  profile: AdminProfile;
}

const TOKEN_KEY = 'admin_token';
const PROFILE_KEY = 'admin_profile';

export function loadAdminSession(): AdminSession | null {
  const storedToken = localStorage.getItem(TOKEN_KEY);
  const storedProfile = localStorage.getItem(PROFILE_KEY);

  if (!storedToken || !storedProfile) {
    return null;
  }

  try {
    const profile = JSON.parse(storedProfile) as AdminProfile;
    if (!profile || typeof profile.name !== 'string' || typeof profile.provider !== 'string') {
      throw new Error('Invalid profile');
    }
    return { token: storedToken, profile };
  } catch (err) {
    console.warn('Profil administrateur invalide, réinitialisation.', err);
    clearAdminSession();
    return null;
  }
}

export function saveAdminSession(token: string, provider: string, name: string): AdminSession {
  const profile: AdminProfile = { name, provider };
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  return { token, profile };
}

export function clearAdminSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(PROFILE_KEY);
}
