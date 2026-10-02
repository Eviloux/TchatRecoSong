<template>
  <section class="home-view">
    <header class="banner">
      <ChannelLogo :size="104" class="banner__logo" />
      <div class="banner__text">
        <LiveBadge class="banner__live" />
        <h1 class="banner__title">Fais découvrir ta chanson préférée à Océane</h1>
        <p class="banner__subtitle">Colle un lien YouTube ou Spotify. Les plus votées passent en premier pendant le stream.</p>
      </div>
    </header>

    <form class="composer" @submit.prevent="submit" novalidate>
      <div class="field">
        <label for="link">Lien YouTube ou Spotify</label>
        <input
          id="link"
          v-model="link"
          type="url"
          maxlength="2000"
          placeholder="https://youtu.be/..."
          :disabled="loading || !backendReady"
          required
        />
      </div>
      <div class="field">
        <label for="comment">Un petit mot <span class="optional">(optionnel)</span></label>
        <input
          id="comment"
          v-model="comment"
          type="text"
          maxlength="1000"
          placeholder="Pour la session piano…"
          :disabled="loading || !backendReady"
        />
      </div>
      <button type="submit" class="btn" :disabled="loading || !backendReady">
        {{ loading ? 'Envoi…' : 'Envoyer ♪' }}
      </button>
    </form>

    <p v-if="!backendReady" class="notice" role="status">{{ backendWaitMessage }}</p>
    <p v-if="feedback" class="notice" :class="`notice--${feedbackType}`" role="status">{{ feedback }}</p>

    <SongList ref="songListRef" allow-voting />
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import ChannelLogo from '../components/ChannelLogo.vue';
import LiveBadge from '../components/LiveBadge.vue';
import SongList from '../components/SongList.vue';
import { getApiUrl } from '../utils/api';

type SongListInstance = {
  refresh: () => Promise<void> | void;
};

const API_URL = getApiUrl();
const link = ref('');
const comment = ref('');
const feedback = ref('');
const feedbackType = ref<'success' | 'error' | ''>('');
const loading = ref(false);
const backendReady = ref(true);
const songListRef = ref<SongListInstance | null>(null);
let availabilityTimer: ReturnType<typeof window.setInterval> | undefined;
const backendWaitMessage = 'Le serveur se réveille, encore quelques secondes…';

const YOUTUBE_REGEX = /^(https?:\/\/)?((www|m)\.)?(youtube\.com|youtu\.be)\//i;
const SPOTIFY_REGEX = /^(https?:\/\/)?(open\.)?spotify\.com\//i;

const HEALTH_POLL_INTERVAL_MS = 5000;
const HEALTH_TIMEOUT_MS = 8000;
let healthCheckInFlight = false;

const stopAvailabilityPolling = () => {
  if (availabilityTimer) {
    window.clearInterval(availabilityTimer);
    availabilityTimer = undefined;
  }
};

const checkBackendAvailability = async () => {
  // Évite d'empiler les requêtes pendant le réveil (lent) du backend Render.
  if (!API_URL || healthCheckInFlight) {
    return;
  }

  healthCheckInFlight = true;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_URL}/health`, {
      method: 'GET',
      cache: 'no-store',
      signal: controller.signal,
    });
    if (response.ok) {
      const wasUnavailable = !backendReady.value;
      backendReady.value = true;
      stopAvailabilityPolling();
      if (feedbackType.value === 'error' && feedback.value === backendWaitMessage) {
        feedback.value = '';
        feedbackType.value = '';
      }
      // La liste a pu être chargée (en vain) pendant que le backend dormait.
      if (wasUnavailable && songListRef.value) {
        await songListRef.value.refresh();
      }
      return;
    }

    backendReady.value = false;
  } catch (error) {
    console.warn('Backend injoignable, nouvelle tentative dans quelques secondes.', error);
    backendReady.value = false;
  } finally {
    window.clearTimeout(timeout);
    healthCheckInFlight = false;
  }
};

const startAvailabilityPolling = () => {
  if (!API_URL || availabilityTimer) {
    return;
  }
  backendReady.value = false;
  checkBackendAvailability();
  availabilityTimer = window.setInterval(checkBackendAvailability, HEALTH_POLL_INTERVAL_MS);
};

onMounted(startAvailabilityPolling);

onBeforeUnmount(stopAvailabilityPolling);

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
      body: JSON.stringify({ link: trimmed, comment: comment.value.trim() || null }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: 'Erreur serveur.' }));
      throw new Error(payload.detail ?? "Impossible d'enregistrer la chanson.");
    }

    feedback.value = 'Merci ! Ta reco est dans la liste ♡';
    feedbackType.value = 'success';
    link.value = '';
    comment.value = '';

    if (songListRef.value) {
      await songListRef.value.refresh();
    }
  } catch (error: any) {
    console.error(error);
    if (error instanceof TypeError) {
      // Erreur réseau : on revérifie la disponibilité au lieu de bloquer le formulaire.
      feedback.value = backendWaitMessage;
      startAvailabilityPolling();
    } else {
      feedback.value = error.message ?? "Impossible d'enregistrer la chanson.";
    }
    feedbackType.value = 'error';
  } finally {
    loading.value = false;
  }
};
</script>
