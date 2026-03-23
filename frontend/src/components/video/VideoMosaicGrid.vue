<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { 
  Play, Pause, Volume2, VolumeX, Maximize, 
  Download, RefreshCw
} from 'lucide-vue-next'

const props = defineProps({
  outputs: {
    type: Object,
    required: true,
    default: () => ({})
  },
  videoStatus: {
    type: String,
    default: 'completed'
  },
  renderingProgress: {
    type: Number,
    default: 0
  },
  refreshKey: {
    type: Number,
    default: 0
  },
  posterUrl: {
    type: String,
    default: ''
  }
})

const mosaicVideoRefs = ref<HTMLVideoElement[]>([])
const isPlayingSync = ref(false)
const syncTime = ref(0)


const individualPlaying = ref<Record<string, boolean>>({})
const individualMuted = ref<Record<string, boolean>>({})

// Helper to set video refs
const setMosaicVideoRef = (el: any) => {
  if (el && !mosaicVideoRefs.value.includes(el)) {
    mosaicVideoRefs.value.push(el)
  }
}

// Master Controls
const toggleSyncPlay = () => {
  isPlayingSync.value = !isPlayingSync.value
  mosaicVideoRefs.value.forEach(video => {
    if (isPlayingSync.value) video.play()
    else video.pause()
  })
  
  // Update individual states to match sync
  Object.keys(props.outputs).forEach(ratio => {
    individualPlaying.value[ratio] = isPlayingSync.value
  })
}

const handleSyncSeek = (e: any) => {
  const time = e.target.value
  syncTime.value = time
  mosaicVideoRefs.value.forEach(video => {
    video.currentTime = time
  })
}



// Individual Controls
const toggleIndividualPlay = (ratio: string) => {
  const video = mosaicVideoRefs.value.find(v => v.src.includes(props.outputs[ratio]))
  if (video) {
    if (video.paused) {
      video.play()
      individualPlaying.value[ratio] = true
    } else {
      video.pause()
      individualPlaying.value[ratio] = false
    }
  }
}

const toggleIndividualMute = (ratio: string) => {
  const video = mosaicVideoRefs.value.find(v => v.src.includes(props.outputs[ratio]))
  if (video) {
    video.muted = !video.muted
    individualMuted.value[ratio] = video.muted
  }
}

const handleFullscreen = (event: Event) => {
  const video = (event.target as HTMLElement).closest('.group')?.querySelector('video')
  if (video) {
    if (video.requestFullscreen) video.requestFullscreen()
  }
}

const getVideoUrl = (path: string) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  
  // Clean path to avoid double 'storage/' or leading slashes
  const cleanPath = path.replace(/^storage\/?/, '').replace(/^\//, '')
  
  // Robust detection: strip existing query params to check extension
  const pathPart = (cleanPath.split('?')[0] || '').toLowerCase()
  const isVideo = pathPart.endsWith('.mp4') || pathPart.endsWith('.webm')
  
  const url = `/api/storage/${cleanPath}`
  
  // CRITICAL: Final videos should NEVER use the refreshKey/cache-buster during polling.
  if (isVideo) {
    return url
  }
  
  // Use proper separator if URL already has params
  const separator = url.includes('?') ? '&' : '?'
  return props.refreshKey ? `${url}${separator}t=${props.refreshKey}` : url
}

// Reset refs on outputs change ONLY if keys or values actually changed
// This prevents polling from resetting the playing state every 3 seconds
watch(() => props.outputs, (newVal, oldVal) => {
  // Use JSON stringify for a stable content check across polling object replacements
  const newStr = JSON.stringify(newVal || {})
  const oldStr = JSON.stringify(oldVal || {})
  
  if (newStr !== oldStr) {
    console.log('[VideoMosaicGrid] Outputs content changed, resetting video references')
    mosaicVideoRefs.value = []
    
    // Reset playing state if formats changed (keys added/removed)
    const newKeys = Object.keys(newVal || {})
    const oldKeys = Object.keys(oldVal || {})
    if (newKeys.length !== oldKeys.length) {
      individualPlaying.value = {}
      // Initialize new keys
      newKeys.forEach(ratio => {
         if (individualPlaying.value[ratio] === undefined) {
           individualPlaying.value[ratio] = false
           individualMuted.value[ratio] = true
         }
      })
    }
  }
}, { deep: true, immediate: true })

