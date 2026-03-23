<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import AppButton from '../components/ui/AppButton.vue'
import { Play, Trash2, Pause, Music, Plus, Clock, Disc, Mic2, Tag } from 'lucide-vue-next'
import MusicUploadModal from '../components/music/MusicUploadModal.vue'
import MusicDeleteModal from '../components/music/MusicDeleteModal.vue' // New component

interface MusicTrack {
  id: number
  title: string
  artist: string
  genre: string
  mood: string
  duration_seconds: number
  file_path: string
}

const tracks = ref<MusicTrack[]>([])
const loading = ref(true)

// Modals
const showUploadModal = ref(false)
const showDeleteModal = ref(false)
const trackToDelete = ref<MusicTrack | null>(null)

// Audio Player
const currentAudio = ref<HTMLAudioElement | null>(null)
const currentTrackId = ref<number | null>(null)
const isPlaying = ref(false)

async function fetchMusics() {
  try {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/music/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('Failed to fetch music')
    tracks.value = await response.json()
  } catch {
    console.error('Error fetching music')
  } finally {
    loading.value = false
  }
}

function confirmDelete(track: MusicTrack) {
  trackToDelete.value = track
  showDeleteModal.value = true
}

async function handleDelete(id: number) {
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/v1/music/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    if (!response.ok) throw new Error('Failed to delete')
    
    showDeleteModal.value = false
    trackToDelete.value = null
    await fetchMusics()
    
    if (currentTrackId.value === id) {
      stopAudio()
    }
  } catch {
    alert('Não foi possível excluir a música.')
  }
}

function playTrack(track: MusicTrack) {
  if (currentTrackId.value === track.id && isPlaying.value) {
    pauseAudio()
    return
  }
  if (currentAudio.value) {
    currentAudio.value.pause()
    currentAudio.value.currentTime = 0
  }
  const audioUrl = `/api/storage/${track.file_path}`
  currentAudio.value = new Audio(audioUrl)
  currentAudio.value.onended = () => {
    isPlaying.value = false
    currentTrackId.value = null
  }
  currentAudio.value.play().catch(e => console.error("Play error:", e))
  currentTrackId.value = track.id
  isPlaying.value = true
}

function pauseAudio() {
  if (currentAudio.value) {
    currentAudio.value.pause()
    isPlaying.value = false
  }
}

function stopAudio() {
  if (currentAudio.value) {
    currentAudio.value.pause()
    currentAudio.value = null
  }
  isPlaying.value = false
  currentTrackId.value = null
}

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

onMounted(() => {
  fetchMusics()
})
</script>

<template>
  <AppLayout>
    <div class="space-y-8 container mx-auto p-6 max-w-7xl">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 class="text-3xl font-bold tracking-tight text-zinc-900 flex items-center gap-3">
            <Music class="h-8 w-8 text-indigo-600" />
            Biblioteca de Áudio
          </h2>
          <p class="text-zinc-500 mt-1">
            Gerencie suas músicas e trilhas sonoras para seus vídeos.
          </p>
        </div>
        <AppButton
          size="lg"
          class="shadow-lg shadow-indigo-500/20"
          @click="showUploadModal = true"
        >
          <Plus class="mr-2 h-5 w-5" />
          Adicionar Música
        </AppButton>
      </div>

      <!-- Empty State -->
      <div
        v-if="!loading && tracks.length === 0"
        class="flex flex-col items-center justify-center p-12 border-2 border-dashed border-zinc-200 bg-zinc-50 rounded-xl text-center space-y-4"
      >
        <div class="bg-white p-4 rounded-full shadow-sm border border-zinc-100">
          <Music class="h-12 w-12 text-zinc-400" />
        </div>
        <div>
          <h3 class="text-lg font-semibold text-zinc-900">
            Nenhuma música encontrada
          </h3>
          <p class="text-zinc-500 max-w-md mt-1">
            Sua biblioteca está vazia. Comece enviando arquivos MP3 para usar em seus projetos.
          </p>
        </div>
        <AppButton
          variant="secondary"
          @click="showUploadModal = true"
        >
          Enviar Primeira Música
        </AppButton>
      </div>

      <!-- Music List (Table Layout) -->
      <div
        v-else
        class="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-zinc-50 text-zinc-500 uppercase font-medium text-xs tracking-wider border-b border-zinc-200">
              <tr>
                <th class="px-6 py-4 w-16">
                  Play
                </th>
                <th class="px-6 py-4">
                  Título
                </th>
                <th class="px-6 py-4">
                  Artista
                </th>
                <th class="px-6 py-4">
                  Gênero / Clima
                </th>
                <th class="px-6 py-4 text-right">
                  Duração
                </th>
                <th class="px-6 py-4 text-right">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-100">
              <tr 
                v-for="track in tracks" 
                :key="track.id" 
                class="hover:bg-zinc-50 transition-colors group"
                :class="{ 'bg-indigo-50/50': currentTrackId === track.id }"
              >
                <td class="px-6 py-4">
                  <button 
                    class="h-10 w-10 rounded-full bg-zinc-100 hover:bg-indigo-600 hover:text-white flex items-center justify-center text-indigo-600 transition-all shadow-sm hover:shadow-md group-hover:scale-110"
                    @click="playTrack(track)"
                  >
                    <Pause
                      v-if="currentTrackId === track.id && isPlaying"
                      class="h-4 w-4 fill-current"
                    />
                    <Play
                      v-else
                      class="h-4 w-4 ml-0.5 fill-current"
                    />
                  </button>
                </td>
                <td class="px-6 py-4">
                  <div class="font-medium text-zinc-900 text-base">
                    {{ track.title }}
                  </div>
                  <div class="text-xs text-zinc-500 lg:hidden">
                    {{ track.artist }}
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center gap-2 text-zinc-600">
                    <Mic2 class="h-3 w-3 text-zinc-400" />
                    {{ track.artist }}
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex flex-wrap gap-2">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700 border border-indigo-200">
                      <Disc class="mr-1 h-3 w-3" />
                      {{ track.genre }}
                    </span>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-700 border border-emerald-200">
                      <Tag class="mr-1 h-3 w-3" />
                      {{ track.mood }}
                    </span>
                  </div>
                </td>
                <td class="px-6 py-4 text-right font-mono text-zinc-500">
                  <div class="flex items-center justify-end gap-2">
                    <Clock class="h-3 w-3" />
                    {{ formatDuration(track.duration_seconds) }}
                  </div>
                </td>
                <td class="px-6 py-4 text-right">
                  <button 
                    class="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                    title="Excluir Música"
                    @click="confirmDelete(track)"
                  >
                    <Trash2 class="h-4 w-4" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Modals -->
      <MusicUploadModal 
        v-model:open="showUploadModal" 
        @success="fetchMusics" 
      />
      
      <MusicDeleteModal
        v-model:open="showDeleteModal"
        :track-id="trackToDelete?.id || null"
        :track-title="trackToDelete?.title || ''"
        @confirm="handleDelete"
      />
    </div>
  </AppLayout>
</template>
