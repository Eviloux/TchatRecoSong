<template>
  <section class="admin-view">
    <header>
      <h2>Espace administrateur</h2>
      <p v-if="profile">Connecté en tant que {{ profile.name }} ({{ profile.provider }})</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="!token" class="login-options">
      <p>Connectez-vous avec un compte Google autorisé pour gérer les recommandations.</p>
      <div id="google-login" class="login-button" v-if="googleClientId"></div>
      <p class="login-hint">
        L'identifiant OAuth est récupéré automatiquement auprès de l'API. Vérifiez la configuration Render si le bouton
        n'apparaît pas.
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

const callGoogleAuthEndpoint = async (payload: Record<string, string>) => {
  if (!API_URL) {
    error.value = 'API non configurée.';
    return;
  }
  try {
    error.value = '';
    const response = await fetch(`${API_URL}/auth/google`, {
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
  await callGoogleAuthEndpoint({ credential: response.credential });
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

const fetchAuthConfig = async () => {
  if (!API_URL) return;
  try {
    const response = await fetch(`${API_URL}/auth/config`);
    if (!response.ok) return;
    const data = await response.json();
    if (data.google_client_id) {
      googleClientId.value = data.google_client_id;
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
  scheduleGoogleInitRetry();
  await fetchAuthConfig();
  ensureGoogleButton();
});

onBeforeUnmount(() => {
  if (googleInitTimer !== null) {
    window.clearInterval(googleInitTimer);
    googleInitTimer = null;
  }
});
</script>
