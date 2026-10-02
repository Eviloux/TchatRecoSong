<template>
  <div id="app">
    <header class="app-header">
      <RouterLink to="/" class="app-title">
        <span class="app-title__note" aria-hidden="true">♪</span>
        {{ branding.siteName }}
      </RouterLink>
      <div class="app-header__right">
        <nav class="app-nav" aria-label="Navigation principale">
          <RouterLink v-for="link in navLinks" :key="link.to" :to="link.to">
            {{ link.label }}
          </RouterLink>
        </nav>
        <ThemeToggle />
      </div>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
import ThemeToggle from './components/ThemeToggle.vue';
import { branding } from './branding';

const navLinks = [
  { to: '/', label: 'Proposer' },
  { to: '/admin', label: 'Admin' },
];
</script>
