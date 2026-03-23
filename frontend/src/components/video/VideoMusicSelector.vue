<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Music, X, Search, Pause } from 'lucide-vue-next'
import MusicSearchModal from '../modals/MusicSearchModal.vue'

const props = defineProps<{
  modelValue: number | null | undefined // music_id
  initialTrack?: any // Optional: To show info if we only have ID initially (requires hydration parent side)
}>()

const emit = defineEmits(['update:modelValue', 'change'])

const isModalOpen = ref(false)
const selectedTrack = ref<any>(props.initialTrack || null)

// Watch for external changes (e.g. initial load)
watch(() => props.initialTrack, (val) => {
  if (val) selectedTrack.value = val
}, { immediate: true })

// If we have an ID but no track info, we might need to fetch it. 
// Ideally parent provides it, or we fetch here. For simplicity, we assume parent might resolve it 
// or we just show "Música Selecionada (ID: ...)" until we select a new one.
// Current implementation relies on 'select' event to populate info locally.

const hasMusic = computed(() => !!props.modelValue)

// Audio Preview
const isPlaying = ref(false)
const audio = ref<HTMLAudioElement | null>(null)

function handleSelect(track: any) {
  selectedTrack.value = track
  emit('update:modelValue', track.id)
  emit('change', track)
}

function removeMusic() {
  stopAudio()
  selectedTrack.value = null
  emit('update:modelValue', null)
  emit('change', null)
}

function togglePlay() {
  if (!selectedTrack.value) return

  if (isPlaying.value) {
    audio.value?.pause()
    isPlaying.value = false
  } else {
    // Stop if playing previous
    if (audio.value) audio.value.pause()
    
    // Check if we have file_path (from object) or we need to fetch?
    // If selectedTrack is full object, use file_path.
    if (selectedTrack.value.file_path) {
        audio.value = new Audio(`/api/storage/${selectedTrack.value.file_path}`)
        audio.value.onended = () => isPlaying.value = false
        audio.value.play()
        isPlaying.value = true
    }
  }
}

function stopAudio() {
  if (audio.value) {
    audio.value.pause()
    audio.value = null
  }
  isPlaying.value = false
}
</script>

<template>
  <div class="w-full">
    <!-- Selected State -->
    <div 
      v-if="hasMusic" 
      class="group relative overflow-hidden rounded-xl border border-indigo-100 bg-white dark:bg-zinc-900/50 p-4 transition-all hover:border-indigo-300 hover:shadow-md"
    >
      <div class="flex items-center gap-4">
        <!-- Play/Pause Toggle -->
        <AppButton
          variant="secondary"
          size="md"
          icon-only
          class="shrink-0 !rounded-full bg-indigo-50 text-indigo-600 hover:bg-indigo-600 hover:text-white transition-all shadow-sm"
          @click="togglePlay"
        >
          <Pause
            v-if="isPlaying"
            class="h-5 w-5 fill-current"
          />
          <Music
            v-else
            class="h-5 w-5"
          />
        </AppButton>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-0.5">
            <h4 class="font-bold text-zinc-900 dark:text-zinc-100 truncate text-sm">
              {{ selectedTrack?.title || 'Música Selecionada' }}
            </h4>
            <span
              v-if="selectedTrack?.genre"
              class="px-1.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400"
            >
              {{ selectedTrack.genre }}
            </span>
          </div>
          <p class="text-xs text-zinc-500 flex items-center gap-1.5">
            <span class="truncate">{{ selectedTrack?.artist || 'Artista Desconhecido' }}</span>
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <AppButton 
            variant="ghost" 
            size="sm"
            icon-only
            title="Trocar música"
            @click="isModalOpen = true"
          >
            <Search class="h-4 w-4" />
          </AppButton>
          <AppButton 
            variant="ghost" 
            size="sm"
            icon-only
            class="text-zinc-400 hover:text-red-600 hover:bg-red-50"
            title="Remover música"
            @click="removeMusic"
          >
            <X class="h-4 w-4" />
          </AppButton>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else>
      <button 
        class="w-full group flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-zinc-200 dark:border-zinc-800 p-10 text-center transition-all duration-300 hover:bg-indigo-50/30 hover:border-indigo-300 hover:shadow-sm"
        @click="isModalOpen = true"
      >
        <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 group-hover:scale-110 group-hover:rotate-6 transition-all duration-300 shadow-sm">
          <Music class="h-7 w-7" />
        </div>
        <div class="space-y-1.5">
          <h4 class="text-base font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Adicionar Trilha Sonora
          </h4>
          <p class="text-xs text-zinc-500 max-w-[280px] mx-auto leading-relaxed">
            Personalize a experiência do seu vídeo com músicas premium de nossa galeria.
          </p>
        </div>
      </button>
    </div>

    <MusicSearchModal 
      v-model:open="isModalOpen" 
      @select="handleSelect" 
    />
  </div>
</template>

<style scoped>
/* No extra styles needed, using Tailwind and established patterns */
</style>
