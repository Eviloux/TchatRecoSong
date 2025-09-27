<template>
  <section class="song-list">
    <header class="song-list__header">
      <h2>Recommandations enregistrées</h2>
      <button type="button" @click="fetchSongs">Rafraîchir</button>
    </header>
    <ul v-if="songs.length" class="song-list__items">
      <li v-for="song in songs" :key="song.id" class="song-card">
        <div class="song-card__info">
          <h3>{{ song.title }}</h3>
          <p class="artist">{{ song.artist }}</p>
          <a :href="song.link" target="_blank" rel="noopener">Ouvrir le lien</a>
        </div>
        <span class="votes">{{ song.votes }} vote(s)</span>
      </li>
    </ul>
    <p v-else class="song-list__empty">Aucune recommandation pour le moment.</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

interface Song {
  id: number;
  title: string;
  artist: string;
  link: string;
  votes: number;
}

const API_URL = import.meta.env.VITE_API_URL;
const songs = ref<Song[]>([]);

const fetchSongs = async () => {
  if (!API_URL) return;
  try {
    const response = await fetch(`${API_URL}/songs/`);
    if (!response.ok) throw new Error('Erreur serveur');
    songs.value = await response.json();
  } catch (error) {
    console.error('Impossible de récupérer les chansons', error);
  }
};

onMounted(fetchSongs);

defineExpose({
  refresh: fetchSongs,
});
</script>
