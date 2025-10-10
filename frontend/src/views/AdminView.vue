<template>
  <section class="admin-view">
    <header>
      <h2>Espace administrateur</h2>
      <p v-if="profile">Connecté en tant que {{ profile.name }} ({{ profile.provider }})</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="!token" class="login-options">
      <p>
        Connectez-vous avec un compte autorisé pour gérer les recommandations.
      </p>

      <form
        v-if="passwordLoginEnabled"
        class="email-login"
        @submit.prevent="submitEmailLogin"
        novalidate
      >
        <label for="admin-email">Adresse e-mail</label>
        <input
          id="admin-email"
          v-model="email"
          type="email"
          autocomplete="username"
          required
          :disabled="emailLoginLoading"
        />

        <label for="admin-password">Mot de passe</label>
        <input
          id="admin-password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          :disabled="emailLoginLoading"
        />

        <button type="submit" :disabled="emailLoginLoading">
          {{ emailLoginLoading ? 'Connexion…' : 'Se connecter' }}
        </button>
      </form>

      <div
        v-if="passwordLoginEnabled && googleClientId"
        class="login-divider"
        role="presentation"
      >
        <span>ou</span>
      </div>

      <div id="google-login" class="login-button" v-if="googleClientId"></div>
      <p class="login-hint">
        L'identifiant OAuth est récupéré automatiquement auprès de l'API. Utilisez vos identifiants locaux si le bouton
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
const passwordLoginEnabled = ref(false);

const token = ref<string | null>(localStorage.getItem('admin_token'));
const storedProfile = localStorage.getItem('admin_profile');
const profile = ref<AdminProfile | null>(storedProfile ? JSON.parse(storedProfile) : null);
const error = ref('');
const songListRef = ref<SongListHandle | null>(null);
const email = ref('');
const password = ref('');
const emailLoginLoading = ref(false);

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
  email.value = '';
  password.value = '';
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
    if (typeof data.password_login_enabled === 'boolean') {
      passwordLoginEnabled.value = data.password_login_enabled;
    }
  } catch (err) {
    console.error('Impossible de récupérer la configuration auth', err);
  }
};

const submitEmailLogin = async () => {
  if (!API_URL) {
    error.value = 'API non configurée.';
    return;
  }

  const trimmedEmail = email.value.trim();
  if (!trimmedEmail || !password.value) {
    error.value = 'Merci de renseigner votre e-mail et votre mot de passe.';
    return;
  }

  emailLoginLoading.value = true;
  try {
    error.value = '';
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: trimmedEmail, password: password.value }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: 'Connexion impossible.' }));
      throw new Error(payload.detail || 'Connexion impossible.');
    }

    const data = await response.json();
    storeSession(data.token, data.provider, data.name);
    email.value = '';
    password.value = '';
  } catch (err: any) {
    console.error(err);
    error.value = err.message || 'Connexion impossible.';
  } finally {
    emailLoginLoading.value = false;
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
