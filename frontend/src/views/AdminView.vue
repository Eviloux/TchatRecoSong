<template>
  <section class="admin-view">
    <header>
      <h2>Espace administrateur</h2>
      <p v-if="profile">Connecté en tant que {{ profile.name }} ({{ profile.provider }})</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="!token" class="login-options">
      <p>Connectez-vous avec un compte autorisé pour gérer les recommandations.</p>
      <div id="google-login" class="login-button" v-if="googleClientId"></div>
      <button
        v-if="twitchClientId"
        type="button"
        class="twitch-login"
        @click="loginWithTwitch"
      >
        <span class="icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false" role="img">
            <path
              d="M3 1L1 5v14h5v4h4l4-4h4l5-5V1H3zm18 12l-3 3h-5l-4 4v-4H4V3h17v10z"
            />
            <path d="M17 6h-2v5h2V6zm-5 0h-2v5h2V6z" />
          </svg>
        </span>
        <span class="label">Login with Twitch</span>
      </button>
      <p class="login-hint">
        Les identifiants OAuth sont récupérés automatiquement auprès de l'API. Vérifiez la configuration
        Render si les boutons n'apparaissent pas.
      </p>
    </div>

    <div v-else class="admin-content">
      <button type="button" class="logout" @click="logout">Se déconnecter</button>
      <SongList ref="songListRef" :token="token" />

      <AdminPanel :token="token" @ban-rules-changed="handleBanRuleCreated" />

    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import SongList from '../components/SongList.vue';
import AdminPanel from '../components/AdminPanel.vue';
import { getApiUrl } from '../utils/api';

interface AdminProfile {
  name: string;
  provider: string;
}

type SongListHandle = {
  refresh: () => Promise<void> | void;
};

declare global {
  interface Window {
    google?: any;
  }
}

const API_URL = getApiUrl();

const googleClientId = ref<string | null>(import.meta.env.VITE_GOOGLE_CLIENT_ID || null);
const twitchClientId = ref<string | null>(import.meta.env.VITE_TWITCH_CLIENT_ID || null);

const token = ref<string | null>(localStorage.getItem('admin_token'));
const storedProfile = localStorage.getItem('admin_profile');
const profile = ref<AdminProfile | null>(storedProfile ? JSON.parse(storedProfile) : null);
const error = ref('');
const songListRef = ref<SongListHandle | null>(null);

const TWITCH_STATE_KEY = 'twitch_oauth_state';
const TWITCH_RESULT_KEY = 'twitch_oauth_result';

const twitchPopup = ref<Window | null>(null);
let twitchMessageHandler: ((event: MessageEvent) => void) | null = null;
let twitchPopupMonitor: number | null = null;

const detachTwitchMessageHandler = () => {
  if (twitchMessageHandler) {
    window.removeEventListener('message', twitchMessageHandler);
    twitchMessageHandler = null;
  }
};

const stopTwitchPopupMonitor = () => {
  if (twitchPopupMonitor !== null) {
    window.clearInterval(twitchPopupMonitor);
    twitchPopupMonitor = null;
  }
};

const closeTwitchPopup = () => {
  if (twitchPopup.value && !twitchPopup.value.closed) {
    twitchPopup.value.close();
  }
  twitchPopup.value = null;
};

const resetTwitchFlow = () => {
  detachTwitchMessageHandler();
  stopTwitchPopupMonitor();
  closeTwitchPopup();
  sessionStorage.removeItem(TWITCH_STATE_KEY);
};

const finalizeTwitchError = (message: string) => {
  resetTwitchFlow();
  error.value = message;
};

const finalizeTwitchSuccess = async (accessToken: string, state: string | null | undefined) => {
  const expectedState = sessionStorage.getItem(TWITCH_STATE_KEY);
  if (!expectedState || !state || state !== expectedState) {
    resetTwitchFlow();
    error.value = 'Réponse Twitch invalide ou expirée.';
    return;
  }
  resetTwitchFlow();
  await callAuthEndpoint('twitch', { access_token: accessToken });
};

const generateTwitchState = () => {
  if (window.crypto?.getRandomValues) {
    const array = new Uint8Array(16);
    window.crypto.getRandomValues(array);
    return Array.from(array, (value) => value.toString(16).padStart(2, '0')).join('');
  }
  return Math.random().toString(36).slice(2, 18);
};

const processTwitchResultString = async (raw: string) => {
  try {
    const data = JSON.parse(raw);
    if (data?.type === 'twitch-auth-success' && typeof data.accessToken === 'string') {
      await finalizeTwitchSuccess(data.accessToken, data.state);
    } else if (data?.type === 'twitch-auth-error') {
      const message = typeof data.error === 'string' && data.error ? data.error : 'Connexion Twitch refusée.';
      finalizeTwitchError(message);
    }
  } catch (err) {
    console.error('Impossible de traiter la réponse Twitch stockée', err);
  }
};

const handleTwitchStorageEvent = (event: StorageEvent) => {
  if (event.key === TWITCH_RESULT_KEY && event.newValue) {
    void processTwitchResultString(event.newValue);
    try {
      localStorage.removeItem(TWITCH_RESULT_KEY);
    } catch (err) {
      console.error('Impossible de nettoyer les données Twitch du stockage', err);
    }
  }
};

const storeSession = (authToken: string, provider: string, name: string) => {
  token.value = authToken;
  profile.value = { name, provider };
  localStorage.setItem('admin_token', authToken);
  localStorage.setItem('admin_profile', JSON.stringify(profile.value));
};

const logout = () => {
  token.value = null;
  profile.value = null;
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_profile');
};

