<template>
  <section class="home-view">
    <h2>Soumettre une recommandation</h2>
    <p class="home-description">
      Tapez <strong>!reco</strong> dans le tchat Twitch. Un ticket temporaire apparaît
      ici avec un lien direct vers le formulaire de soumission.
    </p>

    <div class="active-requests" v-if="requests.length">
      <article v-for="request in requests" :key="request.token" class="request-card">
        <header>
          <h3>Ticket pour {{ request.twitch_user }}</h3>
          <span class="expires">Expire le {{ formatDate(request.expires_at) }}</span>
        </header>
        <p v-if="request.comment" class="comment">“{{ request.comment }}”</p>
        <div class="actions">
          <RouterLink class="cta" :to="{ name: 'submit', params: { token: request.token } }">
            Ouvrir le formulaire
          </RouterLink>
          <button type="button" @click="copyLink(request.token)">Copier le lien</button>
        </div>
      </article>
    </div>
    <p v-else class="empty-state">Aucun ticket actif pour le moment.</p>

    <form class="manual-form" @submit.prevent="goToToken">
      <label for="token-input">Vous avez déjà un token ?</label>
      <div class="manual-inputs">
        <input
          id="token-input"
          v-model="manualToken"
          type="text"
          placeholder="Collez le token reçu"
          required
        />
        <button type="submit">Continuer</button>
      </div>
    </form>

    <p v-if="feedback" class="feedback" :class="{ error: feedbackType === 'error', success: feedbackType === 'success' }">
      {{ feedback }}
    </p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useRouter, RouterLink } from 'vue-router';

interface SubmissionRequest {
  token: string;
  twitch_user: string;
  comment?: string | null;
  expires_at: string;
}

const router = useRouter();
const manualToken = ref('');
const requests = ref<SubmissionRequest[]>([]);
const feedback = ref('');
const feedbackType = ref<'error' | 'success' | null>(null);
let pollingHandle: number | undefined;

const API_URL = import.meta.env.VITE_API_URL;

const fetchRequests = async () => {
  if (!API_URL) {
    feedback.value = "VITE_API_URL n'est pas configuré.";
    feedbackType.value = 'error';
    return;
  }
  try {
    const response = await fetch(`${API_URL}/requests/active`);
    if (!response.ok) throw new Error('Erreur serveur');
    const data = await response.json();
    requests.value = data;
  } catch (error) {
    console.error(error);
    feedback.value = 'Impossible de récupérer les tickets actifs.';
    feedbackType.value = 'error';
  }
};

const goToToken = () => {
  if (!manualToken.value) return;
  router.push({ name: 'submit', params: { token: manualToken.value.trim() } });
};

const copyLink = async (token: string) => {
  try {
    await navigator.clipboard.writeText(`${window.location.origin}/submit/${token}`);
    feedback.value = 'Lien copié dans le presse-papiers !';
    feedbackType.value = 'success';
  } catch (error) {
    console.error(error);
    feedback.value = 'Impossible de copier le lien sur cet appareil.';
    feedbackType.value = 'error';
  }
};

const formatDate = (input: string) => {
  return new Date(input).toLocaleTimeString();
};

onMounted(() => {
  fetchRequests();
  pollingHandle = window.setInterval(fetchRequests, 10000);
});

onUnmounted(() => {
  if (pollingHandle) window.clearInterval(pollingHandle);
});
</script>
