<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Play, Pause, Mic2, Loader2, Check } from 'lucide-vue-next'
import api from '../../lib/axios'

interface Voice {
  name: string;
  description: string;
  gender: string;
  category: string;
  demo_url: string;
}

defineProps<{
  modelValue: string
}>()

const emit = defineEmits(['update:modelValue'])

const voices = ref<Voice[]>([])
const isLoading = ref(true)
const currentAudio = ref<HTMLAudioElement | null>(null)
const playingVoice = ref<string | null>(null)
const isOpen = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get('/voices')
    voices.value = data
  } catch (error) {
    console.error('Failed to load voices', error)
  } finally {
    isLoading.value = false
  }
})

const selectVoice = (voiceName: string) => {
  emit('update:modelValue', voiceName)
  isOpen.value = false
}

const toggleAudio = (e: Event, voice: Voice) => {
  e.stopPropagation() // Prevent selection when clicking play
  
  if (playingVoice.value === voice.name) {
    currentAudio.value?.pause()
    playingVoice.value = null
  } else {
    if (currentAudio.value) {
      currentAudio.value.pause()
    }

    try {
        const audio = new Audio(voice.demo_url)
        console.log('Audio instance created:', audio)
        console.log('Audio setup type:', typeof audio.play)
        
        audio.onended = () => {
          playingVoice.value = null
        }
        
        audio.play().catch(err => console.error("Play failed", err))
        
        currentAudio.value = audio
        playingVoice.value = voice.name
    } catch (e) {
        console.error("Audio error", e)
    }
  }
}

const getCategoryColor = (category: string) => {
  const map: Record<string, string> = {
    'Versatile': 'text-blue-500 bg-blue-500/10',
    'Authoritative': 'text-purple-500 bg-purple-500/10',
    'Storytelling': 'text-amber-500 bg-amber-500/10',
    'Announcer': 'text-indigo-500 bg-indigo-500/10',
    'Energetic': 'text-orange-500 bg-orange-500/10',
    'Professional': 'text-slate-500 bg-slate-500/10',
    'Dynamic': 'text-red-500 bg-red-500/10',
    'Emotive': 'text-rose-500 bg-rose-500/10',
    'Friendly': 'text-emerald-500 bg-emerald-500/10',
    'Calm': 'text-teal-500 bg-teal-500/10',
    'Expressive': 'text-fuchsia-500 bg-fuchsia-500/10',
    'Realistic': 'text-cyan-500 bg-cyan-500/10',
    'Natural': 'text-lime-500 bg-lime-500/10'
  }
  return map[category] || 'text-zinc-500 bg-zinc-500/10'
}
</script>

<template>
  <div class="relative w-full">
    <!-- Selected View (Trigger) -->
    <div 
      class="w-full bg-background border border-input rounded-md px-3 py-2 text-sm flex items-center justify-between cursor-pointer hover:border-primary transition-colors"
      :class="{'border-primary ring-1 ring-primary/20': isOpen}"
      @click="isOpen = !isOpen"
    >
      <div class="flex items-center gap-2">
        <Mic2
          :size="14"
          class="text-primary"
        />
        <span
          v-if="modelValue"
          class="font-medium"
        >{{ modelValue }}</span>
        <span
          v-else
          class="text-muted-foreground"
        >Selecione uma voz...</span>
      </div>
      <Loader2
        v-if="isLoading"
        :size="14"
        class="animate-spin text-muted-foreground"
      />
    </div>

    <!-- Dropdown List -->
    <div
      v-if="isOpen"
      class="absolute z-50 w-[300px] mt-1 bg-white dark:bg-zinc-900 border border-border rounded-lg shadow-xl max-h-[300px] overflow-y-auto p-1 text-foreground"
    >
      <div
        v-if="isLoading"
        class="p-4 text-center text-muted-foreground text-xs"
      >
        Carregando vozes...
      </div>
        
      <div 
        v-for="voice in voices"
        v-else 
        :key="voice.name"
        class="group flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 cursor-pointer transition-colors relative"
        :class="{'bg-primary/5': modelValue === voice.name}"
        @click="selectVoice(voice.name)"
      >
        <!-- Play Button -->
        <button 
          class="w-8 h-8 rounded-full flex items-center justify-center bg-muted group-hover:bg-background border border-transparent group-hover:border-border transition-all text-foreground hover:text-primary z-10 shrink-0"
          :class="{'text-primary border-primary bg-primary/10': playingVoice === voice.name}"
          @click="(e) => toggleAudio(e, voice)"
        >
          <Pause
            v-if="playingVoice === voice.name"
            :size="12"
            fill="currentColor"
          />
          <Play
            v-else
            :size="12"
            fill="currentColor"
            class="ml-0.5"
          />
        </button>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between">
            <span class="font-medium text-sm truncate">{{ voice.name }}</span>
            <span
              v-if="modelValue === voice.name"
              class="text-primary"
            >
              <Check :size="14" />
            </span>
          </div>
          <div class="flex items-center gap-2 mt-0.5">
            <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
              {{ voice.gender === 'male' ? 'M' : 'F' }}
            </span>
            <span 
              class="text-[10px] px-1.5 py-0.5 rounded-full"
              :class="getCategoryColor(voice.category)"
            >
              {{ voice.category }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Backpack Overlay to close -->
    <div
      v-if="isOpen"
      class="fixed inset-0 z-40 bg-transparent"
      @click="isOpen = false"
    />
  </div>
</template>
