<template>
  <div class="songlist-container">
    <h2>Liste des chansons</h2>
    <ul>
      <li v-for="song in songs" :key="song.id">
        <img :src="song.thumbnail" alt="" width="50" />
        {{ song.title }} - {{ song.artist }} ({{ song.votes }} votes)
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import '../assets/styles/songlist.scss'

interface Song {
  id: number
  title: string
  artist: string
  link: string
  thumbnail?: string
  votes: number
}

const API_URL = import.meta.env.VITE_API_URL
const songs = ref<Song[]>([])

async function fetchSongs() {
  const res = await fetch(`${API_URL}/songs/`)
  songs.value = await res.json()
}

onMounted(fetchSongs)
</script>
