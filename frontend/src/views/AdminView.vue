<template>
  <section class="admin-view">
    <header>
      <h2>Espace administrateur</h2>
      <p v-if="profile">Connecté en tant que {{ profile.name }} ({{ profile.provider }})</p>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <p v-if="loading" class="loading">Vérification de la session en cours…</p>

    <div v-else-if="token" class="admin-content">
      <button type="button" class="logout" @click="logout">Se déconnecter</button>
      <SongList ref="songListRef" :token="token" />

      <AdminPanel :token="token" @ban-rules-changed="handleBanRuleCreated" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import SongList from '../components/SongList.vue';
import AdminPanel from '../components/AdminPanel.vue';
import {
  clearAdminSession,
  ensureValidStoredAdminSession,
  loadStoredAdminSession,
  type AdminProfile,
} from '../utils/adminSession';

type SongListHandle = {
  refresh: () => Promise<void> | void;
};

const storedSession = loadStoredAdminSession();
const token = ref<string | null>(storedSession.token);
const profile = ref<AdminProfile | null>(storedSession.profile);
const error = ref('');
const songListRef = ref<SongListHandle | null>(null);
const loading = ref(true);
const router = useRouter();

const logout = () => {
  token.value = null;
  profile.value = null;
  clearAdminSession();
  router.replace({ name: 'login' });
};

const handleBanRuleCreated = async () => {
  if (songListRef.value) {
    await songListRef.value.refresh();
  }
};

const refreshStoredSession = async () => {
  const result = await ensureValidStoredAdminSession({ force: true });
  if (result.status === 'valid') {
    token.value = result.token;
    profile.value = result.profile;
    error.value = '';
    return;
  }

  if (result.status === 'invalid') {
    logout();
    return;
  }

  error.value = 'Impossible de vérifier la session administrateur.';
  console.warn('Erreur lors de la vérification de la session admin', result.error);
  if (!token.value) {
    router.replace({ name: 'login' });
  }
};
onMounted(async () => {
  await refreshStoredSession();
  loading.value = false;
});
</script>
