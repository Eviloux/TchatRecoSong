<template>
  <div class="song-list">
    <div v-if="songs.length === 0" class="empty-message">
      Aucune chanson suggérée pour le moment.
    </div>

    <div v-else class="songs-grid">
      <div v-for="song in songs" :key="song.id" class="song-card">
        <img :src="song.thumbnail" :alt="song.title" class="song-thumbnail" />
        <div class="song-info">
          <h3>{{ song.title }}</h3>
          <p>{{ song.artist }}</p>
          <p>Suggestions: {{ song.counter }}</p>
          <a :href="song.url" target="_blank" rel="noopener noreferrer">Écouter</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue'

export default defineComponent({
  name: 'SongList',
  setup() {
    const songs = ref<Array<any>>([])

    const fetchSongs = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/songs/`)
        songs.value = await res.json()
      } catch (err) {
        console.error('Erreur lors de la récupération des chansons:', err)
      }
    }

    onMounted(fetchSongs)

    return { songs }
  }
})
</script>
