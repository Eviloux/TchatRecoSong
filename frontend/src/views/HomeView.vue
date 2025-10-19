<template>
  <section class="home-view">
    <header class="hero">
      <h2 class="hero-title">Dépose ta reco en quelques secondes</h2>
      <p class="hero-subtitle">Colle ton lien YouTube ou Spotify ci-dessous.</p>
    </header>

    <form class="submission-form" @submit.prevent="submit" novalidate>
      <label for="link">Lien YouTube ou Spotify</label>
      <input
        id="link"
        v-model="link"
        type="url"
        placeholder="https://www.youtube.com/watch?v=..."
        :disabled="loading || !backendReady"
        required
      />
      <button type="submit" :disabled="loading || !backendReady">
        {{ loading ? 'Envoi en cours…' : 'Envoyer ma recommandation' }}
      </button>
    </form>

    <p v-if="!backendReady" class="backend-status">{{ backendWaitMessage }}</p>

    <p v-if="feedback" class="feedback" :class="feedbackType">{{ feedback }}</p>

    <SongList ref="songListRef" allow-voting />
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import SongList from '../components/SongList.vue';
import { getApiUrl } from '../utils/api';

type SongListInstance = {
  refresh: () => Promise<void> | void;
};

const API_URL = getApiUrl();
const link = ref('');
const feedback = ref('');
const feedbackType = ref<'success' | 'error' | ''>('');
const loading = ref(false);
const backendReady = ref(true);
const songListRef = ref<SongListInstance | null>(null);
let availabilityTimer: ReturnType<typeof window.setInterval> | undefined;
const backendWaitMessage = 'Veuillez attendre que le backend soit démarré.';

const YOUTUBE_REGEX = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\//i;
const SPOTIFY_REGEX = /^(https?:\/\/)?(open\.)?spotify\.com\//i;

const markBackendUnavailable = () => {
  backendReady.value = false;
};

const checkBackendAvailability = async () => {
  if (!API_URL) {
    return;
  }

  try {
    const response = await fetch(`${API_URL}/health`, { method: 'GET', cache: 'no-store' });
    if (response.ok) {
      backendReady.value = true;
      if (feedbackType.value === 'error' && feedback.value === backendWaitMessage) {
        feedback.value = '';
        feedbackType.value = '';
      }
      return;
    }

    markBackendUnavailable();
  } catch (error) {
    console.error('Backend indisponible', error);
    markBackendUnavailable();
  }
};

onMounted(() => {
  if (!API_URL) {
    return;
  }

  markBackendUnavailable();
  checkBackendAvailability();
  availabilityTimer = window.setInterval(checkBackendAvailability, 5000);
});

onBeforeUnmount(() => {
  if (availabilityTimer) {
    window.clearInterval(availabilityTimer);
    availabilityTimer = undefined;
  }
});

const submit = async () => {
  if (!API_URL) {
    feedback.value = "VITE_API_URL n'est pas configuré.";
    feedbackType.value = 'error';
    return;
  }

  feedback.value = '';
  feedbackType.value = '';
  const trimmed = link.value.trim();

  if (!trimmed || (!YOUTUBE_REGEX.test(trimmed) && !SPOTIFY_REGEX.test(trimmed))) {
    feedback.value = 'Merci de coller un lien YouTube ou Spotify valide.';
    feedbackType.value = 'error';
    return;
  }

  if (!backendReady.value) {
    feedback.value = backendWaitMessage;
    feedbackType.value = 'error';
    return;
  }

  loading.value = true;
  try {
    const response = await fetch(`${API_URL}/public/submissions/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ link: trimmed }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: 'Erreur serveur.' }));
      throw new Error(payload.detail ?? "Impossible d'enregistrer la chanson.");
    }

    feedback.value = 'Merci ! Ta recommandation a été enregistrée.';
    feedbackType.value = 'success';
    link.value = '';

    if (songListRef.value) {
      await songListRef.value.refresh();
    }
  } catch (error: any) {
    console.error(error);
    if (error instanceof TypeError) {
      feedback.value = backendWaitMessage;
      markBackendUnavailable();
    } else {
      feedback.value = error.message ?? "Impossible d'enregistrer la chanson.";
    }
    feedbackType.value = 'error';
  } finally {
    loading.value = false;
  }
};
</script>
