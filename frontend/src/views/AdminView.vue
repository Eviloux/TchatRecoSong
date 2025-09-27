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
      <p class="login-hint">Configurez les variables <code>VITE_GOOGLE_CLIENT_ID</code> et <code>VITE_TWITCH_CLIENT_ID</code>.</p>
    </div>

    <div v-else class="admin-content">
      <button type="button" class="logout" @click="logout">Se déconnecter</button>

      <section class="request-creator">
        <h3>Créer un ticket de soumission</h3>
        <form @submit.prevent="createRequest">
          <div class="field">
            <label for="twitch-user">Utilisateur Twitch</label>
            <input id="twitch-user" v-model="requestForm.twitch_user" required />
          </div>
          <div class="field">
            <label for="comment">Commentaire (optionnel)</label>
            <input id="comment" v-model="requestForm.comment" placeholder="Précision pour le viewer" />
          </div>
          <button type="submit">Générer le ticket</button>
        </form>
        <p v-if="requestFeedback" class="feedback">{{ requestFeedback }}</p>
      </section>

      <section class="active-requests" v-if="activeRequests.length">
        <h3>Tickets actifs</h3>
        <ul>
          <li v-for="request in activeRequests" :key="request.token">
            <span>{{ request.twitch_user }} · expire le {{ formatDate(request.expires_at) }}</span>
            <a :href="`${windowLocation}/submit/${request.token}`" target="_blank" rel="noopener">Ouvrir</a>
          </li>
        </ul>
      </section>

      <SongList />
      <AdminPanel :token="token" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import SongList from '../components/SongList.vue';
import AdminPanel from '../components/AdminPanel.vue';

interface SubmissionRequest {
  token: string;
  twitch_user: string;
  expires_at: string;
}

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
const requestForm = ref({ twitch_user: '', comment: '' });
const requestFeedback = ref('');
const activeRequests = ref<SubmissionRequest[]>([]);
const windowLocation = window.location.origin;

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
    await fetchActiveRequests();
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

const fetchActiveRequests = async () => {
  if (!API_URL) return;
  try {
    const response = await fetch(`${API_URL}/requests/active`);
    if (!response.ok) throw new Error('Erreur serveur');
    activeRequests.value = await response.json();
  } catch (err) {
    console.error(err);
  }
};

const formatDate = (input: string) => new Date(input).toLocaleTimeString();

const createRequest = async () => {
  if (!token.value || !API_URL) return;
  try {
    requestFeedback.value = '';
    const payload = {
      twitch_user: requestForm.value.twitch_user.trim(),
      comment: requestForm.value.comment?.trim() || undefined,
    };
    const response = await fetch(`${API_URL}/requests/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token.value}`,
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: 'Erreur inconnue.' }));
      throw new Error(data.detail);
    }
    const data = await response.json();
    requestFeedback.value = `Ticket ${data.token} créé. Partagez ${windowLocation}/submit/${data.token}`;
    requestForm.value.twitch_user = '';
    requestForm.value.comment = '';
    await fetchActiveRequests();
  } catch (err: any) {
    console.error(err);
    requestFeedback.value = err.message || 'Impossible de créer le ticket.';
  }
};

onMounted(async () => {
  initGoogle();
  await checkTwitchRedirect();
  await fetchActiveRequests();
});
</script>
