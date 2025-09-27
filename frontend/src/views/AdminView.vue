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
      <button v-if="twitchClientId" type="button" @click="loginWithTwitch">Connexion Twitch</button>
      <p class="login-hint">
        Configurez les variables <code>VITE_GOOGLE_CLIENT_ID</code> et <code>VITE_TWITCH_CLIENT_ID</code> si nécessaire.
      </p>
    </div>

    <div v-else class="admin-content">
      <button type="button" class="logout" @click="logout">Se déconnecter</button>
      <SongList />
      <AdminPanel :token="token" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import SongList from '../components/SongList.vue';
import AdminPanel from '../components/AdminPanel.vue';

interface AdminProfile {
  name: string;
  provider: string;
}

declare global {
  interface Window {
    google?: any;
  }
}

const API_URL = import.meta.env.VITE_API_URL;
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const twitchClientId = import.meta.env.VITE_TWITCH_CLIENT_ID;

const token = ref<string | null>(localStorage.getItem('admin_token'));
const storedProfile = localStorage.getItem('admin_profile');
const profile = ref<AdminProfile | null>(storedProfile ? JSON.parse(storedProfile) : null);
const error = ref('');

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

const callAuthEndpoint = async (endpoint: 'google' | 'twitch', payload: Record<string, string>) => {
  if (!API_URL) return;
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

const initGoogle = () => {
  if (!googleClientId || !window.google) return;
  window.google.accounts.id.initialize({ client_id: googleClientId, callback: handleGoogleCredential });
  window.google.accounts.id.renderButton(document.getElementById('google-login'), {
    theme: 'outline',
    size: 'large',
  });
};

const loginWithTwitch = () => {
  error.value = '';
  if (!twitchClientId) {
    error.value = 'TWITCH_CLIENT_ID manquant.';
    return;
  }
  const redirectUri = `${window.location.origin}/admin`;
  const url = new URL('https://id.twitch.tv/oauth2/authorize');
  url.searchParams.set('client_id', twitchClientId);
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

onMounted(async () => {
  initGoogle();
  await checkTwitchRedirect();
});
</script>
