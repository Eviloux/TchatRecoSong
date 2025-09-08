<template>
  <div class="adminpanel-container">
    <h2>Administration : Règles de ban</h2>
    <form @submit.prevent="submit">
      <input v-model="title" placeholder="Titre (optionnel)" />
      <input v-model="artist" placeholder="Artiste (optionnel)" />
      <input v-model="link" placeholder="Lien (optionnel)" />
      <button type="submit">Ajouter règle</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import '../assets/styles/adminpanel.scss'

const API_URL = import.meta.env.VITE_API_URL
const title = ref('')
const artist = ref('')
const link = ref('')

async function submit() {
  await fetch(`${API_URL}/ban/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: title.value || null,
      artist: artist.value || null,
      link: link.value || null
    })
  })
  title.value = ''
  artist.value = ''
  link.value = ''
}
</script>
