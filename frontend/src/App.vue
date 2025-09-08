<template>
  <div id="app">
    <h1>Twitch Song Recommender</h1>
    <SongList />
    <AdminPanel />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import SongList from './components/SongList.vue'
import AdminPanel from './components/AdminPanel.vue'

export default defineComponent({
  name: 'App',
  components: {
    SongList,
    AdminPanel
  }
})
</script>
