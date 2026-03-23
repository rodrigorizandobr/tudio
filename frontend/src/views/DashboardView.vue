<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useVideoStore } from '../stores/video.store'
import AppLayout from '../components/layout/AppLayout.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppInput from '../components/ui/AppInput.vue'
import AppModal from '../components/ui/AppModal.vue'
import { Plus, ChevronRight, File, Loader2, CheckCircle2, AlertCircle, Wand2, Trash2, Search, Filter, ArrowUpDown, History, RotateCcw } from 'lucide-vue-next'
import { agentService, type Agent } from '../services/agent.service'


const videoStore = useVideoStore()
const router = useRouter()

const isModalOpen = ref(false)
const agents = ref<Agent[]>([])
const isDeletingId = ref<number | null>(null)

const form = ref<{
  prompt: string
  language: string
  target_duration_minutes: number
  agent_id?: string
  aspect_ratio: string
  auto_image_source?: string
  auto_generate_narration?: boolean
  audio_transition_padding: number
}>({
  prompt: '',
  language: 'pt-br',
  target_duration_minutes: 5,
  agent_id: undefined,
  aspect_ratio: '16:9',
  auto_image_source: 'none',
  auto_generate_narration: false,
  audio_transition_padding: 0.5
})


onMounted(async () => {
  videoStore.fetchVideos()
  try {
    const loadedAgents = await agentService.list()
    agents.value = loadedAgents || []
  } catch (e) {
    console.error("Failed to load agents", e)
    agents.value = []
  }
})


const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const openCreateModal = () => {
  router.push('/panel/videos/new')
}

const goToDetails = (id: number) => {
  router.push(`/panel/videos/${id}`)
}

const handleSubmit = async () => {
  if (!form.value.prompt) return

  const id = await videoStore.createVideo({
    prompt: form.value.prompt,
    language: form.value.language,
    target_duration_minutes: Number(form.value.target_duration_minutes),
    agent_id: form.value.agent_id,
    aspect_ratios: [form.value.aspect_ratio],
    auto_image_source: form.value.auto_image_source,
    auto_generate_narration: form.value.auto_generate_narration,
    audio_transition_padding: form.value.audio_transition_padding
  })


  if (id) {
    isModalOpen.value = false
    // Optionally redirect or just refresh list (store already refreshes?)
    // In this case, we'll navigate to details
    router.push(`/panel/videos/${id}`)
  }
}

const handleRestore = async (e: Event, id: number) => {
  e.stopPropagation()
  isDeletingId.value = id
  try {
    await videoStore.restoreVideo(id)
  } finally {
    isDeletingId.value = null
  }
}


const handleDelete = async (e: Event, id: number) => {
  e.stopPropagation()
  isDeletingId.value = id
  try {
    await videoStore.deleteVideo(id)
  } finally {
    isDeletingId.value = null
  }
}

// Search & Filter Logic
let searchTimeout: any = null
const handleSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    videoStore.fetchVideos()
  }, 500)
}

const toggleDeleted = async () => {
  videoStore.showDeleted = !videoStore.showDeleted
  await videoStore.fetchVideos()
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'processing': return 'warning'
    case 'rendering': return 'warning'
    case 'rendering_scenes': return 'warning'
    case 'error': return 'danger'
    default: return 'neutral'
  }
}
</script>

