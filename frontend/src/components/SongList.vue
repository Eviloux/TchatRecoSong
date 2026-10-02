<template>
  <section class="song-list">
    <header class="song-list__header">
      <h2>{{ isAdmin ? 'Recos du tchat' : 'Le top du tchat' }}</h2>
      <div class="song-list__tools">
        <div class="tabs" role="tablist" aria-label="Ordre du classement">
          <button
            v-for="option in sortOptions"
            :key="option.value"
            type="button"
            role="tab"
            :aria-selected="sortMode === option.value"
            :class="{ 'is-active': sortMode === option.value }"
            @click="sortMode = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <button type="button" class="refresh" @click="fetchSongs" aria-label="Rafraîchir la liste">↻</button>
      </div>
    </header>

    <ol v-if="sortedSongs.length" class="playlist">
      <li v-for="(song, index) in sortedSongs" :key="song.id" class="track">
        <span class="track__rank">{{ index + 1 }}</span>
        <span class="track__cover" :style="coverStyle(song, index)">
          <img v-if="song.thumbnail" :src="song.thumbnail" alt="" loading="lazy" />
        </span>
        <div class="track__info">
          <a :href="song.link" target="_blank" rel="noopener noreferrer" class="track__title">{{ song.title }}</a>
          <span class="track__artist">{{ song.artist }}</span>
        </div>
        <span v-if="providerOf(song.link)" class="chip" :class="`chip--${providerOf(song.link)}`">
          {{ providerOf(song.link) === 'youtube' ? 'YouTube' : 'Spotify' }}
        </span>
        <div class="track__actions">
          <button
            v-if="isVotingEnabled"
            type="button"
            class="heart"
            :class="{ 'is-voted': hasVoted(song.id) }"
            :disabled="hasVoted(song.id) || voting === song.id"
            :aria-label="hasVoted(song.id) ? `Vote enregistré pour ${song.title}` : `Voter pour ${song.title}`"
            @click="vote(song.id)"
          >
            {{ hasVoted(song.id) ? '♥' : '♡' }} <span class="votes">{{ song.votes }}</span>
          </button>
          <span v-else class="votes">{{ song.votes }} ♥</span>
          <button
            v-if="isAdmin"
            type="button"
            class="btn-danger"
            :disabled="deleting === song.id"
            @click="remove(song.id)"
          >
            Supprimer
          </button>
        </div>
        <p v-if="song.comment" class="track__comment">
          <span class="track__comment-label">Mot du viewer</span>
          {{ song.comment }}
        </p>
      </li>
    </ol>
    <p v-else class="song-list__empty">Aucune reco pour le moment. Sois la première personne à en proposer une ♪</p>
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
  thumbnail: string | null;
  comment: string | null;
  votes: number;
}

type SortMode = 'votes' | 'recent';
type Provider = 'youtube' | 'spotify';

const sortOptions: { value: SortMode; label: string }[] = [
  { value: 'votes', label: 'Les plus votées' },
  { value: 'recent', label: 'Les plus récentes' },
];

// Pochettes de repli (vinyles) quand le fournisseur ne donne pas de miniature.
const COVER_COLORS = ['#9D7BEA', '#9CC9F0', '#A8CF8E', '#C3B1F2', '#BFDDF5'];

const props = defineProps<{ token?: string | null; allowVoting?: boolean }>();
const emit = defineEmits<{ (e: 'song-deleted'): void }>();


const API_URL = getApiUrl();

const songs = ref<Song[]>([]);
const voting = ref<number | null>(null);
const deleting = ref<number | null>(null);
const votedSongs = ref<Set<number>>(new Set());

const STORAGE_KEY = 'tchatreco:votedSongs';

const sortMode = ref<SortMode>('votes');

const isAdmin = computed(() => Boolean(props.token));

// L'API renvoie les chansons par votes ; les identifiants croissent avec l'ordre d'ajout.
const sortedSongs = computed(() =>
  [...songs.value].sort((a, b) => (sortMode.value === 'votes' ? b.votes - a.votes : b.id - a.id)),
);

const providerOf = (link: string): Provider | null => {
  try {
    const host = new URL(link).hostname;
    if (host.endsWith('youtube.com') || host === 'youtu.be') return 'youtube';
    if (host.endsWith('spotify.com')) return 'spotify';
  } catch {
    // Anciens liens enregistrés sans https:// : pas de pastille.
  }
  return null;
};

const coverStyle = (song: Song, index: number) =>
  song.thumbnail ? {} : { background: COVER_COLORS[index % COVER_COLORS.length] };
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

// Soumettre une chanson compte déjà comme un vote côté serveur : on la marque
// comme votée pour que ce viewer ne puisse pas ajouter un 2e vote avec le cœur.
const markAsVoted = (songId: number) => {
  votedSongs.value.add(songId);
  persistVotes();
};

const vote = async (songId: number) => {
  if (!API_URL || !isVotingEnabled.value || hasVoted(songId) || voting.value === songId) return;
  voting.value = songId;
  try {
    const response = await fetch(`${API_URL}/songs/${songId}/vote`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Vote impossible');
    const updated: Song = await response.json();
    // Le tri est assuré par `sortedSongs`.
    songs.value = songs.value.map((song) => (song.id === songId ? { ...song, votes: updated.votes } : song));
    markAsVoted(songId);
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
  markAsVoted,
});
</script>
