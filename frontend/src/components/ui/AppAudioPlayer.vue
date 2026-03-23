<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Play, Pause } from 'lucide-vue-next'

const props = defineProps<{
  src: string
}>()

const audio = ref<HTMLAudioElement | null>(null)
const isPlaying = ref(false)
const duration = ref(0)
const currentTime = ref(0)

const formatTime = (seconds: number) => {
  if (!seconds || isNaN(seconds)) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const togglePlay = () => {
  if (!audio.value) return
  if (isPlaying.value) {
    audio.value.pause()
  } else {
    audio.value.play()
  }
}

const onTimeUpdate = () => {
  if (audio.value) {
    currentTime.value = audio.value.currentTime
  }
}

const onLoadedMetadata = () => {
  if (audio.value) {
    duration.value = audio.value.duration
  }
}

const onEnded = () => {
  isPlaying.value = false
  currentTime.value = 0
}

const onSeek = (event: Event) => {
  const target = event.target as HTMLInputElement
  const time = parseFloat(target.value)
  if (audio.value) {
    audio.value.currentTime = time
    currentTime.value = time
  }
}

// Watch src change to reset
watch(() => props.src, () => {
  isPlaying.value = false
  currentTime.value = 0
  if (audio.value) {
    audio.value.load()
  }
})

onMounted(() => {
    // optional: auto-load if needed, usually browser handles it on distinct src
})
</script>

<template>
  <div class="audio-player">
    <audio 
      ref="audio" 
      :src="src" 
      preload="none"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
      @play="isPlaying = true"
      @pause="isPlaying = false"
      @ended="onEnded"
    />

    <button
      class="play-btn"
      title="Play/Pause"
      @click="togglePlay"
    >
      <Pause
        v-if="isPlaying"
        :size="16"
        fill="currentColor"
      />
      <Play
        v-else
        :size="16"
        fill="currentColor"
      />
    </button>

    <div class="progress-container">
      <input 
        type="range" 
        min="0" 
        :max="duration" 
        :value="currentTime" 
        class="progress-bar"
        @input="onSeek"
      >
    </div>

    <div class="time-display">
      {{ formatTime(currentTime) }}/{{ formatTime(duration) }}
    </div>
  </div>
</template>

<style scoped>
.audio-player {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-full);
  min-width: 240px;
}

.play-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-base);
  color: white;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.2s;
}

.play-btn:hover {
  opacity: 0.9;
}

.progress-container {
  flex: 1;
  display: flex;
  align-items: center;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: var(--border-subtle);
  border-radius: 2px;
  appearance: none;
  cursor: pointer;
}

.progress-bar::-webkit-slider-thumb {
  appearance: none;
  width: 10px;
  height: 10px;
  background: var(--primary-base);
  border-radius: 50%;
  cursor: pointer;
}

.time-display {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
</style>