<template>
  <AppLayout>
    <div class="dashboard-header">
      <div>
        <h1 class="page-title">
          Meus Vídeos
        </h1>
        <p class="page-subtitle">
          Gerencie e gere seus vídeos com IA.
        </p>
      </div>
      <AppButton
        variant="primary"
        title="Novo Vídeo"
        @click="openCreateModal"
      >
        <Plus :size="20" />
      </AppButton>
    </div>

    <!-- Filters & Search Toolbar -->
    <div class="filters-toolbar">
      <div class="search-box">
        <Search :size="18" class="search-icon" />
        <input 
          v-model="videoStore.searchQuery" 
          type="text" 
          placeholder="Buscar por título ou prompt..." 
          @input="handleSearch"
        />
      </div>

      <div class="toolbar-actions">
        <!-- Status Filter -->
        <div class="filter-select-wrapper">
          <Filter :size="16" class="filter-icon" />
          <select 
            v-model="videoStore.statusFilter" 
            @change="videoStore.fetchVideos"
          >
            <option :value="null">Todos os Status</option>
            <option value="pending">Pendente</option>
            <option value="processing">Processando</option>
            <option value="completed">Concluído</option>
            <option value="error">Erro</option>
          </select>
        </div>

        <!-- Sorting -->
        <div class="filter-select-wrapper">
          <ArrowUpDown :size="16" class="filter-icon" />
          <select 
            v-model="videoStore.sortBy" 
            @change="videoStore.fetchVideos"
          >
            <option value="created_at">Data (Recentes)</option>
            <option value="title">Título (A-Z)</option>
            <option value="progress">Progresso</option>
            <option value="status">Status</option>
          </select>
        </div>
        <!-- Trash Toggle -->
        <AppButton 
          :variant="videoStore.showDeleted ? 'danger' : 'outline'"
          class="trash-toggle"
          @click="toggleDeleted"
        >
          <Trash2 v-if="!videoStore.showDeleted" :size="18" />
          <History v-else :size="18" />
          <span class="ml-2 hidden md:inline">{{ videoStore.showDeleted ? 'Sair da Lixeira' : 'Lixeira' }}</span>
        </AppButton>
      </div>
    </div>

    <!-- Video Creation Modal -->
    <AppModal 
      v-model:open="isModalOpen" 
      title="Criar Novo Vídeo" 
      description="Preencha os detalhes para gerar seu vídeo com IA."
    >
      <form
        class="wizard-form"
        @submit.prevent="handleSubmit"
      >
        <div class="app-input-group">
          <label
            for="prompt"
            class="app-label"
          >Sobre o que é o seu vídeo?</label>
          <textarea
            id="prompt"
            v-model="form.prompt"
            class="app-input modal-textarea"
            placeholder="ex: Um documentário sobre a história do café..."
            required
            autofocus
            rows="4"
          />
        </div>

        <div class="form-row">
          <div class="app-input-group">
            <label
              for="language"
              class="app-label"
            >Idioma</label>
            <div class="select-wrapper">
              <select
                id="language"
                v-model="form.language"
                class="app-select"
              >
                <option value="pt-br">
                  Português (BR)
                </option>
                <option value="en-us">
                  Inglês (US)
                </option>
                <option value="es">
                  Espanhol
                </option>
              </select>
            </div>
          </div>

          <div class="app-input-group">
            <label
              for="agent"
              class="app-label"
            >Agente (Prompt)</label>
            <div class="select-wrapper">
              <select
                id="agent"
                v-model="form.agent_id"
                class="app-select"
              >
                <option :value="undefined">
                  Padrão do Sistema
                </option>
                <option
                  v-for="agent in agents"
                  :key="agent.id"
                  :value="agent.id"
                >
                  {{ agent.name }}
                </option>
              </select>
            </div>
          </div>


          <AppInput
            id="duration"
            v-model="form.target_duration_minutes"
            label="Duração Alvo (minutos)"
            type="number"
            min="0"
            max="180"
            required
            :hint="form.target_duration_minutes == 0 ? 'IA definirá o tempo ideal' : ''"
          />
          <span
            v-if="form.target_duration_minutes === 0"
            class="text-xs text-blue-500 font-medium ml-1"
          >
            Modo Automático: A IA decidirá a duração.
          </span>
        </div>

        <!-- Row 2: Format & Auto-Image -->
        <div class="form-row">
          <div class="app-input-group">
            <label
              for="aspect_ratio"
              class="app-label"
            >Formato</label>
            <div class="select-wrapper">
              <select
                id="aspect_ratio"
                v-model="form.aspect_ratio"
                class="app-select"
              >
                <option value="16:9">
                  Horizontal (16:9)
                </option>
                <option value="9:16">
                  Vertical (9:16)
                </option>
              </select>
            </div>
          </div>

          <div class="app-input-group">
            <label
              for="auto_image"
              class="app-label"
            >Imagens Automáticas</label>
            <div class="select-wrapper">
              <select
                id="auto_image"
                v-model="form.auto_image_source"
                class="app-select"
              >
                <option value="none">
                  Manual (Escolher depois)
                </option>
                <option value="unsplash">
                  Unsplash (Artístico)
                </option>
                <option value="google">
                  Google Images
                </option>
                <option value="bing">
                  Bing Images
                </option>
              </select>
            </div>
          </div>
        </div>

        <div class="form-row">
          <div class="app-input-group checkbox-group">
            <label class="app-label">Narração</label>
            <div class="checkbox-wrapper">
              <input 
                id="auto_narration" 
                v-model="form.auto_generate_narration" 
                type="checkbox"
                class="app-checkbox"
              >
              <label
                for="auto_narration"
                class="checkbox-label"
              >Gerar Narração Automaticamente</label>
            </div>
          </div>
        </div>

        <div class="app-input-group bg-zinc-50 dark:bg-zinc-900/40 p-4 rounded-xl border border-zinc-100 dark:border-zinc-800">
          <div class="flex items-center justify-between mb-3">
            <label for="audio_padding" class="app-label !mb-0 flex items-center gap-2">
              <Music :size="16" class="text-primary" />
              Padding de Áudio
            </label>
            <span class="text-xs font-bold text-primary font-mono bg-primary/10 px-2 py-0.5 rounded">{{ form.audio_transition_padding }}s</span>
          </div>
          <div class="flex items-center gap-4">
            <input
              v-model.number="form.audio_transition_padding"
              type="range"
              min="0.3"
              max="5"
              step="0.1"
              class="flex-1 h-2 bg-zinc-200 dark:bg-zinc-800 rounded-full appearance-none cursor-pointer accent-violet-600"
            />
            <input 
              id="audio_padding"
              v-model.number="form.audio_transition_padding" 
              type="number" 
              step="0.1"
              min="0.3"
              max="5"
              class="app-input h-10 w-20 text-center font-bold !bg-white dark:!bg-zinc-950"
            />
          </div>
          <p class="text-[10px] text-zinc-400 mt-2 italic">Ajuste o tempo de silêncio entre as transições de áudio.</p>
        </div>

        <div class="form-actions">
          <AppButton
            type="submit"
            variant="primary"
            size="lg"
            :loading="videoStore.isCreating"
            title="Gerar Vídeo"
          >
            <Wand2 :size="18" />
          </AppButton>
        </div>
      </form>
    </AppModal>

    <div
      v-if="videoStore.isLoading && videoStore.videos.length === 0"
      class="loading-state"
    >
      <Loader2
        class="spinner"
        :size="32"
      />
      <p>Carregando vídeos...</p>
    </div>

    <div
      v-else-if="videoStore.videos.length === 0"
      class="empty-state"
    >
      <AppCard class="empty-card">
        <div v-if="videoStore.searchQuery || videoStore.statusFilter || videoStore.showDeleted" class="empty-content">
          <Search :size="48" class="empty-icon text-zinc-300" />
          <h3>Nenhum resultado encontrado</h3>
          <p>Tente ajustar seus filtros ou busca para encontrar o que procura.</p>
          <AppButton
            variant="outline"
            title="Limpar Filtros"
            @click="() => { videoStore.searchQuery = ''; videoStore.statusFilter = null; videoStore.showDeleted = false; videoStore.fetchVideos(); }"
          >
            Limpar tudo
          </AppButton>
        </div>
        <div v-else class="empty-content">
          <File
            :size="48"
            class="empty-icon"
          />
          <h3>Nenhum vídeo ainda</h3>
          <p>Crie seu primeiro vídeo gerado por IA para começar.</p>
          <AppButton
            variant="primary"
            title="Criar Vídeo"
            @click="openCreateModal"
          >
            <Plus :size="18" />
          </AppButton>
        </div>
      </AppCard>
    </div>

    <div
      v-else
      class="video-grid"
    >
      <div
        v-for="video in videoStore.videos"
        :key="video.id"
        class="video-item"
        :class="{ 'status-processing': video.status === 'processing' || video.status === 'rendering' || video.status === 'rendering_scenes' }"
        @click="goToDetails(video.id)"
      >
        <div class="video-info">
          <div class="video-main">
            <h3 class="video-title">
              {{ video.prompt.slice(0, 60) }}<span v-if="video.prompt.length > 60">...</span>
            </h3>
            <span class="video-meta">
              {{ formatDate(video.created_at) }} • 
              {{ video.language }} • 
              <span class="duration-small">
                {{ video.status === 'completed' && video.total_duration_seconds ? (video.total_duration_seconds / 60).toFixed(1) : video.target_duration_minutes }} min
              </span>
            </span>
          </div>
        </div>
        
        <div class="video-status">
          <div :class="['status-badge', getStatusColor(video.status)]">
            <Loader2
              v-if="['processing', 'rendering', 'rendering_scenes'].includes(video.status)"
              :size="14"
              class="spin"
            />
            <CheckCircle2
              v-if="video.status === 'completed'"
              :size="14"
            />
            <AlertCircle
              v-if="video.status === 'error'"
              :size="14"
            />
            <span>{{ video.status }}</span>
          </div>
                    <div v-if="videoStore.showDeleted" class="flex items-center gap-1">
            <button 
              class="p-2 text-green-500 hover:bg-green-50 dark:hover:bg-green-900/10 transition-colors flex items-center justify-center min-w-[36px]"
              @click.stop="handleRestore($event, video.id)"
              :disabled="isDeletingId === video.id"
              title="Restaurar Vídeo (Tirar da lixeira)"
            >
              <Loader2 v-if="isDeletingId === video.id" :size="18" class="animate-spin" />
              <RotateCcw v-else :size="18" />
            </button>
          </div>
          
          <button 
            v-else
            class="p-2 text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors delete-btn flex items-center justify-center min-w-[36px]"
            data-testid="delete-video-btn"
            @click.stop="handleDelete($event, video.id)"
            :disabled="isDeletingId === video.id"
            title="Excluir Vídeo"
          >
            <Loader2 v-if="isDeletingId === video.id" :size="18" class="animate-spin" />
            <Trash2 v-else :size="18" />
          </button>

          <ChevronRight
            :size="20"
            class="chevron"
          />
        </div>
      </div>
    </div>

  </AppLayout>
