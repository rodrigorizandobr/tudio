<template>
  <div class="processing-timeline p-3 rounded-xl border border-gray-100 bg-white/50 backdrop-blur-sm dark:bg-gray-800/50 dark:border-gray-700 shadow-sm">
    <!-- Steps Container -->
    <div class="timeline-steps">
      <!-- Step 1: Roteiro -->
      <div
        class="step-item"
        :class="getStepClass(1, scriptProgress)"
      >
        <div class="step-content">
          <div class="step-circle">
            <span
              v-if="scriptProgress >= 100"
              class="icon-check"
            ><Check :size="16" /></span>
            <span v-else-if="getStepClass(1, scriptProgress) === 'processing'">
              <Loader2 :size="16" class="animate-spin text-primary" />
            </span>
            <span v-else>1</span>
          </div>
          <div class="step-info">
            <span class="label-title">Roteiro</span>
            <span class="label-percent">{{ scriptProgress.toFixed(0) }}%</span>
          </div>
        </div>
        <div class="step-actions">
          <button 
            class="action-btn" 
            :disabled="videoStore.isLoading"
            title="Reprocessar Roteiro (Reiniciar)"
            @click="handleReprocessScript"
          >
            <RefreshCw
              :size="14"
              :class="{ 'animate-spin': videoStore.isLoading && activeAction === 'script' }"
            />
          </button>
          <button 
            v-if="videoStore.isLoading && activeAction === 'script'"
            class="action-btn text-red-500 hover:bg-red-50" 
            title="Interromper Roteiro"
            @click="videoStore.cancelVideo(props.video.id)"
          >
            <Square :size="14" class="fill-current" />
          </button>
        </div>
      </div>

      <!-- Arrow Separator -->
      <div class="arrow-separator text-gray-300 dark:text-gray-600">
        <ArrowRight :size="16" />
      </div>

      <!-- Step 2: Mídia (Imagens e Vídeos) -->
      <div
        class="step-item"
        :class="getStepClass(2, mediaProgress)"
      >
        <div class="step-content">
          <div class="step-circle">
            <span
              v-if="mediaProgress >= 100"
              class="icon-check"
            ><Check :size="16" /></span>
            <span v-else-if="getStepClass(2, mediaProgress) === 'processing'">
              <Loader2 :size="16" class="animate-spin text-primary" />
            </span>
            <span v-else>2</span>
          </div>
          <div class="step-info">
            <span class="label-title">Mídia</span>
            <span class="label-percent">{{ mediaProgress.toFixed(0) }}%</span>
          </div>
        </div>
        <div class="step-actions">
          <button 
            class="action-btn" 
            :disabled="videoStore.isLoading || scriptProgress < 100" 
            title="Reprocessar Imagens"
            @click="handleReprocessMedia"
          >
            <RefreshCw
              :size="14"
              :class="{ 'animate-spin': videoStore.isLoading && activeAction === 'media' }"
            />
          </button>
          <button 
            v-if="videoStore.isLoading && activeAction === 'media'"
            class="action-btn text-red-500 hover:bg-red-50" 
            title="Interromper Mídia"
            @click="videoStore.cancelVideo(props.video.id)"
          >
            <Square :size="14" class="fill-current" />
          </button>
        </div>
      </div>

      <!-- Arrow Separator -->
      <div class="arrow-separator text-gray-300 dark:text-gray-600">
        <ArrowRight :size="16" />
      </div>

      <!-- Step 3: Narração -->
      <div
        class="step-item"
        :class="getStepClass(3, narrationProgress)"
      >
        <div class="step-content">
          <div class="step-circle">
            <span
              v-if="narrationProgress >= 100"
              class="icon-check"
            ><Check :size="16" /></span>
            <span v-else-if="getStepClass(3, narrationProgress) === 'processing'">
              <Loader2 :size="16" class="animate-spin text-primary" />
            </span>
            <span v-else>3</span>
          </div>
          <div class="step-info">
            <span class="label-title">Narração</span>
            <span class="label-percent">{{ narrationProgress.toFixed(0) }}%</span>
          </div>
        </div>
        <div class="step-actions">
          <button 
            class="action-btn" 
            :disabled="videoStore.isLoading || scriptProgress < 100"
            title="Reprocessar Narração"
            @click="handleReprocessAudio"
          >
            <RefreshCw
              :size="14"
              :class="{ 'animate-spin': videoStore.isLoading && activeAction === 'audio' }"
            />
          </button>
          <button 
            v-if="videoStore.isLoading && activeAction === 'audio'"
            class="action-btn text-red-500 hover:bg-red-50" 
            title="Interromper Narração"
            @click="videoStore.cancelVideo(props.video.id)"
          >
            <Square :size="14" class="fill-current" />
          </button>
        </div>
      </div>

      <!-- Arrow Separator -->
      <div class="arrow-separator text-gray-300 dark:text-gray-600">
        <ArrowRight :size="16" />
      </div>

      <!-- Step 4: Cenas (Processamento individual) -->
      <div
        class="step-item"
        :class="getStepClass(4, sceneRenderingProgress)"
      >
        <div class="step-content">
          <div class="step-circle">
            <span
              v-if="sceneRenderingProgress >= 100"
              class="icon-check"
            ><Check :size="16" /></span>
            <span v-else-if="getStepClass(4, sceneRenderingProgress) === 'processing'">
              <Loader2 :size="16" class="animate-spin text-primary" />
            </span>
            <span v-else>4</span>
          </div>
          <div class="step-info">
            <span class="label-title">Cenas</span>
            <span class="label-percent">{{ sceneRenderingProgress.toFixed(0) }}%</span>
          </div>
        </div>
        <div class="step-actions">
          <button 
            class="action-btn" 
            :disabled="videoStore.isLoading || mediaProgress < 100 || narrationProgress < 100 || props.video?.status === 'rendering_scenes'" 
            title="Gerar Vídeos das Cenas"
            @click="handleRenderScenes"
          >
            <RefreshCw
              :size="14"
              :class="{ 'animate-spin': videoStore.isLoading && activeAction === 'scenes' || props.video?.status === 'rendering_scenes' }"
            />
          </button>
          <button 
            v-if="props.video?.status === 'rendering_scenes' || (videoStore.isLoading && activeAction === 'scenes')"
            class="action-btn text-red-500 hover:bg-red-50" 
            title="Interromper Processamento de Cenas"
            @click="videoStore.cancelVideo(props.video.id)"
          >
            <Square :size="14" class="fill-current" />
          </button>
        </div>
      </div>

      <!-- Arrow Separator -->
      <div class="arrow-separator text-gray-300 dark:text-gray-600">
        <ArrowRight :size="16" />
      </div>

      <!-- Step 5: Legenda -->
      <div
        class="step-item"
        :class="captionStepClass"
      >
        <div class="step-content">
          <div class="step-circle">
            <span
              v-if="captionProgress >= 100"
              class="icon-check"
            ><Check :size="16" /></span>
            <span v-else-if="props.video?.caption_status === 'processing'">
              <Loader2 :size="16" class="animate-spin text-primary" />
            </span>
            <span v-else>5</span>
          </div>
          <div class="step-info">
            <span class="label-title">Legenda</span>
            <span class="label-percent">{{ captionStatusLabel }}</span>
          </div>
        </div>
        <div class="step-actions">
          <button
            class="action-btn"
            :disabled="videoStore.isLoading || sceneRenderingProgress < 100 || props.video?.caption_status === 'processing'"
            title="Gerar / Reprocessar Legendas"
            @click="handleReprocessCaptions"
          >
            <Captions
              v-if="captionProgress === 0 && props.video?.caption_status !== 'processing'"
              :size="14"
            />
            <RefreshCw
              v-else
              :size="14"
              :class="{ 'animate-spin': (videoStore.isLoading && activeAction === 'captions') || props.video?.caption_status === 'processing' }"
            />
          </button>
          <button 
            v-if="props.video?.caption_status === 'processing' || (videoStore.isLoading && activeAction === 'captions')"
            class="action-btn text-red-500 hover:bg-red-50" 
            title="Interromper Legendas"
            @click="videoStore.cancelVideo(props.video.id)"
          >
            <Square :size="14" class="fill-current" />
          </button>
        </div>
      </div>

      <!-- Arrow Separator -->
      <div class="arrow-separator text-gray-300 dark:text-gray-600">
        <ArrowRight :size="16" />
      </div>

      <!-- Step 6: Vídeo Final -->
      <div
        class="step-item"
        :class="getStepClass(6, renderingProgress)"
      >
        <div class="step-content">
          <div class="step-circle">
            <span
              v-if="renderingProgress >= 100"
              class="icon-check"
            ><Check :size="16" /></span>
            <span v-else-if="getStepClass(6, renderingProgress) === 'processing'">
              <Loader2 :size="16" class="animate-spin text-primary" />
            </span>
            <span v-else>6</span>
          </div>
          <div class="step-info">
            <span class="label-title">Vídeo Final</span>
            <span class="label-percent">{{ renderingProgress.toFixed(0) }}%</span>
          </div>
        </div>
        <div class="step-actions">
          <button 
            class="action-btn" 
            :disabled="videoStore.isLoading || captionProgress < 100 || isRendering"
            title="Gerar Vídeo Final"
            @click="handleRender"
          >
            <Play
              v-if="!isRendering && renderingProgress < 100 && !videoStore.isLoading"
              :size="14"
              class="ml-0.5"
            />
            <RefreshCw
              v-else
              :size="14"
              :class="{ 'animate-spin': isRendering || (videoStore.isLoading && activeAction === 'render') }"
            />
          </button>
          <button 
            v-if="isRendering || (videoStore.isLoading && activeAction === 'render')"
            class="action-btn text-red-500 hover:bg-red-50" 
            title="Interromper Renderização Final"
            @click="videoStore.cancelVideo(props.video.id)"
          >
            <Square :size="14" class="fill-current" />
          </button>
        </div>
      </div>
    </div>
    
    <!-- Error Modal -->
    <AppModal 
      v-model:open="showErrorModal" 
      title="Erro no Processamento" 
      size="sm"
    >
      <div class="flex flex-col items-center gap-4 text-center py-4">
        <div class="p-3 bg-red-100 dark:bg-red-900/30 rounded-full text-red-600 dark:text-red-400">
          <AlertTriangle :size="32" />
        </div>
        <p class="text-gray-600 dark:text-gray-300">
          {{ errorMessage }}
        </p>
        <div class="w-full flex justify-center mt-4">
          <AppButton 
            variant="secondary"
            @click="showErrorModal = false"
          >
            Fechar
          </AppButton>
        </div>
      </div>
    </AppModal>

    <!-- Reprocess Confirmation Modal -->
    <AppModal 
      v-model:open="showReprocessConfirm" 
      title="Confirmar Reprocessamento" 
      size="sm"
    >
      <div class="flex flex-col items-center gap-4 text-center py-4">
        <p class="text-gray-600 dark:text-gray-300">
          Deseja reiniciar todo o processo? Isso apagará o progresso atual.
        </p>
        <div class="w-full flex gap-3 justify-center mt-4">
          <AppButton 
            variant="secondary"
            @click="showReprocessConfirm = false"
          >
            Cancelar
          </AppButton>
          <AppButton 
            variant="danger"
            @click="confirmReprocess"
          >
            Confirmar
          </AppButton>
        </div>
      </div>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, RefreshCw, Play, ArrowRight, AlertTriangle, Captions, Loader2, Square } from 'lucide-vue-next'
