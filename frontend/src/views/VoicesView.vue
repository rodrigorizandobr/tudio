
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '../components/layout/AppLayout.vue'
import AppToast from '../components/ui/AppToast.vue'
import { Play, Pause, Mic2, User, Sparkles, Wand2 } from 'lucide-vue-next'
import api from '../lib/axios'

interface Voice {
  name: string;
  description: string;
  gender: string;
  category: string;
  demo_url: string;
}

const voices = ref<Voice[]>([])
const isLoading = ref(true)
const fetchError = ref<string | null>(null)
const currentAudio = ref<HTMLAudioElement | null>(null)
const playingVoice = ref<string | null>(null)

// Toast State
const showToast = ref(false)
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'info'>('info')

const triggerToast = (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
  toastMessage.value = msg
  toastType.value = type
  showToast.value = true
}

onMounted(async () => {
  try {
    const { data } = await api.get('/voices')
    voices.value = data
  } catch (error: any) {
    console.error('Failed to load voices', error)
    fetchError.value = "Não foi possível carregar as vozes. Verifique se o servidor está rodando."
  } finally {
    isLoading.value = false
  }
})

const toggleAudio = (voice: Voice) => {
  if (playingVoice.value === voice.name) {
    currentAudio.value?.pause()
    playingVoice.value = null
  } else {
    if (currentAudio.value) {
      currentAudio.value.pause()
      currentAudio.value = null
    }

    try {
        const url = getFullUrl(voice.demo_url)
        const audio = new Audio(url)
        
        audio.onended = () => {
          playingVoice.value = null
        }
        
        audio.onerror = (e) => {
            console.error("Audio playback error", e)
            triggerToast(`Não foi possível reproduzir o áudio da voz ${voice.name}.`, 'error')
            playingVoice.value = null
        }

        const playPromise = audio.play()
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.error("Play prevented or failed:", error)
                if (error.name === "NotSupportedError" || error.message.includes("supported")) {
                     triggerToast("Formato de áudio não suportado ou arquivo corrompido.", 'error')
                } else {
                     triggerToast("Erro ao tentar reproduzir áudio.", 'error')
                }
                playingVoice.value = null
            })
        }
        
        currentAudio.value = audio
        playingVoice.value = voice.name
    } catch (e) {
        console.error("Sync audio error:", e)
        triggerToast("Erro interno ao tentar tocar o áudio.", 'error')
    }
  }
}

const getFullUrl = (url: string) => {
    return url 
}

// Visual Helpers
const getGradient = (name: string) => {
  const gradients = [
    'from-rose-400 to-orange-300',
    'from-violet-400 to-purple-300',
    'from-blue-400 to-cyan-300',
    'from-emerald-400 to-teal-300',
    'from-amber-400 to-yellow-300',
    'from-fuchsia-400 to-pink-300',
    'from-indigo-400 to-blue-300',
    'from-lime-400 to-green-300',
  ]
  // Deterministic gradient based on name length/char code
  const index = name.charCodeAt(0) % gradients.length
  return gradients[index]
}

const getCategoryColor = (category: string) => {
  const map: Record<string, string> = {
    'Versatile': 'text-blue-500 bg-blue-500/10 border-blue-500/20',
    'Authoritative': 'text-purple-500 bg-purple-500/10 border-purple-500/20',
    'Storytelling': 'text-amber-500 bg-amber-500/10 border-amber-500/20',
    'Announcer': 'text-indigo-500 bg-indigo-500/10 border-indigo-500/20',
    'Energetic': 'text-orange-500 bg-orange-500/10 border-orange-500/20',
    'Professional': 'text-slate-500 bg-slate-500/10 border-slate-500/20',
    'Dynamic': 'text-red-500 bg-red-500/10 border-red-500/20',
    'Emotive': 'text-rose-500 bg-rose-500/10 border-rose-500/20',
    'Friendly': 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    'Calm': 'text-teal-500 bg-teal-500/10 border-teal-500/20',
    'Expressive': 'text-fuchsia-500 bg-fuchsia-500/10 border-fuchsia-500/20',
    'Realistic': 'text-cyan-500 bg-cyan-500/10 border-cyan-500/20',
    'Natural': 'text-lime-500 bg-lime-500/10 border-lime-500/20'
  }
  return map[category] || 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20'
}
</script>

