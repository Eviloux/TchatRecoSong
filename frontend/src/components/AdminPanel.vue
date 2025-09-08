<template>
  <div class="admin-panel">
    <h2>Règles de ban</h2>

    <div class="ban-list">
      <div v-for="rule in banRules" :key="rule.id" class="ban-card">
        <p>Titre: {{ rule.title || '—' }}</p>
        <p>Artiste: {{ rule.artist || '—' }}</p>
        <p>Lien: {{ rule.url || '—' }}</p>
      </div>
    </div>

    <form @submit.prevent="addRule">
      <input v-model="newRule.title" type="text" placeholder="Titre" />
      <input v-model="newRule.artist" type="text" placeholder="Artiste" />
      <input v-model="newRule.url" type="text" placeholder="Lien YouTube/Spotify" />
      <button type="submit">Ajouter</button>
    </form>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue'

export default defineComponent({
  name: 'AdminPanel',
  setup() {
    const banRules = ref<Array<any>>([])
    const newRule = ref({ title: '', artist: '', url: '' })

    const fetchBanRules = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/ban/`)
        banRules.value = await res.json()
      } catch (err) {
        console.error('Erreur lors de la récupération des règles:', err)
      }
    }

    const addRule = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/ban/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newRule.value)
        })
        if (res.ok) {
          await fetchBanRules()
          newRule.value = { title: '', artist: '', url: '' }
        }
      } catch (err) {
        console.error('Erreur lors de l’ajout de la règle:', err)
      }
    }

    onMounted(fetchBanRules)

    return { banRules, newRule, addRule }
  }
})
</script>