import { useVideoStore } from '../../stores/video.store'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'
import api from '../../lib/axios'
const props = defineProps<{
  video: any
}>()

const videoStore = useVideoStore()
const emit = defineEmits(['action-started'])
const activeAction = ref<string | null>(null)
const showErrorModal = ref(false)
const errorMessage = ref('')
const showReprocessConfirm = ref(false)

// ... computed properties ...

// Computed Properties
const scriptProgress = computed(() => {
  if (!props.video || !props.video.chapters) return 0
  const chapters = props.video.chapters
  if (chapters.length === 0) return 0
  const completed = chapters.filter((c: any) => c.status === 'completed' || c.status === 'COMPLETED').length
  return Math.min(100, (completed / chapters.length) * 100)
})

const allScenes = computed(() => {
  if (!props.video || !props.video.chapters) return []
  let scenes: any[] = []
  props.video.chapters.forEach((c: any) => {
    if (c.subchapters) {
      c.subchapters.forEach((s: any) => {
        if (s.scenes) scenes = scenes.concat(s.scenes)
      })
    }
  })
  return scenes
})

const mediaProgress = computed(() => {
  const scenes = allScenes.value
  if (scenes.length === 0) return 0
  const processed = scenes.filter((s: any) => s.cropped_image_url || s.video_url || s.original_image_url).length
  return Math.min(100, (processed / scenes.length) * 100)
})