</template>

<style scoped>
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  color: var(--text-secondary);
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 0;
  color: var(--text-muted);
  gap: 1rem;
}

.spin {
  animation: spin 1s linear infinite;
}

.empty-card {
  width: 100%;
  max-width: 500px;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 1rem;
}

.empty-icon {
  color: var(--text-muted);
}

.video-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.video-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
}

.video-item:hover {
  border-color: var(--border-active);
  background: var(--bg-card-hover);
  transform: translateX(4px);
}

.video-item.status-processing {
  border-color: var(--primary-base);
  background: linear-gradient(90deg, var(--bg-card), rgba(139, 92, 246, 0.05), var(--bg-card));
  background-size: 200% 100%;
  animation: processing-pulse 3s infinite ease-in-out;
}

@keyframes processing-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.video-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.video-meta {
  font-size: 0.875rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.duration-small {
  font-weight: 600;
  color: var(--color-violet-600);
  background: var(--color-violet-50);
  padding: 1px 6px;
  border-radius: 4px;
}

.video-status {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-badge.neutral { background: var(--color-zinc-100); color: var(--color-zinc-500); }
.status-badge.warning { background: rgba(234, 179, 8, 0.1); color: #ca8a04; }
.status-badge.success { background: rgba(34, 197, 94, 0.1); color: #16a34a; }
.status-badge.danger { background: rgba(239, 68, 68, 0.1); color: #dc2626; }

.chevron {
  color: var(--text-muted);
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Wizard Form Styles inside Modal */
.wizard-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0 2.5rem 0; /* Add bottom padding to avoid cutting off fields */
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.app-input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.app-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.select-wrapper {
  position: relative;
}

.app-select {
  width: 100%;
  height: 40px;
  padding: 0 0.75rem;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.925rem;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2371717a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 1rem;
}

.app-select:focus {
  outline: none;
  border-color: var(--color-violet-500);
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.1);
}

/* Filters Toolbar Premium Styles */
.filters-toolbar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 1.25rem;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 20px -5px rgba(0, 0, 0, 0.05);
}

.dark .filters-toolbar {
  background: rgba(24, 24, 27, 0.4);
  border-color: rgba(63, 63, 70, 0.4);
}

.search-box {
  position: relative;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.search-box input {
  width: 100%;
  height: 2.75rem;
  padding: 0 1rem 0 2.75rem;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  font-size: 0.925rem;
  transition: all 0.2s ease;
}

.search-box input:focus {
  outline: none;
  border-color: var(--color-violet-500);
  box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1);
  background: white;
}

.dark .search-box input:focus {
  background: var(--bg-app);
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.filter-select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 0 0.75rem;
  height: 2.75rem;
  transition: border-color 0.2s ease;
}

.filter-select-wrapper:focus-within {
  border-color: var(--color-violet-500);
}

.filter-icon {
  color: var(--text-muted);
  margin-right: 0.5rem;
}

.filter-select-wrapper select {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 500;
  height: 100%;
  cursor: pointer;
  padding-right: 1.5rem;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%2371717a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right center;
  background-size: 1rem;
}

.filter-select-wrapper select:focus {
  outline: none;
}
.trash-toggle {
  height: 2.75rem !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

@media (min-width: 768px) {
  .filters-toolbar {
    flex-direction: row;
    align-items: center;
  }
}

.modal-textarea {
  height: auto !important;
  min-height: 100px;
  resize: vertical;
  padding: 0.75rem;
  font-family: inherit;
  line-height: 1.5;
  background: var(--color-white) !important; /* Force white background */
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
}

.modal-textarea:focus {
  outline: none;
  border-color: var(--primary-base);
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}



.checkbox-wrapper {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    min-height: 40px;
    padding: 0 0.75rem;
    background: var(--bg-card); /* Match input bg */
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.2s ease;
}

.checkbox-wrapper:hover {
    border-color: var(--border-hover);
    background: var(--bg-subtle);
}

.checkbox-wrapper:has(.app-checkbox:checked) {
    border-color: var(--primary-base);
    background: rgba(139, 92, 246, 0.05); /* Slight tint */
}

.app-checkbox {
    width: 1.25rem;
    height: 1.25rem;
    accent-color: var(--primary-base);
    cursor: pointer;
    /* Remove default styling if needed, but accent-color is usually enough for simple pro look */
}

.checkbox-label {
    font-size: 0.925rem;
    color: var(--text-primary);
    cursor: pointer;
    user-select: none;
    font-weight: 500;
}
</style>
