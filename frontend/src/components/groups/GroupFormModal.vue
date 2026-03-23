<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import AppModal from '../ui/AppModal.vue'
import AppInput from '../ui/AppInput.vue'
import AppButton from '../ui/AppButton.vue'
import api from '../../lib/axios'
import { Save } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  groupToEdit?: any // If present, we are in edit mode
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'saved'): void
}>()

const isOpen = computed({
  get: () => props.open,
  set: (val) => emit('update:open', val)
})

const name = ref('')
const rulesInput = ref('')
const isLoading = ref(false)
const showError = ref(false)
const errorText = ref('')
const availableRules = ['script:create', 'script:read', 'script:delete', 'group:manage', 'user:manage', '*', 'settings:manage']

// Initialize form when opening/changing target
watch(() => props.groupToEdit, (newGroup) => {
  if (newGroup) {
    name.value = newGroup.name
    rulesInput.value = newGroup.rules ? newGroup.rules.join(', ') : ''
  } else {
    name.value = ''
    rulesInput.value = ''
  }
}, { immediate: true })

// Also watch open to reset if opening in create mode
watch(() => props.open, (val) => {
  if (val && !props.groupToEdit) {
    name.value = ''
    rulesInput.value = ''
  }
})

const isEdit = computed(() => !!props.groupToEdit)

const handleSubmit = async () => {
  isLoading.value = true
  try {
    const rules = rulesInput.value.split(',').map(r => r.trim()).filter(r => r)
    
    // Create/Update Logic
    // backend uses POST /users/groups for both create/update (upsert)
    // assuming backend supports it (based on previous analysis)
    
    await api.post('/users/groups', {
      name: name.value,
      rules: rules
    })
    
    emit('saved')
    isOpen.value = false
  } catch (e: any) {
    errorText.value = `Erro ao ${isEdit.value ? 'atualizar' : 'criar'} grupo: ${e.response?.data?.detail || e.message}`
    showError.value = true
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <AppModal
    v-model:open="isOpen"
    :title="isEdit ? 'Editar Grupo' : 'Criar Novo Grupo'"
  >
    <form
      class="modal-form"
      @submit.prevent="handleSubmit"
    >
      <AppInput
        id="group-name"
        v-model="name"
        label="Nome do Grupo (ID)"
        placeholder="ex: editor, viewer"
        required
        :disabled="isEdit"
      />

      <div class="app-input-group">
        <label class="app-label">Regras (Permissões)</label>
        <p class="hint">
          Regras separadas por vírgula. Clique nas sugestões abaixo para adicionar.
        </p>
        <AppInput
          id="rules"
          v-model="rulesInput"
          label=""
          placeholder="script:read, script:create"
        />
        
        <div class="chips">
          <button 
            v-for="rule in availableRules" 
            :key="rule" 
            type="button"
            class="chip"
            @click="rulesInput = rulesInput ? rulesInput + ', ' + rule : rule"
          >
            + {{ rule }}
          </button>
        </div>
      </div>

      <div class="form-actions">
        <AppButton
          variant="ghost"
          type="button"
          @click="isOpen = false"
        >
          Cancelar
        </AppButton>
        <AppButton 
          type="submit" 
          variant="primary" 
          :loading="isLoading" 
          :title="isEdit ? 'Salvar Alterações' : 'Criar Grupo'"
        >
          <Save :size="18" />
        </AppButton>
      </div>
    </form>
  </AppModal>

  <!-- Error Modal -->
  <AppModal
    v-model:open="showError"
    title="Erro"
    description=""
  >
    <div class="error-content">
      <p>{{ errorText }}</p>
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
</template>

<style scoped>
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

.app-input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.app-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-zinc-400);
}

.hint {
  font-size: 0.75rem;
  color: var(--color-zinc-500);
  margin-bottom: 0.25rem;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.chip {
  background: var(--bg-card-hover);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.chip:hover {
  background: var(--bg-card);
  border-color: var(--primary-base);
  color: var(--text-primary);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
}
</style>