const narrationProgress = computed(() => {
  const scenes = allScenes.value
  if (scenes.length === 0) return 0
  const processed = scenes.filter((s: any) => s.audio_url).length
  return Math.min(100, (processed / scenes.length) * 100)
})

const sceneRenderingProgress = computed(() => {
  const scenes = allScenes.value
  if (scenes.length === 0) return 0
  const processed = scenes.filter((s: any) => s.generated_video_url).length
  const manualPercent = Math.min(100, (processed / scenes.length) * 100)
  
  // If already at the next stages, scenes must be 100%
  if (props.video?.status === 'rendering' || props.video?.status === 'completed') {
    return 100
  }
  
  // If actively rendering scenes, trust the explicit progress field more
  if (props.video?.status === 'rendering_scenes') {
    return props.video.rendering_progress || manualPercent
  }
  
  return manualPercent
})

const renderingProgress = computed(() => {
  if (!props.video || props.video.status !== 'rendering') {
    // If we have final outputs, it's 100%
    if (props.video?.outputs && Object.keys(props.video.outputs).length > 0) {
        return 100
    }
    return 0
  }
  return props.video.rendering_progress || 0
})

const isRendering = computed(() => {
  return props.video?.status === 'rendering'
})

const getStepClass = (stepId: number, progress: number) => {
  if (progress >= 100) return 'completed'
  
  // Status-aware processing state
  const status = props.video?.status
  if (status === 'processing' && stepId <= 3) return 'processing'
  if (status === 'rendering_scenes' && stepId === 4) return 'processing'
  if (status === 'rendering' && stepId === 6) return 'processing'

  if (progress > 0) return 'processing'
  return 'pending'
}

