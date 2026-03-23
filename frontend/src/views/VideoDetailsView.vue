<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVideoStore } from '../stores/video.store'
import AppLayout from '../components/layout/AppLayout.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppModal from '../components/ui/AppModal.vue'

import AppAudioPlayer from '../components/ui/AppAudioPlayer.vue'
import ImageSearchModal from '../components/modals/ImageSearchModal.vue'
import VideoSearchModal from '../components/modals/VideoSearchModal.vue'
import VideoPublishModal from '../components/modals/VideoPublishModal.vue'
import VideoProcessingTimeline from '../components/video/VideoProcessingTimeline.vue'
import VideoMusicSelector from '../components/video/VideoMusicSelector.vue'
import VideoMosaicGrid from '../components/video/VideoMosaicGrid.vue'
import InlineEditable from '../components/ui/InlineEditable.vue'
import UploadProgressToast from '../components/ui/UploadProgressToast.vue'
import { useUploadToast } from '../composables/useUploadToast'
import { agentService, type Agent } from '../services/agent.service'
import { Bot } from 'lucide-vue-next'

const { addJobs: addUploadJobs } = useUploadToast()

const handleUploadStarted = (payload: { videoTitle: string; formats: string[]; uploads: any[] }) => {
  addUploadJobs(payload)
}

// ... existing code ...

// When fetching video, if music_id exists, we should try to get the track details
// to show in the selector.
const selectedMusicTrack = ref<any>(null)
const localAudioInstructions = ref('')
const isAudioInstructionsFocused = ref(false)
let audioInstructionsSaveTimeout: any = null
// const currentAgentName = ref<string>('Padrão do Sistema') // Deprecated: using dropdown now
const agentsList = ref<Agent[]>([])
const oldStatusMap = new Map<string, any>()

// Fetch Agents for Dropdown
async function fetchAgents() {
  try {
     const loaded = await agentService.list()
     agentsList.value = loaded || []
  } catch (e) {
     console.error("Failed to fetch agents list", e)
     agentsList.value = []
  }
}

// Fetch Agent Name
// Fetch Agent Name - REMOVED (Replaced by full list fetch)
// async function fetchAgentName(agentId?: string) { ... }

// When fetching video, if music_id exists, we should try to get the track details
// to show in the selector.
async function hydrateMusicDetails(musicId: number) {
   if (!musicId) {
     selectedMusicTrack.value = null
     return
   }
   try {
      const token = localStorage.getItem('token')
      // Retrieve ALL musics (cached or new req) and find one? Or use a specific endpoint?
      // Since list is small for now, list all is fine. Or fetch specific if we had endpoint.
      // We don't have GET /music/{id} in frontend store yet, but we can quick fetch list.
      // OPTIMIZATION: create GET /api/v1/music/{id} on backend or just filter list here.
      // Let's filter list for simplicity now as per "list_all" pattern. 
      // Actually backend music router DOES NOT have get by ID for public, only delete. 
      // Let's rely on list.
      const response = await fetch('/api/v1/music/', {
         headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
         const tracks = await response.json()
         selectedMusicTrack.value = tracks.find((t: any) => t.id === musicId) || null
      }
   } catch(e) {
      console.error("Failed to hydrate music", e)
   }
}

// Update fetch function to call hydrate
// Update fetch function to call hydrate
const fetchVideoData = async () => {
  try {
    // 1. Fetch Agents for list only if empty (optimization: don't call every 3s)

    const fetchPromise = videoStore.getVideo(videoId.value, true)
    
    // 1. Fetch Agents for list only if empty (optimization: don't call every 3s)
    let agentsPromise = Promise.resolve()
    if (agentsList.value.length === 0) {
      agentsPromise = fetchAgents()
    }

    await Promise.all([fetchPromise, agentsPromise])
    
    // Detect finished captioning or new URLs to burst cache
    let needsRefresh = false
    if (videoStore.currentVideo?.chapters) {
      videoStore.currentVideo.chapters.forEach((c: any) => {
        c.subchapters?.forEach((s: any) => {
          s.scenes?.forEach((sc: any) => {
            const oldStatus = oldStatusMap.get(sc.id)
            
            // Only refresh if status transitioned from processing to done
            // Standard reactivity handles "URL appeared" for new scenes without cache bursting
            if (oldStatus === 'processing' && sc.caption_status === 'done') {
              console.log(`[Polling] Scene ${sc.id} captioning finished, flag for refresh`)
              needsRefresh = true
            }
            
            // Update map for next poll
            oldStatusMap.set(sc.id, sc.caption_status)
            oldStatusMap.set(`${sc.id}_url`, sc.captioned_video_url)
          })
        })
      })
    }
    
    // Check for completed scene rendering tasks
    for (const key in isRenderingScene.value) {
      if (isRenderingScene.value[key]) {
          const parts = key.split('-')
          if (parts.length === 3) {
             const chId = Number(parts[0])
             const subId = Number(parts[1])
             const scIdx = Number(parts[2])
             
             const chapter = videoStore.currentVideo?.chapters?.find((c: any) => c.id === chId)
             const subchapter = chapter?.subchapters?.find((s: any) => s.id === subId)
             const scene = subchapter?.scenes?.[scIdx]
             
             if (scene && scene.generated_video_url) {
                  console.log(`[Polling] Scene ${key} rendering finished, flag for refresh`)
                  isRenderingScene.value[key] = false
                  needsRefresh = true
             }
          }
      }
    }

    // Auto-clear caption generating state when polling confirms the scene is no longer processing
    for (const key in isGeneratingCaptionScene.value) {
      if (isGeneratingCaptionScene.value[key]) {
          const parts = key.split('-')
          if (parts.length === 3) {
             const chId = Number(parts[0])
             const subId = Number(parts[1])
             const scIdx = Number(parts[2])
             
             const chapter = videoStore.currentVideo?.chapters?.find((c: any) => c.id === chId)
             const subchapter = chapter?.subchapters?.find((s: any) => s.id === subId)
             const scene = subchapter?.scenes?.[scIdx]
             
             if (scene && scene.caption_status !== 'processing') {
                  console.log(`[Polling] Scene ${key} caption finished (status: ${scene.caption_status}), clearing spinner.`)
                  isGeneratingCaptionScene.value[key] = false
                  if (scene.caption_status === 'done') needsRefresh = true
             }
          }
      }
    }

    if (needsRefresh) {
      console.log("[Polling] Applying global refresh key increment")
      imageRefreshKey.value++
    }

    // Hydrate music (non-blocking if already hydrated or no change)
    if (videoStore.currentVideo?.music_id && (!selectedMusicTrack.value || selectedMusicTrack.value.id !== videoStore.currentVideo.music_id)) {
       // We don't necessarily need to await this to let the poll finish, but let's keep it safe
       await hydrateMusicDetails(videoStore.currentVideo.music_id)
    }

    // Check for completed audio generation tasks
    for (const key in isReprocessingSceneAudio.value) {
      if (isReprocessingSceneAudio.value[key]) {
          const parts = key.split('-')
          if (parts.length === 3) {
             const chId = Number(parts[0])
             const subId = Number(parts[1])
             const scIdx = Number(parts[2])
             
             const chapter = videoStore.currentVideo?.chapters?.find((c: any) => c.id === chId)
             const subchapter = chapter?.subchapters?.find((s: any) => s.id === subId)
             const scene = subchapter?.scenes?.[scIdx]
             
             if (scene && scene.audio_url) {
                 isReprocessingSceneAudio.value[key] = false
             }
          }
      }
    }

    // Check for completed scene rendering tasks
    for (const key in isRenderingScene.value) {
      if (isRenderingScene.value[key]) {
          const parts = key.split('-')
          if (parts.length === 3) {
             const chId = Number(parts[0])
             const subId = Number(parts[1])
             const scIdx = Number(parts[2])
             
             const chapter = videoStore.currentVideo?.chapters?.find((c: any) => c.id === chId)
             const subchapter = chapter?.subchapters?.find((s: any) => s.id === subId)
             const scene = subchapter?.scenes?.[scIdx]
             
             if (scene && scene.generated_video_url) {
                 console.log(`Scene ${key} rendering finished, bursting cache...`)
                 isRenderingScene.value[key] = false
                 imageRefreshKey.value++ // Force player reload
             }
          }
      }
    }
    
    // Check polling status after fetch (status might have changed)
    checkPollingStatus()
    
    // Sync local audio instructions if not focused and NOT currently saving
    if (!isAudioInstructionsFocused.value && !isSavingInline.value['audio_generation_instructions'] && videoStore.currentVideo) {
      localAudioInstructions.value = videoStore.currentVideo.audio_generation_instructions || ''
    }

    // Sync caption local state
    if (videoStore.currentVideo?.caption_style) {
      selectedCaptionStyle.value = videoStore.currentVideo.caption_style
    }
    if (videoStore.currentVideo?.caption_options) {
      captionOptions.value = { ...videoStore.currentVideo.caption_options }
    }
    if (typeof videoStore.currentVideo?.caption_force_whisper === 'boolean') {
      captionForceWhisper.value = videoStore.currentVideo.caption_force_whisper
    }
  } catch (err) {
    console.error("fetchVideoData failed:", err)
  }
}

// ... existing code ...
import { 
  ArrowLeft, 
  Loader2, 

  AlertCircle, 
  Wand2,
  Image as ImageIcon, 
  Film, 
  Music, 
  Clock, 
  User, 
  Mic2,
  AlertTriangle,
  RefreshCcw,
  RotateCcw,
  Mic,
  Square,
  Download,
  Trash2,
  Search as SearchIcon,

  Edit2,
  Save,
  ChevronDown,
  ChevronRight,
  Copy,
  Youtube,
  Globe,
  Palette,
  Tags,
  FileText,
  Monitor,
  RefreshCw,
  CheckCircle2,
  Circle,
  Captions
} from 'lucide-vue-next'

import api from '../lib/axios'

const route = useRoute()
const router = useRouter()

const videoStore = useVideoStore()
const isPublishModalOpen = ref(false)

// ─── Caption Card state ──────────────────────────────────────────────────────
const captionStyles = [
  { id: 'karaoke',    label: 'Karaoke',    emoji: '🎤' },
  { id: 'word_pop',   label: 'Word Pop',   emoji: '✨' },
  { id: 'typewriter', label: 'Typewriter', emoji: '⌨️' },
  { id: 'highlight',  label: 'Highlight',  emoji: '🔆' },
  { id: 'bounce',     label: 'Bounce',     emoji: '💫' },
]
const selectedCaptionStyle = ref('karaoke')
const captionOptions = ref<Record<string, any>>({ position: 'bottom', words_per_line: 4 })
const captionForceWhisper = ref(false)

// Poll caption status while processing
let _captionPollTimer: ReturnType<typeof setInterval> | null = null

// --- CAPTION AUTOSAVE LOGIC ---
let captionSaveTimeout: any = null
const triggerCaptionAutosave = () => {
  if (captionSaveTimeout) clearTimeout(captionSaveTimeout)
  captionSaveTimeout = setTimeout(async () => {
    if (!videoStore.currentVideo) return
    try {
      await videoStore.saveCaptionStyle(
        videoStore.currentVideo.id,
        selectedCaptionStyle.value,
        captionOptions.value,
        captionForceWhisper.value
      )
      console.log('Caption style autosaved')
    } catch (e) {
      console.error('Autosave failed:', e)
    }
  }, 1000) // 1s debounce
}

// Watch style, options, and whisper toggle for changes
watch([selectedCaptionStyle, captionOptions, captionForceWhisper], () => {
  triggerCaptionAutosave()
}, { deep: true })

const onTimelineAction = async (actionType: string) => {
  console.log('[onTimelineAction]', actionType)
  
  if (actionType === 'captions') {
    // Optimistic update for immediate feedback
    if (videoStore.currentVideo) {
      videoStore.currentVideo.caption_status = 'processing'
      videoStore.currentVideo.caption_progress = 0
    }
    resumeCaptionPoll()
  }
  
  if (actionType === 'scenes') {
    // If we trigger scenes, we should also poll for status
    checkPollingStatus()
  }
  
  // Always fetch for definitive state
  if (videoStore.currentVideo?.id) {
    await videoStore.fetchVideo(videoStore.currentVideo.id)
  }
}

const pauseCaptionPoll = () => { if (_captionPollTimer) { clearInterval(_captionPollTimer); _captionPollTimer = null } }
const resumeCaptionPoll = () => {
  pauseCaptionPoll()
  _captionPollTimer = setInterval(async () => {
    if (!videoStore.currentVideo) { pauseCaptionPoll(); return }
    if (videoStore.currentVideo.caption_status !== 'processing') { pauseCaptionPoll(); return }
    try {
      const { data } = await api.get(`/videos/${videoStore.currentVideo.id}/captions/status`)
      if (data.caption_status !== videoStore.currentVideo.caption_status) {
        await videoStore.fetchVideo(videoStore.currentVideo.id)
      }
      if (data.caption_status !== 'processing') pauseCaptionPoll()
    } catch { pauseCaptionPoll() }
  }, 3000)
}

watch(() => videoStore.currentVideo?.caption_status, (status) => {
  if (status === 'processing') resumeCaptionPoll()
  else pauseCaptionPoll()
})
// ────────────────────────────────────────────────────────────────────────────


const videoId = ref((route.params.id as string) || '')

const hasChapterErrors = computed(() => {
  if (!videoStore.currentVideo || !videoStore.currentVideo.chapters) return false
  return videoStore.currentVideo.chapters.some((c: any) => c.status === 'error')
})

const mergedOutputs = computed(() => {
  if (!videoStore.currentVideo) return {}
  const rawOutputs = videoStore.currentVideo.outputs || {}
  const captionedOutputs = videoStore.currentVideo.captioned_outputs || {}
  
  // Create a merged object where captioned versions override raw ones
  const merged = { ...rawOutputs }
  Object.keys(captionedOutputs).forEach(ratio => {
    if (captionedOutputs[ratio]) {
      merged[ratio] = captionedOutputs[ratio]
    }
  })
  return merged
})



let pollInterval: any = null

onMounted(async () => {
  console.log(`[VideoDetails] Mounting for video ${videoId.value}`)
  await fetchVideoData()
  // Initial check handled by watcher, but good to have fallback
  checkPollingStatus()
})

onUnmounted(() => {
  console.log(`[VideoDetails] Unmounting video ${videoId.value}`)
  stopPolling()
})

// Watch for route ID changes to reset everything (Fix: stuck polling on old IDs)
watch(
  () => route.params.id,
  (newId, oldId) => {
    if (newId !== oldId) {
      console.log(`[VideoDetails] Route ID changed from ${oldId} to ${newId}. Resetting polling.`)
      stopPolling()
      // Clear current video to avoid showing stale data
      videoStore.currentVideo = null
      videoId.value = String(newId)
      fetchVideoData()
    }
  }
)

// Watch for status changes to auto-start/stop polling
watch(
  () => [videoStore.currentVideo?.status, videoStore.currentVideo?.caption_status],
  () => {
    checkPollingStatus()
  },
  { deep: true }
)

const checkPollingStatus = () => {
  const status = videoStore.currentVideo?.status
  const activeStatuses = ['pending', 'processing', 'rendering', 'rendering_scenes']
  
  // Also check if any scene is processing captions
  const hasActiveSceneCaptioning = videoStore.currentVideo?.chapters?.some((c: any) => 
    c.subchapters?.some((s: any) => 
      s.scenes?.some((sc: any) => sc.caption_status === 'processing')
    )
  )

  const isCaptioning = videoStore.currentVideo?.caption_status === 'processing'

  // Check all local in-progress states
  const hasActiveReprocessing = Object.values(isReprocessingSceneAudio.value).some(v => v)
  const hasActiveRendering = Object.values(isRenderingScene.value).some(v => v)
  const hasActiveCaptionGeneration = Object.values(isGeneratingCaptionScene.value).some(v => v)

  const shouldPoll = (status && activeStatuses.includes(status))
    || hasActiveSceneCaptioning
    || isCaptioning
    || hasActiveReprocessing
    || hasActiveRendering
    || hasActiveCaptionGeneration

  if (shouldPoll) {
    startPolling()
  } else {
    stopPolling()
  }
}



const startPolling = () => {
  if (pollInterval) return // Already polling
  console.log('Starting polling...')
  pollInterval = setInterval(fetchVideoData, 3000) // Poll every 3s
}

const stopPolling = () => {
  if (pollInterval) {
    console.log(`Stopping polling for video ${videoId.value}...`)
    clearInterval(pollInterval)
    pollInterval = null
  }
}

const goBack = () => router.push('/panel')





const copyToClipboard = (text: string) => {
  if (!text) return
  navigator.clipboard.writeText(text)
}

const saveVideoField = async (field: string, value: any) => {
  if (!videoStore.currentVideo) return
  isSavingInline.value[field] = true
  try {
    console.log(`Saving ${field}:`, value)
    await videoStore.updateVideo(videoStore.currentVideo.id, {
      [field]: value
    })
  } catch (error) {
    console.error(`Failed to save ${field}:`, error)
  } finally {
    isSavingInline.value[field] = false
  }
}

// Robust Debounced save for audio instructions (Input Stability Pattern)
const handleAudioInstructionsInput = () => {
  isAudioInstructionsFocused.value = true
  if (audioInstructionsSaveTimeout) {
    clearTimeout(audioInstructionsSaveTimeout)
  }
  audioInstructionsSaveTimeout = window.setTimeout(() => {
    saveVideoField('audio_generation_instructions', localAudioInstructions.value)
  }, 1000)
}

const handleAudioInstructionsBlur = async () => {
  if (audioInstructionsSaveTimeout) {
    clearTimeout(audioInstructionsSaveTimeout)
  }
  // Keep the "focused" lock active during the PUT so polling
  // does NOT overwrite localAudioInstructions before the save completes
  await saveVideoField('audio_generation_instructions', localAudioInstructions.value)
  // Only release the lock after the PUT resolves
  isAudioInstructionsFocused.value = false
}


const isReprocessModalOpen = ref(false)
const chapterToReprocess = ref<any>(null)

const toggleAspectRatio = async (ratio: string) => {
  if (!videoStore.currentVideo) return
  
  const currentRatios = [...(videoStore.currentVideo.aspect_ratios || ['16:9'])]
  const index = currentRatios.indexOf(ratio)
  
  if (index === -1) {
    currentRatios.push(ratio)
  } else {
    // Prevent removing the last aspect ratio
    if (currentRatios.length <= 1) return
    currentRatios.splice(index, 1)
  }
  
  await saveVideoField('aspect_ratios', currentRatios)
}

const reprocessChapter = (chapter: any) => {
  chapterToReprocess.value = chapter
  isReprocessModalOpen.value = true
}

const confirmReprocessChapter = async () => {
    if (!chapterToReprocess.value || !videoStore.currentVideo) return
    
    const chapterId = chapterToReprocess.value.id
    isReprocessModalOpen.value = false
    chapterToReprocess.value = null

    const success = await videoStore.reprocessChapter(videoStore.currentVideo.id, chapterId)
    if (success) {
      // Optimistic Update
      videoStore.currentVideo.status = 'processing'
      videoStore.currentVideo.progress = 0
      startPolling()
    }
}


// --- Scene Audio Recording Logic ---
// (Legacy Mosaic Logic Removed - Moved to VideoMosaicGrid.vue)


const isCancelling = ref(false)
const isDeleting = ref(false)

const handleCancel = async () => {
  if (!confirm('Tem certeza que deseja cancelar a geração deste vídeo? Todo o progresso atual será perdido.')) {
     return
  }
  
  isCancelling.value = true
  try {
     await videoStore.cancelVideo(Number(videoId.value))
     showError('O processamento do vídeo foi cancelado.', 'Cancelado')
  } catch (e: any) {
     showError('Falha ao cancelar: ' + (e.message || 'Erro desconhecido'), 'Erro')
  } finally {
     isCancelling.value = false
  }
}

const handleDeleteVideo = async () => {
  // Soft delete as requested (mark as deleted)
  // No confirmation required as per request: "nao precisa nem ter confirmacao para apagar o video"
  isDeleting.value = true
  try {
    const success = await videoStore.deleteVideo(Number(videoId.value))
    if (success) {
      router.push('/panel')
    }
  } catch (e: any) {
    showError('Falha ao excluir vídeo: ' + (e.message || 'Erro desconhecido'), 'Erro')
  } finally {
    isDeleting.value = false
  }
}

const recordingState = ref<Record<string, 'idle' | 'recording' | 'recorded'>>({})
const audioBlobs = ref<Record<string, Blob>>({})
const mediaRecorders = ref<Record<string, MediaRecorder>>({})
const audioChunks = ref<Record<string, Blob[]>>({})

// Error Modal State
const isErrorModalOpen = ref(false)
const errorMessage = ref('')

// Image Search Modal State
const isImageSearchOpen = ref(false)
const currentSearchScene = ref<any>(null)
const imageRefreshKey = ref(0)
/* isReprocessingSceneAudio moved below to match original location */


const currentSearchContext = ref({ chapterId: 0, subId: 0, sceneOrder: 0 }) // Robust context storage
const isDownloadingImage = ref(false)

// Video Search Modal State
const isVideoSearchOpen = ref(false)
const currentVideoSearchScene = ref<any>(null)
const currentVideoSearchContext = ref({ chapterId: 0, subId: 0, sceneOrder: 0 })
const isDownloadingVideo = ref(false)

// Crop Editor State
const cropEditorOpen = ref(false)
const cropImageUrl = ref('')
const currentCropScene = ref<any>(null)
const currentCropSceneId = ref('')
const isSavingCrop = ref(false)

// Video Player Selection
const selectedFormat = ref('16:9')

watch(
  () => videoStore.currentVideo?.outputs,
  (outputs) => {
    if (outputs) {
      const availableKeys = Object.keys(outputs)
      if (availableKeys.length > 0 && !availableKeys.includes(selectedFormat.value)) {
        // Prioritize 16:9 if it exists, otherwise use the first available
        selectedFormat.value = availableKeys.includes('16:9') ? '16:9' : (availableKeys[0] || '16:9')
      }
    }
  },
  { immediate: true, deep: true }
)

const openImageSearch = async (scene: any, chapterId: number, subId: number, sceneOrder: number) => {
  // Store context explicitly
  currentSearchContext.value = {
      chapterId: chapterId,
      subId: subId,
      sceneOrder: sceneOrder
  }
  
  // Set scene data first
  currentSearchScene.value = scene
  
  // Wait for Vue to process the reactive update before opening modal
  await nextTick()
  
  // Now open the modal with the updated scene data
  isImageSearchOpen.value = true
}

// Helper to get image source (local vs external)
const getImageUrl = (path: string) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  
  const separator = path.includes('?') ? '&' : '?'
  // CACHE BUSTING: Append the global refresh key to force update on change
  return `/api/storage/${path}${separator}t=${imageRefreshKey.value}`
}

