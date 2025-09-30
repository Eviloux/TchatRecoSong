<template>
  <section class="song-list">
    <header class="song-list__header">
      <h2>Recommandations enregistrées</h2>
      <button type="button" @click="fetchSongs">Rafraîchir</button>
    </header>
    <ul v-if="songs.length" class="song-list__items">
      <li v-for="song in songs" :key="song.id" class="song-card">
        <div class="song-card__info">
          <h3>{{ song.title }}</h3>
          <p class="artist">{{ song.artist }}</p>
          <a :href="song.link" target="_blank" rel="noopener">Ouvrir le lien</a>
        </div>
        <div class="song-card__actions">
          <span class="votes">{{ song.votes }} vote(s)</span>
          <button
            v-if="isVotingEnabled"
            type="button"
            class="vote-button"
            :disabled="hasVoted(song.id) || voting === song.id"
            @click="vote(song.id)"
          >
            {{ hasVoted(song.id) ? 'Vote enregistré' : 'Voter' }}
          </button>
          <button
            v-if="isAdmin"
            type="button"
            class="delete-button"
            :disabled="deleting === song.id"
            @click="remove(song.id)"
          >
            Supprimer
          </button>
        </div>
      </li>
    </ul>
    <p v-else class="song-list__empty">Aucune recommandation pour le moment.</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getApiUrl } from '../utils/api';

interface Song {
  id: number;
  title: string;
  artist: string;
  link: string;
  votes: number;
}

const props = defineProps<{ token?: string | null; allowVoting?: boolean }>();
const emit = defineEmits<{ (e: 'song-deleted'): void }>();

const API_URL = getApiUrl();
const songs = ref<Song[]>([]);
const voting = ref<number | null>(null);
const deleting = ref<number | null>(null);
const votedSongs = ref<Set<number>>(new Set());

const STORAGE_KEY = 'tchatreco:votedSongs';

const isAdmin = computed(() => Boolean(props.token));
const isVotingEnabled = computed(() => Boolean(props.allowVoting));

const loadVotes = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      votedSongs.value = new Set(JSON.parse(stored));
    }
  } catch (error) {
    console.warn('Impossible de charger les votes locaux', error);
  }
};

const persistVotes = () => {
  try {
    const payload = JSON.stringify(Array.from(votedSongs.value));
    localStorage.setItem(STORAGE_KEY, payload);
  } catch (error) {
    console.warn('Impossible de sauvegarder les votes locaux', error);
  }
};

const fetchSongs = async () => {
  if (!API_URL) return;
  try {
    const response = await fetch(`${API_URL}/songs/`);
    if (!response.ok) throw new Error('Erreur serveur');
    songs.value = await response.json();
  } catch (error) {
    console.error('Impossible de récupérer les chansons', error);
  }
};

const hasVoted = (songId: number) => votedSongs.value.has(songId);

const vote = async (songId: number) => {
  if (!API_URL || !isVotingEnabled.value || hasVoted(songId) || voting.value === songId) return;
  voting.value = songId;
  try {
    const response = await fetch(`${API_URL}/songs/${songId}/vote`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Vote impossible');
    const updated: Song = await response.json();
    songs.value = songs.value
      .map((song) => (song.id === songId ? { ...song, votes: updated.votes } : song))
      .sort((a, b) => b.votes - a.votes);
    votedSongs.value.add(songId);
    persistVotes();
  } catch (error) {
    console.error('Impossible de voter pour cette chanson', error);
  } finally {
    voting.value = null;
  }
};

const remove = async (songId: number) => {
  if (!API_URL || !props.token || deleting.value === songId) return;
  deleting.value = songId;
  try {
    const response = await fetch(`${API_URL}/songs/${songId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${props.token}`,
      },
    });
    if (response.status === 404) throw new Error('Chanson introuvable');
    if (!response.ok) throw new Error('Suppression impossible');
    songs.value = songs.value.filter((song) => song.id !== songId);
    votedSongs.value.delete(songId);
    persistVotes();
    emit('song-deleted');
  } catch (error) {
    console.error('Impossible de supprimer la chanson', error);
  } finally {
    deleting.value = null;
  }
};

onMounted(() => {
  loadVotes();
  fetchSongs();
});

defineExpose({
  refresh: fetchSongs,
  hasVoted,
});
</script>
