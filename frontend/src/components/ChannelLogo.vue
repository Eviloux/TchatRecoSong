<template>
  <span class="channel-logo" :style="{ '--logo-size': `${size}px` }">
    <img v-if="!failed" :src="branding.logoUrl" :alt="`Logo de ${branding.channelName}`" @error="failed = true" />
    <span v-else class="channel-logo__fallback" aria-hidden="true">{{ branding.initials }}</span>
  </span>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { branding } from '../branding';

withDefaults(defineProps<{ size?: number }>(), { size: 48 });

// Tant que le logo n'est pas déposé, on affiche les initiales plutôt qu'une image cassée.
const failed = ref(false);
</script>
