import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useVideoStore } from '../video.store'
import api from '../../lib/axios'

vi.mock('../../lib/axios')

describe('Video Store', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        vi.spyOn(console, 'error').mockImplementation(() => { })
        vi.spyOn(console, 'warn').mockImplementation(() => { })
        vi.spyOn(console, 'log').mockImplementation(() => { })
    })

    it('deletes a video and updates local state', async () => {
        const store = useVideoStore()
        const mockVideo = { id: 123, prompt: 'Test Video', status: 'completed' } as any
        store.videos = [mockVideo]
        store.currentVideo = mockVideo

        const mockDelete = vi.mocked(api.delete).mockResolvedValue({ status: 204 })

        const result = await store.deleteVideo(123)

        expect(result).toBe(true)
        expect(mockDelete).toHaveBeenCalledWith('/videos/123')
        expect(store.videos).toHaveLength(0)
        expect(store.currentVideo).toBeNull()
    })

    it('handles delete failure', async () => {
        const store = useVideoStore()
        const mockVideo = { id: 123, prompt: 'Test Video', status: 'completed' } as any
        store.videos = [mockVideo]

        vi.mocked(api.delete).mockRejectedValue({
            response: { data: { detail: 'Delete failed' } }
        })

        const result = await store.deleteVideo(123)

        expect(result).toBe(false)
        expect(store.videos).toHaveLength(1)
        expect(store.error).toBe('Delete failed')
    })

    it('fetches videos', async () => {
        const store = useVideoStore()
        const mockVideos = [{ id: 1, prompt: 'V1' }, { id: 2, prompt: 'V2' }]
        vi.mocked(api.get).mockResolvedValue({ data: mockVideos })

        await store.fetchVideos()

        expect(store.videos).toEqual(mockVideos)
        expect(store.isLoading).toBe(false)
    })

    it('handles fetch error with response detail', async () => {
        const store = useVideoStore()
        vi.mocked(api.get).mockRejectedValue({
            response: { data: { detail: 'Specific Error' } }
        })

        await store.fetchVideos()

        expect(store.error).toBe('Specific Error')
    })

    it('handles fetch error', async () => {
        const store = useVideoStore()
        vi.mocked(api.get).mockRejectedValue(new Error('Fetch failed'))

        await store.fetchVideos()

        expect(store.videos).toEqual([])
        expect(store.error).toBe('Erro ao carregar vídeos.')
    })

    it('gets a single video', async () => {
        const store = useVideoStore()
        const mockVideo = { id: 1, prompt: 'V1' }
        vi.mocked(api.get).mockResolvedValue({ data: mockVideo })

        await store.getVideo('1')

        expect(store.currentVideo).toEqual(mockVideo)
    })

    it('creates a video', async () => {
        const store = useVideoStore()
        const newVideo = { id: 3, prompt: 'New' }
        vi.mocked(api.post).mockResolvedValue({ data: newVideo })

        const payload = { prompt: 'New', target_duration_minutes: 5, language: 'pt-br' }
        const result = await store.createVideo(payload)

        expect(result).toBe(3)
        expect(store.videos[0]).toEqual(newVideo)
    })

    it('reprocesses a video', async () => {
        const store = useVideoStore()
        const video = { id: 1, status: 'error' } as any
        store.currentVideo = video
        const updated = { id: 1, status: 'processing' }
        vi.mocked(api.post).mockResolvedValue({ data: updated })

        const result = await store.reprocessVideo(1)

        expect(result).toBe(true)
        expect(store.currentVideo!.status).toBe('processing')
    })

    it('cancels processing', async () => {
        const store = useVideoStore()
        const cancelled = { id: 1, status: 'cancelled' }
        vi.mocked(api.post).mockResolvedValue({ data: cancelled })

        await store.cancelVideo(1)

        expect(api.post).toHaveBeenCalledWith('/videos/1/cancel')
    })

    it('duplicates a video', async () => {
        const store = useVideoStore()
        const newVideo = { id: 2, prompt: 'Copy' }
        vi.mocked(api.post).mockResolvedValue({ data: newVideo })

        const result = await store.duplicateVideo(1)

        expect(result).toEqual(newVideo)
        expect(api.post).toHaveBeenCalledWith('/videos/1/duplicate')
    })

    it('updates a video', async () => {
        const store = useVideoStore()
        const updated = { id: 1, title: 'Updated' }
        vi.mocked(api.put).mockResolvedValue({ data: updated })

        await store.updateVideo(1, { title: 'Updated' })

        expect(api.put).toHaveBeenCalledWith('/videos/1', { title: 'Updated' })
        expect(store.currentVideo?.title).toBe('Updated')
    })

    it('reprocesses a chapter', async () => {
        const store = useVideoStore()
        store.currentVideo = { id: 1 } as any
        const updated = { id: 1, status: 'processing' } as any
        vi.mocked(api.post).mockResolvedValue({ data: updated })

        const result = await store.reprocessChapter(1, 10)

        expect(result).toBe(true)
        expect(api.post).toHaveBeenCalledWith('/videos/1/chapters/10/reprocess')
        expect(store.currentVideo?.status).toBe('processing')
    })

    it('reprocesses video audio', async () => {
        const store = useVideoStore()
        store.currentVideo = { id: 1 } as any
        const updated = { id: 1, status: 'processing' }
        vi.mocked(api.post).mockResolvedValue({ data: updated })

        const result = await store.reprocessVideoAudio(1)

        expect(result).toBe(true)
        expect(api.post).toHaveBeenCalledWith('/videos/1/reprocess/audio')
        expect(store.currentVideo!.status).toBe('processing')
    })

    it('reprocesses video images', async () => {
        const store = useVideoStore()
        store.currentVideo = { id: 1 } as any
        const updated = { id: 1, status: 'processing' } as any
        vi.mocked(api.post).mockResolvedValue({ data: updated })

        const result = await store.reprocessVideoImages(1, 'google')

        expect(result).toBe(true)
        expect(api.post).toHaveBeenCalledWith('/videos/1/reprocess/images', null, {
            params: { provider: 'google' }
        })
        expect(store.currentVideo!.status).toBe('processing')
    })

    it('reprocessVideoImages does not update current if ID mismatch', async () => {
        const store = useVideoStore()
        store.currentVideo = { id: 2 } as any
        vi.mocked(api.post).mockResolvedValue({ data: { id: 1 } })
        await store.reprocessVideoImages(1)
        expect(store.currentVideo!.id).toBe(2)
    })

    it('triggers render', async () => {
        const store = useVideoStore()
        store.currentVideo = { id: 1 } as any
        const updated = { id: 1, status: 'rendering' }
        vi.mocked(api.post).mockResolvedValue({ data: updated })

        const result = await store.triggerRender(1)

        expect(result).toBe(true)
        expect(api.post).toHaveBeenCalledWith('/videos/1/render')
        expect(store.currentVideo!.status).toBe('rendering')
    })

    it('uploads scene audio', async () => {
        const store = useVideoStore()
        const updatedVideo = { id: 1, chapters: [] } as any
        vi.mocked(api.post).mockResolvedValue({ data: updatedVideo })

        const blob = new Blob(['test'], { type: 'audio/webm' })
        const result = await store.uploadSceneAudio(1, 1, 1, 0, blob, 10.5)

        expect(result).toBe(true)
        expect(api.post).toHaveBeenCalledWith(
            expect.stringContaining('/videos/1/scenes/audio'),
            expect.any(FormData),
            expect.any(Object)
        )
    })

    it('deletes scene audio', async () => {
        const store = useVideoStore()
        const updatedVideo = { id: 1, chapters: [] } as any
        vi.mocked(api.delete).mockResolvedValue({ data: updatedVideo })

        const result = await store.deleteSceneAudio(1, 1, 1, 0)

        expect(result).toBe(true)
        expect(api.delete).toHaveBeenCalledWith(
            '/videos/1/scenes/audio',
            expect.objectContaining({
                params: { chapter_id: 1, subchapter_id: 1, scene_index: 0 }
            })
        )
    })

    it('handles generic errors in various methods', async () => {
        const store = useVideoStore()
        vi.mocked(api.post).mockRejectedValue(new Error('Generic Error'))
        vi.mocked(api.delete).mockRejectedValue(new Error('Delete Error'))
        vi.mocked(api.put).mockRejectedValue(new Error('Update Error'))

        expect(await store.reprocessVideo(1)).toBe(false)
        expect(store.error).toBe('Generic Error')

        expect(await store.reprocessChapter(1, 1)).toBe(false)
        expect(await store.reprocessVideoAudio(1)).toBe(false)
        expect(await store.reprocessVideoImages(1)).toBe(false)
        expect(await store.triggerRender(1)).toBe(false)

        expect(await store.uploadSceneAudio(1, 1, 1, 0, new Blob())).toBe(false)
        expect(await store.deleteSceneAudio(1, 1, 1, 0)).toBe(false)
        expect(await store.updateVideo(1, {})).toBe(false)
    })

    it('updateVideo handles index not found', async () => {
        const store = useVideoStore()
        store.videos = [{ id: 2, prompt: 'Other' }] as any
        const updated = { id: 1, title: 'Updated' }
        vi.mocked(api.put).mockResolvedValue({ data: updated })

        await store.updateVideo(1, { title: 'Updated' })
        expect(store.videos[0]!.id).toBe(2) // No change in list
        expect(store.currentVideo?.title).toBe('Updated')
    })

    it('uploadSceneAudio updates currentVideo on success', async () => {
        const store = useVideoStore()
        const updatedVideo = { id: 1, chapters: [{ id: 10 }] } as any
        store.currentVideo = { id: 1 } as any
        const mockPost = vi.mocked(api.post).mockResolvedValue({ data: updatedVideo })
        const blob = new Blob(['test'], { type: 'audio/webm' })
        await store.uploadSceneAudio(1, 1, 1, 0, blob, 10)

        const formData = mockPost.mock.calls![0]![1] as FormData
        expect(formData.get('duration_seconds')).toBe('10')
    })

    it('deleteSceneAudio updates currentVideo on success', async () => {
        const store = useVideoStore()
        const updatedVideo = { id: 1, chapters: [] } as any
        store.currentVideo = { id: 1, chapters: [{ id: 10 }] } as any
        vi.mocked(api.delete).mockResolvedValue({ data: updatedVideo })

        await store.deleteSceneAudio(1, 1, 1, 0)

        expect(store.currentVideo!.chapters).toHaveLength(0)
    })

    it('handles duplicate error', async () => {
        const store = useVideoStore()
        vi.mocked(api.post).mockRejectedValue(new Error('Duplicate Error'))
        const result = await store.duplicateVideo(1)
        expect(result).toBeNull()
        expect(store.error).toBe('Duplicate Error')
    })
    it('getVideo handles error', async () => {
        const store = useVideoStore()
        vi.mocked(api.get).mockRejectedValue(new Error('Get Error'))
        await store.getVideo('1')
        expect(store.error).toBe('Get Error')
    })

    it('createVideo handles error', async () => {
        const store = useVideoStore()
        vi.mocked(api.post).mockRejectedValue(new Error('Create Error'))
        const result = await store.createVideo({ prompt: 'test', target_duration_minutes: 1, language: 'en' })
        expect(result).toBeNull()
        expect(store.error).toBe('Create Error')
    })

    it('cancelVideo handles error', async () => {
        const store = useVideoStore()
        vi.mocked(api.post).mockRejectedValue(new Error('Cancel Error'))
        await expect(store.cancelVideo(1)).rejects.toThrow('Cancel Error')
    })

    it('uploadSceneAudio handles generic error', async () => {
        const store = useVideoStore()
        vi.mocked(api.post).mockRejectedValue(new Error('Upload Error'))
        const result = await store.uploadSceneAudio(1, 1, 1, 0, new Blob())
        expect(result).toBe(false)
    })

    it('deleteVideo clears currentVideo if it matches', async () => {
        const store = useVideoStore()
        const video = { id: 1 } as any
        store.videos = [video]
        store.currentVideo = video
        vi.mocked(api.delete).mockResolvedValue({ status: 204 })

        await store.deleteVideo(1)
        expect(store.currentVideo).toBeNull()
    })

    it('deleteVideo handles error without response detail', async () => {
        const store = useVideoStore()
        vi.mocked(api.delete).mockRejectedValue(new Error('Generic Delete Error'))
        await store.deleteVideo(1)
        expect(store.error).toBe('Erro ao excluir vídeo.')
    })

    it('reprocessVideo does not update currentVideo if ID does not match', async () => {
        const store = useVideoStore()
        store.currentVideo = { id: 2, status: 'completed' } as any
        const updated = { id: 1, status: 'processing' } as any
        vi.mocked(api.post).mockResolvedValue({ data: updated })

        await store.reprocessVideo(1)
        expect(store.currentVideo!.id).toBe(2)
        expect(store.currentVideo!.status).toBe('completed')
    })

    it('fetchVideos handles null data with empty array', async () => {
        const store = useVideoStore()
        vi.mocked(api.get).mockResolvedValue({ data: null })
        await store.fetchVideos()
        expect(store.videos).toEqual([])
    })

    it('uploadSceneAudio handles missing duration', async () => {
        const store = useVideoStore()
        vi.mocked(api.post).mockResolvedValue({ data: {} })
        const blob = new Blob()
        await store.uploadSceneAudio(1, 1, 1, 0, blob)
        // Verify FormData does NOT contain duration_seconds
        const formData = vi.mocked(api.post).mock.calls[0]![1] as FormData
        expect(formData.get('duration_seconds')).toBeNull()
    })

    it('deleteVideo does not clear currentVideo if it does not match', async () => {
        const store = useVideoStore()
        store.currentVideo = { id: 2 } as any
        vi.mocked(api.delete).mockResolvedValue({ status: 204 })
        await store.deleteVideo(1)
        expect(store.currentVideo!.id).toBe(2)
    })
    it('reprocessVideo handles error without message', async () => {
        const store = useVideoStore()
        vi.mocked(api.post).mockRejectedValue({})
        await store.reprocessVideo(1)
        expect(store.error).toBe('Failed to reprocess video')
    })
    it('cancelVideo updates video in list and currentVideo', async () => {
        const store = useVideoStore()
        const oldVideo = { id: 1, status: 'processing' } as any
        const updatedVideo = { id: 1, status: 'cancelled' } as any
        store.videos = [oldVideo]
        store.currentVideo = oldVideo
        vi.mocked(api.post).mockResolvedValue({ data: updatedVideo })

        await store.cancelVideo(1)
        expect(store.videos[0]!.status).toBe('cancelled')
        expect(store.currentVideo!.status).toBe('cancelled')
    })

    it('updateVideo updates video in list', async () => {
        const store = useVideoStore()
        const oldVideo = { id: 1, title: 'Old' } as any
        const updatedVideo = { id: 1, title: 'New' } as any
        store.videos = [oldVideo]
        vi.mocked(api.put).mockResolvedValue({ data: updatedVideo })

        await store.updateVideo(1, { title: 'New' })
        expect(store.videos[0]!.title).toBe('New')
    })
})
