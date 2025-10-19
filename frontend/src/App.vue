<template>
  <div id="app">
    <header class="app-header">
      <h1 class="app-title">Tchat Reco Song</h1>
      <nav class="app-nav">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
        >
          {{ link.label }}
        </RouterLink>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';

const navLinks = [
  { to: '/', label: 'Soumettre' },
  { to: '/admin', label: 'Admin' },
];
</script>