<template>
  <AppLayout title="Galeria de Vozes">
    <div class="space-y-12 pb-12">
      <!-- Hero Section -->
      <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-zinc-900 to-black border border-white/10 p-8 md:p-12 text-center text-white isolate">
        <div class="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
        <div class="absolute -top-24 -left-24 w-96 h-96 bg-primary-base/30 rounded-full blur-3xl filter opacity-50 animate-pulse-slow" />
        <div class="absolute -bottom-24 -right-24 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl filter opacity-50 animate-pulse-slow delay-1000" />
         
        <div class="relative z-10 max-w-2xl mx-auto space-y-6">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 backdrop-blur-md text-sm font-medium text-white/90">
            <Sparkles
              :size="14"
              class="text-yellow-300"
            />
            <span>Powered by OpenAI GPT-4o Audio</span>
          </div>
          <h2 class="text-4xl md:text-5xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white to-white/60">
            Encontre a voz perfeita.
          </h2>
          <p class="text-lg text-white/70 leading-relaxed">
            Navegue por nossa coleção exclusiva de vozes neurais ultra-realistas.
            Perfeitas para narrações, contação de histórias e interações dinâmicas.
          </p>
        </div>
      </div>

      <!-- Loading State -->
      <div
        v-if="isLoading"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
      >
        <div
          v-for="i in 8"
          :key="i"
          class="h-[280px] rounded-2xl bg-zinc-100 dark:bg-zinc-800/50 animate-pulse"
        />
      </div>

      <!-- Error State -->
      <div
        v-else-if="fetchError"
        class="p-8 text-center rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500"
      >
        <p class="text-lg font-medium">
          {{ fetchError }}
        </p>
      </div>

      <!-- Grid -->
      <div
        v-else
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 md:gap-8"
      >
        <div
          v-if="voices.length === 0"
          class="col-span-full text-center py-20"
        >
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 text-muted-foreground mb-4">
            <Mic2 :size="32" />
          </div>
          <p class="text-lg text-muted-foreground">
            Nenhuma voz encontrada.
          </p>
        </div>

        <div 
          v-for="voice in voices" 
          :key="voice.name"
          class="group relative bg-white dark:bg-zinc-900/50 border border-border-subtle hover:border-primary-base/30 rounded-3xl p-6 transition-all duration-300 hover:shadow-2xl hover:shadow-primary-base/5 hover:-translate-y-1 overflow-hidden"
        >
          <!-- Playing Background Pulse -->
          <div 
            class="absolute inset-0 bg-primary-base/5 opacity-0 transition-opacity duration-500 pointer-events-none"
            :class="{ 'opacity-100': playingVoice === voice.name }"
          />

          <!-- Header: Avatar & Play -->
          <div class="relative flex items-center justify-between mb-6">
            <!-- Avatar -->
            <div 
              class="w-16 h-16 rounded-2xl bg-gradient-to-br p-[2px] shadow-lg transition-transform duration-500 group-hover:scale-105"
              :class="getGradient(voice.name)"
            >
              <div class="w-full h-full rounded-[14px] bg-white dark:bg-zinc-900 flex items-center justify-center relative overflow-hidden">
                <User 
                  :size="28" 
                  class="text-zinc-400 dark:text-zinc-500 relative z-10 transition-colors duration-300 group-hover:text-primary-base"
                  :class="{ 'text-primary-base': playingVoice === voice.name }"
                />
                <!-- Waveform Animation (Only when playing) -->
                <div
                  v-if="playingVoice === voice.name"
                  class="absolute inset-0 flex items-end justify-center gap-[3px] pb-2 opacity-50"
                >
                  <div class="w-1 bg-primary-base rounded-full animate-wave1" />
                  <div class="w-1 bg-primary-base rounded-full animate-wave2" />
                  <div class="w-1 bg-primary-base rounded-full animate-wave3" />
                  <div class="w-1 bg-primary-base rounded-full animate-wave1" />
                </div>
              </div>
            </div>

            <!-- Play Button -->
            <button 
              class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-primary-base/20 hover:scale-110 active:scale-95 shadow-md z-10"
              :class="playingVoice === voice.name 
                ? 'bg-primary-base text-white shadow-primary-base/30' 
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white hover:bg-zinc-200 dark:hover:bg-zinc-700'"
              @click="toggleAudio(voice)"
            >
              <Pause
                v-if="playingVoice === voice.name"
                :size="20"
                fill="currentColor"
                class="relative left-[1px]"
              />
              <Play
                v-else
                :size="20"
                fill="currentColor"
                class="relative left-[2px]"
              />
            </button>
          </div>
           
          <!-- Content -->
          <div class="space-y-3 relative z-10">
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-xl text-zinc-900 dark:text-white capitalize tracking-tight">
                {{ voice.name }}
              </h3>
              <span 
                class="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full border bg-opacity-10 backdrop-blur-sm"
                :class="getCategoryColor(voice.category)"
              >
                {{ voice.category }}
              </span>
            </div>
              
            <p class="text-sm text-muted-foreground leading-relaxed line-clamp-3 h-[60px]">
              {{ voice.description }}
            </p>
          </div>

          <!-- Footer -->
          <div class="mt-6 pt-4 border-t border-border-subtle flex items-center justify-between text-xs font-medium text-muted-foreground relative z-10">
            <div class="flex items-center gap-2 px-2 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800/50">
              <Mic2 :size="12" />
              <span class="capitalize">{{ voice.gender === 'male' ? 'Masculina' : voice.gender === 'female' ? 'Feminina' : 'Neutra' }}</span>
            </div>
              
            <div class="flex items-center gap-1.5 opacity-60 group-hover:opacity-100 transition-opacity">
              <Wand2 :size="12" />
              <span>AI Generated</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <AppToast 
      :visible="showToast" 
      :message="toastMessage" 
      :type="toastType" 
      :duration="3000"
      @close="showToast = false"
    />
  </AppLayout>
</template>

<style scoped>
/* Smooth Pulse Animation */
@keyframes pulse-slow {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.1); }
}
.animate-pulse-slow {
  animation: pulse-slow 8s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Waveform Animations */
@keyframes wave {
  0%, 100% { height: 4px; }
  50% { height: 16px; }
}

.animate-wave1 { animation: wave 1s ease-in-out infinite; animation-delay: 0.0s; }
.animate-wave2 { animation: wave 1s ease-in-out infinite; animation-delay: 0.2s; }
.animate-wave3 { animation: wave 1s ease-in-out infinite; animation-delay: 0.4s; }
</style>
