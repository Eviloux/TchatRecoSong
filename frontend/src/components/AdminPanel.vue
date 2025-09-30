<template>
  <section class="admin-panel">
    <h2>Gestion des ban words</h2>
    <p v-if="!token" class="warning">
      Connectez-vous pour ajouter des règles de bannissement.
    </p>

    <ul v-if="banRules.length" class="ban-list">
      <li v-for="rule in banRules" :key="rule.id">
        <div class="ban-details">
          <strong v-if="rule.title">Titre :</strong> {{ rule.title || '—' }} ·
          <strong v-if="rule.artist">Artiste :</strong> {{ rule.artist || '—' }} ·
          <strong v-if="rule.link">Lien :</strong> {{ rule.link || '—' }}
        </div>
        <div v-if="isAuthenticated" class="ban-actions">
          <button
            type="button"
            @click="startEdit(rule)"
            :disabled="isSubmitting || deletingRuleId === rule.id"
          >
            Modifier
          </button>
          <button
            type="button"
            class="danger"
            @click="deleteRule(rule.id)"
            :disabled="deletingRuleId === rule.id"
          >
            {{ deletingRuleId === rule.id ? 'Suppression…' : 'Supprimer' }}
          </button>
        </div>
      </li>
    </ul>
    <p v-else class="ban-empty">Aucune règle enregistrée pour le moment.</p>

    <form v-if="isAuthenticated" class="ban-form" @submit.prevent="submit">
      <p v-if="editingRule" class="edit-info">
        Modification de la règle #{{ editingRule.id }}
      </p>
      <div class="field">
        <label for="ban-title">Titre</label>
        <input id="ban-title" v-model="form.title" placeholder="Titre exact" />
      </div>
      <div class="field">
        <label for="ban-artist">Artiste</label>
        <input id="ban-artist" v-model="form.artist" placeholder="Artiste exact" />
      </div>
      <div class="field">
        <label for="ban-link">Lien</label>
        <input id="ban-link" v-model="form.link" placeholder="https://..." />
      </div>
      <div class="form-actions">
        <button type="submit" :disabled="isSubmitting">
          {{ editingRule ? 'Mettre à jour la règle' : 'Ajouter une règle' }}
        </button>
        <button
          v-if="editingRule"
          type="button"
          class="secondary"
          :disabled="isSubmitting"
          @click="cancelEdit"
        >
          Annuler
        </button>
      </div>
    </form>
    <p v-if="formError" class="form-error">{{ formError }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, watch, reactive, ref } from 'vue';
import { getApiUrl } from '../utils/api';

interface BanRule {
  id: number;
  title?: string | null;
  artist?: string | null;
  link?: string | null;
}

const props = defineProps<{ token: string | null }>();

const emit = defineEmits<{ (e: 'ban-rules-changed'): void }>();
const API_URL = getApiUrl();
const banRules = ref<BanRule[]>([]);
const form = reactive({ title: '', artist: '', link: '' });
const formError = ref('');
const isSubmitting = ref(false);
const deletingRuleId = ref<number | null>(null);
const editingRuleId = ref<number | null>(null);

const isAuthenticated = computed(() => Boolean(props.token));
const editingRule = computed(() =>
  editingRuleId.value ? banRules.value.find((rule) => rule.id === editingRuleId.value) ?? null : null,
);


const fetchBanRules = async () => {
  if (!API_URL) return;
  try {
    const response = await fetch(`${API_URL}/ban/`);
    if (!response.ok) throw new Error('Erreur serveur');
    banRules.value = await response.json();
  } catch (error) {
    console.error('Impossible de récupérer les ban rules', error);
  }
};

const submit = async () => {

  if (!props.token || !API_URL) {
    formError.value = "API non configurée.";
    return;
  }

  const payload = {
    title: form.title.trim() || null,
    artist: form.artist.trim() || null,
    link: form.link.trim() || null,
  };

  if (!payload.title && !payload.artist && !payload.link) {

    formError.value = 'Renseignez au moins un champ pour enregistrer une règle.';

    return;
  }

  try {
    isSubmitting.value = true;
    const isEditing = Boolean(editingRuleId.value);
    const endpoint = isEditing ? `${API_URL}/ban/${editingRuleId.value}` : `${API_URL}/ban/`;
    const method = isEditing ? 'PUT' : 'POST';
    const response = await fetch(endpoint, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${props.token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: "Erreur lors de l'enregistrement." }));
      throw new Error(data.detail || "Erreur lors de l'enregistrement.");
    }
    form.title = '';
    form.artist = '';
    form.link = '';
    formError.value = '';

    editingRuleId.value = null;
    await fetchBanRules();
    emit('ban-rules-changed');
  } catch (error) {
    console.error(error);
    formError.value = error instanceof Error ? error.message : "Impossible d'enregistrer cette règle.";
  } finally {
    isSubmitting.value = false;
  }
};

const startEdit = (rule: BanRule) => {
  editingRuleId.value = rule.id;
  form.title = rule.title ?? '';
  form.artist = rule.artist ?? '';
  form.link = rule.link ?? '';
  formError.value = '';
};

const cancelEdit = () => {
  editingRuleId.value = null;
  form.title = '';
  form.artist = '';
  form.link = '';
  formError.value = '';
};

const deleteRule = async (ruleId: number) => {
  if (!props.token || !API_URL || deletingRuleId.value === ruleId) {
    return;
  }
  deletingRuleId.value = ruleId;
  try {
    const response = await fetch(`${API_URL}/ban/${ruleId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${props.token}`,
      },
    });
    if (response.status === 404) {
      throw new Error('Règle introuvable.');
    }
    if (!response.ok) {
      throw new Error('Suppression impossible.');
    }
    if (editingRuleId.value === ruleId) {
      cancelEdit();
    }
    await fetchBanRules();
    emit('ban-rules-changed');
  } catch (error) {
    console.error('Impossible de supprimer la règle', error);
    formError.value = error instanceof Error ? error.message : 'Suppression impossible.';
  } finally {
    deletingRuleId.value = null;

  }
};

onMounted(fetchBanRules);
watch(
  () => props.token,
  (newToken) => {
    if (!newToken) {
      cancelEdit();
    }
    fetchBanRules();
  }
);
</script>
