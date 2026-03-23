<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppCard from '../components/ui/AppCard.vue'

import api from '../lib/axios'
import { Save, AlertTriangle, Plus, CheckCircle2, AlertCircle, Info, Check, X } from 'lucide-vue-next'
import AppModal from '../components/ui/AppModal.vue'

interface Setting {
  key: string
  value: string
  is_secret: boolean
  is_new?: boolean
}

const settingsData = ref<Setting[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const newKey = ref('')
const newValue = ref('')

// Modal States
const isConfirmModalOpen = ref(false)
const isSuccessModalOpen = ref(false)
const isErrorModalOpen = ref(false)
const errorMessage = ref('')
const isAccessDeniedModalOpen = ref(false)

const fetchSettings = async () => {
  isLoading.value = true
  try {
    // Explicitly using the full path with trailing slash if needed, 
    // although with our backend change /settings (no slash) should also work.
    const res = await api.get('/settings')
    console.log('[SettingsView] Data received:', res.data)
    
    // Fix: Handle dictionary response from backend
    if (!Array.isArray(res.data) && typeof res.data === 'object') {
        settingsData.value = Object.entries(res.data).map(([key, value]) => ({
            key: key,
            value: String(value),
            is_secret: key.includes('KEY') || key.includes('SECRET') || key.includes('PASSWORD') || key.includes('TOKEN'),
            is_new: false
        }))
    } else {
        settingsData.value = res.data
    }
  } catch (e: any) {
    console.error('[SettingsView] Fetch failed:', e)
    if (e.response?.status === 403) {
      isAccessDeniedModalOpen.value = true
    } else if (e.response?.status === 401) {
      console.warn("Unauthorized access to settings")
    } else {
      errorMessage.value = "Não foi possível carregar as configurações. Verifique os logs."
      isErrorModalOpen.value = true
    }
  } finally {
    isLoading.value = false
  }
}

const isPromptField = (key: string) => {
  return key.toLowerCase().includes('prompt')
}

const getPromptTags = (key: string) => {
  const k = key.toUpperCase()
  const base = [
    '{topic}', '{duration}', '{language}', 
    '{agent_name}', '{agent_description}', '{agent_icon}',
    '{agent_prompt_init}', '{agent_prompt_chapters}', 
    '{agent_prompt_subchapters}', '{agent_prompt_scenes}'
  ]
  const metadata = ['{video_title}', '{video_description}', '{video_tags}', '{video_visual_style}', '{video_music}', '{video_characters}']
  const chapter = ['{chapter_order}', '{chapter_title}', '{chapter_description}']
  const sub = ['{subchapter_order}', '{subchapter_title}', '{subchapter_description}']

  if (k.includes('INIT')) return base
  if (k.includes('CHAPTERS')) return [...base, ...metadata]
  if (k.includes('SUBCHAPTERS')) return [...base, ...metadata, ...chapter]
  if (k.includes('SCENES')) return [...base, ...metadata, ...chapter, ...sub]
  return []
}

const addNewKey = () => {
  if (!newKey.value) return
  settingsData.value.push({ 
    key: newKey.value.toUpperCase(), 
    value: newValue.value, 
    is_secret: false, 
    is_new: true 
  })
  newKey.value = ''
  newValue.value = ''
}

const triggerSaveConfirm = () => {
  isConfirmModalOpen.value = true
}

const handleSave = async () => {
  isConfirmModalOpen.value = false
  isSaving.value = true
  try {
    const payload = settingsData.value.reduce((acc, curr) => {
      const isMasked = curr.is_secret && curr.value.includes('...')
      if (!isMasked) {
        acc[curr.key] = curr.value
      }
      return acc
    }, {} as Record<string, string>)
    
    await api.post('/settings', { settings: payload })
    isSuccessModalOpen.value = true
    fetchSettings()
  } catch (e: any) {
    errorMessage.value = e.message || 'Falha ao salvar as configurações'
    isErrorModalOpen.value = true
  } finally {
    isSaving.value = false
  }
}

onMounted(fetchSettings)
</script>

<template>
  <AppLayout>
    <div class="header">
      <div>
        <h1>Configurações</h1>
        <p>Gerencie variáveis de ambiente e credenciais.</p>
      </div>
      <AppButton
        variant="primary"
        :loading="isSaving"
        title="Salvar Alterações"
        @click="triggerSaveConfirm"
      >
        <Save :size="18" />
      </AppButton>
    </div>

    <div class="alert-box">
      <AlertTriangle :size="20" />
      <span><strong>Cuidado:</strong> Os valores são armazenados no arquivo <code>.env</code>. Reinicie o servidor após alterações.</span>
    </div>

    <AppCard>
      <div class="settings-list">
        <div
          v-for="(item, idx) in settingsData"
          :key="idx"
          class="setting-item"
        >
          <div class="setting-key">
            <span :class="{ 'new-key': item.is_new }">{{ item.key }}</span>
            <div
              v-if="isPromptField(item.key)"
              class="tags-hint"
            >
              <div class="tags-label">
                Tags disponíveis:
              </div>
              <div class="tags-container">
                <code
                  v-for="tag in getPromptTags(item.key)"
                  :key="tag"
                  class="tag-code"
                >{{ tag }}</code>
              </div>
            </div>
          </div>
          <div class="setting-value">
            <textarea 
              v-if="isPromptField(item.key)"
              v-model="item.value" 
              class="simple-input simple-textarea code-editor" 
              rows="12"
              autocomplete="off"
              placeholder="Insira seu prompt aqui..."
            />

            <input 
              v-else
              v-model="item.value" 
              class="simple-input" 
              type="text"
              autocomplete="off"
            >
          </div>
        </div>
      </div>
       
      <div class="add-row">
        <input
          v-model="newKey"
          placeholder="NEW_VARIABLE_KEY"
          class="simple-input key-input"
        >
        <input
          v-model="newValue"
          placeholder="Value"
          class="simple-input"
        >
        <AppButton
          size="sm"
          variant="secondary"
          title="Adicionar Variável"
          @click="addNewKey"
        >
          <Plus :size="16" />
        </AppButton>
      </div>
    </AppCard>

    <!-- Confirm Save Modal -->
    <AppModal
      v-model:open="isConfirmModalOpen"
      title="Confirmar Alterações"
    >
      <div class="modal-alert-content">
        <AlertTriangle
          class="warning-icon"
          :size="48"
        />
        <p>Aterar as configurações do sistema requer que o servidor seja reiniciado para que as mudanças entrem em vigor.</p>
        <p>Deseja continuar?</p>
      </div>
      <div class="form-actions">
        <AppButton
          variant="ghost"
          title="Cancelar"
          @click="isConfirmModalOpen = false"
        >
          <X :size="18" />
        </AppButton>
        <AppButton
          variant="primary"
          title="Sim, Salvar"
          @click="handleSave"
        >
          <Check :size="18" />
        </AppButton>
      </div>
    </AppModal>

    <!-- Success Modal -->
    <AppModal
      v-model:open="isSuccessModalOpen"
      title="Configurações Salvas"
    >
      <div class="modal-status-content">
        <CheckCircle2
          class="success-icon"
          :size="48"
        />
        <p>Configurações atualizadas com sucesso!</p>
        <p class="restart-warning">
          Lembre-se de reiniciar o servidor backend para aplicar as novas variáveis de ambiente.
        </p>
      </div>
      <div class="form-actions">
        <AppButton
          variant="primary"
          title="Ok"
          @click="isSuccessModalOpen = false"
        >
          <Check :size="18" />
        </AppButton>
      </div>
    </AppModal>

    <!-- Error Modal -->
    <AppModal
      v-model:open="isErrorModalOpen"
      title="Erro"
    >
      <div class="modal-status-content">
        <AlertCircle
          class="error-icon"
          :size="48"
        />
        <p>{{ errorMessage }}</p>
      </div>
      <div class="form-actions">
        <AppButton
          variant="primary"
          title="Ok"
          @click="isErrorModalOpen = false"
        >
          <Check :size="18" />
        </AppButton>
      </div>
    </AppModal>

    <!-- Access Denied Modal -->
    <AppModal
      v-model:open="isAccessDeniedModalOpen"
      title="Acesso Negado"
    >
      <div class="modal-status-content">
        <Info
          class="info-icon"
          :size="48"
        />
        <p>Apenas administradores podem acessar esta página.</p>
      </div>
      <div class="form-actions">
        <AppButton
          variant="primary"
          title="Ok"
          @click="isAccessDeniedModalOpen = false"
        >
          <Check :size="18" />
        </AppButton>
      </div>
    </AppModal>
  </AppLayout>
</template>

<style scoped>
/* Existing styles... */

.modal-alert-content, .modal-status-content {
  display: flex;
  flex-direction: column;
  items-align: center;
  text-align: center;
  gap: 1rem;
  padding: 1rem 0;
}

.warning-icon { color: var(--color-amber-500); align-self: center; }
.success-icon { color: var(--color-green-500); align-self: center; }
.error-icon { color: var(--color-red-500); align-self: center; }
.info-icon { color: var(--color-blue-500); align-self: center; }

.restart-warning {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-style: italic;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
}
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

.alert-box {
  background: rgba(234, 179, 8, 0.1);
  color: #ca8a04;
  padding: 1rem;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  border: 1px solid rgba(234, 179, 8, 0.2);
}

.settings-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.setting-item {
  display: grid;
  grid-template-columns: 250px 1fr;
  align-items: start;
  gap: 1rem;
  padding: 1rem 0;
  border-bottom: 1px solid var(--border-subtle);
}

.setting-key {
  font-family: monospace;
  font-size: 0.9rem;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

.lock-icon {
  color: var(--text-muted);
}

.new-key {
  color: #16a34a;
  font-weight: bold;
}

.simple-input {
  width: 100%;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  padding: 0.5rem;
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: monospace;
}

.simple-input:focus {
  outline: none;
  border-color: var(--primary-base);
}

.simple-textarea {
  resize: vertical;
  min-height: 80px;
  line-height: 1.5;
}

.code-editor {
  font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  background: var(--bg-app);
  color: var(--primary-base);
  border-left: 3px solid var(--primary-base);
}

.code-editor {
  font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  background: var(--bg-app);
  color: var(--primary-base);
  border-left: 3px solid var(--primary-base);
}

.markdown-body {
  /* Future: could add real markdown styling here */
}

.add-row {
  display: grid;
  grid-template-columns: 250px 1fr auto;
  gap: 1rem;
  align-items: center;
  padding-top: 1rem;
  background: var(--bg-card-hover);
  padding: 1rem;
  border-radius: var(--radius-md);
}

.tags-hint {
  margin-top: 0.5rem;
  font-family: var(--font-sans);
  width: 100%;
}

.tags-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.tag-code {
  font-family: monospace;
  font-size: 0.75rem;
  background: rgba(var(--primary-rgb), 0.1);
  color: var(--primary-base);
  padding: 0.1rem 0.4rem;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(var(--primary-rgb), 0.2);
}

.key-input {
  text-transform: uppercase;
}
</style>
