<script setup lang="ts">
import { ref, watch } from 'vue'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'
import { Search, Loader2, Play, ExternalLink, Download } from 'lucide-vue-next'
import api from '../../lib/axios'
import { useVideoDownloadStore } from '../../stores/videoDownload'

interface VideoResult {
  id: string
  video_url: string
  thumbnail: string
  width: number
  height: number
  duration: number
  description: string
  author_name: string
  author_url: string
  provider: 'pexels' | 'pixabay' | 'google'
  file_size?: number
  quality?: string
}

interface Props {
  open: boolean
  initialQuery?: string
  initialProvider?: 'pexels' | 'pixabay' | 'google'
  context?: {
      videoId: number | string
      chapterId: number
      subId: number
      sceneOrder: number
  }
}

interface Emits {
  (e: 'update:open', value: boolean): void
  (e: 'select', video: VideoResult): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const downloadStore = useVideoDownloadStore()

const searchQuery = ref('')
const results = ref<VideoResult[]>([])
const isSearching = ref(false)
const hasSearched = ref(false)
const provider = ref<'pexels' | 'pixabay' | 'google'>('pexels')
const orientation = ref<'landscape' | 'portrait' | 'square'>('landscape')
const size = ref<'large' | 'medium' | 'small'>('medium')

// Error Modal State
const isErrorModalOpen = ref(false)
const errorMessage = ref('')
const errorTitle = ref('Erro na Busca')

// Initialize with initial query and provider when modal opens
watch(
  () => [props.open, props.initialProvider, props.initialQuery],
  ([isOpen, initialProvider, initialQuery]) => {
    if (isOpen) {
      // Set provider FIRST (before query)
      if (initialProvider && typeof initialProvider === 'string') {
        provider.value = initialProvider as 'pexels' | 'pixabay' | 'google'
      }
      
      // Then set query and search
      if (initialQuery && typeof initialQuery === 'string') {
        searchQuery.value = initialQuery
        handleSearch(true) // Attempt auto-load from cache only
      }
    } else {
      // Reset state when modal closes
      searchQuery.value = ''
      results.value = []
      hasSearched.value = false
      provider.value = 'pexels' // Reset to default
    }
  }
)

const searchController = ref<AbortController | null>(null)

const handleSearch = async (onlyIfCached = false) => {
  if (!searchQuery.value.trim()) return
  
  // Cancel any pending request
  if (searchController.value) {
    searchController.value.abort()
    searchController.value = null
  }

  isSearching.value = true
  
  // Create new controller for this request
  const controller = new AbortController()
  searchController.value = controller

  try {
    const response = await api.get('/video-search/search', {
      params: { 
        q: searchQuery.value, 
        provider: provider.value,
        orientation: orientation.value,
        size: size.value,
        limit: 20,
        only_if_cached: onlyIfCached
      },
      signal: controller.signal
    })
    
    const data = response.data
    const hasResults = data.results && data.results.length > 0
    
    if (onlyIfCached && !hasResults) {
        // Cache miss on auto-search: Do nothing visual
        hasSearched.value = false
    } else {
        results.value = data.results || []
        hasSearched.value = true
    }
    
  } catch (error: any) {
    if (error.code === 'ERR_CANCELED' || error.name === 'CanceledError') {
      return // Do not process error
    }
    
    console.error('Video search failed:', error)
    if (!onlyIfCached) {
        results.value = []
        hasSearched.value = true
        showError(error)
    }
  } finally {
    // Only turn off loading if this is the active request
    if (searchController.value === controller) {
       isSearching.value = false
       searchController.value = null
    }
  }
}

// Watch provider to trigger re-search
watch(provider, () => {
  if (searchQuery.value.trim()) {
    handleSearch(false)
  }
})

const showError = (error: any) => {
  let msg = 'Erro desconhecido'
  
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail
    if (typeof detail === 'string') {
      msg = detail
    } else if (typeof detail === 'object') {
      msg = detail.message || detail.msg || JSON.stringify(detail)
    }
  } else if (error.message) {
    msg = error.message
  }
  
  errorMessage.value = msg
  errorTitle.value = 'Erro na Busca'
  isErrorModalOpen.value = true
}

const selectVideo = (video: VideoResult) => {
  emit('select', video)
  emit('update:open', false)
}

const openExternal = (url: string) => {
  if (url) window.open(url, '_blank')
}

const startDownload = (video: VideoResult) => {
  if (props.context) {
      downloadStore.startDownload(video, {
          projectVideoId: String(props.context.videoId),
          chapterId: props.context.chapterId,
          subId: props.context.subId,
          sceneIndex: props.context.sceneOrder
      })
  } else {
    downloadStore.startDownload(video)
  }
}

const getProviderName = () => {
  if (provider.value === 'pixabay') return 'Pixabay'
  if (provider.value === 'google') return 'Google (SerpApi)'
  return 'Pexels'
}

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatFileSize = (bytes?: number): string => {
  if (!bytes) return ''
  const mb = bytes / (1024 * 1024)
  return `${mb.toFixed(1)}MB`
}
</script>

