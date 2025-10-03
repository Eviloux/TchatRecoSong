<template>
  <section class="twitch-callback">
    <p v-if="status === 'loading'">Connexion à Twitch…</p>
    <p v-else-if="status === 'success'">Connexion réussie, redirection en cours…</p>
    <p v-else class="error">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { exchangeAdminAuth } from '../services/adminAuth';
import { saveAdminSession } from '../utils/adminSession';

type Status = 'loading' | 'success' | 'error';

const status = ref<Status>('loading');
const error = ref('');
const router = useRouter();

const parseAccessToken = (): string | null => {
  if (!window.location.hash) {
    return null;
  }
  const params = new URLSearchParams(window.location.hash.replace('#', ''));
  return params.get('access_token');
};

onMounted(async () => {
  const accessToken = parseAccessToken();
  if (!accessToken) {
    status.value = 'error';
    error.value = 'Authentification Twitch annulée ou invalide.';
    return;
  }

  try {
    const data = await exchangeAdminAuth('twitch', { access_token: accessToken });
    saveAdminSession(data.token, data.provider, data.name);
    status.value = 'success';
    await router.replace({ name: 'admin' });
  } catch (err: any) {
    console.error(err);
    status.value = 'error';
    error.value = err?.message || 'Connexion impossible.';
  } finally {
    window.history.replaceState({}, document.title, window.location.pathname);
  }
});
</script>

<style scoped>
.twitch-callback {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 0.75rem;
  text-align: center;
}

.error {
  color: #ff5a5f;
  font-weight: 600;
}
</style>
