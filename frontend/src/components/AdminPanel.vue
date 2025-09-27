<template>
  <section class="admin-panel">
    <h2>Gestion des ban words</h2>
    <p v-if="!token" class="warning">
      Connectez-vous pour ajouter des règles de bannissement.
    </p>

    <ul v-if="banRules.length" class="ban-list">
      <li v-for="rule in banRules" :key="rule.id">
        <strong v-if="rule.title">Titre :</strong> {{ rule.title || '—' }} ·
        <strong v-if="rule.artist">Artiste :</strong> {{ rule.artist || '—' }} ·
        <strong v-if="rule.link">Lien :</strong> {{ rule.link || '—' }}
      </li>
    </ul>
    <p v-else class="ban-empty">Aucune règle enregistrée pour le moment.</p>

    <form v-if="token" class="ban-form" @submit.prevent="submit">
      <div class="field">
        <label for="ban-title">Titre</label>
        <input id="ban-title" v-model="form.title" placeholder="Titre exact" />
      </div>
      <div class="field">
        <label for="ban-artist">Artiste</label>
        <input id="ban-artist" v-model="form.artist" placeholder="Artiste exact" />
      </div>
      <div class="field">
        <label for="ban-link">Lien</label>
        <input id="ban-link" v-model="form.link" placeholder="https://..." />
      </div>
      <button type="submit">Ajouter une règle</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { onMounted, watch, reactive, ref } from 'vue';

interface BanRule {
  id: number;
  title?: string | null;
  artist?: string | null;
  link?: string | null;
}

const props = defineProps<{ token: string | null }>();
const API_URL = import.meta.env.VITE_API_URL;
const banRules = ref<BanRule[]>([]);
const form = reactive({ title: '', artist: '', link: '' });

const fetchBanRules = async () => {
  if (!API_URL) return;
  try {
    const response = await fetch(`${API_URL}/ban/`);
    if (!response.ok) throw new Error('Erreur serveur');
    banRules.value = await response.json();
  } catch (error) {
    console.error('Impossible de récupérer les ban rules', error);
  }
};

const submit = async () => {
  if (!props.token || !API_URL) return;
  try {
    const response = await fetch(`${API_URL}/ban/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${props.token}`,
      },
      body: JSON.stringify({ ...form }),
    });
    if (!response.ok) throw new Error('Erreur lors de la création.');
    form.title = '';
    form.artist = '';
    form.link = '';
    await fetchBanRules();
  } catch (error) {
    console.error(error);
  }
};

onMounted(fetchBanRules);
watch(
  () => props.token,
  () => {
    fetchBanRules();
  }
);
</script>
