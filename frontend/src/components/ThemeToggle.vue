<template>
  <button
    type="button"
    class="theme-toggle"
    :class="{ 'is-light': isLight }"
    role="switch"
    :aria-checked="isLight"
    :aria-label="label"
    :title="label"
    @click="toggleTheme"
  >
    <span class="theme-toggle__icons" aria-hidden="true"><span>☾</span><span>☀</span></span>
    <span class="theme-toggle__knob" aria-hidden="true">{{ isLight ? '☀' : '☾' }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTheme } from '../utils/theme';

const { theme, toggleTheme } = useTheme();
const isLight = computed(() => theme.value === 'light');
const label = computed(() => (isLight.value ? 'Activer le thème sombre' : 'Activer le thème clair'));
</script>
