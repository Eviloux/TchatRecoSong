<template>
  <section class="admin-view login-view">
    <header>
      <h2>Connexion administrateur</h2>
      <p class="login-hint">Connectez-vous avec un compte autorisé pour gérer les recommandations.</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <p v-if="!ready" class="loading">Vérification de la session en cours…</p>

    <div v-else class="login-options">
      <form v-if="passwordLoginEnabled" class="email-login" @submit.prevent="submitEmailLogin" novalidate>
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

      <div v-if="passwordLoginEnabled && googleClientId" class="login-divider" role="presentation">
        <span>ou</span>
      </div>

      <div id="google-login" class="login-button" v-if="googleClientId"></div>

      <div v-if="twitchClientId && (passwordLoginEnabled || googleClientId)" class="login-divider" role="presentation">
        <span>ou</span>
      </div>

      <button v-if="twitchClientId" class="twitch-login-btn" :disabled="twitchLoginLoading" @click="startTwitchLogin">
        <svg width="20" height="20" viewBox="0 0 256 268" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M17.458 0L0 46.556v186.2h63.983v34.934h34.932l34.897-34.934h52.36L256 162.954V0H17.458zm23.259 23.263H232.73v128.029l-40.739 40.742H128L93.1 226.93v-34.896H40.717V23.263zm63.983 93.085h23.263V58.17H104.7v58.178zm63.992 0h23.263V58.17h-23.263v58.178z"/>
        </svg>
        {{ twitchLoginLoading ? 'Connexion Twitch…' : 'Se connecter avec Twitch' }}
      </button>

      <p v-if="configLoading" class="login-hint" role="status">
        Le serveur se réveille, les options de connexion arrivent…
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { fetchWithTimeout, getApiUrl } from '../utils/api';
import {
  ensureValidStoredAdminSession,
  loadStoredAdminSession,
  persistAdminSession,
  type AdminProfile,
} from '../utils/adminSession';

declare global {
  interface Window {
    google?: any;
  }
}

const API_URL = getApiUrl();

const route = useRoute();
const router = useRouter();

const googleClientId = ref<string | null>(import.meta.env.VITE_GOOGLE_CLIENT_ID || null);
const twitchClientId = ref<string | null>(import.meta.env.VITE_TWITCH_CLIENT_ID || null);
const passwordLoginEnabled = ref(false);
const twitchLoginLoading = ref(false);

const backendUnavailableMessage = "Le backend n'est pas encore lancé, merci de patienter.";

const storedSession = loadStoredAdminSession();
const token = ref<string | null>(storedSession.token);
const ready = ref(false);
const error = ref('');
const email = ref('');
const password = ref('');
const emailLoginLoading = ref(false);

const redirectTarget = computed(() => {
  const redirect = route.query.redirect;
  if (typeof redirect === 'string' && redirect.startsWith('/')) {
    return redirect;
  }
  return '/admin';
});

const storeSession = async (authToken: string, provider: string, name: string, subject?: string) => {
  const sessionProfile: AdminProfile = { name, provider };
  if (subject) {
    sessionProfile.subject = subject;
  }
  token.value = authToken;
  persistAdminSession(authToken, sessionProfile);
  await router.replace(redirectTarget.value);
};

const isBackendUnavailableError = (err: unknown) => {
  if (!err) {
    return false;
  }
  // TypeError : réseau/CORS ; AbortError : délai de fetchWithTimeout dépassé.
  if (err instanceof TypeError || (err instanceof DOMException && err.name === 'AbortError')) {
    return true;
  }
  if (err instanceof Error) {
    const message = err.message.toLowerCase();
    return err.name === 'TypeError' || message.includes('failed to fetch') || message.includes('networkerror');
  }
  return false;
};

