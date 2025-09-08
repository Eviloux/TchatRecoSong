<template>
  <div class="app-container">
    <h1>Twitch Song Recommender</h1>
    <SongList />
    <AdminPanel />
  </div>
</template>

<script setup lang="ts">
import SongList from './components/SongList.vue'
import AdminPanel from './components/AdminPanel.vue'
import './assets/styles/app.scss'
</script>
