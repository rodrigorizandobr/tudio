import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../lib/axios'
import { useUIStore } from './ui.store'

export interface Video {
    id: number
    prompt: string
    status: 'pending' | 'processing' | 'rendering' | 'rendering_scenes' | 'completed' | 'error' | 'cancelled'
    visual_style?: string
    aspect_ratios?: string[]
    outputs?: Record<string, string>
    agent_id?: string
    language: string

    // Sprint 62
    title?: string
    description?: string
    tags?: string
    // Sprint 63
    music?: string
    music_id?: number | null // Sprint 105

    // Sprint 71
    audio_transition_padding: number

    // Sprint 72
    audio_generation_instructions?: string

    created_at: string
    updated_at?: string
    progress: number
    rendering_progress?: number
    target_duration_minutes?: number
    total_duration_seconds: number
    video_url?: string
    timestamps_index?: string
    error_message?: string | null
    characters?: any[]
    chapters?: any[]

    // Captions (Sprint 200)
    caption_status?: 'none' | 'processing' | 'done' | 'error'
    caption_progress?: number
    caption_style?: string
    caption_force_whisper?: boolean
    caption_options?: Record<string, any>
    captioned_outputs?: Record<string, string>
}

export const useVideoStore = defineStore('video', () => {
    const uiStore = useUIStore()
    const videos = ref<Video[]>([])
    const currentVideo = ref<Video | null>(null)
    const isLoading = ref(false)
    const isCreating = ref(false)
    const error = ref<string | null>(null)

    // Filter & Sort State
    const searchQuery = ref('')
    const statusFilter = ref<string | null>(null)
    const showDeleted = ref(false)
    const sortBy = ref('created_at')
    const sortOrder = ref<'asc' | 'desc'>('desc')

    const fetchVideos = async () => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null
        try {
            const params: any = {
                sort_by: sortBy.value,
                sort_order: sortOrder.value,
                show_deleted: showDeleted.value
            }
            if (searchQuery.value) params.search = searchQuery.value
            if (statusFilter.value) params.status = statusFilter.value

            const response = await api.get('/videos', { params })
            videos.value = response.data ?? []
        } catch (e: any) {
            console.error('Failed to fetch videos:', e)
            error.value = e.response?.data?.detail || 'Erro ao carregar vídeos.'
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }

    const getVideo = async (id: string, silent: boolean = false) => {
        if (!silent) {
            isLoading.value = true
            uiStore.startLoading()
        }
        error.value = null
        try {
            const response = await api.get(`/videos/${id}`)
            currentVideo.value = response.data
        } catch (e: any) {
            error.value = e.message || 'Failed to fetch video'
        } finally {
            if (!silent) {
                isLoading.value = false
                uiStore.stopLoading()
            }
        }
    }

    /** Alias for getVideo — refreshes currentVideo by numeric ID */
    const fetchVideo = async (id: number, silent: boolean = false) => {
        await getVideo(String(id), silent)
    }

    const createVideo = async (payload: { prompt: string; target_duration_minutes: number; language: string; agent_id?: string; aspect_ratios?: string[]; auto_image_source?: string; auto_generate_narration?: boolean; script_content?: string; audio_transition_padding?: number }) => {

        isCreating.value = true
        error.value = null
        try {
            const response = await api.post('/videos/', payload)
            // Add to list and select it
            const newVideo = response.data
            videos.value.unshift(newVideo)
            return newVideo.id
        } catch (e: any) {
            error.value = e.message || 'Failed to create video'
            return null
        } finally {
            isCreating.value = false
        }
    }

    const reprocessVideo = async (id: number) => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null

        // Optimistic UI Update: Show processing immediately
        if (currentVideo.value && currentVideo.value.id === id) {
            currentVideo.value.status = 'processing'
            currentVideo.value.progress = 0
            currentVideo.value.error_message = null
        }

        try {
            const response = await api.post(`/videos/${id}/reprocess`)
            if (currentVideo.value && currentVideo.value.id === id) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            error.value = e.message || 'Failed to reprocess video'
            return false
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }

    const reprocessChapter = async (videoId: number, chapterId: number) => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null
        try {
            const response = await api.post(`/videos/${videoId}/chapters/${chapterId}/reprocess`)
            if (currentVideo.value && currentVideo.value.id === videoId) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            error.value = e.message || 'Failed to reprocess chapter'
            return false
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }

    const cancelVideo = async (id: number) => {
        isLoading.value = true
        error.value = null
        try {
            const response = await api.post<Video>(`/videos/${id}/cancel`)

            // Update local state if it matches current video
            if (currentVideo.value && currentVideo.value.id === id) {
                currentVideo.value = response.data
            }

            // Update in list
            const index = videos.value.findIndex(v => v.id === id)
            if (index !== -1) {
                videos.value[index] = response.data
            }

            return response.data
        } catch (err: any) {
            error.value = 'Failed to cancel video'
            console.error(err)
            throw err
        } finally {
            isLoading.value = false
        }
    }

    const duplicateVideo = async (videoId: number) => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null
        try {
            const response = await api.post(`/videos/${videoId}/duplicate`)
            // We do NOT set currentVideo here because we likely want to redirect
            return response.data // Returns the new video object
        } catch (e: any) {
            error.value = e.message || 'Failed to duplicate video'
            return null
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }

    const uploadSceneAudio = async (videoId: number, chapterId: number, subChapterId: number, sceneIndex: number, file: Blob, duration?: number) => {
        // No global loading to avoid full screen freeze, handle locally in UI
        try {
            const formData = new FormData()
            formData.append('chapter_id', chapterId.toString())
            formData.append('subchapter_id', subChapterId.toString())
            formData.append('scene_index', sceneIndex.toString())
            formData.append('file', file, 'recording.webm')
            if (duration) {
                formData.append('duration_seconds', duration.toString())
            }

            const response = await api.post(`/videos/${videoId}/scenes/audio`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })

            // Update current video with new data
            if (currentVideo.value && currentVideo.value.id === videoId) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            console.error('Upload failed:', e)
            return false
        }
    }

    const deleteSceneAudio = async (videoId: number, chapterId: number, subChapterId: number, sceneIndex: number) => {
        try {
            const response = await api.delete(`/videos/${videoId}/scenes/audio`, {
                params: {
                    chapter_id: chapterId,
                    subchapter_id: subChapterId,
                    scene_index: sceneIndex
                }
            })

            // Update current video w/ cleaned scene
            if (currentVideo.value && currentVideo.value.id === videoId) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            console.error('Delete audio failed:', e)
            return false
        }
    }

    const updateVideo = async (id: number, data: any) => {
        try {
            const response = await api.put(`/videos/${id}`, data)
            currentVideo.value = response.data
            // Update in list if exists
            const index = videos.value.findIndex(v => v.id === id)
            if (index !== -1) {
                videos.value[index] = response.data
            }
            return true
        } catch (e: any) {
            console.error('Update failed:', e)
            return false
        }
    }

    const reprocessVideoAudio = async (videoId: number) => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null
        try {
            const response = await api.post(`/videos/${videoId}/reprocess/audio`)
            if (currentVideo.value && currentVideo.value.id === videoId) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            error.value = e.message || 'Failed to reprocess audio'
            return false
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }

    const reprocessVideoImages = async (id: number, provider = "unsplash") => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null
        try {
            const response = await api.post(`/videos/${id}/reprocess/images`, null, {
                params: { provider }
            })
            if (currentVideo.value && currentVideo.value.id === id) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            error.value = e.message || 'Failed to reprocess images'
            return false
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }

    const triggerSceneRender = async (id: number, force: boolean = false) => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null
        try {
            const response = await api.post(`/videos/${id}/render/scenes`, null, {
                params: { force }
            })
            if (currentVideo.value && currentVideo.value.id === id) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            error.value = e.message || 'Failed to trigger scene render'
            return false
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }

    const triggerRender = async (id: number) => {
        isLoading.value = true
        uiStore.startLoading()
        error.value = null
        try {
            const response = await api.post(`/videos/${id}/render`)
            if (currentVideo.value && currentVideo.value.id === id) {
                currentVideo.value = response.data
            }
            return true
        } catch (e: any) {
            error.value = e.message || 'Failed to trigger render'
            return false
        } finally {
            isLoading.value = false
            uiStore.stopLoading()
        }
    }


    const renderScene = async (videoId: number, chapterId: number, subId: number, sceneIdx: number) => {
        try {
            // Just fire the render job. The API returns immediately (202 Accepted style).
            // Do NOT overwrite currentVideo here — the optimistic state (generated_video_url = null)
            // must persist so the loading overlay stays visible during the background processing.
            // Polling will pick up the new URL when the job finishes.
            await api.post(`/videos/${videoId}/chapters/${chapterId}/subchapters/${subId}/scenes/${sceneIdx}/render`)
            return true
        } catch (e: any) {
            console.error('Failed to trigger scene render:', e)
            error.value = e.response?.data?.detail || 'Erro ao processar cena.'
            return false
        }
    }

    const saveCaptionStyle = async (videoId: number, style: string, options: any, forceWhisper: boolean = false) => {
        try {
            const response = await api.patch(`/videos/${videoId}/captions/style`, {
                style,
                force_whisper: forceWhisper,
                options
            })
            // Update local state
            if (currentVideo.value && currentVideo.value.id === videoId) {
                currentVideo.value.caption_style = style
                currentVideo.value.caption_force_whisper = forceWhisper
                currentVideo.value.caption_options = options
            }
            return response.data
        } catch (e: any) {
            console.error('Failed to save caption style:', e)
            throw e
        }
    }

    const deleteVideo = async (id: number) => {
        try {
            await api.delete(`/videos/${id}`)

            // Remove from local list
            videos.value = videos.value.filter(v => v.id !== id)

            // Clear current if matches
            if (currentVideo.value && currentVideo.value.id === id) {
                currentVideo.value = null
            }
            return true
        } catch (e: any) {
            console.error('Delete video failed:', e)
            error.value = e.response?.data?.detail || 'Erro ao excluir vídeo.'
            return false
        }
    }

    const restoreVideo = async (id: number) => {
        try {
            await api.post(`/videos/${id}/restore`)

            // Remove from local list (since it's no longer "deleted/in trash")
            videos.value = videos.value.filter(v => v.id !== id)

            return true
        } catch (e: any) {
            console.error('Restore video failed:', e)
            error.value = e.response?.data?.detail || 'Erro ao restaurar vídeo.'
            return false
        }
    }


    return {
        videos,
        currentVideo,
        isLoading,
        isCreating,
        error,
        searchQuery,
        statusFilter,
        showDeleted,
        sortBy,
        sortOrder,
        fetchVideos,
        getVideo,
        fetchVideo,
        createVideo,
        reprocessVideo,
        reprocessChapter,
        cancelVideo,
        duplicateVideo,
        reprocessVideoAudio,
        reprocessVideoImages,
        triggerVideoImages: reprocessVideoImages,
        triggerVideoAudio: reprocessVideoAudio,
        triggerSceneRender,
        triggerRender,
        renderScene,
        uploadSceneAudio,
        deleteSceneAudio,
        updateVideo,
        saveCaptionStyle,
        deleteVideo,
        restoreVideo
    }
})

