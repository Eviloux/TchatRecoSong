<template>
  <section class="submission-view">
    <header>
      <h2>Formulaire de recommandation</h2>
      <p v-if="request">Ticket réservé pour <strong>{{ request.twitch_user }}</strong>.</p>
    </header>

    <p v-if="loading">Chargement du ticket en cours…</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <form v-if="!loading && request && !success" @submit.prevent="submit">
      <label for="link">Lien YouTube ou Spotify</label>
      <input
        id="link"
        v-model="link"
        type="url"
        placeholder="https://www.youtube.com/..."
        required
      />
      <button type="submit">Envoyer</button>
    </form>

    <p v-if="success" class="success">Merci ! Ta recommandation a bien été enregistrée.</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const token = route.params.token as string;

interface SubmissionRequest {
  token: string;
  twitch_user: string;
  comment?: string | null;
}

const API_URL = import.meta.env.VITE_API_URL;
const loading = ref(true);
const error = ref('');
const success = ref(false);
const request = ref<SubmissionRequest | null>(null);
const link = ref('');

const YOUTUBE_REGEX = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\//i;
const SPOTIFY_REGEX = /^(https?:\/\/)?(open\.)?spotify\.com\//i;

const fetchRequest = async () => {
  if (!API_URL) {
    error.value = "VITE_API_URL n'est pas configuré.";
    loading.value = false;
    return;
  }
  try {
    const response = await fetch(`${API_URL}/requests/${token}`);
    if (!response.ok) throw new Error('Ticket expiré ou introuvable.');
    request.value = await response.json();
  } catch (err) {
    console.error(err);
    error.value = 'Ticket expiré ou introuvable.';
  } finally {
    loading.value = false;
  }
};

const submit = async () => {
  if (!API_URL) return;
  if (!YOUTUBE_REGEX.test(link.value) && !SPOTIFY_REGEX.test(link.value)) {
    error.value = 'Seuls les liens YouTube ou Spotify sont acceptés.';
    return;
  }

  try {
    const response = await fetch(`${API_URL}/requests/${token}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ link: link.value.trim() }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: 'Erreur inconnue.' }));
      throw new Error(payload.detail ?? 'Erreur serveur');
    }
    success.value = true;
  } catch (err: any) {
    console.error(err);
    error.value = err.message ?? "Impossible d'envoyer la recommandation.";
  }
};

onMounted(fetchRequest);
</script>
