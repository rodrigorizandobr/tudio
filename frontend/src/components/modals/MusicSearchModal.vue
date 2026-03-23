<script setup lang="ts">
import { ref, watch } from 'vue'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import { Search, Play, Pause, Check, Music, Clock, Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits(['update:open', 'select'])

const tracks = ref<any[]>([])
const filteredTracks = ref<any[]>([])
const loading = ref(true)
const searchQuery = ref('')
const currentAudio = ref<HTMLAudioElement | null>(null)
const currentTrackId = ref<number | null>(null)
const isPlaying = ref(false)

async function fetchMusics() {
  try {
    loading.value = true
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/music/', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('Failed to fetch music')
    tracks.value = await response.json()
    filterTracks()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

function filterTracks() {
  if (!searchQuery.value) {
    filteredTracks.value = tracks.value
    return
  }
  const query = searchQuery.value.toLowerCase()
  filteredTracks.value = tracks.value.filter(t => 
    t.title.toLowerCase().includes(query) || 
    t.artist.toLowerCase().includes(query) ||
    t.genre.toLowerCase().includes(query) || 
    t.mood.toLowerCase().includes(query)
  )
}

watch(searchQuery, filterTracks)

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    if (tracks.value.length === 0) fetchMusics()
    searchQuery.value = ''
  } else {
    stopAudio()
  }
})

function selectTrack(track: any) {
  stopAudio()
  emit('select', track)
  emit('update:open', false)
}

function playTrack(track: any) {
  if (currentTrackId.value === track.id && isPlaying.value) {
    pauseAudio()
    return
  }
  stopAudio()
  
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
</script>

<template>
  <AppModal 
    :open="open" 
    title="Biblioteca de Áudio" 
    description="Explore nossa galeria de trilhas sonoras selecionadas para seu vídeo."
    size="lg"
    @update:open="$emit('update:open', $event)"
  >
    <div class="space-y-6 min-h-[500px] flex flex-col">
      <!-- Search Bar -->
      <div class="relative px-1">
        <AppInput 
          id="music-search"
          v-model="searchQuery" 
          placeholder="Busque por ritmo, clima ou gênero..." 
          class="pl-11 h-12 text-base shadow-sm border-zinc-200 focus:border-indigo-400 focus:ring-indigo-100"
        >
          <template #prefix>
            <Search class="h-5 w-5 text-zinc-400" />
          </template>
        </AppInput>
      </div>

      <!-- Content Area -->
      <div class="flex-1 overflow-hidden flex flex-col">
        <!-- Loading State -->
        <div
          v-if="loading"
          class="flex flex-col items-center justify-center py-24 gap-4"
        >
          <Loader2 class="h-10 w-10 text-indigo-500 animate-spin" />
          <p class="text-zinc-500 font-medium animate-pulse">Sincronizando biblioteca...</p>
        </div>

        <!-- Empty State -->
        <div
          v-else-if="filteredTracks.length === 0"
          class="flex flex-col items-center justify-center py-20 text-center"
        >
          <div class="h-20 w-20 bg-zinc-50 rounded-full flex items-center justify-center mb-4 border border-zinc-100 shadow-inner">
            <Music class="h-10 w-10 text-zinc-300" />
          </div>
          <h3 class="text-zinc-900 font-bold mb-1">Nenhuma música encontrada</h3>
          <p class="text-zinc-500 text-sm max-w-xs">Tente usar termos mais genéricos ou verifique se o clima está correto.</p>
          <AppButton variant="ghost" class="mt-4" @click="searchQuery = ''">Limpar busca</AppButton>
        </div>

        <!-- List -->
        <div
          v-else
          class="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-4 pb-6"
        >
          <div 
            v-for="track in filteredTracks" 
            :key="track.id"
            class="flex items-center gap-6 p-5 rounded-3xl border border-zinc-100 bg-white hover:border-violet-200 hover:shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all duration-300 group/track relative overflow-hidden"
            :class="{ 
              'border-violet-500 bg-violet-50/10 ring-1 ring-violet-500/5': currentTrackId === track.id,
              'grayscale-[0.2] opacity-70': currentTrackId !== null && currentTrackId !== track.id && isPlaying
            }"
          >
            <!-- Premium Active Indicator -->
            <div 
              v-if="currentTrackId === track.id"
              class="absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b from-violet-500 to-fuchsia-500"
            />

            <!-- Play Button (Polished Circular Design) -->
            <div class="relative h-14 w-14 shrink-0 group">
              <button 
                class="absolute inset-0 rounded-full bg-zinc-50 text-zinc-600 flex items-center justify-center transition-all duration-300 shadow-sm border border-zinc-100 group-hover/track:scale-110 group-hover/track:bg-violet-600 group-hover/track:text-white group-hover/track:border-transparent group-hover/track:shadow-violet-200 active:scale-95"
                @click.stop="playTrack(track)"
              >
                <Pause
                  v-if="currentTrackId === track.id && isPlaying"
                  class="h-6 w-6 fill-current"
                />
                <Play
                  v-else
                  class="h-6 w-6 ml-1 fill-current"
                />
              </button>
              
              <!-- Waveform Animation (Premium Pulse) -->
              <div 
                v-if="currentTrackId === track.id && isPlaying"
                class="absolute -bottom-2 left-1/2 -translate-x-1/2 flex gap-0.5 items-end h-4"
              >
                <div class="w-1 bg-violet-400 animate-[music-wave_0.5s_ease-in-out_infinite]" style="height: 40%" />
                <div class="w-1 bg-violet-600 animate-[music-wave_0.8s_ease-in-out_infinite]" style="height: 100%" />
                <div class="w-1 bg-violet-500 animate-[music-wave_0.6s_ease-in-out_infinite]" style="height: 70%" />
              </div>
            </div>

            <!-- Enhanced Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-3 mb-1.5">
                <h4 class="font-extrabold text-zinc-900 truncate tracking-tight text-lg">
                  {{ track.title }}
                </h4>
                <div class="flex items-center gap-2">
                  <span 
                    v-if="track.genre"
                    class="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-zinc-100 text-zinc-500/80 border border-zinc-200/50"
                  >
                    {{ track.genre }}
                  </span>
                  <span 
                    v-if="track.mood"
                    class="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-violet-50 text-violet-600 border border-violet-100"
                  >
                    {{ track.mood }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-3 text-sm text-zinc-400 font-medium">
                <span class="truncate">{{ track.artist }}</span>
                <span class="w-1 h-1 rounded-full bg-zinc-200" />
                <div class="flex items-center gap-1.5 opacity-60">
                  <Clock class="h-3.5 w-3.5" />
                  <span class="font-mono text-xs">{{ formatDuration(track.duration_seconds) }}</span>
                </div>
              </div>
            </div>

            <!-- Action Area -->
            <div class="flex items-center">
              <AppButton 
                variant="primary"
                size="md"
                class="px-8 rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl shadow-violet-500/20 hover:shadow-violet-500/40 hover:-translate-y-0.5 transition-all flex items-center gap-2"
                @click="selectTrack(track)"
              >
                Escolher
                <Check class="h-4 w-4" />
              </AppButton>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <template #footer>
      <AppButton
        variant="ghost"
        @click="$emit('update:open', false)"
      >
        Fechar Galeria
      </AppButton>
    </template>
  </AppModal>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0,0,0,0.02);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: var(--border-hover);
}

@keyframes music-wave {
  0%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.5); }
}
</style>