// Helper for actions
const executeAction = async (actionName: string, actionFn: () => Promise<boolean>) => {
    activeAction.value = actionName
    emit('action-started', actionName)
    const success = await actionFn()
    if (!success) {
        errorMessage.value = videoStore.error || 'Ocorreu um erro desconhecido.'
        showErrorModal.value = true
    }
    activeAction.value = null
}

// Actions
const handleReprocessScript = async () => {
  showReprocessConfirm.value = true
}

const confirmReprocess = async () => {
  showReprocessConfirm.value = false
  await executeAction('script', () => videoStore.reprocessVideo(props.video.id))
}

const handleReprocessMedia = async () => {
    await executeAction('media', () => videoStore.reprocessVideoImages(props.video.id))
}

const handleReprocessAudio = async () => {
    await executeAction('audio', () => videoStore.reprocessVideoAudio(props.video.id))
}

const handleReprocessCaptions = async () => {
    await executeAction('captions', async () => {
        try {
            await api.post(`/videos/${props.video.id}/captions/generate`, {
                style: props.video.caption_style || 'karaoke',
                force_whisper: props.video.caption_force_whisper || false,
                scope: 'video',
                options: props.video.caption_options || {}
            })
            // Optimistic update: show 'processing' immediately without waiting for next poll
            if (videoStore.currentVideo && videoStore.currentVideo.id === props.video.id) {
                videoStore.currentVideo.caption_status = 'processing'
                videoStore.currentVideo.caption_progress = 0
            }
            return true
        } catch (e: any) {
            errorMessage.value = e.response?.data?.detail || 'Erro ao gerar legendas.'
            showErrorModal.value = true
            return false
        }
    })
}