<template>
  <AppModal
    :open="open"
    title="Buscar Vídeo"
    size="xl"
    @update:open="(val) => emit('update:open', val)"
  >
    <div class="search-modal">
      <div class="search-header">
        <div class="provider-tabs">
          <button 
            :class="['tab', { active: provider === 'pexels' }]"
            title="Alta Qualidade / Stock Videos"
            @click="provider = 'pexels'"
          >
            Pexels
          </button>
          <button 
            :class="['tab', { active: provider === 'pixabay' }]"
            title="Vídeos gratuitos do Pixabay"
            @click="provider = 'pixabay'"
          >
            Pixabay
          </button>
          <button 
            :class="['tab', { active: provider === 'google' }]"
            title="Busca via SerpApi"
            @click="() => { provider = 'google'; console.log('Switched to Google'); }"
          >
            Google (Beta)
          </button>
        </div>

        <div class="search-controls">
          <div class="search-bar">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Digite o termo de busca..."
              class="search-input"
              @keyup.enter="() => handleSearch(false)"
            >
            <AppButton 
              variant="primary" 
              :loading="isSearching"
              title="Buscar"
              @click="() => handleSearch(false)"
            >
              <Search :size="18" />
            </AppButton>
          </div>

          <div class="filters">
            <select
              v-model="orientation"
              class="filter-select"
            >
              <option value="landscape">
                Paisagem
              </option>
              <option value="portrait">
                Retrato
              </option>
              <option value="square">
                Quadrado
              </option>
            </select>

            <select
              v-model="size"
              class="filter-select"
            >
              <option value="large">
                Alta Qualidade
              </option>
              <option value="medium">
                Média Qualidade
              </option>
              <option value="small">
                Baixa Qualidade
              </option>
            </select>
          </div>
        </div>
      </div>

      <div
        v-if="isSearching"
        class="loading-state"
      >
        <Loader2
          :size="32"
          class="spin"
        />
        <p>Buscando em {{ getProviderName() }}...</p>
      </div>

      <div
        v-else-if="hasSearched && results.length === 0"
        class="empty-state"
      >
        <p>Nenhum vídeo encontrado para "{{ searchQuery }}"</p>
      </div>

      <div
        v-else-if="results.length > 0"
        class="results-grid"
      >
        <div 
          v-for="video in results" 
          :key="video.id"
          class="video-card"
          @click="selectVideo(video)"
        >
          <div class="video-thumbnail">
            <img
              :src="video.thumbnail"
              :alt="video.description"
            >
            <div class="play-overlay">
              <Play
                :size="32"
                fill="white"
              />
            </div>
            <div class="video-duration">
              {{ formatDuration(video.duration) }}
            </div>
          </div>
          <div class="video-info">
            <span class="author">{{ video.author_name }}</span>
            <div class="card-actions">
              <button 
                class="icon-btn-action" 
                title="Abrir em nova aba"
                @click.stop="openExternal(video.video_url || '')"
              >
                <ExternalLink :size="16" />
              </button>
              <button 
                class="icon-btn-action" 
                title="Baixar Vídeo"
                @click.stop="startDownload(video)"
              >
                <Download :size="16" />
              </button>
            </div>
            <span
              v-if="video.file_size"
              class="file-size"
            >{{ formatFileSize(video.file_size) }}</span>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <p class="attribution">
          Vídeos por 
          <a
            v-if="provider === 'pexels'"
            href="https://pexels.com"
            target="_blank"
          >Pexels</a>
          <a
            v-else-if="provider === 'pixabay'"
            href="https://pixabay.com"
            target="_blank"
          >Pixabay</a>
          <a
            v-else
            href="https://serpapi.com"
            target="_blank"
          >Google (SerpApi)</a>
        </p>
      </div>
    </div>
  </AppModal>

  <!-- Error Modal -->
  <AppModal
    v-model:open="isErrorModalOpen"
    :title="errorTitle"
    description=""
  >
    <div class="modal-error-content">
      <p>{{ errorMessage }}</p>
      <div class="modal-actions">
        <AppButton
          variant="primary"
          @click="isErrorModalOpen = false"
        >
          Entendi
        </AppButton>
      </div>
    </div>
  </AppModal>
</template>

<style scoped>
/* Previous styles... */
.search-modal {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-height: 400px;
}
/* ... existing styles ... */

.video-info {
  padding: 0.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.author {
  color: var(--text-primary);
  font-size: 0.875rem;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
    display: flex;
    gap: 0.25rem;
}

.icon-btn-action {
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--text-secondary);
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
}

.icon-btn-action:hover {
    color: var(--primary-base);
    background: var(--bg-hover);
}

.file-size {
  color: var(--text-muted);
  font-size: 0.75rem;
}
/* ... rest of styles */
.search-header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.provider-tabs {
  display: flex;
  gap: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-subtle);
}

.tab {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.tab:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-subtle);
}

.tab.active {
  color: white;
  background: var(--primary-base);
  font-weight: 500;
}

.tab:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.search-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.search-bar {
  display: flex;
  gap: 0.75rem;
  align-items: stretch;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  background: var(--bg-card);
  border: 2px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--primary-base);
}

.search-input::placeholder {
  color: var(--text-tertiary);
}

.filters {
  display: flex;
  gap: 0.75rem;
}

.filter-select {
  padding: 0.5rem 1rem;
  background: var(--bg-card);
  border: 2px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.875rem;
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s;
}

.filter-select:focus {
  border-color: var(--primary-base);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  color: var(--text-secondary);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
  max-height: 65vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.5rem;
}

.video-card {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  background: var(--bg-subtle);
}

.video-card:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 10;
}

.video-thumbnail {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--bg-subtle);
}

.video-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.play-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.2s;
}

.video-card:hover .play-overlay {
  opacity: 1;
}

.video-duration {
  position: absolute;
  bottom: 0.5rem;
  right: 0.5rem;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
}

.modal-footer {
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid var(--border-subtle);
}

.attribution {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.attribution a {
  color: var(--primary-base);
  text-decoration: none;
}

.attribution a:hover {
  text-decoration: underline;
}

.modal-error-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-error-content p {
  color: var(--text-primary);
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
