<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../lib/axios'
import AppLayout from '../components/layout/AppLayout.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppCard from '../components/ui/AppCard.vue'
import GroupFormModal from '../components/groups/GroupFormModal.vue'
import { Plus, Trash2, Edit3 } from 'lucide-vue-next'

interface Group {
  name: string
  rules: string[]
}

const groups = ref<Group[]>([])
const isLoading = ref(false)

// Modal State
const isModalOpen = ref(false)
const selectedGroup = ref<Group | undefined>(undefined)

// Delete Confirmation Modal
const showDeleteConfirm = ref(false)
const groupToDelete = ref<string | null>(null)

// Error Modal
const showError = ref(false)
const errorMsg = ref('')

const openCreateModal = () => {
  selectedGroup.value = undefined
  isModalOpen.value = true
}

const openEditModal = (group: Group) => {
  selectedGroup.value = group
  isModalOpen.value = true
}

const handleSaved = () => {
  fetchGroups()
}

const fetchGroups = async () => {
  isLoading.value = true
  try {
    const res = await api.get('/users/groups')
    groups.value = res.data
  } catch {
    console.error('Error fetching groups')
  } finally {
    isLoading.value = false
  }
}

const deleteGroup = async (name: string) => {
  groupToDelete.value = name
  showDeleteConfirm.value = true
}

const confirmDelete = async () => {
  if (!groupToDelete.value) return
  try {
    await api.delete(`/users/groups/${groupToDelete.value}`)
    fetchGroups()
  } catch {
    errorMsg.value = 'Falha ao deletar grupo. Tente novamente.'
    showError.value = true
  } finally {
    showDeleteConfirm.value = false
    groupToDelete.value = null
  }
}

onMounted(fetchGroups)
</script>

<template>
  <AppLayout>
    <div class="header">
      <div>
        <h1>Grupos de Usuário</h1>
        <p>Gerencie controle de acesso e permissões.</p>
      </div>
      <AppButton
        variant="primary"
        title="Novo Grupo"
        @click="openCreateModal"
      >
        <Plus :size="20" />
      </AppButton>
    </div>

    <div class="groups-grid">
      <AppCard
        v-for="group in groups"
        :key="group.name"
        :title="group.name"
      >
        <template #header-actions>
          <div class="actions">
            <AppButton 
              v-if="group.name !== 'Super Admin'"
              variant="ghost" 
              size="sm" 
              title="Editar Grupo"
              @click="openEditModal(group)"
            >
              <Edit3 :size="16" />
            </AppButton>
            <AppButton 
              v-if="group.name !== 'Super Admin'"
              variant="ghost" 
              size="sm" 
              class="danger-text" 
              title="Excluir Grupo"
              @click="deleteGroup(group.name)"
            >
              <Trash2 :size="16" />
            </AppButton>
          </div>
        </template>
        <div class="rules-list">
          <span
            v-for="rule in group.rules"
            :key="rule"
            class="rule-badge"
          >{{ rule }}</span>
          <span
            v-if="group.rules.length === 0"
            class="no-rules"
          >No rules assigned</span>
        </div>
      </AppCard>
    </div>

    <GroupFormModal
      v-model:open="isModalOpen"
      :group-to-edit="selectedGroup"
      @saved="handleSaved"
    />

    <!-- Delete Confirmation Modal -->
    <AppModal
      v-model:open="showDeleteConfirm"
      title="Confirmar Exclusão"
      description=""
    >
      <div class="confirm-content">
        <p>Tem certeza que deseja excluir o grupo <strong>{{ groupToDelete }}</strong>?</p>
        <div
          class="modal-actions"
          style="margin-top: 1.5rem; display: flex; justify-content: flex-end; gap: 0.75rem;"
        >
          <AppButton
            variant="ghost"
            @click="showDeleteConfirm = false"
          >
            Cancelar
          </AppButton>
          <AppButton
            variant="primary"
            @click="confirmDelete"
          >
            Confirmar
          </AppButton>
        </div>
      </div>
    </AppModal>

    <!-- Error Modal -->
    <AppModal
      v-model:open="showError"
      title="Erro"
      description=""
    >
      <div class="error-content">
        <p>{{ errorMsg }}</p>
        <div
          class="modal-actions"
          style="margin-top: 1.5rem; display: flex; justify-content: flex-end;"
        >
          <AppButton
            variant="primary"
            @click="showError = false"
          >
            Entendi
          </AppButton>
        </div>
      </div>
    </AppModal>
  </AppLayout>
</template>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}
.header h1 {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--text-primary);
}
.header p { color: var(--text-secondary); }

.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.danger-text { color: #ef4444; }

.rules-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.rule-badge {
  background: var(--color-zinc-100);
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-family: monospace;
}

.no-rules {
  font-style: italic;
  color: var(--text-muted);
  font-size: 0.875rem;
}
</style>
