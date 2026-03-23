/**
 * useUploadToast.ts
 * Composable for managing YouTube upload job progress toasts.
 * Singleton state via module-level refs — shared across all component instances.
 */
import { ref, computed } from 'vue'
import api from '../lib/axios'

export interface UploadJob {
    id: string
    format: string
    label: string
    status: 'pending' | 'uploading' | 'done' | 'error'
    progress: number
    error?: string
    youtubeVideoId?: string
}

// Module-level singleton state
export const uploadJobs = ref<UploadJob[]>([])
export const isToastMinimized = ref(false)

export const isToastVisible = computed(() => uploadJobs.value.length > 0)
export const allUploadsDone = computed(() =>
    uploadJobs.value.length > 0 && uploadJobs.value.every(j => j.status === 'done' || j.status === 'error')
)
export const hasUploadError = computed(() => uploadJobs.value.some(j => j.status === 'error'))
export const overallUploadProgress = computed(() => {
    if (uploadJobs.value.length === 0) return 0
    return Math.round(uploadJobs.value.reduce((sum, j) => sum + j.progress, 0) / uploadJobs.value.length)
})

let pollTimer: ReturnType<typeof setInterval> | null = null
let autoDismissTimer: ReturnType<typeof setTimeout> | null = null

const stopPolling = () => {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

const startPolling = () => {
    stopPolling()
    pollTimer = setInterval(async () => {
        const active = uploadJobs.value.filter(j => j.status === 'pending' || j.status === 'uploading')
        if (active.length === 0) {
            stopPolling()
            if (allUploadsDone.value) {
                autoDismissTimer = setTimeout(() => { uploadJobs.value = [] }, 7000)
            }
            return
        }
        for (const job of active) {
            try {
                const { data } = await api.get(`/social/upload/jobs/${job.id}`)
                job.status = data.status
                job.progress = data.progress ?? job.progress
                job.error = data.error
                job.youtubeVideoId = data.youtube_video_id
            } catch {
                // Silently retry on next tick
            }
        }
    }, 1500)
}

export const useUploadToast = () => {
    const addJobs = (payload: {
        videoTitle: string
        formats: string[]
        uploads: Array<{ ratio: string; jobId?: string }>
    }) => {
        if (autoDismissTimer) { clearTimeout(autoDismissTimer); autoDismissTimer = null }

        const newJobs: UploadJob[] = payload.uploads
            .filter(u => u.jobId)
            .map(u => ({
                id: u.jobId!,
                format: u.ratio,
                label: u.ratio === '16:9' ? 'Horizontal (16:9)' : 'Vertical (9:16)',
                status: 'pending' as const,
                progress: 0,
            }))

        if (newJobs.length === 0) {
            console.warn('[useUploadToast] No valid job IDs received. Skipping toast.')
            return
        }

        uploadJobs.value = newJobs
        isToastMinimized.value = false
        startPolling()
    }

    const dismiss = () => {
        stopPolling()
        if (autoDismissTimer) { clearTimeout(autoDismissTimer); autoDismissTimer = null }
        uploadJobs.value = []
    }

    return { addJobs, dismiss }
}
