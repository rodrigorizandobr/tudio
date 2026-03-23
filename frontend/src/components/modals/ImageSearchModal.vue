<script setup lang="ts">
import { ref, watch } from 'vue'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'
import { Search, Loader2 } from 'lucide-vue-next'
import api from '../../lib/axios'

interface ImageResult {
  id: string
  url: string
  thumb: string
  width: number
  height: number
  description: string
  photographer: string
  photographer_url: string
  provider: 'unsplash' | 'serpapi' | 'bing' | 'cache'
}

interface Props {
  open: boolean
  initialQuery?: string
  initialProvider?: 'unsplash' | 'serpapi' | 'bing' | 'cache'
}

interface Emits {
  (e: 'update:open', value: boolean): void
  (e: 'select', image: ImageResult): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const searchQuery = ref('')
const results = ref<ImageResult[]>([])
const isSearching = ref(false)
const hasSearched = ref(false)
const provider = ref<'unsplash' | 'serpapi' | 'bing' | 'cache'>('unsplash')
const showError = ref(false)
const errorMsg = ref('')

// Initialize with initial query and provider when modal opens
watch(
  () => [props.open, props.initialProvider, props.initialQuery],
  ([isOpen, initialProvider, initialQuery]) => {
    if (isOpen) {
      // Set provider FIRST (before query)
      if (initialProvider && typeof initialProvider === 'string') {
        provider.value = initialProvider as 'unsplash' | 'serpapi' | 'bing' | 'cache'
        console.log('[ImageSearchModal] Setting provider to:', initialProvider)
      }
      
      // Then set query and search
      if (initialQuery && typeof initialQuery === 'string' && provider.value !== 'cache') {
        searchQuery.value = initialQuery
        handleSearch(true) // Attempt auto-load from cache only
      } else if (provider.value === 'cache') {
        // If Cache, ignore initial query and load recent images globally
        searchQuery.value = ''
        handleSearch(false)
      }
    } else {
      // Reset state when modal closes
      searchQuery.value = ''
      results.value = []
      hasSearched.value = false
      provider.value = 'unsplash' // Reset to default
    }
  }
)

const searchController = ref<AbortController | null>(null)

const handleSearch = async (onlyIfCached = false) => {
  // Allow empty search query only for 'cache' provider
  if (!searchQuery.value.trim() && provider.value !== 'cache') return
  
  // Cancel pending
  if (searchController.value) {
    searchController.value.abort()
    searchController.value = null
  }
  
  isSearching.value = true
  
  // New controller
  const controller = new AbortController()
  searchController.value = controller
  
  try {
    const response = await api.get('/images/search', {
      params: { 
        q: searchQuery.value, 
        limit: 300,
        provider: provider.value,
        only_if_cached: onlyIfCached
      },
      signal: controller.signal
    })
    
    // Logic: 
    // If we only checked cache and got nothing, treat as if we haven't searched yet (waiting for user click)
    // If not onlyIfCached (manual search), always set hasSearched to true
    
    const data = response.data
    const hasResults = data.results && data.results.length > 0
    
    if (onlyIfCached && !hasResults) {
        // Cache miss on auto-search: Do nothing visual, just keep query in input
        hasSearched.value = false
    } else {
        results.value = data.results || []
        hasSearched.value = true
    }
    
  } catch (error: any) {
    if (error.code === 'ERR_CANCELED' || error.name === 'CanceledError') {
      console.log('Image search canceled')
      return
    }

    console.error('Image search failed:', error)
    if (!onlyIfCached) {
        results.value = []
        hasSearched.value = true
        errorMsg.value = `Erro na busca: ${error.response?.data?.detail || error.message}`
        showError.value = true
    }
  } finally {
    if (searchController.value === controller) {
        isSearching.value = false
        searchController.value = null
    }
  }
}

// Watch provider for auto-search/cancel
watch(provider, (newProvider) => {
    if (newProvider === 'cache') {
        // Always clear query and fetch global recent images
        searchQuery.value = ''
        handleSearch(false)
    } else if (searchQuery.value.trim()) {
        handleSearch(false)
    }
})

const selectImage = (image: ImageResult) => {
  emit('select', image)
  emit('update:open', false)
}

const getProviderName = () => {
  if (provider.value === 'serpapi') return 'Google (SerpApi)'
  if (provider.value === 'bing') return 'Bing'
  if (provider.value === 'cache') return 'Cache Local'
  return 'Unsplash'
}
</script>

<template>
  <AppModal
    :open="open"
    title="Buscar Imagem"
    size="xl"
    @update:open="(val) => emit('update:open', val)"
  >
    <div class="search-modal">
      <div class="search-header">
        <div class="provider-tabs">
          <button 
            :class="['tab', { active: provider === 'unsplash' }]"
            title="Alta Qualidade / Artístico"
            @click="provider = 'unsplash'"
          >
            Unsplash
          </button>
          <button 
            :class="['tab', { active: provider === 'serpapi' }]"
            title="Notícias e Eventos (Google)"
            @click="provider = 'serpapi'"
          >
            Google
          </button>
          <button 
            :class="['tab', { active: provider === 'bing' }]"
            title="Alternativa Microsoft"
            @click="provider = 'bing'"
          >
            Bing
          </button>
          <button 
            :class="['tab', { active: provider === 'cache' }]"
            title="Imagens recentemente buscadas (Cache)"
            @click="provider = 'cache'"
          >
            Cache
          </button>
        </div>

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
        <p>Nenhuma imagem encontrada para "{{ searchQuery }}"</p>
      </div>

      <div
        v-else-if="results.length > 0"
        class="results-grid"
      >
        <div 
          v-for="image in results" 
          :key="image.id"
          class="image-card"
          @click="selectImage(image)"
        >
          <img
            :src="image.thumb"
            :alt="image.description"
          >
          <div class="image-overlay">
            <span class="photographer">{{ image.photographer }}</span>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <p class="attribution">
          Fotos por 
          <a
            v-if="provider === 'unsplash'"
            href="https://unsplash.com"
            target="_blank"
          >Unsplash</a>
          <a
            v-else-if="provider === 'serpapi'"
            href="https://serpapi.com"
            target="_blank"
          >Google (SerpApi)</a>
          <a
            v-else-if="provider === 'bing'"
            href="https://bing.com"
            target="_blank"
          >Bing</a>
          <span v-else-if="provider === 'cache'">Sistema Local (Cache)</span>
        </p>
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
</template>

<style scoped>
.search-modal {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-height: 400px;
}

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

.tab:hover {
  color: var(--text-primary);
  background: var(--bg-subtle);
}

.tab.active {
  color: white;
  background: var(--primary-base);
  font-weight: 500;
}

.search-bar {
  display: flex;
  gap: 0.75rem;
  align-items: stretch; /* Match heights */
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
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  max-height: 65vh;
  overflow-y: auto;
  overflow-x: hidden; /* Force hide horizontal scroll */
  padding-right: 0.5rem;
}

.image-card {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  background: var(--bg-subtle);
  width: 100%; /* Respect grid column width */
}

.image-card:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 10;
}

.image-card img {
  width: 100%;
  height: auto;
  display: block;
  object-fit: cover;
  aspect-ratio: 1 / 1; /* Square thumbnails for consistency */
  background: var(--bg-subtle);
}

.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.5rem;
  background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
  opacity: 0;
  transition: opacity 0.2s;
}

.image-card:hover .image-overlay {
  opacity: 1;
}

.photographer {
  color: white;
  font-size: 0.75rem;
  text-shadow: 0 1px 2px rgba(0,0,0,0.8);
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
</style>
