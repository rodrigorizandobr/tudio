import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../lib/axios'

interface VideoMeta {
    id: string
    title: string
    provider: 'pexels' | 'pixabay' | 'google'
    thumbnail: string
    duration: number
}

interface DownloadState {
    status: 'idle' | 'downloading' | 'completed' | 'error'
    progress: number
    videoMeta: VideoMeta | null
    localUrl: string | null
    errorMessage: string | null
}

export const useVideoDownloadStore = defineStore('videoDownload', () => {
    const status = ref<DownloadState['status']>('idle')
    const progress = ref(0)
    const videoMeta = ref<VideoMeta | null>(null)
    const localUrl = ref<string | null>(null)
    const errorMessage = ref<string | null>(null)

    const isDownloading = computed(() => status.value === 'downloading')
    const isCompleted = computed(() => status.value === 'completed')
    const isError = computed(() => status.value === 'error')
    const isVisible = computed(() => status.value !== 'idle')

    let simulationInterval: number | null = null

    const reset = () => {
        status.value = 'idle'
        progress.value = 0
        videoMeta.value = null
        localUrl.value = null
        errorMessage.value = null
        if (simulationInterval) {
            clearInterval(simulationInterval)
            simulationInterval = null
        }
    }

    const startDownload = async (video: any, options?: {
        projectVideoId?: string,
        chapterId?: number,
        subId?: number,
        sceneIndex?: number
    }) => {
        // If already downloading, maybe confirm or queue? For now, replace.
        reset()

        status.value = 'downloading'
        progress.value = 5 // Start at 5%

        // Normalize meta
        videoMeta.value = {
            id: video.id,
            title: video.description || video.author_name || 'Sem título',
            provider: video.provider,
            thumbnail: video.thumbnail,
            duration: video.duration
        }

        // Simulate progress while waiting for backend
        simulationInterval = window.setInterval(() => {
            if (progress.value < 90) {
                // Slow initialization, then random increments
                const increment = Math.random() * 2 + 0.5
                progress.value = Math.min(progress.value + increment, 90)
            }
        }, 500)

        try {
            // Determine correct download payload based on provider
            // Backend expects:
            // Pexels/Pixabay: video_url, video_id, provider
            // Google/Youtube: video_url, video_id, provider

            const payload: any = {
                video_url: video.video_url || video.link, // Handle different API response shapes if any
                video_id: String(video.id),
                provider: video.provider
            }

            // Add context if provided
            if (options) {
                if (options.projectVideoId) payload.project_video_id = Number(options.projectVideoId)
                if (options.chapterId) payload.chapter_id = options.chapterId
                if (options.subId) payload.subchapter_id = options.subId
                if (options.sceneIndex) payload.scene_index = options.sceneIndex
            }

            console.log('[VideoDownload] Starting download:', payload)

            const response = await api.post('/video-search/download', payload)

            // Force 100%
            progress.value = 100
            if (simulationInterval) clearInterval(simulationInterval)

            // Backend returns { local_path: "...", local_url: "..." }
            // We need local_url for the frontend player

            // Assuming backend returns relative path or full URL. 
            // If it returns 'storage/videos/...', we might need to prepend API URL if not serving static directly?
            // Usually setup maps /storage to static. Let's assume response.data.local_url is usable.

            // Note: Previous tasks fixed local_url.
            const result = response.data

            // If local_url is missing, construct it from path (fallback)
            // Ideally backend sends full correct URL.
            let finalUrl = result.local_url
            if (!finalUrl && result.local_path) {
                // Fallback logic if needed, but let's trust backend first
                finalUrl = result.local_path
            }

            // Ensure it's a full URL if it's relative
            if (finalUrl && !finalUrl.startsWith('http')) {
                // If it starts with storage/, prepend /api/
                if (finalUrl.startsWith('storage/')) {
                    finalUrl = '/api/' + finalUrl
                } else if (!finalUrl.startsWith('/')) {
                    // Safe fallback
                    finalUrl = '/api/storage/' + finalUrl
                }
            }

            localUrl.value = finalUrl
            status.value = 'completed'
            console.log('[VideoDownload] Completed:', finalUrl)

        } catch (error: any) {
            console.error('[VideoDownload] Error:', error)
            status.value = 'error'
            errorMessage.value = error.response?.data?.detail || 'Falha no download'
            if (simulationInterval) clearInterval(simulationInterval)
        }
    }

    const closePip = () => {
        // Only allow close if completed or error? Or allow canceling?
        // User requested "allow user to do other things", so close just hides PIP but keeps download?
        // No, "close" usually means "dismiss result".
        // If downloading, maybe warn? For now simple close.
        reset()
    }

    return {
        status,
        progress,
        videoMeta,
        localUrl,
        errorMessage,
        isDownloading,
        isCompleted,
        isError,
        isVisible,
        startDownload,
        closePip,
        reset
    }
})