onMounted(() => {
  console.log('[VideoMosaicGrid] Mounted')
})

onUnmounted(() => {
  console.log('[VideoMosaicGrid] Unmounted')
})
</script>

<template>
  <div class="p-4 md:p-8 bg-zinc-950 min-h-[500px] flex flex-col gap-8 rounded-b-2xl">
    <!-- Rendering State / Progress Overlay -->
    <div 
      v-if="videoStatus === 'rendering' || videoStatus === 'rendering_scenes'"
      class="w-full max-w-4xl mx-auto mb-8 animate-in fade-in slide-in-from-top-4 duration-700"
    >
      <div class="bg-zinc-900/50 backdrop-blur-xl border border-violet-500/30 rounded-3xl p-8 shadow-[0_0_50px_rgba(139,92,246,0.1)] relative overflow-hidden group">
        <!-- Animated Background Glow -->
        <div class="absolute -top-24 -left-24 w-48 h-48 bg-violet-600/20 rounded-full blur-[80px] group-hover:bg-violet-600/30 transition-colors"></div>
        <div class="absolute -bottom-24 -right-24 w-48 h-48 bg-fuchsia-600/20 rounded-full blur-[80px] group-hover:bg-fuchsia-600/30 transition-colors"></div>

        <div class="relative z-10 flex flex-col items-center gap-6">
          <div class="flex items-center gap-4">
            <div class="relative">
              <div class="w-16 h-16 rounded-2xl bg-violet-600/20 flex items-center justify-center border border-violet-500/30">
                <RefreshCw :size="32" class="text-violet-400 animate-spin" />
              </div>
              <div class="absolute -top-1 -right-1 w-4 h-4 bg-fuchsia-500 rounded-full animate-ping"></div>
            </div>
            <div>
              <h2 class="text-2xl font-black text-white tracking-tight">RENDERIZANDO...</h2>
              <p class="text-zinc-400 text-sm font-medium">Otimizando para múltiplos formatos</p>
            </div>
          </div>

          <div class="w-full space-y-3">
            <div class="flex justify-between items-end">
              <span class="text-[10px] font-black text-violet-400 tracking-[0.3em] uppercase">Progresso Global</span>
              <span class="text-2xl font-mono font-black text-white italic">{{ renderingProgress.toFixed(1) }}%</span>
            </div>
            <div class="h-4 w-full bg-white/5 rounded-full p-1 border border-white/10 relative overflow-hidden">
              <div 
                class="h-full bg-gradient-to-r from-violet-600 via-fuchsia-500 to-violet-600 bg-[length:200%_100%] animate-gradient-x rounded-full transition-all duration-1000 ease-out shadow-[0_0_15px_rgba(139,92,246,0.5)]"
                :style="{ width: `${renderingProgress}%` }"
              ></div>
            </div>
            <div class="flex justify-between text-[9px] font-bold text-zinc-500 tracking-wider">
              <span>ESTIMATIVA: ~2 MIN</span>
              <span>GPU ACCELERATION: ON</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Mosaic Grid -->
    <div 
      v-if="Object.keys(outputs).length > 0"
      class="grid gap-6 w-full h-full transition-all duration-700 ease-out"
      :class="[
        Object.keys(outputs).length === 1 ? 'grid-cols-1 max-w-4xl mx-auto' : 'grid-cols-1 md:grid-cols-12'
      ]"
    >

      <div 
        v-for="(url, ratio) in outputs" 
        :key="ratio"
        class="relative group rounded-2xl overflow-hidden border border-white/10 shadow-2xl transition-all duration-500 hover:scale-[1.03] hover:z-20 hover:border-violet-500/50 hover:shadow-violet-500/20 bg-zinc-900 mx-auto w-full"
        :class="[
          ratio === '9:16' ? 'md:col-span-4 lg:col-span-3 max-h-[75vh] aspect-[9/16]' : 'md:col-span-8 lg:col-span-6 aspect-video'
        ]"
      >
        <!-- Individual Badge -->
        <div class="absolute top-4 left-4 z-30 px-3 py-1 bg-black/60 backdrop-blur-md rounded-full border border-white/10 flex items-center gap-2">
          <div class="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse"></div>
          <span class="text-[10px] font-black text-white/90 tracking-wider uppercase">{{ ratio }}</span>
        </div>

        <video 
          :ref="setMosaicVideoRef"
          class="w-full h-full object-contain bg-zinc-900"
          :src="getVideoUrl(url as string)"
          :poster="getVideoUrl(posterUrl)"
          preload="none"
          loop
          muted
          playsinline
          crossorigin="anonymous"
        ></video>

        <!-- Hover Overlay -->
        <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-t from-black/80 via-transparent to-transparent flex flex-col justify-end p-4">
          <div class="flex justify-between items-center">
            <div class="flex gap-2">
              <button 
                class="p-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white hover:bg-violet-500 transition-colors"
                @click="toggleIndividualPlay(ratio as string)"
              >
                <Play v-if="!individualPlaying[ratio]" :size="14" fill="currentColor" />
                <Pause v-else :size="14" fill="currentColor" />
              </button>
              <button 
                class="p-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white hover:bg-violet-500 transition-colors"
                @click="toggleIndividualMute(ratio as string)"
              >
                <Volume2 v-if="!individualMuted[ratio]" :size="14" />
                <VolumeX v-else :size="14" />
              </button>
              <button 
                class="p-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white hover:bg-violet-500 transition-colors"
                @click="handleFullscreen($event)"
              >
                <Maximize :size="14" />
              </button>
            </div>
            <a 
              :href="getVideoUrl(url as string)" 
              target="_blank" 
              download
              class="px-3 py-1.5 rounded-full bg-violet-600 text-[10px] font-bold text-white shadow-lg shadow-violet-600/30 hover:bg-violet-500 transition-all flex items-center gap-1"
            >
              <Download :size="10" />
              DOWNLOAD
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Master Sync Controls -->
    <div 
      v-if="Object.keys(outputs).length > 1"
      class="sticky bottom-4 left-0 right-0 z-40 mx-auto w-full max-w-4xl"
    >
      <div class="bg-zinc-900/80 backdrop-blur-2xl border border-white/10 rounded-3xl p-4 shadow-[0_0_50px_rgba(139,92,246,0.15)] flex flex-col md:flex-row items-center gap-6">
        <!-- Play/Pause Big Button -->
        <button 
          class="w-14 h-14 flex-shrink-0 flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 hover:from-violet-400 hover:to-fuchsia-500 text-white transition-all transform active:scale-90 shadow-xl shadow-violet-500/30 group"
          @click="toggleSyncPlay" 
        >
          <Play v-if="!isPlayingSync" :size="28" fill="currentColor" class="translate-x-0.5 group-hover:scale-110 transition-transform" />
          <Pause v-else :size="28" fill="currentColor" class="group-hover:scale-110 transition-transform" />
        </button>

        <!-- Master Scrubber -->
        <div class="flex-grow w-full space-y-2">
          <div class="flex justify-between items-end">
            <span class="text-[9px] font-black text-violet-400 tracking-[0.2em] uppercase">Sincronização Ativa</span>
            <span class="text-[10px] font-mono text-zinc-500">MASTER TIME LOCK</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="100" 
            step="0.1"
            class="w-full accent-violet-500 h-1 rounded-full appearance-none bg-zinc-800 cursor-pointer hover:h-2 transition-all"
            :value="syncTime"
            @input="handleSyncSeek"
          />
        </div>


      </div>
    </div>
  </div>
</template>
