<template>
  <a
    class="live-badge"
    :class="`live-badge--${state}`"
    :href="branding.channelUrl"
    target="_blank"
    rel="noopener noreferrer"
    :title="state === 'live' && streamTitle ? streamTitle : undefined"
  >
    <span v-if="state !== 'unknown'" class="live-badge__dot" aria-hidden="true"></span>
    {{ label }}
  </a>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { branding } from '../branding';
import { getApiUrl } from '../utils/api';

type LiveState = 'live' | 'offline' | 'unknown';

// Le backend met le statut en cache 60 s : inutile d'interroger plus souvent.
const REFRESH_INTERVAL_MS = 120_000;

const state = ref<LiveState>('unknown');
const streamTitle = ref<string | null>(null);
let timer: number | undefined;

const label = computed(() => {
  if (state.value === 'live') return 'En live';
  if (state.value === 'offline') return 'Hors ligne';
  return 'Chaîne Twitch';
});

const refresh = async () => {
  try {
    const response = await fetch(`${getApiUrl()}/twitch/live`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Statut ${response.status}`);
    const data: { live: boolean | null; title: string | null } = await response.json();
    state.value = data.live === null ? 'unknown' : data.live ? 'live' : 'offline';
    streamTitle.value = data.title;
  } catch {
    // Backend endormi ou Twitch injoignable : simple lien vers la chaîne.
    state.value = 'unknown';
  }
};

onMounted(() => {
  refresh();
  timer = window.setInterval(refresh, REFRESH_INTERVAL_MS);
});

onBeforeUnmount(() => window.clearInterval(timer));
</script>