const handleBanRuleCreated = async () => {
  if (songListRef.value) {
    await songListRef.value.refresh();
  }
};

const callAuthEndpoint = async (endpoint: 'google' | 'twitch', payload: Record<string, string>) => {
  if (!API_URL) {
    error.value = 'API non configurée.';
    return;
  }
  try {
    error.value = '';
    const response = await fetch(`${API_URL}/auth/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
      throw new Error(data.detail);
    }
    const data = await response.json();
    storeSession(data.token, data.provider, data.name);
  } catch (err: any) {
    console.error(err);
    error.value = err.message || 'Connexion impossible.';
  }
};

const handleGoogleCredential = async (response: any) => {
  error.value = '';
  await callAuthEndpoint('google', { credential: response.credential });
};

let googleInitTimer: number | null = null;

const consumePendingTwitchResult = async () => {
  try {
    const raw = localStorage.getItem(TWITCH_RESULT_KEY);
    if (!raw) {
      return;
    }
    localStorage.removeItem(TWITCH_RESULT_KEY);
    await processTwitchResultString(raw);
  } catch (err) {
    console.error('Impossible de lire le résultat Twitch stocké', err);
  }
};

const ensureGoogleButton = async () => {
  if (!googleClientId.value || !window.google?.accounts?.id) {
    return;
  }

  await nextTick();
  const container = document.getElementById('google-login');
  if (!container) {
    return;
  }

  container.innerHTML = '';
  const width = Math.min(container.offsetWidth || 320, 320);
  window.google.accounts.id.initialize({ client_id: googleClientId.value, callback: handleGoogleCredential });

  window.google.accounts.id.renderButton(container, {
    theme: 'outline',
    size: 'large',
    width,
    text: 'signin_with',
    shape: 'rectangular',
  });
};

const scheduleGoogleInitRetry = () => {
  if (googleInitTimer !== null) {
    return;
  }
  googleInitTimer = window.setInterval(() => {
    if (window.google?.accounts?.id) {
      ensureGoogleButton();
      if (googleInitTimer !== null) {
        window.clearInterval(googleInitTimer);
        googleInitTimer = null;
      }
    }
  }, 250);
};

const loginWithTwitch = () => {
  error.value = '';
  if (!twitchClientId.value) {
    error.value = 'Identifiant client Twitch manquant.';
    return;
  }

  const redirectUri = `${window.location.origin}/twitch-callback`;
  const state = generateTwitchState();
  sessionStorage.setItem(TWITCH_STATE_KEY, state);

  const url = new URL('https://id.twitch.tv/oauth2/authorize');
  url.searchParams.set('client_id', twitchClientId.value);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('response_type', 'token');
  url.searchParams.set('scope', 'user:read:email');
  url.searchParams.set('state', state);

  detachTwitchMessageHandler();
  twitchMessageHandler = async (event: MessageEvent) => {
    if (event.origin !== window.location.origin) {
      return;
    }
    const data = event.data;
    if (!data || typeof data !== 'object') {
      return;
    }
    if (data.type === 'twitch-auth-success' && typeof data.accessToken === 'string') {
      await finalizeTwitchSuccess(data.accessToken, data.state);
    } else if (data.type === 'twitch-auth-error') {
      const message = typeof data.error === 'string' && data.error ? data.error : 'Connexion Twitch refusée.';
      finalizeTwitchError(message);
    }
  };
  window.addEventListener('message', twitchMessageHandler);

  stopTwitchPopupMonitor();
  const features = 'width=500,height=700,menubar=no,toolbar=no,status=no';
  const popup = window.open(url.toString(), 'twitch-oauth', features);
  if (!popup) {
    sessionStorage.removeItem(TWITCH_STATE_KEY);
    detachTwitchMessageHandler();
    error.value = 'Autorisez les pop-ups pour continuer avec Twitch.';
    return;
  }
  twitchPopup.value = popup;

  twitchPopupMonitor = window.setInterval(() => {
    if (!twitchPopup.value || twitchPopup.value.closed) {
      if (twitchPopupMonitor !== null) {
        window.clearInterval(twitchPopupMonitor);
        twitchPopupMonitor = null;
      }
      const hadState = sessionStorage.getItem(TWITCH_STATE_KEY);
      resetTwitchFlow();
      if (hadState) {
        error.value = 'Connexion Twitch annulée.';
      }
    }
  }, 500);
};

const fetchAuthConfig = async () => {
  if (!API_URL) return;
  try {
    const response = await fetch(`${API_URL}/auth/config`);
    if (!response.ok) return;
    const data = await response.json();
    if (data.google_client_id) {
      googleClientId.value = data.google_client_id;
    }
    if (data.twitch_client_id) {
      twitchClientId.value = data.twitch_client_id;
    }
  } catch (err) {
    console.error('Impossible de récupérer la configuration auth', err);
  }
};

watch(googleClientId, () => {
  ensureGoogleButton();
  scheduleGoogleInitRetry();
});

watch(token, async (newToken) => {
  if (newToken === null) {
    await nextTick();
    ensureGoogleButton();
    scheduleGoogleInitRetry();
  }
});

onMounted(async () => {
  window.addEventListener('storage', handleTwitchStorageEvent);
  scheduleGoogleInitRetry();
  await fetchAuthConfig();
  await consumePendingTwitchResult();
  ensureGoogleButton();
});

onBeforeUnmount(() => {
  if (googleInitTimer !== null) {
    window.clearInterval(googleInitTimer);
    googleInitTimer = null;
  }
  window.removeEventListener('storage', handleTwitchStorageEvent);
  resetTwitchFlow();
});
</script>