const callGoogleAuthEndpoint = async (payload: Record<string, string>) => {
  if (!API_URL) {
    error.value = 'API non configurée.';
    return;
  }
  try {
    error.value = '';
    const response = await fetchWithTimeout(`${API_URL}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, 20_000);
    if (!response.ok) {
      if (response.status === 403) {
        throw new Error("Votre utilisateur n'est pas dans la whitelist.");
      }
      const data = await response.json().catch(() => ({ detail: 'Connexion impossible.' }));
      throw new Error(data.detail || 'Connexion impossible.');
    }
    const data = await response.json();
    await storeSession(data.token, data.provider, data.name, data.subject);
  } catch (err: any) {
    console.error(err);
    if (isBackendUnavailableError(err)) {
      error.value = backendUnavailableMessage;
      return;
    }
    error.value = err?.message || 'Connexion impossible.';
  }
};

const handleGoogleCredential = async (response: any) => {
  error.value = '';
  await callGoogleAuthEndpoint({ credential: response.credential });
};

let googleInitTimer: number | null = null;

const ensureGoogleButton = async () => {
  if (!ready.value || !googleClientId.value || !window.google?.accounts?.id) {
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
  if (googleInitTimer !== null || !ready.value) {
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

const twitchRedirectUri = `${window.location.origin}/login`;

const startTwitchLogin = () => {
  if (!twitchClientId.value) return;
  const params = new URLSearchParams({
    client_id: twitchClientId.value,
    redirect_uri: twitchRedirectUri,
    response_type: 'code',
    scope: 'user:read:email',
  });
  window.location.href = `https://id.twitch.tv/oauth2/authorize?${params}`;
};

const handleTwitchCallback = async (code: string) => {
  if (!API_URL) {
    error.value = 'API non configurée.';
    return;
  }
  twitchLoginLoading.value = true;
  try {
    error.value = '';
    const response = await fetchWithTimeout(`${API_URL}/auth/twitch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, redirect_uri: twitchRedirectUri }),
    }, 20_000);
    if (!response.ok) {
      if (response.status === 403) {
        throw new Error("Ce compte Twitch n'est pas autorisé à accéder à l'administration.");
      }
      const data = await response.json().catch(() => ({ detail: 'Connexion Twitch impossible.' }));
      throw new Error(data.detail || 'Connexion Twitch impossible.');
    }
    const data = await response.json();
    await storeSession(data.token, data.provider, data.name, data.subject);
  } catch (err: any) {
    console.error(err);
    if (isBackendUnavailableError(err)) {
      error.value = backendUnavailableMessage;
      return;
    }
    error.value = err?.message || 'Connexion Twitch impossible.';
  } finally {
    twitchLoginLoading.value = false;
  }
};

const configLoading = ref(true);
const CONFIG_RETRY_DELAY_MS = 3000;
const CONFIG_MAX_ATTEMPTS = 20; // ~1 min : durée typique d'un réveil Render
let configRetryTimer: number | undefined;

// Récupère les identifiants OAuth publics. Pendant le réveil du backend on
// réessaie en arrière-plan, sans jamais bloquer l'affichage de la page.
const fetchAuthConfig = async (attempt = 1): Promise<void> => {
  if (!API_URL) {
    configLoading.value = false;
    return;
  }
  try {
    const response = await fetchWithTimeout(`${API_URL}/auth/config`, {}, 8000);
    if (!response.ok) throw new Error(`Statut ${response.status}`);
    const data = await response.json();
    if (data.google_client_id) {
      googleClientId.value = data.google_client_id;
    }
    if (data.twitch_client_id) {
      twitchClientId.value = data.twitch_client_id;
    }
    if (typeof data.password_login_enabled === 'boolean') {
      passwordLoginEnabled.value = data.password_login_enabled;
    }
    configLoading.value = false;
  } catch (err) {
    if (attempt >= CONFIG_MAX_ATTEMPTS) {
      console.error('Impossible de récupérer la configuration auth', err);
      configLoading.value = false;
      error.value = backendUnavailableMessage;
      return;
    }
    configRetryTimer = window.setTimeout(() => fetchAuthConfig(attempt + 1), CONFIG_RETRY_DELAY_MS);
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
    const response = await fetchWithTimeout(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: trimmedEmail, password: password.value }),
    }, 20_000);

    if (!response.ok) {
      if (response.status === 401 || response.status === 404) {
        throw new Error('Login / mot de passe introuvable en base.');
      }
      const payload = await response.json().catch(() => ({ detail: 'Connexion impossible.' }));
      throw new Error(payload.detail || 'Connexion impossible.');
    }

    const data = await response.json();
    email.value = '';
    password.value = '';
    await storeSession(data.token, data.provider, data.name, data.subject);
  } catch (err: any) {
    console.error(err);
    if (isBackendUnavailableError(err)) {
      error.value = backendUnavailableMessage;
      return;
    }
    error.value = err?.message || 'Connexion impossible.';
  } finally {
    emailLoginLoading.value = false;
  }
};

watch(googleClientId, () => {
  ensureGoogleButton();
  scheduleGoogleInitRetry();
});

onMounted(async () => {
  // En parallèle : la page ne doit jamais attendre la config pour s'afficher.
  fetchAuthConfig();

  try {
    // Retour de Twitch : ?code=...
    const twitchCode = route.query.code;
    if (typeof twitchCode === 'string' && twitchCode) {
      // Retirer le code de l'URL tout de suite : il n'est utilisable qu'une fois.
      const cleanQuery = { ...route.query };
      delete cleanQuery.code;
      delete cleanQuery.scope;
      await router.replace({ path: route.path, query: cleanQuery });

      ready.value = true;
      await handleTwitchCallback(twitchCode);
    }

    if (token.value) {
      const validation = await ensureValidStoredAdminSession();
      if (validation.status === 'valid') {
        await storeSession(
          validation.token,
          validation.profile.provider,
          validation.profile.name,
          validation.profile.subject,
        );
        return;
      }
      token.value = null;
      if (validation.status === 'error') {
        error.value = 'Impossible de vérifier la session administrateur.';
        console.warn('Erreur lors de la validation préalable de la session admin', validation.error);
      }
    }
  } finally {
    // Quoi qu'il arrive (erreur, navigation annulée…), la page sort de l'état
    // « Vérification… » : c'était la cause de la page bloquée.
    ready.value = true;
    ensureGoogleButton();
    scheduleGoogleInitRetry();
  }
});

onBeforeUnmount(() => {
  window.clearTimeout(configRetryTimer);
  if (googleInitTimer !== null) {
    window.clearInterval(googleInitTimer);
    googleInitTimer = null;
  }
});
</script>
