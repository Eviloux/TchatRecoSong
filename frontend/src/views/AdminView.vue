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
import { useRoute, useRouter } from 'vue-router';
import SongList from '../components/SongList.vue';
import AdminPanel from '../components/AdminPanel.vue';
import { exchangeAdminAuth, fetchAuthConfigFromApi } from '../services/adminAuth';
import {
  AdminProfile,
  clearAdminSession,
  loadAdminSession,
  saveAdminSession,
} from '../utils/adminSession';

type SongListHandle = {
  refresh: () => Promise<void> | void;
};

declare global {
  interface Window {
    google?: any;
  }
}

const router = useRouter();
const route = useRoute();

const googleClientId = ref<string | null>(import.meta.env.VITE_GOOGLE_CLIENT_ID || null);
const twitchClientId = ref<string | null>(import.meta.env.VITE_TWITCH_CLIENT_ID || null);

const normalizeRedirectUri = (raw?: string | null) => {
  const fallback = `${window.location.origin}/admin`;
  if (!raw) {
    return fallback;
  }

  try {
    return new URL(raw, window.location.origin).toString();
  } catch (err) {
    console.warn('URI de redirection Twitch invalide, utilisation du fallback.', err);
    return fallback;
  }
};

const resolvedTwitchRedirectUri = ref<string>(
  normalizeRedirectUri(import.meta.env.VITE_TWITCH_REDIRECT_URI),
);

const existingSession = loadAdminSession();
const token = ref<string | null>(existingSession?.token ?? null);
const profile = ref<AdminProfile | null>(existingSession?.profile ?? null);
const error = ref('');
const songListRef = ref<SongListHandle | null>(null);

let googleInitTimer: number | null = null;
let twitchFragmentProcessing = false;

const storeSession = (authToken: string, provider: string, name: string) => {
  const session = saveAdminSession(authToken, provider, name);
  token.value = session.token;
  profile.value = session.profile;
};

const logout = () => {
  token.value = null;
  profile.value = null;
  clearAdminSession();
};

const handleBanRuleCreated = async () => {
  if (songListRef.value) {
    await songListRef.value.refresh();
  }
};

const callAuthEndpoint = async (endpoint: 'google' | 'twitch', payload: Record<string, string>) => {
  try {
    error.value = '';
    const data = await exchangeAdminAuth(endpoint, payload);
    storeSession(data.token, data.provider, data.name);
  } catch (err: any) {
    console.error(err);
    error.value = err?.message || 'Connexion impossible.';
  }
};

const handleGoogleCredential = async (response: any) => {
  error.value = '';
  await callAuthEndpoint('google', { credential: response.credential });
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

const normalizeAdminUrl = () => {
  const resolved = router.resolve({ name: 'admin' });
  return new URL(resolved.href, window.location.origin).toString();
};

const cleanupTwitchFragment = () => {
  const absoluteAdmin = normalizeAdminUrl();
  window.history.replaceState({}, document.title, absoluteAdmin);
  if (route.name !== 'admin' || route.hash) {
    router.replace({ name: 'admin', hash: undefined }).catch(() => {
      // Ignorer les échecs de navigation redondants
    });
  }
};

const handleTwitchFragment = async (hash?: string | null): Promise<boolean> => {
  if (twitchFragmentProcessing) {
    return false;
  }

  const rawHash = typeof hash === 'string' && hash.length > 0 ? hash : window.location.hash;
  if (!rawHash) {
    return false;
  }

  const trimmed = rawHash.startsWith('#') ? rawHash.slice(1) : rawHash;
  if (!trimmed) {
    return false;
  }

  const params = new URLSearchParams(trimmed);
  const hasRelevantParams =
    params.has('access_token') || params.has('error') || params.has('error_description');

  if (!hasRelevantParams) {
    return false;
  }

  twitchFragmentProcessing = true;
  cleanupTwitchFragment();

  try {
    const errorParam = params.get('error');
    const errorDescription = params.get('error_description');
    const accessToken = params.get('access_token');

    if (errorParam) {
      error.value = errorDescription || errorParam;
      return true;
    }

    if (!accessToken) {
      return true;
    }

    await callAuthEndpoint('twitch', { access_token: accessToken });
    return true;
  } finally {
    twitchFragmentProcessing = false;
  }
};

const loginWithTwitch = () => {
  error.value = '';
  if (!twitchClientId.value) {
    error.value = 'TWITCH_CLIENT_ID manquant.';
    return;
  }

  const redirectUri = resolvedTwitchRedirectUri.value;
  const authorizeUrl = new URL('https://id.twitch.tv/oauth2/authorize');
  authorizeUrl.searchParams.set('client_id', twitchClientId.value);
  authorizeUrl.searchParams.set('redirect_uri', redirectUri);
  authorizeUrl.searchParams.set('response_type', 'token');
  authorizeUrl.searchParams.set('scope', 'user:read:email');
  window.location.href = authorizeUrl.toString();
};

const fetchAuthConfig = async () => {
  const data = await fetchAuthConfigFromApi();
  if (!data) {
    return;
  }

  if (data.google_client_id) {
    googleClientId.value = data.google_client_id;
  }

  if (data.twitch_client_id) {
    twitchClientId.value = data.twitch_client_id;
  }

  if (data.twitch_redirect_uri) {
    resolvedTwitchRedirectUri.value = normalizeRedirectUri(data.twitch_redirect_uri);
  }
};

watch(googleClientId, () => {
  ensureGoogleButton();
  scheduleGoogleInitRetry();
});

watch(
  () => token.value,
  async (newToken) => {
    if (newToken === null) {
      await nextTick();
      ensureGoogleButton();
      scheduleGoogleInitRetry();
    }
  }
);

watch(
  () => route.hash,
  (newHash) => {
    void handleTwitchFragment(newHash);
  }
);

onMounted(async () => {
  const twitchHandled = await handleTwitchFragment(route.hash);

  scheduleGoogleInitRetry();
  await fetchAuthConfig();
  ensureGoogleButton();

  if (twitchHandled && token.value) {
    // refresh the admin list when a Twitch login has just been processed
    if (songListRef.value) {
      void songListRef.value.refresh();
    }
  }
});

onBeforeUnmount(() => {
  if (googleInitTimer !== null) {
    window.clearInterval(googleInitTimer);
    googleInitTimer = null;
  }
});
</script>