const getVideoUrl = (path: string) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  
  // Remove 'storage/' prefix and leading slash
  const cleanPath = path.replace(/^storage\/?/, '').replace(/^\//, '')
  
  // Robust detection: strip existing query params to check extension
  const pathPart = (cleanPath.split('?')[0] || '').toLowerCase()
  const isVideo = pathPart.endsWith('.mp4') || pathPart.endsWith('.webm')
  
  const url = `/api/storage/${cleanPath}`
  
  // CRITICAL: Final videos should NEVER use the refreshKey during polling.
  if (isVideo) {
    // If the path already has a timestamp from backend, we keep it as is.
    // Our goal is just to NOT add the frontend's imageRefreshKey which changes often.
    return url
  }
  
  // Use proper separator if URL already has params
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}t=${imageRefreshKey.value}`
}

const handleImageSelect = async (image: any) => {
  if (!currentSearchScene.value || !videoStore.currentVideo) {
    showError('Vídeo não carregado. Tente novamente.')
    return
  }
  
  // Optimistic update: Show image immediately using external URL
  const tempUrl = image.url
  currentSearchScene.value.original_image_url = tempUrl
  imageRefreshKey.value++ // Force UI update
  
  // Close search modal immediately and show loading
  isImageSearchOpen.value = false
  isDownloadingImage.value = true
  
  try {
    // 1. Get IDs from the robust context
    const { chapterId, subId, sceneOrder } = currentSearchContext.value
    
    // Fallback safety (should not happen with new context)
    const safeCh = chapterId || 1
    const safeSub = subId || 1
    const safeSc = sceneOrder || 1
    
    const sceneId = `${safeCh}-${safeSub}-${safeSc}`
    
    console.log('Downloading image:', {
      video_id: videoStore.currentVideo.id,
      scene_id: sceneId,
      image_url: image.url,
      context: currentSearchContext.value
    })
    
    // Call download endpoint
    const downloadResponse = await api.post('/images/download', {
      image_url: image.url,
      video_id: videoStore.currentVideo.id,
      scene_id: sceneId
    })
    
    console.log('Download response:', downloadResponse.data)
    
    // CRITICAL FIX: Ensure we update the EXACT object in the store before saving
    // Do not rely solely on currentSearchScene reference
    const targetScene = findSceneInStore(safeCh, safeSub, safeSc)
    if (targetScene) {
        console.log(`Updating scene ${sceneId} url to:`, downloadResponse.data.original_image_url)
        targetScene.original_image_url = downloadResponse.data.original_image_url
        
        // Update local reference too for UI
        currentSearchScene.value.original_image_url = downloadResponse.data.original_image_url
    } else {
        console.error("CRITICAL: Could not find scene in store to update:", sceneId)
    }
    
    imageRefreshKey.value++
    
    // Save updated video
    console.log("Saving video with updated scene...", JSON.parse(JSON.stringify(targetScene || {})))
    await api.put(`/videos/${videoStore.currentVideo.id}`, videoStore.currentVideo)
    
    console.log('Image downloaded and saved:', downloadResponse.data.original_image_url)
    
    // Refresh video data
    // Refresh video data (non-blocking for success)
    try {
      await videoStore.getVideo(String(videoStore.currentVideo.id))
    } catch (refreshError) {
      console.warn('Video refresh failed after image update, but image was saved:', refreshError)
    }
    
    // Stop loading
    isDownloadingImage.value = false
    
  } catch (error: any) {
    isDownloadingImage.value = false
    console.error('Failed to download image:', error)
    
    let msg = 'Erro desconhecido'
    if (error.response?.data?.detail) {
        msg = typeof error.response.data.detail === 'object' 
              ? JSON.stringify(error.response.data.detail) 
              : error.response.data.detail
    } else if (error.message) {
        msg = error.message
    }
    
    showError('Falha ao baixar imagem: ' + msg, 'Erro no Download')
  }
}

const errorTitle = ref('Atenção')

const showError = (message: string, title: string = 'Atenção') => {
  errorMessage.value = typeof message === 'object' ? JSON.stringify(message) : message
  errorTitle.value = title
  isErrorModalOpen.value = true
}

/* openCropEditor removed as it is unused in the current version */

const handleCropSaved = async (croppedUrl: string) => {
  if (!currentCropSceneId.value || !videoStore.currentVideo) return
  
  isSavingCrop.value = true
  
  try {
    // Parse ID to find exact scene in store
    // ID Format: chapter-sub-scene
    const parts = currentCropSceneId.value.split('-')
    if (parts.length !== 3) {
        throw new Error("ID de cena inválido para salvar crop")
    }
    const chOrder = Number(parts[0])
    const subOrder = Number(parts[1])
    const scOrder = Number(parts[2])

    // Find the scene in the store explicitly
    const targetScene = findSceneInStore(chOrder, subOrder, scOrder)
    
    if (targetScene) {
        // Update scene with cropped URL
        targetScene.cropped_image_url = croppedUrl
        // Update local reference too
        if (currentCropScene.value) {
            currentCropScene.value.cropped_image_url = croppedUrl
        }
        
        console.log(`Updating scene ${currentCropSceneId.value} cropped_url to:`, croppedUrl)
    } else {
        throw new Error("Cena não encontrada no store para atualizar")
    }
    
    // Save to backend
    await api.put(`/videos/${videoStore.currentVideo.id}`, videoStore.currentVideo)
    
    console.log('Image cropped successfully:', croppedUrl)
    
    // Force refresh from server
    await videoStore.getVideo(videoId.value)
    
    // Force UI update by changing key
    imageRefreshKey.value++
    
  } catch (error: any) {
    console.error('Failed to save cropped image:', error)
    showError('Falha ao salvar crop: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSavingCrop.value = false
  }
}

const getAudioStream = async (): Promise<MediaStream> => {
  // 1. Try modern API
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    return await navigator.mediaDevices.getUserMedia({ audio: true })
  }

  // 2. Try legacy standard
  const nav = navigator as any
  const getUserMedia = nav.getUserMedia || nav.webkitGetUserMedia || nav.mozGetUserMedia || nav.msGetUserMedia

  if (getUserMedia) {
    return new Promise((resolve, reject) => {
       getUserMedia.call(nav, { audio: true }, resolve, reject)
    })
  }

  throw new Error('Seu navegador não suporta gravação de áudio ou o contexto não é seguro (HTTPS).')
}

const startRecording = async (sceneId: string) => {
  try {
    const stream = await getAudioStream()
    const mediaRecorder = new MediaRecorder(stream)
    mediaRecorders.value[sceneId] = mediaRecorder
    audioChunks.value[sceneId] = []

    mediaRecorder.ondataavailable = (event) => {
      if (audioChunks.value[sceneId]) {
        audioChunks.value[sceneId].push(event.data)
      }
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks.value[sceneId], { type: 'audio/webm' })
      audioBlobs.value[sceneId] = blob
      recordingState.value[sceneId] = 'recorded'
      
      // Stop all tracks to release microphone
      stream.getTracks().forEach(track => track.stop())
      // onstop logic handled in stopRecording for upload access
    }

    mediaRecorder.start()
    recordingState.value[sceneId] = 'recording'
  } catch (err: any) {
    console.error('Error accessing microphone:', err)
    showError(err.message || 'Erro ao acessar o microfone. Verifique as permissões.')
  }
}

const isUploading = ref<Record<string, boolean>>({})

const stopRecording = (sceneId: string, chapterId?: number, subchapterId?: number, sceneIndex?: number) => {
  const recorder = mediaRecorders.value[sceneId]
  if (recorder && recorder.state !== 'inactive') {
    recorder.stop()
    
    // Setup one-time listener for save/upload
    recorder.onstop = async () => {
      const blob = new Blob(audioChunks.value[sceneId], { type: 'audio/webm' })
      audioBlobs.value[sceneId] = blob
      recordingState.value[sceneId] = 'recorded'
      
      // Stop tracks
      const stream = recorder.stream
      stream.getTracks().forEach(track => track.stop())

      // Calculate duration
      const audioUrl = URL.createObjectURL(blob)
      const audio = new Audio(audioUrl)
      
      // Wait for metadata to get duration
      audio.onloadedmetadata = async () => {
         const duration = audio.duration
         
         // Upload if we have IDs
         if (chapterId !== undefined && subchapterId !== undefined && sceneIndex !== undefined) {
            isUploading.value[sceneId] = true
            await videoStore.uploadSceneAudio(
               Number(videoId.value), 
               chapterId, 
               subchapterId, 
               sceneIndex, 
               blob,
               duration
            )
            isUploading.value[sceneId] = false
         }
         
         // cleanup
         // window.URL.revokeObjectURL(audioUrl) // keep valid for local play if needed until refresh
      }
    }
  }
}





// Delete Audio Logic
const isDeleteModalOpen = ref(false)
const pendingDeleteArgs = ref<{sceneId: string, chapterId: number, subId: number, idx: number} | null>(null)

const openDeleteModal = (sceneId: string, chapterId: number, subId: number, idx: number) => {
  pendingDeleteArgs.value = { sceneId, chapterId, subId, idx }
  isDeleteModalOpen.value = true
}

const confirmDelete = async () => {
    if (!pendingDeleteArgs.value) return
    const { sceneId, chapterId, subId, idx } = pendingDeleteArgs.value
    
    // Call store
    await videoStore.deleteSceneAudio(Number(videoId.value), chapterId, subId, idx)
    
    // Cleanup local state
    if (audioBlobs.value[sceneId]) delete audioBlobs.value[sceneId]
    if (recordingState.value[sceneId]) delete recordingState.value[sceneId]
    
    isDeleteModalOpen.value = false
    pendingDeleteArgs.value = null
}

const getAudioSource = (sceneId: string, audioUrl?: string) => {
  if (audioBlobs.value[sceneId]) {
    return URL.createObjectURL(audioBlobs.value[sceneId])
  }
  if (audioUrl) {
    return audioUrl
  }
  return ''
}

const downloadAudio = (sceneId: string, sceneIndex: number, audioUrl?: string) => {
  const blob = audioBlobs.value[sceneId]
  
  const downloadFromUrl = (url: string) => {
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `scene_${sceneIndex + 1}_narration.webm`
      document.body.appendChild(a)
      a.click()
      if (blob) window.URL.revokeObjectURL(url)
  }

  if (blob) {
    downloadFromUrl(URL.createObjectURL(blob))
  } else if (audioUrl) {
    // If backend url, open directly or fetch to blob? 
    // Link download works for same origin.
    downloadFromUrl(audioUrl)
  }
}

const getSceneUniqueId = (chapterId: number, subchapterId: number, sceneIndex: number) => {
  return `${chapterId}-${subchapterId}-${sceneIndex}`
}

const findSceneInStore = (chOrder: number, subOrder: number, scOrder: number) => {
  if (!videoStore.currentVideo?.chapters) return null
  
  const chapter = videoStore.currentVideo.chapters.find((c: any) => c.order === chOrder)
  if (!chapter) return null
  
  const subchapter = chapter.subchapters?.find((s: any) => s.order === subOrder)
  if (!subchapter) return null
  
  // Scene order is 1-based index usually, but let's check how it's stored. 
  // In the loop: (scene as any).order might be reliable now.
  // The 'scenes' array is ordered. scene.order should match.
  return subchapter.scenes?.find((s: any) => s.order === scOrder)
}

// Video Search Functions
const openVideoSearch = async (scene: any, chapterId: number, subId: number, sceneOrder: number) => {
  // Store context explicitly
  currentVideoSearchContext.value = {
    chapterId: chapterId,
    subId: subId,
    sceneOrder: sceneOrder
  }
  
  // Set scene data first
  currentVideoSearchScene.value = scene
  
  // Wait for Vue to process the reactive update before opening modal
  await nextTick()
  
  // Now open the modal with the updated scene data
  isVideoSearchOpen.value = true
}

const handleVideoSelect = async (video: any) => {
  if (!currentVideoSearchScene.value || !videoStore.currentVideo) {
    showError('Vídeo não carregado. Tente novamente.')
    return
  }
  
  // Optimistic update: Show video immediately using external URL
  const tempUrl = video.video_url
  currentVideoSearchScene.value.video_url = tempUrl
  
  // Close search modal immediately and show loading
  isVideoSearchOpen.value = false
  isDownloadingVideo.value = true
  
  try {
    // 1. Get IDs from the robust context
    const { chapterId, subId, sceneOrder } = currentVideoSearchContext.value
    
    // Fallback safety (should not happen with new context)
    const safeCh = chapterId || 1
    const safeSub = subId || 1
    const safeSc = sceneOrder || 1
    
    const sceneId = `${safeCh}-${safeSub}-${safeSc}`
    
    console.log('Downloading video:', {
      video_id: videoStore.currentVideo.id,
      scene_id: sceneId,
      video_url: video.video_url,
      context: currentVideoSearchContext.value
    })
    
    // Call download endpoint
    const downloadResponse = await api.post('/video-search/download', {
      video_url: video.video_url,
      video_id: String(video.id),
      provider: video.provider,
      project_video_id: videoStore.currentVideo.id,
      chapter_id: chapterId,
      subchapter_id: subId,
      scene_index: sceneOrder
    })
    
    console.log('Video download response:', downloadResponse.data)
    
    // Update scene with permanent local URL
    currentVideoSearchScene.value.video_url = downloadResponse.data.local_url
    
    // Save updated video
    await api.put(`/videos/${videoStore.currentVideo.id}`, videoStore.currentVideo)
    
    console.log('Video downloaded and saved:', downloadResponse.data.local_url)
    
    // Refresh video data (non-blocking for success)
    try {
      await videoStore.getVideo(String(videoStore.currentVideo.id))
    } catch (refreshError) {
      console.warn('Video refresh failed after video update, but video was saved:', refreshError)
    }
    
    // Stop loading
    isDownloadingVideo.value = false
    
  } catch (error: any) {
    isDownloadingVideo.value = false
    console.error('Failed to download video:', error)
    
    let msg = 'Erro desconhecido'
    if (error.response?.data?.detail) {
      msg = typeof error.response.data.detail === 'object' 
            ? JSON.stringify(error.response.data.detail) 
            : error.response.data.detail
    } else if (error.message) {
      msg = error.message
    }
    
    showError('Falha ao baixar vídeo. Objeto recebido: ' + JSON.stringify(video) + '. Erro API: ' + msg, 'Erro no Download')
  }
}


// --- Collapse Logic ---
const collapsedChapters = ref<Set<number>>(new Set())
const collapsedSubchapters = ref<Set<string>>(new Set()) // Use composite key "chId-subId"

const toggleChapter = (chapterId: number) => {
  if (collapsedChapters.value.has(chapterId)) {
    collapsedChapters.value.delete(chapterId)
  } else {
    collapsedChapters.value.add(chapterId)
  }
}

const toggleSubchapter = (chapterId: number, subId: number) => {
  const key = `${chapterId}-${subId}`
  if (collapsedSubchapters.value.has(key)) {
    collapsedSubchapters.value.delete(key)
  } else {
    collapsedSubchapters.value.add(key)
  }
}

const isChapterCollapsed = (chapterId: number) => collapsedChapters.value.has(chapterId)
const isSubchapterCollapsed = (chapterId: number, subId: number) => collapsedSubchapters.value.has(`${chapterId}-${subId}`)

// --- Character Editing Logic ---
import AppVoiceSelector from '../components/ui/AppVoiceSelector.vue'

const editingCharacterName = ref<string | null>(null)
const editCharacterForm = ref({
  name: '',
  description: '',
  voice: ''
})
const isSavingCharacter = ref(false)

const startEditingCharacter = (char: any) => {
  editingCharacterName.value = char.name
  editCharacterForm.value = {
    name: char.name,
     // Priority logic matching backend
    description: char.physical_description || char.description || '',
    voice: char.voice || char.voice_type || ''
  }
}

const cancelEditingCharacter = () => {
  editingCharacterName.value = null
  editCharacterForm.value = { name: '', description: '', voice: '' }
}

const saveCharacter = async () => {
  if (!editingCharacterName.value || !videoStore.currentVideo) return

  isSavingCharacter.value = true
  try {
    // Clone existing characters to avoid mutating state directly before save
    const currentChars = videoStore.currentVideo.characters || []
    const updatedCharacters = [...currentChars]
    
    // Find index using the ORIGINAL name (stored in editingCharacterName)
    const index = updatedCharacters.findIndex((c: any) => c.name === editingCharacterName.value)
    
    if (index !== -1) {
      // Update character data
      // We map description to both description fields to be safe/consistent
      updatedCharacters[index] = {
        ...updatedCharacters[index],
        name: editCharacterForm.value.name,
        description: editCharacterForm.value.description,
        physical_description: editCharacterForm.value.description, // Sync both
        voice: editCharacterForm.value.voice
      }

      // Call API
      await api.put(`/videos/${videoStore.currentVideo.id}`, {
        characters: updatedCharacters
      })
      
      // Update local store immediately to reflect changes
      videoStore.currentVideo.characters = updatedCharacters
      
      // Close edit mode
      editingCharacterName.value = null
      
      // Optional: Show success toast/notification
    }
  } catch (error: any) {
    console.error('Failed to save character:', error)
    showError('Falha ao salvar personagem: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSavingCharacter.value = false
  }
}

// --- Scene Editing Logic ---


const getCharacterVoice = (charName: string) => {
  if (!videoStore.currentVideo || !videoStore.currentVideo.characters) return 'Voz Padrão'
  const char = videoStore.currentVideo.characters.find((c: any) => c.name === charName)
  return char?.voice || char?.voice_type || 'Voz Padrão'
}




const isDuplicateLoading = ref(false)

const handleDuplicateVideo = async () => {
    if (!videoStore.currentVideo) return
    
    // Confirm? Maybe not needed for duplicate, it's non-destructive.
    // But good UX to show loading.
    isDuplicateLoading.value = true
    try {
        const newVideo = await videoStore.duplicateVideo(videoStore.currentVideo.id)
        if (newVideo) {
             // Force full reload or router push
            router.push({ name: 'video-details', params: { id: newVideo.id } })
        }
    } catch (error) {
        console.error("Failed to duplicate:", error)
        showError("Falha ao duplicar vídeo.", "Erro")
    } finally {
        isDuplicateLoading.value = false
    }
}

const isSavingInline = ref<Record<string, boolean>>({})

const handleInlineSave = async (scene: any, field: string, value: string, chapterId: number, subId: number, sceneIdx: number) => {
    if (!videoStore.currentVideo) return

    // Construct a unique key for loading state
    const sceneUniqueId = getSceneUniqueId(chapterId, subId, sceneIdx)
    const key = `${sceneUniqueId}-${field}`
    
    // Check strict equality to avoid unnecessary saves (though component handles this too)
    if (scene[field] === value) return

    isSavingInline.value[key] = true
    
    console.log(`Inline saving ${field} for scene ${sceneUniqueId}:`, value)
    
    try {
        // Update local object immediately
        scene[field] = value 
        
        // Save entire video structure
        await api.put(`/videos/${videoStore.currentVideo.id}`, {
            chapters: videoStore.currentVideo.chapters
        })
        
        console.log('Inline save success')
        
    } catch (error: any) {
        console.error('Inline save failed:', error)
        showError('Falha ao salvar alteração: ' + (error.response?.data?.detail || error.message))
        // Revert? Complex without deep clone. For now trusting user to retry.
    } finally {
        isSavingInline.value[key] = false
    }
}

const isTogglingDelete = ref<Record<string, boolean>>({})

const toggleSceneDelete = async (scene: any, chapterId: number, subId: number, sceneIdx: number) => {
    if (!videoStore.currentVideo) return
    
    const sceneUniqueId = getSceneUniqueId(chapterId, subId, sceneIdx)
    isTogglingDelete.value[sceneUniqueId] = true
    
    try {
        // Toggle local state
        scene.deleted = !scene.deleted
        
        // Save entire video structure
        // We use the same generic update because we added 'deleted' to the model
        await api.put(`/videos/${videoStore.currentVideo.id}`, {
            chapters: videoStore.currentVideo.chapters
        })
        
        console.log(`Scene ${sceneUniqueId} delete status toggled to ${scene.deleted}`)
        
    } catch (error: any) {
        console.error('Failed to toggle delete:', error)
        showError('Falha ao atualizar status da cena: ' + (error.message || error))
        // Revert local change on error
        scene.deleted = !scene.deleted
    } finally {
        isTogglingDelete.value[sceneUniqueId] = false
    }
}



const isReprocessingSceneAudio = ref<Record<string, boolean>>({})

const isRenderingScene = ref<Record<string, boolean>>({})

const isGeneratingCaptionScene = ref<Record<string, boolean>>({})

const handleRenderScene = async (sceneKey: string, chapterId: number, subId: number, sceneIdx: number) => {
  if (!videoStore.currentVideo) return
  isRenderingScene.value[sceneKey] = true
  try {
    // Optimistic: clear the existing URL so the player immediately shows a loading state
    const chapter = videoStore.currentVideo.chapters?.find((c: any) => c.id === chapterId)
    const subchapter = chapter?.subchapters?.find((s: any) => s.id === subId)
    if (subchapter?.scenes?.[sceneIdx]) {
      subchapter.scenes[sceneIdx].generated_video_url = null
    }
    const success = await videoStore.renderScene(videoStore.currentVideo.id, chapterId, subId, sceneIdx)
    if (success) {
        startPolling()
    } else {
        isRenderingScene.value[sceneKey] = false
    }
  } catch (e) {
    console.error('[handleRenderScene] Error:', e)
    isRenderingScene.value[sceneKey] = false
  }
}

const generateSceneCaption = async (sceneKey: string, sceneId: number) => {
  if (!videoStore.currentVideo) return
  isGeneratingCaptionScene.value[sceneKey] = true
  try {
    await api.post(`/videos/${videoStore.currentVideo.id}/scenes/${sceneId}/captions/generate`)
    // Optimistic update: set the scene's caption_status to 'processing' immediately
    // so the spinner stays visible until polling confirms the real status.
    videoStore.currentVideo.chapters?.forEach((c: any) => {
      c.subchapters?.forEach((s: any) => {
        s.scenes?.forEach((sc: any) => {
          if (sc.id === sceneId) {
            sc.caption_status = 'processing'
          }
        })
      })
    })
    // Trigger polling immediately to show "processing" state
    startPolling()
    // NOTE: isGeneratingCaptionScene[key] is NOT reset here.
    // The polling loop in fetchVideoData will reset it when caption_status is no longer 'processing'.
  } catch (e) {
    console.error('[generateSceneCaption] Error:', e)
    // Reset on error so the button becomes clickable again
    isGeneratingCaptionScene.value[sceneKey] = false
  }
}


const reprocessSceneAudio = async (sceneId: string, scene: any, chapterId: number, subId: number, sceneIdx: number) => {
  if (!videoStore.currentVideo) return
  
  // CRITICAL: Save video state before reprocessing to ensure instructions/voice changes are applied
  try {
      await api.put(`/videos/${videoStore.currentVideo.id}`, videoStore.currentVideo)
  } catch (saveError) {
      console.error("Failed to save video state before audio reprocessing", saveError)
      showError("Falha ao salvar alterações antes de gerar o áudio.")
      return
  }
  
  isReprocessingSceneAudio.value[sceneId] = true
  scene.audio_url = null // Optimistically clear audio to show it is regenerating
  
  console.log(`Reprocessing info - Target: Ch ${chapterId} > Sub ${subId} > Idx ${sceneIdx}`)

  try {
     // Hierarchical API Call
     await api.post(`/videos/${videoStore.currentVideo.id}/chapters/${chapterId}/subchapters/${subId}/scenes/${sceneIdx}/reprocess/audio`)
     
     // CLEAR LOCAL STATE: remove microphone blob and reset recording state
     if (audioBlobs.value[sceneId]) delete audioBlobs.value[sceneId]
     if (audioChunks.value[sceneId]) delete audioChunks.value[sceneId]
     recordingState.value[sceneId] = 'idle'
     
     // Trigger polling to reflect the "Processing" status and eventually the new audio
     startPolling()
  } catch (error: any) {
     console.error('Failed to reprocess scene audio:', error)
     showError('Falha ao gerar áudio com IA: ' + (error.response?.data?.detail || error.message))
     isReprocessingSceneAudio.value[sceneId] = false
  }
}
</script>

<template>
  <AppLayout>
    <div
      v-if="videoStore.isLoading && !videoStore.currentVideo"
      class="loading-full-page"
    >
      <Loader2 class="spinner-xl" />
      <p>Carregando detalhes do vídeo...</p>
    </div>

    <template v-else-if="videoStore.currentVideo">
    <div class="details-header">
      <AppButton
        variant="ghost"
        size="sm"
        class="back-btn"
        title="Voltar para o Dashboard"
        @click="goBack"
      >
        <ArrowLeft :size="20" />
      </AppButton>
      
      <div
        v-if="videoStore.currentVideo"
        class="header-content"
      >
        <div class="title-section">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <h1 class="text-3xl font-bold tracking-tight text-foreground">
                  {{ videoStore.currentVideo.title || videoStore.currentVideo.prompt }}
                </h1>
                <button
                  class="p-1 text-muted-foreground/50 hover:text-primary transition-colors"
                  title="Copiar Título"
                  @click="copyToClipboard(videoStore.currentVideo.title || videoStore.currentVideo.prompt)"
                >
                  <Copy :size="18" />
                </button>
              </div>
              <span
                v-if="!videoStore.currentVideo.title"
                class="text-xs text-muted-foreground uppercase tracking-wider font-semibold mt-1 block"
              >
                Prompt Original
              </span>

              <!-- Cancelled Banner -->
              <div
                v-if="videoStore.currentVideo.status === 'cancelled'"
                class="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 rounded-full text-xs font-semibold border border-amber-200 dark:border-amber-800"
              >
                <AlertCircle :size="14" />
                Processamento Cancelado
              </div>
            </div>
            <div class="flex items-center gap-2">
              <AppButton
                v-if="['pending', 'processing', 'rendering', 'rendering_scenes'].includes(videoStore.currentVideo?.status) || videoStore.currentVideo?.caption_status === 'processing'"
                variant="outline"
                size="sm"
                class="gap-2 text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300 dark:border-red-900/30 dark:text-red-400 dark:hover:bg-red-900/10"
                :loading="isCancelling"
                title="Interromper geração"
                @click="handleCancel"
              >
                <Square v-if="!isCancelling" :size="16" class="fill-current" />
                {{ isCancelling ? 'Parando...' : 'Parar' }}
              </AppButton>

              <AppButton 
                v-if="videoStore.currentVideo?.status === 'completed'"
                variant="primary" 
                size="md"
                title="Publicar no YouTube"
                @click="isPublishModalOpen = true"
              >
                <Youtube :size="20" />
                Publicar
              </AppButton>

              <AppButton 
                variant="secondary" 
                size="md"
                :disabled="isDuplicateLoading || videoStore.isLoading"
                title="Duplicar Vídeo"
                @click="handleDuplicateVideo"
              >
                <component
                  :is="isDuplicateLoading ? RefreshCw : Copy"
                  :size="18"
                  :class="{ 'animate-spin': isDuplicateLoading }"
                />
                {{ isDuplicateLoading ? 'Duplicando...' : 'Duplicar' }}
              </AppButton>

              <AppButton
                variant="outline"
                size="md"
                class="hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10"
                :loading="isDeleting"
                title="Excluir Vídeo"
                data-testid="delete-video-btn"
                @click="handleDeleteVideo"
              >
                <Trash2 :size="18" />
              </AppButton>
            </div>
          </div>
            
          <!-- Moved button to be inside the flex container for alignment -->
            
          <!-- Topic / Prompt Section -->
          <div class="description-box mt-4 p-4 bg-muted/30 rounded-lg border border-border/50 relative group">
            <h3 class="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
              <span class="w-1 h-4 bg-indigo-500 rounded-full" />
              Assunto Original (Prompt)
            </h3>
            <p class="text-base text-muted-foreground leading-relaxed whitespace-pre-wrap pr-8">
              {{ videoStore.currentVideo.prompt }}
            </p>
            <button 
              class="absolute top-4 right-4 p-1.5 text-muted-foreground/50 hover:text-primary hover:bg-primary/5 rounded-md transition-colors opacity-0 group-hover:opacity-100" 
              title="Copiar Assunto" 
              @click="copyToClipboard(videoStore.currentVideo.prompt)"
            >
              <Copy :size="16" />
            </button>
          </div>

          <div class="description-box mt-4 p-4 bg-muted/30 rounded-lg border border-border/50 relative group">
            <h3 class="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
              <span class="w-1 h-4 bg-primary rounded-full" />
              Sobre o Vídeo
            </h3>
            <p
              v-if="videoStore.currentVideo.description"
              class="text-base text-muted-foreground leading-relaxed whitespace-pre-wrap pr-8"
            >
              {{ videoStore.currentVideo.description }}
            </p>
            <p
              v-else
              class="text-sm text-muted-foreground/60 italic"
            >
              Nenhuma descrição disponível para este vídeo.
            </p>
            
            <button
              v-if="videoStore.currentVideo.description" 
              class="absolute top-4 right-4 p-1.5 text-muted-foreground/50 hover:text-primary hover:bg-primary/5 rounded-md transition-colors opacity-0 group-hover:opacity-100" 
              title="Copiar Descrição" 
              @click="copyToClipboard(videoStore.currentVideo.description)"
            >
              <Copy :size="16" />
            </button>
          </div>

          <!-- Metadata Card (Premium Redesign) -->
          <div class="mt-8 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden group">
            <div class="p-4 border-b border-zinc-100 dark:border-zinc-800/50 flex items-center gap-3 bg-zinc-50/50 dark:bg-zinc-900/50">
              <div class="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg group-hover:scale-105 transition-transform duration-300">
                <component
                  :is="FileText"
                  :size="20"
                />
              </div>
              <div>
                <h3 class="text-sm font-semibold text-foreground">
                  Detalhes do Projeto
                </h3>
                <p class="text-[11px] text-muted-foreground">
                  Informações técnicas e configurações
                </p>
              </div>
            </div>
              
            <div class="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Style (Full Width) -->
              <!-- Style & Ratio (Merged) -->
              <div class="md:col-span-2 grid grid-cols-2 gap-4">
                <!-- Style -->
                <div class="flex items-center gap-3 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-900/30">
                  <div class="p-2 bg-pink-100 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400 rounded-md">
                    <component
                      :is="Palette"
                      :size="16"
                    />
                  </div>
                  <div>
                    <p class="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                      Estilo Visual
                    </p>
                    <p class="text-sm font-medium text-foreground">
                      {{ videoStore.currentVideo.visual_style || 'Padrão' }}
                    </p>
                  </div>
                </div>

                <!-- Active Aspect Ratios (Interactive Multi-Select) -->
                <div class="flex items-center gap-3 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-900/30">
                  <div class="p-2 bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 rounded-md">
                    <component
                      :is="Monitor"
                      :size="16"
                    />
                  </div>
                  <div class="flex-1">
                    <div class="flex items-center gap-2">
                       <p class="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                        Formatos de Renderização
                      </p>
                      <Loader2 v-if="isSavingInline['aspect_ratios']" class="w-3 h-3 animate-spin text-primary" />
                    </div>
                    <div class="flex flex-wrap gap-2 mt-1">
                      <button 
                        v-for="ratio in ['16:9', '9:16']" 
                        :key="ratio"
                        class="px-3 py-1 text-[10px] font-bold rounded-md transition-all flex items-center gap-1.5"
                        :class="(videoStore.currentVideo.aspect_ratios || ['16:9']).includes(ratio) 
                          ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 border border-violet-200 dark:border-violet-700/50' 
                          : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-400 dark:text-zinc-500 border border-transparent hover:bg-zinc-200 dark:hover:bg-zinc-700'"
                        :disabled="isSavingInline['aspect_ratios']"
                        @click="toggleAspectRatio(ratio)"
                      >
                        <component 
                          :is="(videoStore.currentVideo.aspect_ratios || ['16:9']).includes(ratio) ? CheckCircle2 : Circle" 
                          :size="12" 
                        />
                        {{ ratio === '16:9' ? 'Horizontal' : 'Vertical' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Agent (Editable Sprint 109) -->
              <div class="col-span-1 md:col-span-2 flex items-center gap-3 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-900/30 relative group cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors">
                <div class="p-2 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-md">
                  <component
                    :is="Bot"
                    :size="16"
                  />
                </div>
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <p class="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                      Agente Responsável
                    </p>
                    <Loader2 v-if="isSavingInline['agent_id']" class="w-3 h-3 animate-spin text-primary" />
                  </div>
                  <div class="flex items-center gap-2">
                    <select 
                      v-model="videoStore.currentVideo.agent_id" 
                      class="bg-transparent text-sm font-medium text-foreground outline-none w-full appearance-none cursor-pointer"
                      @change="saveVideoField('agent_id', videoStore.currentVideo.agent_id)"
                    >
                      <option :value="undefined">
                        Padrão do Sistema
                      </option>
                      <option :value="null">
                        Padrão do Sistema
                      </option>
                      <option
                        v-for="agent in agentsList"
                        :key="agent.id"
                        :value="agent.id"
                      >
                        {{ agent.name }}
                      </option>
                    </select>
                    <ChevronDown
                      :size="14"
                      class="text-muted-foreground"
                    />
                  </div>
                </div>
              </div>

              <!-- Language -->
              <div class="flex items-center gap-3 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-900/30">
                <div class="p-2 bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400 rounded-md">
                  <component
                    :is="Globe"
                    :size="16"
                  />
                </div>
                <div>
                  <p class="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                    Idioma
                  </p>
                  <p class="text-sm font-medium text-foreground">
                    {{ videoStore.currentVideo.language }}
                  </p>
                </div>
              </div>

              <!-- Duration -->
              <div class="flex items-center gap-3 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-900/30">
                <div class="p-2 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded-md">
                  <component
                    :is="Clock"
                    :size="16"
                  />
                </div>
                <div>
                  <p class="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                    Duração Estimada
                  </p>
                  <p
                    v-if="videoStore.currentVideo.status === 'completed' && videoStore.currentVideo.total_duration_seconds"
                    class="text-sm font-medium text-foreground"
                  >
                    {{ (videoStore.currentVideo.total_duration_seconds / 60).toFixed(1) }} min
                  </p>
                  <p
                    v-else
                    class="text-sm font-medium text-foreground"
                  >
                    ~{{ videoStore.currentVideo.target_duration_minutes }} min (Alvo)
                  </p>
                </div>
              </div>

              <!-- Music -->
              <div
                v-if="videoStore.currentVideo.music"
                class="flex items-center gap-3 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-900/30"
              >
                <div class="p-2 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-md">
                  <component
                    :is="Music"
                    :size="16"
                  />
                </div>
                <div>
                  <p class="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                    Trilha Sonora
                  </p>
                  <p
                    class="text-sm font-medium text-foreground truncate max-w-[120px]"
                    :title="videoStore.currentVideo.music"
                  >
                    {{ videoStore.currentVideo.music }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Tags Card (Premium Redesign) -->
          <div
            v-if="videoStore.currentVideo.tags"
            class="mt-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden group"
          >
            <div class="p-4 border-b border-zinc-100 dark:border-zinc-800/50 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-900/50">
              <div class="flex items-center gap-3">
                <div class="p-2 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-lg group-hover:scale-105 transition-transform duration-300">
                  <component
                    :is="Tags"
                    :size="20"
                  />
                </div>
                <div>
                  <h3 class="text-sm font-semibold text-foreground">
                    Tags e Palavras-chave
                  </h3>
                  <p class="text-[11px] text-muted-foreground">
                    Termos relevantes para busca
                  </p>
                </div>
              </div>
              <button
                class="p-2 text-muted-foreground/50 hover:text-primary hover:bg-primary/5 rounded-md transition-all duration-200" 
                title="Copiar todas as tags" 
                @click="copyToClipboard(videoStore.currentVideo.tags)"
              >
                <Copy :size="16" />
              </button>
            </div>
              
            <div class="p-4 flex flex-wrap gap-2">
              <span
                v-for="tag in videoStore.currentVideo.tags.split(',')"
                :key="tag" 
                class="px-3 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-xs font-medium rounded-full border border-zinc-200 dark:border-zinc-700 hover:border-amber-300 dark:hover:border-amber-700 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors cursor-default"
              >
                #{{ tag.trim() }}
              </span>
            </div>
          </div>

          <!-- Audio & Trilha (Sprint 105) -->
          <div class="mt-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden group">
            <div class="p-4 border-b border-zinc-100 dark:border-zinc-800/50 flex items-center gap-3 bg-zinc-50/50 dark:bg-zinc-900/50">
              <div class="p-2 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg group-hover:scale-105 transition-transform duration-300">
                <component
                  :is="Music"
                  :size="20"
                />
              </div>
                <div>
                  <div class="flex items-center gap-2">
                    <h3 class="text-sm font-semibold text-foreground">
                      Trilha Sonora
                    </h3>
                    <Loader2 v-if="isSavingInline['music_id']" class="w-3 h-3 animate-spin text-primary" />
                  </div>
                  <p class="text-[11px] text-muted-foreground">
                    Música de fundo e ambiente
                  </p>
                </div>
            </div>
              
            <div class="p-4">
              <VideoMusicSelector 
                v-model="videoStore.currentVideo.music_id"
                :initial-track="selectedMusicTrack"
                @change="(track) => saveVideoField('music_id', track ? track.id : null)"
              />
            </div>
          </div>

          <!-- Audio Padding Config (Sprint 71) -->
          <div class="mt-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden group">
            <div class="p-4 border-b border-zinc-100 dark:border-zinc-800/50 flex items-center gap-3 bg-zinc-50/50 dark:bg-zinc-900/50">
              <div class="p-2 bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 rounded-lg group-hover:scale-105 transition-transform duration-300">
                <component
                  :is="Mic2"
                  :size="20"
                />
              </div>
                <div>
                  <div class="flex items-center gap-2">
                    <h3 class="text-sm font-semibold text-foreground">
                      Padding de Áudio
                    </h3>
                    <Loader2 v-if="isSavingInline['audio_transition_padding']" class="w-3 h-3 animate-spin text-primary" />
                  </div>
                  <p class="text-[11px] text-muted-foreground">
                    Silêncio entre cenas
                  </p>
                </div>
            </div>
            <div class="p-4">
              <div class="flex flex-col gap-4">
                <!-- Number Input -->
                <div class="relative w-full">
                  <input 
                    id="audio_padding"
                    v-model.number="videoStore.currentVideo.audio_transition_padding" 
                    type="number" 
                    step="0.1"
                    min="0.3"
                    max="5"
                    class="flex h-11 w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-transparent px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/20 focus-visible:border-violet-500 disabled:cursor-not-allowed disabled:opacity-50 pr-8 text-right font-mono transition-all duration-200"
                    placeholder="0.5"
                    @blur="saveVideoField('audio_transition_padding', videoStore.currentVideo.audio_transition_padding)"
                  >
                  <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-muted-foreground/70 pointer-events-none">seg</span>
                </div>

                <!-- Range Slider -->
                <div class="flex items-center gap-3">
                  <span class="text-[10px] text-muted-foreground font-mono w-4">0s</span>
                  <input
                    v-model.number="videoStore.currentVideo.audio_transition_padding"
                    type="range"
                    min="0.3"
                    step="0.1"
                    placeholder="0.3"
                    max="5"
                    class="w-full h-1.5 bg-zinc-200 dark:bg-zinc-800 rounded-full appearance-none cursor-pointer accent-violet-600 hover:accent-violet-500 transition-all"
                    @change="saveVideoField('audio_transition_padding', videoStore.currentVideo.audio_transition_padding)"
                  >
                  <span class="text-[10px] text-muted-foreground font-mono w-4">5s</span>
                </div>
              </div>
                  
              <p class="mt-3 text-[11px] text-muted-foreground/60 ml-1">
                Ajuste fino para evitar cortes abruptos no áudio.
              </p>
            </div>
          </div>

          <!-- Audio Instructions Config (Sprint 72) -->
          <div class="mt-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden group">
            <div class="p-4 border-b border-zinc-100 dark:border-zinc-800/50 flex items-center gap-3 bg-zinc-50/50 dark:bg-zinc-900/50">
              <div class="p-2 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-lg group-hover:scale-105 transition-transform duration-300">
                <component
                  :is="User"
                  :size="20"
                />
              </div>
              <div>
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-semibold text-foreground">
                  Direção de Voz (Persona)
                </h3>
                <Loader2 v-if="isSavingInline['audio_generation_instructions']" class="w-3 h-3 animate-spin text-primary" />
              </div>
              <p class="text-[11px] text-muted-foreground">
                Instruções para a IA
              </p>
              </div>
            </div>
              
            <div class="p-4">
              <div class="relative w-full">
                <textarea 
                  id="audio_instructions"
                  v-model="localAudioInstructions"
                  class="flex min-h-[100px] w-full rounded-lg border border-zinc-200 dark:border-zinc-800 bg-transparent px-3 py-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/20 focus-visible:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-50 font-sans resize-y leading-relaxed transition-all duration-200"
                  placeholder="Ex: 'Fale com entusiasmo e energia, como um apresentador de TV. Use pausas dramáticas nos momentos de tensão...'"
                  @focus="isAudioInstructionsFocused = true"
                  @input="handleAudioInstructionsInput"
                  @blur="handleAudioInstructionsBlur"
                />
              </div>
              <p class="mt-2 text-[11px] text-muted-foreground/60 ml-1 flex items-center gap-1">
                <component
                  :is="Wand2"
                  :size="10"
                />
                Dica: Descreva o tom, velocidade e sotaque desejado.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>


    <!-- Partial Failure Warning -->
    <div
      v-if="hasChapterErrors && videoStore.currentVideo?.status !== 'error'"
      class="mb-6 animate-in fade-in slide-in-from-top-2"
    >
      <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 flex items-start gap-4 shadow-sm">
        <div class="p-2 bg-amber-100 dark:bg-amber-900/40 rounded-full text-amber-600 dark:text-amber-500 shrink-0">
          <AlertTriangle :size="20" />
        </div>
        <div>
          <h3 class="font-medium text-amber-900 dark:text-amber-400 text-base">
            Atenção: Alguns capítulos falharam
          </h3>
          <p class="text-sm text-amber-700 dark:text-amber-500 mt-1 leading-relaxed">
            O processo geral foi concluído, mas houve erros em partes do conteúdo. Verifique os capítulos destacados em vermelho abaixo e tente reprocessá-los individualmente.
          </p>
        </div>
      </div>
    </div>

    <div
      v-if="videoStore.isLoading && !videoStore.currentVideo"
      class="loading-full"
    >
      <Loader2
        :size="40"
        class="spin"
      />
    </div>

    <div
      v-else-if="videoStore.currentVideo"
      class="details-content"
    >
      <!-- Video Timeline -->
      <div class="mb-8">
        <VideoProcessingTimeline 
          :video="videoStore.currentVideo" 
          @action-started="onTimelineAction"
        />
      </div>

      <!-- Multi-Format Mosaic Player (Componentized) -->
      <div
        v-if="(videoStore.currentVideo.status === 'completed' || videoStore.currentVideo.status === 'rendering' || videoStore.currentVideo.status === 'rendering_scenes') && mergedOutputs && Object.keys(mergedOutputs).length > 0"
        class="mb-8 animate-in fade-in zoom-in duration-700"
      >
        <AppCard class="overflow-hidden border-2 border-violet-500/30 bg-black/5 shadow-2xl relative">
          <template #header>
            <div class="flex items-center justify-between w-full">
              <div class="flex items-center gap-2 text-primary font-bold">
                <Film :size="20" class="text-violet-500" />
                <h3 class="bg-gradient-to-r from-violet-500 to-fuchsia-500 bg-clip-text text-transparent">
                  PROCESSO DE RENDERIZAÇÃO MULTI-FORMATO
                </h3>
              </div>
              
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 bg-violet-500/10 text-violet-500 text-[10px] font-black rounded border border-violet-500/20 animate-pulse uppercase">
                  STATUS: {{ (videoStore.currentVideo.status as string).toUpperCase() }}
                </span>
              </div>
            </div>
          </template>

          <VideoMosaicGrid 
            :outputs="mergedOutputs" 
            :video-status="videoStore.currentVideo.status"
            :rendering-progress="videoStore.currentVideo.rendering_progress"
            :refresh-key="imageRefreshKey"
            :poster-url="videoStore.currentVideo.chapters?.[0]?.subchapters?.[0]?.scenes?.[0]?.image_url || ''"
          />
        </AppCard>

        <!-- ══ CAPTION CONFIG CARD ══ -->
        <div
          v-if="mergedOutputs && Object.keys(mergedOutputs).length > 0"
          class="mt-4 animate-in fade-in slide-in-from-bottom-2"
        >
          <div class="relative rounded-2xl overflow-hidden border border-violet-200/60 dark:border-violet-800/40 bg-white dark:bg-zinc-900 shadow-sm">
            <!-- Gradient accent header -->
            <div class="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-violet-500 via-fuchsia-500 to-pink-500" />

            <div class="p-5 pt-6">
              <!-- Header row -->
              <div class="flex items-center justify-between mb-5">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                    <Captions :size="16" class="text-violet-600 dark:text-violet-400" />
                  </div>
                  <div>
                    <h3 class="text-sm font-bold text-foreground">Legendas Animadas</h3>
                    <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Word-by-word • TikTok Style</p>
                  </div>
                </div>
              </div>

              <!-- Style selector -->
              <div class="grid grid-cols-5 gap-2 mb-4">
                <button
                  v-for="style in captionStyles"
                  :key="style.id"
                  class="flex flex-col items-center gap-1.5 px-2 py-3 rounded-xl border-2 text-center transition-all"
                  :class="selectedCaptionStyle === style.id
                    ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                    : 'border-zinc-200 dark:border-zinc-700 hover:border-violet-300'"
                  @click="selectedCaptionStyle = style.id"
                >
                  <span class="text-lg">{{ style.emoji }}</span>
                  <span class="text-[10px] font-bold" :class="selectedCaptionStyle === style.id ? 'text-violet-600 dark:text-violet-400' : 'text-zinc-500'">{{ style.label }}</span>
                </button>
              </div>

              <!-- Options row -->
              <div class="grid grid-cols-3 gap-3 mb-4">
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-black text-zinc-500 uppercase tracking-wider">Posição</label>
                  <div class="flex rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700">
                    <button
                      v-for="pos in ['top', 'center', 'bottom']"
                      :key="pos"
                      class="flex-1 py-1.5 text-[10px] font-bold capitalize transition-colors"
                      :class="captionOptions.position === pos
                        ? 'bg-violet-500 text-white'
                        : 'text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-800'"
                      @click="captionOptions.position = pos"
                    >
                      {{ pos === 'top' ? 'Topo' : pos === 'center' ? 'Centro' : 'Base' }}
                    </button>
                  </div>
                </div>
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-black text-zinc-500 uppercase tracking-wider">Palavras/linha</label>
                  <div class="flex rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700">
                    <button
                      v-for="n in [3, 4, 5]"
                      :key="n"
                      class="flex-1 py-1.5 text-[10px] font-bold transition-colors"
                      :class="captionOptions.words_per_line === n
                        ? 'bg-violet-500 text-white'
                        : 'text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-800'"
                      @click="captionOptions.words_per_line = n"
                    >
                      {{ n }}
                    </button>
                  </div>
                </div>
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-black text-zinc-500 uppercase tracking-wider">Forçar Whisper</label>
                  <button
                    class="flex items-center justify-center gap-1.5 py-1.5 rounded-lg border text-[10px] font-bold transition-all"
                    :class="captionForceWhisper
                      ? 'bg-amber-50 border-amber-300 text-amber-700 dark:bg-amber-900/20 dark:border-amber-600 dark:text-amber-400'
                      : 'border-zinc-200 dark:border-zinc-700 text-zinc-400 hover:border-zinc-300'"
                    @click="captionForceWhisper = !captionForceWhisper"
                  >
                    <Wand2 :size="11" />
                    {{ captionForceWhisper ? 'Whisper ativo' : 'Usar texto salvo' }}
                  </button>
                </div>
              </div>

              <!-- Download captioned outputs -->
              <div
                v-if="videoStore.currentVideo.captioned_outputs && Object.keys(videoStore.currentVideo.captioned_outputs).length > 0"
                class="flex flex-wrap gap-2 pt-4 border-t border-zinc-100 dark:border-zinc-800"
              >
                <a
                  v-for="(url, ratio) in videoStore.currentVideo.captioned_outputs"
                  :key="ratio"
                  :href="getVideoUrl(url as string)"
                  download
                  class="flex items-center gap-2 px-3 py-2 rounded-lg bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-700 text-violet-700 dark:text-violet-400 text-xs font-bold hover:bg-violet-100 dark:hover:bg-violet-900/40 transition-colors"
                >
                  <Download :size="13" />
                  {{ ratio }} com legenda
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

   <!-- Timestamps Index Section -->
        <div
          v-if="videoStore.currentVideo.timestamps_index"
          class="mt-4 animate-in fade-in slide-in-from-bottom-2"
        >
          <div class="relative bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-5 group">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-wider">
                <Clock
                  :size="14"
                  class="text-primary"
                />
                Índice de Navegação (Youtube Timestamps)
              </h3>
              <button
                class="flex items-center gap-2 text-xs font-medium text-primary hover:text-primary/80 bg-primary/5 px-2 py-1 rounded-md transition-colors" 
                title="Copiar Índice" 
                @click="copyToClipboard(videoStore.currentVideo.timestamps_index)"
              >
                <Copy :size="14" />
                Copiar Índice
              </button>
            </div>
            <div class="bg-white dark:bg-black/20 p-3 rounded-md border border-zinc-100 dark:border-zinc-800/50">
              <pre class="text-sm text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed select-all">{{ videoStore.currentVideo.timestamps_index }}</pre>
            </div>
          </div>
        </div>
      </div>
      <!-- Error Message Alert -->
      <div
        v-if="videoStore.currentVideo.status === 'error' && videoStore.currentVideo.error_message"
        class="error-alert-box"
      >
        <AlertTriangle :size="20" />
        <div class="error-content">
          <strong>Erro na Geração:</strong>
          <p>{{ videoStore.currentVideo.error_message }}</p>
        </div>
      </div>

      <!-- Characters Section -->
      <div
        v-if="videoStore.currentVideo.characters && videoStore.currentVideo.characters.length > 0"
        class="characters-section"
      >
        <h2 class="section-title">
          Personagens
        </h2>
        <div class="characters-grid">
          <div
            v-for="char in videoStore.currentVideo.characters"
            :key="char.name"
            class="character-card group relative"
          >
            <!-- VIEW MODE -->
            <div v-if="editingCharacterName !== char.name">
              <div class="char-header flex justify-between items-start">
                <div class="flex items-center gap-2">
                  <User
                    :size="16"
                    class="text-primary"
                  />
                  <h3 class="font-semibold">
                    {{ char.name }}
                  </h3>
                </div>
                <!-- Edit Button (Visible on Hover or always visible on mobile) -->
                <button 
                  class="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted rounded text-muted-foreground hover:text-primary"
                  title="Editar Personagem"
                  @click="startEditingCharacter(char)"
                >
                  <Edit2 :size="14" />
                </button>
              </div>
                
              <div class="char-info-row mt-3">
                <span class="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Descrição</span>
                <p class="char-desc text-sm leading-relaxed text-muted-foreground/90 mt-1 line-clamp-4">
                  {{ char.physical_description || char.description || 'Sem descrição' }}
                </p>
              </div>
    
              <div class="char-info-row mt-3">
                <span class="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Voz</span>
                <div class="char-voice flex items-center gap-2 mt-1 bg-muted/40 px-2 py-1 rounded w-fit">
                  <Mic2
                    :size="12"
                    class="text-primary"
                  />
                  <span class="font-medium text-xs">{{ (char as any).voice || (char as any).voice_type || 'Voz Padrão' }}</span>
                </div>
              </div>
            </div>

            <!-- EDIT MODE -->
            <div
              v-else
              class="edit-mode space-y-3"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-primary uppercase">Editando</span>
              </div>

              <!-- Name Input -->
              <div class="space-y-1">
                <label class="text-[10px] uppercase font-bold text-muted-foreground">Nome</label>
                <input 
                  v-model="editCharacterForm.name"
                  class="w-full bg-background border border-input rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Nome do Personagem"
                >
              </div>

              <!-- Voice Input -->
              <div class="space-y-1">
                <label class="text-[10px] uppercase font-bold text-muted-foreground w-full block">Voz</label>
                <AppVoiceSelector v-model="editCharacterForm.voice" />
              </div>

              <!-- Description Input -->
              <div class="space-y-1">
                <label class="text-[10px] uppercase font-bold text-muted-foreground">Descrição</label>
                <textarea 
                  v-model="editCharacterForm.description"
                  rows="4"
                  class="w-full bg-background border border-input rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                  placeholder="Descrição física e visual..."
                />
              </div>

              <!-- Actions -->
              <div class="flex items-center justify-end gap-2 pt-2">
                <AppButton 
                  variant="ghost"
                  size="sm"
                  :disabled="isSavingCharacter"
                  @click="cancelEditingCharacter"
                >
                  Cancelar
                </AppButton>
                <AppButton 
                  size="sm" 
                  variant="primary"
                  :loading="isSavingCharacter"
                  @click="saveCharacter"
                >
                  <Save :size="16" />
                  Salvar
                </AppButton>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- STRUCTURE VIEW -->
      <div v-if="videoStore.currentVideo.chapters && videoStore.currentVideo.chapters.length > 0">
        <h2 class="section-title">
          Estrutura do Vídeo
        </h2>
        <div
          v-for="chapter in videoStore.currentVideo.chapters"
          :key="chapter.id"
          class="chapter-block"
        >
          <AppCard>
            <template #title>
              <div
                class="flex items-center gap-2 cursor-pointer select-none w-full"
                @click="toggleChapter(chapter.id)"
              >
                <component
                  :is="isChapterCollapsed(chapter.id) ? ChevronRight : ChevronDown"
                  :size="20"
                  class="text-muted-foreground transition-transform duration-200"
                />
                <h3 class="text-lg font-semibold leading-none tracking-tight text-foreground dark:text-zinc-100">
                  Capítulo {{ chapter.order }}: {{ chapter.title }}
                </h3>
              </div>
            </template>
            <template #header-actions>
              <div class="chapter-meta-actions">
                <!-- Status Indicator -->
                <div
                  v-if="chapter.status && chapter.status !== 'completed'"
                  class="status-indicator mr-2 flex items-center gap-1"
                >
                  <span
                    v-if="chapter.status === 'processing'"
                    class="text-blue-500 flex items-center"
                    title="Processando..."
                  >
                    <Loader2
                      :size="18"
                      class="animate-spin"
                    />
                  </span>
                  <span
                    v-if="chapter.status === 'error'"
                    class="text-red-400 flex items-center text-xs"
                    :title="chapter.error_message"
                  >
                    <AlertCircle
                      :size="14"
                      class="mr-1"
                    /> Erro
                  </span>
                </div>

                <AppButton 
                  variant="ghost" 
                  size="sm" 
                  :disabled="chapter.status === 'processing'"
                  title="Reprocessar Capítulo"
                  @click.stop="reprocessChapter(chapter)"
                >
                  <RefreshCcw :size="16" />
                </AppButton>
                <div class="chapter-meta">
                  <Clock :size="14" />
                  <span>{{ chapter.estimated_duration_minutes }} min</span>
                </div>
              </div>
            </template>
            
            <div v-if="!isChapterCollapsed(chapter.id)">
              <p class="chapter-desc">
                {{ chapter.description }}
              </p>

              <!-- Chapter Error Alert -->
              <div
                v-if="chapter.status === 'error'"
                class="mt-4 p-4 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/50 rounded-lg flex items-start gap-4 animate-in fade-in slide-in-from-left-2"
              >
                <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-full text-red-600 dark:text-red-400 shrink-0">
                  <AlertCircle :size="20" />
                </div>
                <div class="flex-1">
                  <h4 class="font-semibold text-red-900 dark:text-red-300">
                    Falha no Processamento
                  </h4>
                  <p class="text-sm text-red-700 dark:text-red-400 mt-1 mb-3">
                    {{ chapter.error_message || 'Erro desconhecido ao processar este capítulo.' }}
                  </p>
                  <AppButton 
                    variant="outline" 
                    size="sm" 
                    class="border-red-200 hover:bg-red-100 text-red-700 dark:border-red-800 dark:hover:bg-red-900/40 dark:text-red-300 bg-transparent transition-colors"
                    @click="reprocessChapter(chapter)"
                  >
                    <RefreshCcw
                      :size="14"
                      class="mr-2"
                    />
                    Tentar Novamente
                  </AppButton>
                </div>
              </div>

              <div class="subchapters-list">
                <div
                  v-for="sub in chapter.subchapters"
                  :key="sub.id"
                  class="subchapter-item"
                >
                  <div
                    class="subchapter-header cursor-pointer select-none flex items-center gap-2 hover:bg-muted/50 p-1 rounded-md transition-colors"
                    @click="toggleSubchapter(chapter.id, sub.id)"
                  >
                    <component
                      :is="isSubchapterCollapsed(chapter.id, sub.id) ? ChevronRight : ChevronDown"
                      :size="18"
                      class="text-muted-foreground"
                    />
                    <div class="flex-1">
                      <h3>{{ sub.title }}</h3>
                      <p>{{ sub.description }}</p>
                    </div>
                  </div>
                    
                  <div
                    v-show="!isSubchapterCollapsed(chapter.id, sub.id)"
                    class="scenes-grid mt-4"
                  >
                    <div 
                      v-for="(scene, idx) in sub.scenes" 
                      :key="idx" 
                      class="scene-card group relative transition-all duration-300"
                      :data-scene-id="scene.id"
                      :class="{ 
                        '!bg-red-50 dark:!bg-red-950/20 !border-red-200 dark:!border-red-900/50': !(scene as any).deleted && !((scene as any).original_image_url || ((scene as any).cropped_image_url)),
                        'opacity-70 grayscale border-dashed bg-zinc-50/50 dark:bg-zinc-900/30': (scene as any).deleted
                      }"
                    >
                      <!-- DELETED STATE VIEW -->
                      <div
                        v-if="(scene as any).deleted"
                        class="flex items-center justify-between p-4"
                      >
                        <div class="flex items-center gap-3 overflow-hidden">
                          <span class="text-xs font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2 whitespace-nowrap">
                            <Trash2 :size="14" />
                            Cena {{ (idx as number) + 1 }}
                          </span>
                          <span class="text-sm text-zinc-400 line-through truncate max-w-[400px] italic">{{ (scene as any).narration_content || 'Sem roteiro' }}</span>
                        </div>
                        <AppButton 
                          variant="ghost" 
                          size="sm"
                          class="text-zinc-500 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 h-8 shrink-0"
                          :loading="isTogglingDelete[getSceneUniqueId(chapter.id, sub.id, (idx as number))]"
                          title="Restaurar Cena"
                          @click="toggleSceneDelete(scene, chapter.id, sub.id, (idx as number))"
                        >
                          <RotateCcw
                            :size="14"
                            class="mr-1.5"
                          />
                          <span class="text-xs font-semibold">Restaurar</span>
                        </AppButton>
                      </div>

                      <!-- ACTIVE STATE VIEW -->
                      <div v-else>
                        <div class="scene-header flex items-center justify-between">
                          <div class="flex items-center gap-3">
                            <span class="font-medium text-sm">Cena {{ (idx as number) + 1 }}</span>
                            <div class="scene-duration flex items-center gap-1 text-xs text-muted-foreground bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded">
                              <Clock :size="12" />
                              <span>{{ (scene as any).duration_seconds }}s</span>
                            </div>
                          </div>
                            
                          <!-- DELETE BUTTON -->
                          <!-- DELETE BUTTON -->
                          <button 
                            class="ml-auto p-1 text-zinc-400 hover:text-red-600 transition-colors focus:outline-none"
                            :disabled="isTogglingDelete[getSceneUniqueId(chapter.id, sub.id, (idx as number))]"
                            title="Deletar Cena"
                            @click.stop="toggleSceneDelete(scene, chapter.id, sub.id, (idx as number))"
                          >
                            <Loader2
                              v-if="isTogglingDelete[getSceneUniqueId(chapter.id, sub.id, (idx as number))]"
                              :size="20"
                              class="animate-spin"
                            />
                            <Trash2
                              v-else
                              :size="20"
                            />
                          </button>
                        </div>
                        <div class="scene-body">
                          <!-- SCENE VIEW MODE -->
                          <div class="space-y-5">
                            <!-- Character and Narration -->
                            <div class="scene-primary relative">
                              <!-- Character & Voice Label -->
                              <div
                                v-if="(scene as any).character"
                                class="flex items-center gap-2 mb-4"
                              >
                                <div class="inline-flex items-center gap-2 bg-primary/5 dark:bg-primary/10 border border-primary/20 rounded-xl px-3 py-1.5 shadow-sm">
                                  <User
                                    :size="14"
                                    class="text-primary"
                                    stroke-width="3"
                                  />
                                  <span class="text-xs font-black text-primary uppercase tracking-widest leading-none">
                                    {{ (scene as any).character }}
                                  </span>
                                </div>
                                <span class="text-[10px] font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-widest border-l border-zinc-200 dark:border-zinc-800 pl-3">
                                  {{ getCharacterVoice((scene as any).character) }}
                                </span>
                              </div>

                              <!-- Narration Box -->
                              <div class="narration-container relative bg-zinc-50/50 dark:bg-zinc-900/30 border border-zinc-100 dark:border-zinc-800 p-4 rounded-2xl group/narration">
                                <strong class="text-[10px] font-black text-zinc-400 uppercase tracking-[0.2em] block mb-2 opacity-70">Roteiro da Cena</strong>
                                <InlineEditable
                                  :model-value="(scene as any).narration_content || scene.narration"
                                  multiline
                                  class="text-base text-zinc-800 dark:text-zinc-100 leading-relaxed font-semibold pr-12"
                                  :saving="isSavingInline[`${getSceneUniqueId(chapter.id, sub.id, (idx as number))}-narration_content`]"
                                  @save="(val: string) => handleInlineSave(scene, 'narration_content', val, chapter.id, sub.id, (idx as number))"
                                />
                              </div>
                            </div>

                            <!-- Technical Prompts & Search Details -->
                            <div class="prompts-grid grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-zinc-100 dark:border-zinc-800/50 pt-5">
                              <!-- Prompt Column -->
                              <div class="space-y-3">
                                <div
                                  v-if="(scene as any).image_prompt"
                                  class="prompt-entry"
                                >
                                  <div class="flex items-center gap-2 mb-1">
                                    <ImageIcon
                                      :size="12"
                                      class="text-zinc-400"
                                    />
                                    <label class="text-[9px] font-black uppercase tracking-widest text-zinc-500">Prompt Imagem</label>
                                  </div>
                                  <InlineEditable
                                    :model-value="(scene as any).image_prompt"
                                    multiline
                                    class="text-xs text-zinc-600 dark:text-zinc-400 font-medium bg-zinc-50 dark:bg-zinc-900/50 p-2.5 rounded-lg border border-zinc-100 dark:border-zinc-800"
                                    :saving="isSavingInline[`${getSceneUniqueId(chapter.id, sub.id, (idx as number))}-image_prompt`]"
                                    @save="(val: string) => handleInlineSave(scene, 'image_prompt', val, chapter.id, sub.id, (idx as number))"
                                  />
                                </div>
                                <div
                                  v-if="(scene as any).video_prompt"
                                  class="prompt-entry"
                                >
                                  <div class="flex items-center gap-2 mb-1">
                                    <Film
                                      :size="12"
                                      class="text-zinc-400"
                                    />
                                    <label class="text-[9px] font-black uppercase tracking-widest text-zinc-500">Prompt Vídeo</label>
                                  </div>
                                  <InlineEditable
                                    :model-value="(scene as any).video_prompt"
                                    multiline
                                    class="text-xs text-zinc-600 dark:text-zinc-400 font-medium bg-zinc-50 dark:bg-zinc-900/50 p-2.5 rounded-lg border border-zinc-100 dark:border-zinc-800"
                                    :saving="isSavingInline[`${getSceneUniqueId(chapter.id, sub.id, (idx as number))}-video_prompt`]"
                                    @save="(val: string) => handleInlineSave(scene, 'video_prompt', val, chapter.id, sub.id, (idx as number))"
                                  />
                                </div>
                              </div>

                              <!-- Search & FX Column -->
                              <div class="space-y-3">
                                <div
                                  v-if="(scene as any).image_search"
                                  class="search-entry"
                                >
                                  <div class="flex items-center gap-2 mb-1">
                                    <SearchIcon
                                      :size="12"
                                      class="text-zinc-400"
                                    />
                                    <label class="text-[9px] font-black uppercase tracking-widest text-zinc-500">Busca Imagem</label>
                                  </div>
                                  <div class="flex gap-2 items-center">
                                    <InlineEditable
                                      :model-value="(scene as any).image_search"
                                      class="flex-1 text-xs font-bold underline decoration-dotted p-2.5 rounded-lg border border-zinc-100 dark:border-zinc-800"
                                      :saving="isSavingInline[`${getSceneUniqueId(chapter.id, sub.id, (idx as number))}-image_search`]"
                                      @save="(val: string) => handleInlineSave(scene, 'image_search', val, chapter.id, sub.id, (idx as number))"
                                    />
                                    <AppButton
                                      variant="primary"
                                      size="sm"
                                      icon-only
                                      title="Buscar Imagem"
                                      @click.stop="openImageSearch(scene, chapter.id, sub.id, (idx as number) + 1)"
                                    >
                                      <SearchIcon :size="16" />
                                    </AppButton>
                                  </div>
                                </div>
                                <div
                                  v-if="(scene as any).video_search"
                                  class="search-entry"
                                >
                                  <div class="flex items-center gap-2 mb-1">
                                    <SearchIcon
                                      :size="12"
                                      class="text-zinc-400"
                                    />
                                    <label class="text-[9px] font-black uppercase tracking-widest text-zinc-500">Busca Vídeo</label>
                                  </div>
                                  <div class="flex gap-2 items-center">
                                    <InlineEditable
                                      :model-value="(scene as any).video_search"
                                      class="flex-1 text-xs font-bold underline decoration-dotted p-2.5 rounded-lg border border-zinc-100 dark:border-zinc-800"
                                      :saving="isSavingInline[`${getSceneUniqueId(chapter.id, sub.id, (idx as number))}-video_search`]"
                                      @save="(val: string) => handleInlineSave(scene, 'video_search', val, chapter.id, sub.id, (idx as number))"
                                    />
                                    <AppButton
                                      variant="primary"
                                      size="sm"
                                      icon-only
                                      title="Buscar Vídeo"
                                      @click.stop="openVideoSearch(scene, chapter.id, sub.id, (idx as number) + 1)"
                                    >
                                      <SearchIcon :size="16" />
                                    </AppButton>
                                  </div>
                                </div>
                                <div
                                  v-if="(scene as any).audio_effect_search"
                                  class="search-entry"
                                >
                                  <div class="flex items-center gap-2 mb-1">
                                    <Music
                                      :size="12"
                                      class="text-zinc-400"
                                    />
                                    <label class="text-[9px] font-black uppercase tracking-widest text-zinc-500">Audio FX</label>
                                  </div>
                                  <div class="flex items-center gap-1">
                                    <InlineEditable
                                      :model-value="(scene as any).audio_effect_search"
                                      class="flex-1 text-xs p-2.5 rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 font-bold"
                                      :saving="isSavingInline[`${getSceneUniqueId(chapter.id, sub.id, (idx as number))}-audio_effect_search`]"
                                      @save="(val: string) => handleInlineSave(scene, 'audio_effect_search', val, chapter.id, sub.id, (idx as number))"
                                    />
                                    <span
                                      v-if="(scene as any).audio_effect_seconds_start !== undefined"
                                      class="text-[10px] text-zinc-400 ml-1 font-black shrink-0"
                                    >({{ (scene as any).audio_effect_seconds_start }}s)</span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            <!-- Media Previews -->
                            <div
                              v-if="(scene as any).original_image_url || (scene as any).cropped_image_url || (scene as any).video_url || (scene as any).generated_video_url" 
                              class="media-gallery grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-4"
                            >
                              <div
                                v-if="(scene as any).original_image_url"
                                class="media-item relative aspect-video overflow-hidden rounded-2xl border-2 border-zinc-100 dark:border-zinc-800 shadow-sm"
                              >
                                <img
                                  :src="getImageUrl((scene as any).original_image_url)"
                                  class="w-full h-full object-cover"
                                >
                                <span class="absolute top-2 left-2 px-2 py-0.5 bg-black/60 text-[9px] font-black text-white uppercase tracking-widest rounded-md backdrop-blur-sm">Referência</span>
                              </div>
                                

                              <!-- CONSOLIDATED SCENE PLAYER (Prioritized: Caption > Generated > Visual) -->
                              <div
                                v-if="(scene as any).captioned_video_url || (scene as any).generated_video_url || (scene as any).video_url || isRenderingScene[getSceneUniqueId(chapter.id, sub.id, (idx as number))] || isGeneratingCaptionScene[getSceneUniqueId(chapter.id, sub.id, (idx as number))]"
                                class="media-item aspect-video overflow-hidden rounded-2xl border-2 shadow-sm relative col-span-1 sm:col-span-2 lg:col-span-1"
                                :class="(scene as any).captioned_video_url ? 'border-green-500/50' : ((scene as any).generated_video_url ? 'border-blue-500/30' : 'border-zinc-100 dark:border-zinc-800')"
                              >
                                <!-- Loading Overlay (while scene or caption is processing) -->
                                <div
                                  v-if="isRenderingScene[getSceneUniqueId(chapter.id, sub.id, (idx as number))] || (isGeneratingCaptionScene[getSceneUniqueId(chapter.id, sub.id, (idx as number))] && !(scene as any).captioned_video_url)"
                                  class="absolute inset-0 bg-zinc-900/80 flex flex-col items-center justify-center gap-2 z-10 rounded-2xl"
                                >
                                  <Loader2 :size="28" class="text-white animate-spin" />
                                  <span class="text-white text-[10px] font-bold uppercase tracking-widest">
                                    {{ isRenderingScene[getSceneUniqueId(chapter.id, sub.id, (idx as number))] ? 'Processando cena...' : 'Gerando legenda...' }}
                                  </span>
                                </div>
                                <video
                                  v-if="(scene as any).captioned_video_url || (scene as any).generated_video_url || (scene as any).video_url"
                                  :key="((scene as any).captioned_video_url || (scene as any).generated_video_url || (scene as any).video_url)"
                                  controls
                                  preload="none"
                                  :poster="getImageUrl((scene as any).image_url || (scene as any).cropped_image_url)"
                                  class="w-full h-full object-cover"
                                >
                                  <source
                                    :src="getVideoUrl((scene as any).captioned_video_url || (scene as any).generated_video_url || (scene as any).video_url)"
                                    type="video/mp4"
                                  >
                                </video>
                                <!-- Placeholder when no URL yet -->
                                <div
                                  v-else
                                  class="w-full h-full bg-zinc-900 flex items-center justify-center"
                                >
                                  <Film :size="32" class="text-zinc-600" />
                                </div>
                                <span 
                                  class="absolute top-2 left-2 px-2 py-0.5 text-[9px] font-black text-white uppercase tracking-widest rounded-md backdrop-blur-sm shadow-sm"
                                  :class="(scene as any).captioned_video_url ? 'bg-green-600' : ((scene as any).generated_video_url ? 'bg-blue-600' : 'bg-zinc-900/80')"
                                >
                                  {{ (scene as any).captioned_video_url ? 'Cena com Legenda' : ((scene as any).generated_video_url ? 'Preview da Cena' : 'Cena Visual') }}
                                </span>
                              </div>
                            </div>

                            <!-- Scene Footer (Audio controls) -->
                            <div class="scene-footer mt-5 pt-4 border-t border-dashed border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                              <div class="audio-label flex items-center gap-2">
                                <Mic
                                  :size="14"
                                  class="text-primary"
                                />
                                <span class="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] pt-0.5">Captura de Voz</span>
                              </div>
                              <div class="flex items-center gap-3">
                                <AppButton 
                                  variant="ghost" 
                                  size="md" 
                                  icon-only
                                  class="text-primary hover:bg-primary/10 border border-primary/20 bg-primary/5"
                                  :loading="isReprocessingSceneAudio[getSceneUniqueId(chapter.id, sub.id, (idx as number))]"
                                  title="Gerar áudio com IA"
                                  @click="reprocessSceneAudio(getSceneUniqueId(chapter.id, sub.id, (idx as number)), scene, chapter.id, sub.id, (idx as number))"
                                >
                                  <Wand2 :size="20" />
                                </AppButton>

                                <!-- Process Scene Button (Film Icon) -->
                                <AppButton
                                  variant="ghost" 
                                  size="md" 
                                  icon-only
                                  class="text-amber-600 hover:bg-amber-50 border border-amber-200 bg-amber-50/50 dark:border-amber-900/30 dark:bg-amber-900/10"
                                  :loading="isRenderingScene[getSceneUniqueId(chapter.id, sub.id, (idx as number))]"
                                  title="Processar / Reprocessar Vídeo da Cena"
                                  @click="handleRenderScene(getSceneUniqueId(chapter.id, sub.id, (idx as number)), chapter.id, sub.id, (idx as number))"
                                >
                                  <Film :size="20" />
                                </AppButton>

                                <!-- Caption Button (per scene) -->
                                <div class="flex items-center gap-1">
                                  <AppButton
                                    v-if="(scene as any).audio_url"
                                    variant="ghost"
                                    size="md"
                                    icon-only
                                    :class="[
                                      (scene as any).caption_status === 'done'
                                        ? 'text-violet-600 bg-violet-50 border border-violet-200 dark:bg-violet-900/20 dark:border-violet-700'
                                        : 'text-zinc-500 hover:text-violet-600 hover:bg-violet-50'
                                    ]"
                                    :loading="isGeneratingCaptionScene[getSceneUniqueId(chapter.id, sub.id, (idx as number))]"
                                    :title="(scene as any).caption_status === 'done' ? 'Legenda gerada ✓ (clique para regenerar)' : 'Gerar Legenda desta Cena'"
                                    @click="generateSceneCaption(getSceneUniqueId(chapter.id, sub.id, (idx as number)), (scene as any).id)"
                                  >
                                    <Captions :size="20" />
                                  </AppButton>
                                  <span 
                                    v-if="(scene as any).caption_status === 'done'" 
                                    class="scene-caption-badge text-[9px] font-black text-violet-600 dark:text-violet-400 uppercase tracking-widest bg-violet-100 dark:bg-violet-900/30 px-1.5 py-0.5 rounded-md flex items-center gap-1"
                                  >
                                    ✓ Legenda
                                  </span>
                                </div>

                                <AppButton 
                                  v-if="recordingState[getSceneUniqueId(chapter.id, sub.id, (idx as number))] !== 'recording'"
                                  variant="ghost"
                                  size="md"
                                  icon-only
                                  :class="{ 'text-primary bg-primary/10 border border-primary/20': recordingState[getSceneUniqueId(chapter.id, sub.id, (idx as number))] === 'recorded' }"
                                  title="Gravar Voz"
                                  @click="startRecording(getSceneUniqueId(chapter.id, sub.id, (idx as number)))"
                                >
                                  <Mic :size="20" />
                                </AppButton>
                                <AppButton 
                                  v-if="recordingState[getSceneUniqueId(chapter.id, sub.id, (idx as number))] === 'recording'"
                                  variant="ghost"
                                  size="md"
                                  icon-only
                                  class="animate-pulse text-red-500 bg-red-50 border border-red-200"
                                  title="Parar Gravação"
                                  @click="stopRecording(getSceneUniqueId(chapter.id, sub.id, (idx as number)), chapter.id, sub.id, (idx as number))"
                                >
                                  <Square
                                    :size="20"
                                    fill="currentColor"
                                  />
                                </AppButton>
                                    
                                <div
                                  v-if="recordingState[getSceneUniqueId(chapter.id, sub.id, (idx as number))] === 'recorded' || (scene as any).audio_url"
                                  class="flex items-center gap-2"
                                >
                                  <AppAudioPlayer :src="getAudioSource(getSceneUniqueId(chapter.id, sub.id, (idx as number)), (scene as any).audio_url)" />
                                  <AppButton
                                    variant="ghost"
                                    size="md"
                                    icon-only
                                    title="Baixar Áudio"
                                    @click="downloadAudio(getSceneUniqueId(chapter.id, sub.id, (idx as number)), (idx as number), (scene as any).audio_url)"
                                  >
                                    <Download :size="20" />
                                  </AppButton>
                                  <AppButton
                                    variant="ghost"
                                    size="md"
                                    icon-only
                                    class="text-red-500 hover:bg-red-50"
                                    title="Deletar Áudio"
                                    @click="openDeleteModal(getSceneUniqueId(chapter.id, sub.id, (idx as number)), chapter.id, sub.id, (idx as number))"
                                  >
                                    <Trash2 :size="20" />
                                  </AppButton>
                                </div>
                              </div>
                            </div>
                          </div>



                        <!-- Added missing closing tags -->
                        </div> 
                      </div>
                    </div> <!-- closes scene-card -->
                  </div> <!-- closes scenes-grid -->
                </div> <!-- closes subchapter-item -->
              </div> <!-- closes subchapters-list -->
            </div> <!-- closes v-if="!isChapterCollapsed" (Line 1194) -->
          </AppCard>
        </div>
      </div>
      
      <div
        v-else
        class="empty-structure"
      >
        <AppCard>
          <div class="waiting-message">
            <Loader2
              v-if="(videoStore.currentVideo as any)?.status === 'processing'"
              class="spin"
              :size="48"
            />
            <div class="waiting-text">
              <p class="waiting-title">
                Processando vídeo
              </p>
              <p class="waiting-subtitle">
                Aguardando geração de conteúdo...
              </p>
            </div>
          </div>
        </AppCard>
      </div>


    <!-- Global Error Modal -->
    <AppModal
      v-model:open="isErrorModalOpen"
      :title="errorTitle"
      description=""
    >
      <div class="modal-error-content">
        <p>{{ errorMessage }}</p>
        <div class="modal-actions">
          <AppButton
            variant="primary"
            @click="isErrorModalOpen = false"
          >
            Entendi
          </AppButton>
        </div>
      </div>
    </AppModal>


    <!-- Delete Confirmation Modal -->
    <AppModal
      v-model:open="isDeleteModalOpen"
      title="Apagar Áudio?"
      description="Essa ação removerá o arquivo gravado permanentemente."
    >
      <template #footer>
        <AppButton
          variant="secondary"
          @click="isDeleteModalOpen = false"
        >
          Cancelar
        </AppButton>
        <AppButton
          variant="danger"
          @click="confirmDelete"
        >
          Sim, apagar
        </AppButton>
      </template>
    </AppModal>

    <!-- Image Search Modal -->
    <ImageSearchModal
      :open="isImageSearchOpen"
      :initial-query="currentSearchScene?.image_search || ''"
      :initial-provider="currentSearchScene?.image_search_provider || 'unsplash'"
      @update:open="(val) => isImageSearchOpen = val"
      @select="handleImageSelect"
    />

    <!-- Video Search Modal -->
    <VideoSearchModal
      :open="isVideoSearchOpen"
      :initial-query="currentVideoSearchScene?.video_search || ''"
      :initial-provider="'pexels'"
      :context="{
        videoId: videoStore.currentVideo?.id || 0,
        ...currentVideoSearchContext
      }"
      @update:open="(val: boolean) => isVideoSearchOpen = val"
      @select="handleVideoSelect"
    />

    <ImageCropEditor
      v-model:open="cropEditorOpen"
      :image-url="cropImageUrl"
      :video-id="videoStore.currentVideo?.id"
      :scene-id="currentCropSceneId"
      @crop-saved="handleCropSaved"
    />



    <!-- Loading Overlay -->
    <div
      v-if="isDownloadingImage"
      class="loading-overlay"
    >
      <div class="loading-content">
        <Loader2
          :size="48"
          class="spin"
        />
        <p>Baixando imagem...</p>
      </div>
    </div>

    <!-- Reprocess Confirmation Modal -->
    <AppModal
      v-model:open="isReprocessModalOpen"
      title="Reprocessar Capítulo?"
      description="Isso apagará todas as cenas atuais deste capítulo e iniciará uma nova geração."
    >
      <template #footer>
        <AppButton
          variant="secondary"
          @click="isReprocessModalOpen = false"
        >
          Cancelar
        </AppButton>
        <AppButton
          variant="primary"
          @click="confirmReprocessChapter"
        >
          <RefreshCcw
            :size="16"
          />
          Sim, reprocessar
        </AppButton>
      </template>
    </AppModal>

    <!-- Saving Crop Overlay -->
    <div
      v-if="isSavingCrop"
      class="loading-overlay"
    >
      <div class="loading-content">
        <Loader2
          :size="48"
          class="spin"
        />
        <p>Salvando crop...</p>
      </div>
    </div>

    <VideoPublishModal 
      v-if="videoStore.currentVideo"
      v-model="isPublishModalOpen"
      :video="videoStore.currentVideo"
      @published="fetchVideoData"
      @upload-started="handleUploadStarted"
    />
    <UploadProgressToast />
    </template>

    <div v-else class="error-state">
      <AlertCircle :size="48" class="text-red-500 mb-4" />
      <h2>Vídeo não encontrado</h2>
      <p>O vídeo que você está procurando não existe ou foi excluído.</p>
      <AppButton variant="primary" @click="goBack" class="mt-4">
        Voltar para o Dashboard
      </AppButton>
    </div>
  </AppLayout>
</template>

<style scoped>
.loading-full-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 1rem;
  color: var(--text-secondary);
}

.spinner-xl {
  width: 3rem;
  height: 3rem;
  animation: spin 1s linear infinite;
  color: var(--primary-base);
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  padding: 2rem;
}

.error-state h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.details-header {
  margin-bottom: 2rem;
}

.reprocess-trigger-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  background: var(--color-zinc-900);
  color: white;
  border: none;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow-sm);
}

.reprocess-trigger-btn:hover:not(:disabled) {
  background: var(--color-zinc-800);
}

.reprocess-trigger-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.reprocess-trigger-btn .icon {
  color: var(--color-zinc-300);
}

.reprocess-trigger-btn .chevron {
  color: var(--color-zinc-400);
}

.chapter-meta-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.meta-badges {
  margin-top: 1.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.meta-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  background: var(--color-zinc-100);
  border: 1px solid var(--border-subtle);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.meta-badge .label {
  color: var(--text-muted);
}

.meta-badge .value {
  color: var(--text-primary);
}

.meta-badge .icon {
  color: var(--color-violet-600);
}

.header-content {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.title-section {
  flex: 1;
  min-width: 0;
  margin-right: 1.5rem;
}

.title-section h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.meta-badges {
  display: flex;
  gap: 0.5rem;
}

.badge {
  background: var(--bg-card-hover);
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  text-transform: uppercase;
  border: 1px solid var(--border-subtle);
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.scene-footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-subtle);
}

.scene-images-container {
  display: grid;
  gap: 1rem;
  margin-bottom: 1rem;
  width: 100%;
  grid-template-columns: repeat(2, 1fr);
}

/* Force single column only if strictly one image (e.g. only original exists) */
.scene-images-container:has(.scene-image-preview:only-child) {
  grid-template-columns: 1fr;
}

.scene-image-preview {
  position: relative;
  background: var(--bg-subtle);
  width: 100%;
  display: block;
  aspect-ratio: 16/9;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.scene-image-preview img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.image-label {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: var(--primary-base);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.image-actions {
  position: absolute;
  bottom: 0.75rem;
  right: 0.75rem;
  z-index: 100;
  display: flex;
  gap: 0.25rem;
}

.action-btn {
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px; /* Soft square/rounded */
  cursor: pointer;
  display: flex !important;
  align-items: center;
  justify-content: center;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 100;
  position: relative;
}

.action-btn:hover {
  background: var(--primary-base);
  border-color: var(--primary-base);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); /* Glow effect assuming purple primary */
}

.scene-image-preview.cropped {
  border-color: var(--color-green-600);
}

.status-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-full);
  font-size: 0.875rem;
  font-weight: 500;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
}

/* Inline Action Button for Meta Line */
.premium-action-btn-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-md);
  background: var(--color-zinc-900);
  color: white;
  font-weight: 500;
  font-size: 0.875rem;
  border: 1px solid transparent;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
  cursor: pointer;
  height: 32px; /* Match meta-badge height approx */
}

.premium-action-btn-inline:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
  background: black;
}

.premium-action-btn-inline:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.status-wrapper {
  background: transparent !important; /* Override default meta-badge bg */
  border: 1px solid transparent !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.status-wrapper.completed {
  color: #059669; /* emerald-600 */
}

.status-wrapper.processing {
  color: var(--color-violet-600);
}

.status-wrapper.error {
  color: #dc2626;
}

.status-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.85rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
  box-shadow: var(--shadow-sm);
  border: 1px solid transparent;
}

.status-box.processing {
  color: var(--color-violet-700);
  background: var(--color-violet-50);
  border-color: var(--color-violet-100);
}

.status-box.success {
  background: #f0fdf4;
  color: #15803d; /* emerald-700 */
  border-color: #bbf7d0;
}

.status-box.error {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fecaca;
}

/* Removed empty status-indicator */

/* Document Reading Layout */
.details-content {
  max-width: 100%;
  margin-left: 0;
  margin-right: 0;
  padding: 2rem 0;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.section-title::before {
  content: '';
  display: block;
  width: 4px;
  height: 24px;
  background: var(--primary-base);
  border-radius: var(--radius-full);
}

.characters-section {
  margin-bottom: 3rem;
}

.characters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.character-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1rem;
  transition: all 0.2s;
}

.character-card:hover {
  border-color: var(--border-active);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.char-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  color: var(--color-violet-700);
}

.char-header h3 {
  font-size: 0.95rem;
  font-weight: 600;
}

.char-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
  margin-bottom: 0.75rem;
}

.char-voice {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--color-zinc-50);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  width: fit-content;
}

/* Chapter & Scene Styling */
.chapter-block {
  margin-bottom: 2rem;
}

.chapter-desc {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

.chapter-meta-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chapter-meta {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--text-muted);
  background: var(--color-zinc-100);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-full);
}

.subchapters-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.subchapter-item {
  border-left: 2px solid var(--border-subtle);
  padding-left: 1.5rem;
}

.subchapter-header {
  margin-bottom: 1rem;
}

.subchapter-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.subchapter-header p {
  font-size: 0.9rem;
  color: var(--text-muted);
}

.scenes-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.scene-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color 0.2s;
}

.scene-card:hover {
  border-color: var(--color-violet-200);
}

.scene-header {
  background: var(--color-zinc-50);
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.scene-duration {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
}

.scene-body {
  padding: 1rem;
}

.scene-primary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

@media (max-width: 640px) {
  .scene-primary {
    grid-template-columns: 1fr;
  }
}

.narration p, .visual p {
  font-size: 0.9rem;
  color: var(--text-primary);
  line-height: 1.5;
  margin-top: 0.25rem;
}

.narration strong, .visual strong {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
}

.scene-prompts {
  background: var(--color-zinc-50);
  border-radius: var(--radius-sm);
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.prompt-item {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.prompt-item svg {
  color: var(--color-violet-500);
  flex-shrink: 0;
  margin-top: 2px;
}

.prompt-text, .prompt-text-with-action {
  flex: 1;
}

.prompt-text-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.icon-btn-search {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-violet-600);
  padding: 2px;
  border-radius: 4px;
  transition: background 0.2s;
}

.icon-btn-search:hover {
  background: var(--color-violet-100);
}

.scene-video-container {
  width: 100%;
  margin-bottom: 1rem;
}

.scene-video-preview {
  position: relative;
  background: var(--bg-subtle);
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.scene-footer {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.char-info {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--color-violet-700);
  font-weight: 500;
}

.audio-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Scene Images Container */




.action-btn {
  background: rgba(0,0,0,0.6);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 4px;
  cursor: pointer;
  display: flex;
  transition: background 0.2s;
}

.action-btn:hover {
  background: rgba(0,0,0,0.8);
}

.control-btn {
  border-radius: var(--radius-full);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  color: var(--text-secondary);
}

.control-btn:hover {
  background: var(--color-zinc-200);
  color: var(--text-primary);
}

.record-btn {
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.record-btn:hover {
  background: #fee2e2;
}

.record-btn.has-recording {
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid transparent;
}

.stop-btn {
  color: white;
  background: #dc2626;
}

.stop-btn:hover {
  background: #b91c1c;
}

.delete-btn:hover {
  color: #dc2626;
  background: #fef2f2;
}

.download-btn:hover {
  color: var(--color-violet-600);
  background: var(--color-violet-50);
}

.playback-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: var(--color-zinc-100);
  padding: 2px 4px;
  border-radius: var(--radius-full);
}

/* Modals */
.loading-full {
  height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-violet-500);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-alert-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  border-radius: var(--radius-md);
  padding: 1rem;
  display: flex;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.error-content strong {
  display: block;
  margin-bottom: 0.25rem;
}

:global(.video-details-dropdown-content) {
  background: white;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 4px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); /* Shadow-lg approximation */
  min-width: 180px;
  animation: slideUpAndFade 0.2s ease-in-out;
  z-index: 9999; /* Ensure it stays on top */
}

:global(.video-details-dropdown-item) {
  font-size: 0.875rem;
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  outline: none;
  transition: background 0.1s;
}

:global(.video-details-dropdown-item:hover), :global(.video-details-dropdown-item:focus) {
  background: var(--color-zinc-100);
  color: var(--color-violet-700);
}

@keyframes slideUpAndFade {
  from {
    opacity: 0;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 17, 23, 0.60);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  background: #F3F3F3;
  padding: 2rem 2.5rem;
  border-radius: var(--radius-md);
  border: 1px solid #999;
  box-shadow: 0 8px 32px #CCC;
}

.loading-content .spin {
  color: var(--primary-base);
  opacity: 0.9;
}

.loading-content p {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: 0.025em;
}

.modal-error-content {
  padding: 1rem 0;
  color: var(--text-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

/* Screen Reader Only utility class for accessibility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Waiting Message Styles */
.waiting-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  padding: 4rem 2rem;
  text-align: center;
}

.waiting-text {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Scene Edit Button Hover Fix */
/* Using standard CSS to guarantee visibility on hover, bypassing potential Tailwind conflicts */
.scene-edit-btn {
  opacity: 0;
  transition: all 0.2s ease-in-out;
  color: #18181b !important; /* Always dark color as requested */
}

.scene-card:hover .scene-edit-btn {
  opacity: 1 !important;
}

/* Ensure scene-card has a relative position context */
.scene-card {
  position: relative;
}

/* Custom Easing for "Spring" feel */
.ease-spring {
  transition-timing-function: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.waiting-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.waiting-subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
}

.spin {
  animation: spin 1s linear infinite;
  color: var(--primary-base);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

</style>
