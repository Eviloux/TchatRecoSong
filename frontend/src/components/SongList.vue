<template>
  <div class="song-list">
    <div v-for="song in songs" :key="song.id" class="song-card">
      <p class="song-title">{{ song.title }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface Song {
  id: number;
  title: string;
}

const songs = ref<Song[]>([]);

const fetchSongs = async () => {
  try {
    const res = await fetch(import.meta.env.VITE_API_URL + '/songs/');
    if (!res.ok) throw new Error('Fetch failed');
    songs.value = await res.json();
  } catch (err) {
    console.error(err);
  }
};

onMounted(fetchSongs);
</script>