const captionProgress = computed(() => {
    if (!props.video) return 0
    const status = props.video.caption_status
    if (status === 'done') return 100
    if (status === 'processing') return props.video.caption_progress || 0
    return 0
})

const captionStatusLabel = computed(() => {
    const status = props.video?.caption_status
    if (status === 'done') return '100%'
    if (status === 'processing') {
        const p = props.video?.caption_progress || 0
        return p > 0 ? `${p}%` : 'Gerando...'
    }
    if (status === 'error') return 'Erro'
    return '0%'
})

const captionStepClass = computed(() => {
    const status = props.video?.caption_status
    if (status === 'done') return 'completed'
    if (status === 'processing') return 'processing'
    if (status === 'error') return 'error'
    return 'pending'
})

const handleRenderScenes = async () => {
    // We always use force=true when manually clicking this from timeline to avoid stuck status 409s
    await executeAction('scenes', () => videoStore.triggerSceneRender(props.video.id, true))
}

const handleRender = async () => {
    await executeAction('render', () => videoStore.triggerRender(props.video.id))
}

</script>

<style scoped>
.timeline-steps {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important; /* Critical */
  justify-content: flex-start; /* Start aligns to allow scrolling */
  align-items: center;
  width: 100%;
  overflow-x: auto;
  gap: 1rem;
  padding-bottom: 0.5rem;
  /* Scroll Snap for nice feel */
  scroll-snap-type: x mandatory;
}

.arrow-separator {
    display: block;
    min-width: 16px;
    flex-shrink: 0;
}

.step-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.5rem; 
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background-color: rgba(255,255,255,0.5);
  border: 1px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
  flex-shrink: 0; /* Never shrink */
  min-width: 140px; /* Force width to trigger scroll */
  scroll-snap-align: start;
}

/* Hide scrollbar for cleaner look */
.timeline-steps::-webkit-scrollbar {
  height: 0px;
  background: transparent;
}

.step-item {
  display: flex;
  flex-direction: row; /* Horizontal */
  align-items: center;
  gap: 0.5rem; 
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background-color: rgba(255,255,255,0.5);
  border: 1px solid transparent;
  transition: all 0.2s;
  white-space: nowrap; /* Prevent text wrapping inside step */
  flex-shrink: 0; /* Prevent steps from shrinking too much */
}

.step-item:hover {
    background-color: rgba(255,255,255,0.8);
    border-color: rgba(0,0,0,0.05);
}

.step-content {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0.5rem;
}

.step-circle {
  width: 2rem; /* Smaller circle */
  height: 2rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.875rem;
  transition: all 0.3s ease;
  background-color: var(--color-background-muted, #f3f4f6);
  border: 2px solid #e5e7eb;
  color: #9ca3af;
  flex-shrink: 0;
}

.step-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.1;
}

.label-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #6b7280;
}

.label-percent {
  font-size: 0.7rem;
  color: #9ca3af;
}

.step-actions {
    margin-left: 0.5rem;
    padding-left: 0.5rem;
    border-left: 1px solid #e5e7eb;
    display: flex;
    align-items: center;
}

.action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 0.375rem;
    color: #6b7280;
    transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
    background-color: #f3f4f6;
    color: #111827;
}

.action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* States */
.step-item.completed .step-circle {
  background-color: #10b981;
  color: white;
  border-color: #10b981;
}
.step-item.completed .label-title { color: #059669; }

.step-item.processing .step-circle {
  background-color: #7c3aed;
  color: white;
  border-color: #7c3aed;
}
.step-item.processing .label-title { color: #6d28d9; }

/* Dark Mode */
:global(.dark) .step-item {
    background-color: rgba(31, 41, 55, 0.5);
}
:global(.dark) .step-item:hover {
    background-color: rgba(31, 41, 55, 0.8);
    border-color: rgba(255,255,255,0.05);
}
:global(.dark) .step-circle {
  background-color: #374151;
  border-color: #4b5563;
}
:global(.dark) .step-actions { border-color: #4b5563; }
:global(.dark) .action-btn:hover:not(:disabled) {
    background-color: #374151;
    color: #f3f4f6;
}
</style>
