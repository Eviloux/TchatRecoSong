<template>
  <section class="twitch-callback">
    <h2>Connexion Twitch</h2>
    <p>Vous pouvez fermer cette fenêtre.</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';

const RESULT_STORAGE_KEY = 'twitch_oauth_result';

interface TwitchResult {
  type: 'twitch-auth-success' | 'twitch-auth-error';
  accessToken?: string;
  state?: string | null;
  error?: string;
}

const sendResultToOpener = (payload: TwitchResult) => {
  try {
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(payload, window.location.origin);
      return true;
    }
  } catch (err) {
    console.error("Impossible d'envoyer le résultat Twitch à la fenêtre parente", err);
  }
  return false;
};

const storeResultFallback = (payload: TwitchResult) => {
  try {
    localStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(payload));
  } catch (err) {
    console.error('Impossible de stocker le résultat Twitch', err);
  }
};

const extractHashParams = () => {
  const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash;
  return new URLSearchParams(hash);
};

onMounted(() => {
  try {
    const params = extractHashParams();
    const accessToken = params.get('access_token') || undefined;
    const state = params.get('state');
    const errorDescription = params.get('error_description') || params.get('error') || undefined;

    if (accessToken) {
      const payload: TwitchResult = {
        type: 'twitch-auth-success',
        accessToken,
        state,
      };
      if (!sendResultToOpener(payload)) {
        storeResultFallback(payload);
        window.location.replace('/admin');
      }
    } else {
      const payload: TwitchResult = {
        type: 'twitch-auth-error',
        state,
        error: errorDescription || "Impossible de finaliser l'authentification Twitch.",
      };
      if (!sendResultToOpener(payload)) {
        storeResultFallback(payload);
        window.location.replace('/admin');
      }
    }
  } catch (err) {
    console.error('Erreur inattendue lors du traitement du callback Twitch', err);
    const payload: TwitchResult = {
      type: 'twitch-auth-error',
      error: 'Erreur inattendue lors du traitement de la réponse Twitch.',
    };
    if (!sendResultToOpener(payload)) {
      storeResultFallback(payload);
      window.location.replace('/admin');
    }
  } finally {
    setTimeout(() => {
      try {
        window.close();
      } catch (err) {
        console.error('Impossible de fermer la fenêtre Twitch', err);
      }
    }, 100);
  }
});
</script>

<style scoped>
.twitch-callback {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  text-align: center;
  padding: 2rem;
}

.twitch-callback h2 {
  font-size: 1.5rem;
  font-weight: 600;
}

.twitch-callback p {
  color: #555;
}
</style>
