

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { X, Save, Bot, Search, Check, Loader2, AlertCircle } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import type { Agent } from '../../services/agent.service'
import { getAllIcons } from '../../utils/agent-icons'
import {
  DialogClose,

  DialogContent,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'radix-vue'

const props = defineProps<{
  open: boolean
  agent?: Agent | null
}>()

const emit = defineEmits(['update:open', 'save', 'auto-save'])



const form = ref<Agent>({
  name: '',
  icon: 'Bot',
  description: '',
  prompt_init: '',
  prompt_chapters: '',
  prompt_subchapters: '',
  prompt_scenes: '',
  is_default: false
})

const isEditing = computed(() => !!props.agent?.id)

// Icon Search
const searchQuery = ref('')
const allIcons = getAllIcons()

const filteredIcons = computed(() => {
    if (!searchQuery.value) return allIcons
    const query = searchQuery.value.toLowerCase()
    return allIcons.filter(icon => icon.name.toLowerCase().includes(query))
})

watch(() => props.agent, (newAgent) => {
  if (newAgent) {
    form.value = { ...newAgent }
  } else {
    form.value = {
      name: '',
      icon: 'Bot', // Default
      description: '',
      prompt_init: '',
      prompt_chapters: '',
      prompt_subchapters: '',
      prompt_scenes: '{"scenes": [{"narration_content": "...", "visual_description": "..."}]}',
      is_default: false
    }
  }
}, { immediate: true })

// Auto-Save Logic
const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(form, (newForm) => {
    if (!isEditing.value) return // Only auto-save if editing an existing agent

    // Clear previous timer
    if (debounceTimer) clearTimeout(debounceTimer)
    
    // Don't auto-save immediately on load, check if dirty? 
    // Ideally we'd diff against props.agent, but simpler: reset status to idle on user input
    if (saveStatus.value !== 'saving') {
        saveStatus.value = 'idle'
    }

    debounceTimer = setTimeout(async () => {
        saveStatus.value = 'saving'
        try {
            emit('auto-save', { ...newForm })
            // Simulate a brief delay to ensure the spinner is seen for at least a moment
            setTimeout(() => {
                saveStatus.value = 'saved'
                // Auto-hide the "saved" status after 2 seconds
                setTimeout(() => {
                    if (saveStatus.value === 'saved') { // Only if still saved (not saving again)
                        saveStatus.value = 'idle'
                    }
                }, 2000)
            }, 800)
        } catch {
            saveStatus.value = 'error'
        }
    }, 2000)
}, { deep: true })

const handleSave = () => {
  if (debounceTimer) clearTimeout(debounceTimer) // Cancel pending auto-save
  emit('save', { ...form.value })
}

const getComponent = (iconName: string) => {
    const icon = allIcons.find(i => i.name === iconName)
    return icon ? icon.component : Bot
}
</script>


<template>
  <DialogRoot
    :open="open"
    @update:open="emit('update:open', $event)"
  >
    <DialogPortal>
      <DialogOverlay class="dialog-overlay" />
      <DialogContent class="dialog-content">
        <!-- Header -->
        <div class="dialog-header">
          <DialogTitle class="dialog-title">
            <!-- @vue-ignore -->
            <component
              :is="getComponent(form.icon || 'Bot')"
              class="icon-title"
            />
            {{ isEditing ? 'Editar Agente' : 'Novo Agente' }}

            <div
              v-if="isEditing"
              class="save-indicator ml-3 min-w-[20px] flex items-center justify-center h-5"
            >
              <Transition
                name="fade"
                mode="out-in"
              >
                <Loader2
                  v-if="saveStatus === 'saving'"
                  :size="18"
                  class="animate-spin text-muted"
                />
                <Check
                  v-else-if="saveStatus === 'saved'"
                  :size="18"
                  class="text-green-500"
                />
                <AlertCircle
                  v-else-if="saveStatus === 'error'"
                  :size="18"
                  class="text-error"
                />
              </Transition>
            </div>
          </DialogTitle>

          <DialogClose
            class="close-btn"
            as-child
          >
            <button><X :size="20" /></button>
          </DialogClose>
        </div>

        <!-- Body -->
        <div class="dialog-body">
          <AppInput 
            id="agent-name"
            v-model="form.name" 
            label="Nome do Agente" 
            placeholder="Ex: Agente Criativo V2" 
            class="mb-4"
          />

          <div class="form-group mb-6">
            <label class="mb-2">Ícone do Agente</label>
            
            <div class="icon-search-wrapper mb-3">
              <Search
                :size="16"
                class="search-icon"
              />
              <input 
                v-model="searchQuery" 
                type="text" 
                placeholder="Buscar ícone (ex: robot, user, chat)..." 
                class="icon-search-input"
              >
            </div>

            <div class="icon-grid-container">
              <div class="icon-grid">
                <button 
                  v-for="icon in filteredIcons" 
                  :key="icon.name"
                  type="button"
                  class="icon-option"
                  :class="{ 'selected': form.icon === icon.name }"
                  :title="icon.name"
                  @click="form.icon = icon.name"
                >
                  <!-- @vue-ignore -->
                  <component
                    :is="icon.component"
                    :size="24"
                  />
                </button>
              </div>
                
              <div
                v-if="filteredIcons.length === 0"
                class="no-results"
              >
                Nenhum ícone encontrado.
              </div>
            </div>
          </div>




          <div class="form-group mb-4">
            <label>Descrição</label>
            <textarea
              v-model="form.description"
              class="app-textarea"
              rows="2"
              placeholder="Breve descrição do propósito deste agente..."
            />
          </div>



          <div class="grid grid-cols-1 gap-4">
            <div class="form-group">
              <label>Prompt Inicial (Init)</label>
              <textarea
                v-model="form.prompt_init"
                class="app-textarea code-editor"
                rows="6"
              />
              <span class="hint">Gera o conceito inicial do vídeo.</span>
            </div>


            <div class="form-group">
              <label>Prompt Capítulos</label>
              <textarea
                v-model="form.prompt_chapters"
                class="app-textarea code-editor"
                rows="6"
              />
              <span class="hint">Define a estrutura de capítulos.</span>
            </div>


            <div class="form-group">
              <label>Prompt Sub-capítulos</label>
              <textarea
                v-model="form.prompt_subchapters"
                class="app-textarea code-editor"
                rows="6"
              />
              <span class="hint">Expande capítulos em sub-seções.</span>
            </div>


            <div class="form-group">
              <label>Prompt Cenas</label>
              <textarea
                v-model="form.prompt_scenes"
                class="app-textarea code-editor"
                rows="6"
              />
              <span class="hint">Gera o roteiro detalhado (JSON cenas).</span>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="dialog-footer">
          <AppButton
            variant="secondary"
            @click="emit('update:open', false)"
          >
            Cancelar
          </AppButton>
          <AppButton @click="handleSave">
            <Save
              :size="18"
              class="mr-2"
            />
            Salvar
          </AppButton>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>


<style scoped>
.dialog-overlay {
  background-color: rgba(0, 0, 0, 0.5);
  position: fixed;
  inset: 0;
  z-index: 100;
  backdrop-filter: blur(4px);
  animation: overlayShow 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

.dialog-content {
  background-color: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 38px -10px rgba(22, 23, 24, 0.35), 0 10px 20px -15px rgba(22, 23, 24, 0.2);
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 90vw;
  max-width: 800px; /* Wider for textareas */
  max-height: 90vh;
  padding: 0;
  z-index: 101;
  animation: contentShow 150ms cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.dialog-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.icon-title {
  color: var(--primary-base);
}

.close-btn {
  color: var(--text-muted);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.close-btn:hover {
  color: var(--text-primary);
}

.dialog-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.dialog-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  background: var(--bg-app);
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.form-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
}

.app-textarea {
  width: 100%;
  padding: 0.75rem;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.875rem; /* Monospace-ish if we wanted, but sans is ok */
  font-family: inherit;
  transition: border-color 0.2s;
  resize: vertical;
}

.app-textarea:focus {
  outline: none;
  border-color: var(--primary-base);
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1);
}

.hint {
    font-size: 0.75rem;
    color: var(--text-muted);
}

.code-editor {
  font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  background: var(--bg-app);
  color: var(--primary-base);
  border-left: 3px solid var(--primary-base);
}

/* Icon Search & Grid Styles */
.icon-search-wrapper {
    position: relative;
    width: 100%;
}

.search-icon {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    pointer-events: none;
}

.icon-search-input {
    width: 100%;
    padding: 0.5rem 0.5rem 0.5rem 2.25rem;
    background: var(--bg-app);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 0.875rem;
    transition: all 0.2s;
}

.icon-search-input:focus {
    outline: none;
    border-color: var(--primary-base);
    background: var(--bg-card);
}

.icon-grid-container {
   max-height: 220px;
   overflow-y: auto;
   padding: 0.5rem;
   background: var(--bg-app);
   border: 1px solid var(--border-subtle);
   border-radius: var(--radius-md);
}

.icon-grid {
   display: grid;
   grid-template-columns: repeat(auto-fill, minmax(42px, 1fr));
   gap: 0.5rem;
}

.icon-option {
   display: flex;
   align-items: center;
   justify-content: center;
   width: 42px;
   height: 42px;
   border-radius: var(--radius-md);
   background: var(--bg-card);
   border: 1px solid var(--border-subtle);
   color: var(--text-secondary);
   cursor: pointer;
   transition: all 0.1s ease;
}

.icon-option:hover {
   background: var(--bg-hover);
   color: var(--text-primary);
   transform: scale(1.05);
}

.icon-option.selected {
   background: rgba(124, 58, 237, 0.15);
   color: var(--primary-base);
   border-color: var(--primary-base);
   box-shadow: 0 0 0 1px var(--primary-base);
}

.load-more-wrapper {
    display: flex;
    justify-content: center;
    margin-top: 1rem;
    padding-bottom: 0.5rem;
}

.load-more-btn {
    background: none;
    border: none;
    color: var(--primary-base);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    padding: 0.5rem 1rem;
    border-radius: var(--radius-sm);
}

.load-more-btn:hover {
    background: rgba(124, 58, 237, 0.05);
    text-decoration: underline;
}

.no-results {
    text-align: center;
    padding: 2rem;
    color: var(--text-muted);
    font-size: 0.875rem;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>



