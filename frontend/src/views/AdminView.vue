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
    error.value = 'TWITCH_CLIENT_ID manquant.';
    return;
  }
  const redirectUri = `${window.location.origin}/admin`;
  const url = new URL('https://id.twitch.tv/oauth2/authorize');
  url.searchParams.set('client_id', twitchClientId.value);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('response_type', 'token');
  url.searchParams.set('scope', 'user:read:email');
  window.location.href = url.toString();
};

const checkTwitchRedirect = async () => {
  if (!window.location.hash) return;
  const params = new URLSearchParams(window.location.hash.replace('#', ''));
  const accessToken = params.get('access_token');
  if (accessToken) {
    await callAuthEndpoint('twitch', { access_token: accessToken });
    window.history.replaceState({}, document.title, window.location.pathname);
  }
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

onMounted(async () => {
  scheduleGoogleInitRetry();
  await fetchAuthConfig();
  await checkTwitchRedirect();
  ensureGoogleButton();
});

onBeforeUnmount(() => {
  if (googleInitTimer !== null) {
    window.clearInterval(googleInitTimer);
    googleInitTimer = null;
  }
});
</script>
