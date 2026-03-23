
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUIStore } from '../stores/ui.store'
import { CheckCircle, Trash2, Youtube, PlusCircle, ExternalLink } from 'lucide-vue-next'
import AppButton from '../components/ui/AppButton.vue'
import AppModal from '../components/ui/AppModal.vue'
import AppLayout from '../components/layout/AppLayout.vue'
import api from '../lib/axios'

// Interface matching backend SocialChannelRead
interface SocialChannel {
  id: number
  social_account_id: number
  platform: string
  title: string
  thumbnail_url: string | null
  custom_url: string | null
  subscriber_count: number
  is_active: boolean
}

const ui = useUIStore()
const channels = ref<SocialChannel[]>([])
const isDeleteModalOpen = ref(false)
const channelToDelete = ref<SocialChannel | null>(null)

// Actions
const fetchChannels = async () => {
  try {
    const response = await api.get('/social/channels')
    channels.value = response.data
  } catch (error) {
    console.error('Failed to fetch channels', error)
    ui.showToast('Erro ao carregar canais', 'error')
  }
}

const connectGoogle = async () => {
  try {
    // 1. Get Auth URL
    const response = await api.get('/social/auth/google/url')
    const authUrl = response.data.url
    
    // 2. Open Popup
    const width = 600
    const height = 700
    const left = (window.screen.width - width) / 2
    const top = (window.screen.height - height) / 2
    
    // Open Popup
    window.open(
      authUrl,
      'google_auth',
      `width=${width},height=${height},top=${top},left=${left}`
    )
    
    // 3. Listen for message from popup
    const messageHandler = (event: MessageEvent) => {
        if (event.data.type === 'SOCIAL_AUTH_SUCCESS') {
            ui.showToast('Canal conectado com sucesso!', 'success')
            fetchChannels() // Refresh list
            window.removeEventListener('message', messageHandler)
        }
    }
    
    window.addEventListener('message', messageHandler)
    
  } catch (error) {
    console.error('Auth User error', error)
    ui.showToast('Erro ao iniciar conexão com Google', 'error')
  }
}

const openDeleteModal = (channel: SocialChannel) => {
    channelToDelete.value = channel
    isDeleteModalOpen.value = true
}

const confirmDelete = async () => {
    if (!channelToDelete.value) return
    
    try {
        await api.delete(`/social/channels/${channelToDelete.value.id}`)
        ui.showToast('Canal desconectado.', 'success')
        fetchChannels()
    } catch (error) {
        console.error('Delete error', error)
        ui.showToast('Erro ao desconectar canal', 'error')
    } finally {
        isDeleteModalOpen.value = false
        channelToDelete.value = null
    }
}

const formatSubscribers = (count: number) => {
    return new Intl.NumberFormat('pt-BR', { notation: "compact", compactDisplay: "short" }).format(count)
}

onMounted(() => {
  fetchChannels()
})
</script>

<template>
  <AppLayout title="Redes Sociais">
    <div class="social-networks-view">
      <header class="page-header">
        <div class="header-content">
          <h1>Redes Sociais</h1>
          <p class="subtitle">
            Gerencie suas conexões com YouTube e outras plataformas para publicação.
          </p>
        </div>
        <AppButton
          variant="primary"
          @click="connectGoogle"
        >
          <template #icon>
            <PlusCircle :size="20" />
          </template>
          Conectar Novo Canal
        </AppButton>
      </header>

      <!-- Empty State -->
      <div
        v-if="channels.length === 0"
        class="empty-state"
      >
        <div class="icon-bg">
          <Youtube
            :size="48"
            class="text-red-500"
          />
        </div>
        <h3>Nenhum canal conectado</h3>
        <p>Conecte sua conta do YouTube para publicar seus vídeos gerados diretamente.</p>
        <AppButton
          variant="outline"
          @click="connectGoogle"
        >
          Conectar Agora
        </AppButton>
      </div>

      <!-- Channel Grid -->
      <div
        v-else
        class="channels-grid"
      >
        <div
          v-for="channel in channels"
          :key="channel.id"
          class="channel-card"
        >
          <div class="card-header">
            <div class="platform-badge">
              <Youtube :size="16" />
              <span>YouTube</span>
            </div>
            <button
              class="delete-btn"
              title="Desconectar"
              @click="openDeleteModal(channel)"
            >
              <Trash2 :size="18" />
            </button>
          </div>
              
          <div class="channel-info">
            <img
              :src="channel.thumbnail_url || '/placeholder-user.png'"
              alt="Avatar"
              class="avatar"
            >
            <div class="details">
              <h4>{{ channel.title }}</h4>
              <p class="stats">
                {{ formatSubscribers(channel.subscriber_count) }} inscritos
              </p>
              <a
                v-if="channel.custom_url"
                :href="`https://youtube.com/${channel.custom_url}`"
                target="_blank"
                class="link"
              >
                Ver canal <ExternalLink :size="12" />
              </a>
            </div>
          </div>
              
          <div class="card-footer">
            <div class="status active">
              <CheckCircle :size="14" />
              Conectado
            </div>
          </div>
        </div>
      </div>
      
      <!-- Delete Modal -->
      <AppModal 
        v-model:open="isDeleteModalOpen"
        title="Desconectar Canal"
      >
        <p>Tem certeza que deseja desconectar o canal <strong>{{ channelToDelete?.title }}</strong>?</p>
        <p class="text-sm text-gray-500 mt-2">
          Você poderá conectá-lo novamente a qualquer momento.
        </p>

        <div class="modal-footer">
          <AppButton
            variant="ghost"
            @click="isDeleteModalOpen = false"
          >
            Cancelar
          </AppButton>
          <AppButton
            variant="danger"
            @click="confirmDelete"
          >
            Desconectar
          </AppButton>
        </div>
      </AppModal>
    </div>
  </AppLayout>
</template>

<style scoped>
.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 2rem;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
}

.header-content h1 {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
}

.subtitle {
    color: var(--text-secondary);
}

/* Empty State */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem;
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    border: 1px dashed var(--border-color);
    text-align: center;
}

.icon-bg {
    width: 80px;
    height: 80px;
    background: rgba(239, 68, 68, 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1.5rem;
}

.empty-state h3 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
}

.empty-state p {
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
    max-width: 400px;
}

/* Grid */
.channels-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
}

.channel-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    transition: all 0.2s;
}

.channel-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
    border-color: var(--primary-color);
}

.card-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 1.5rem;
}

.platform-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border-radius: 99px;
    font-size: 0.875rem;
    font-weight: 500;
}

.delete-btn {
    background: none;
    border: none;
    color: var(--text-tertiary);
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
    transition: color 0.2s;
}

.delete-btn:hover {
    color: var(--error-color);
    background: var(--bg-hover);
}

.channel-info {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--border-color);
}

.details h4 {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}

.stats {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-bottom: 0.25rem;
}

.link {
    font-size: 0.8rem;
    color: var(--primary-color);
    display: flex;
    align-items: center;
    gap: 0.25rem;
    text-decoration: none;
}

.link:hover {
    text-decoration: underline;
}

.card-footer {
    border-top: 1px solid var(--border-color);
    padding-top: 1rem;
    display: flex;
    justify-content: flex-end;
}

.status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
}

.status.active {
    color: var(--success-color);
}

/* Modal text utilities since we don't use Tailwind utility classes for everything in scoped css */
.text-sm { font-size: 0.875rem; }
.text-gray-500 { color: var(--text-secondary); }
.mt-2 { margin-top: 0.5rem; }
.text-red-500 { color: #ef4444; }
</style>
