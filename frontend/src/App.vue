<template>
  <div id="app">
    <header class="app-header">
      <h1 class="app-title">Tchat Reco Song</h1>
      <nav class="app-nav">
        <RouterLink to="/">Soumettre</RouterLink>
        <RouterLink to="/admin">Admin</RouterLink>
        <RouterLink to="/login">Connexion</RouterLink>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
</script>
