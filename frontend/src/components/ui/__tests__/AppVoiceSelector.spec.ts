import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AppVoiceSelector from '../AppVoiceSelector.vue'
import api from '../../../lib/axios'

// Mock API
vi.mock('../../../lib/axios', () => ({
    default: {
        get: vi.fn()
    }
}))

// Mock Audio
class MockAudio {
    play = vi.fn().mockImplementation(function () { return Promise.resolve() })
    pause = vi.fn()
    onended: any = null
}

const AudioMock = vi.fn().mockImplementation(function () { return new MockAudio() })

describe('AppVoiceSelector.vue', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.spyOn(console, 'error').mockImplementation(() => { })

        // Setup global Audio mock
        vi.stubGlobal('Audio', AudioMock)
        window.Audio = AudioMock as any
    })

    it('loads voices on mount', async () => {
        const voices = [
            { name: 'Voice 1', category: 'News', gender: 'male', demo_url: 'url1' },
            { name: 'Voice 2', category: 'Narrative', gender: 'female', demo_url: 'url2' }
        ]
        vi.mocked(api.get).mockResolvedValue({ data: voices })

        const wrapper = mount(AppVoiceSelector, {
            props: { modelValue: '' }
        })

        await flushPromises()

        // Check loading state gone
        expect(wrapper.find('.animate-spin').exists()).toBe(false)

        // Open dropdown
        await wrapper.find('.cursor-pointer').trigger('click')

        const items = wrapper.findAll('.group') // voice items
        expect(items).toHaveLength(2)
        expect(items.length).toBeGreaterThan(0)
        expect(items[0]?.text()).toContain('Voice 1')
    })

    it('selects a voice', async () => {
        const voices = [{ name: 'Voice 1', category: 'News', gender: 'male', demo_url: 'url1' }]
        vi.mocked(api.get).mockResolvedValue({ data: voices })

        const wrapper = mount(AppVoiceSelector, {
            props: { modelValue: '' }
        })
        await flushPromises()

        await wrapper.find('.cursor-pointer').trigger('click') // Open
        await wrapper.find('.group').trigger('click') // Select first

        expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['Voice 1'])
    })

    it('handles API error', async () => {
        vi.mocked(api.get).mockRejectedValue(new Error('Failed'))

        mount(AppVoiceSelector, { props: { modelValue: '' } })
        await flushPromises()

        expect(console.error).toHaveBeenCalled()
    })

    it('plays audio on button click', async () => {
        // Local mock to ensure clean state and reference
        class LocalMockAudio {
            play = vi.fn().mockImplementation(function () { return Promise.resolve() })
            pause = vi.fn()
            onended: any = null
        }
        const localMockInstance = new LocalMockAudio()
        const LocalAudioMock = vi.fn().mockImplementation(function () { return localMockInstance })

        // Override global just for this test
        vi.stubGlobal('Audio', LocalAudioMock)
        window.Audio = LocalAudioMock as any

        const voices = [{ name: 'Voice 1', category: 'News', gender: 'male', demo_url: 'url1' }]
        vi.mocked(api.get).mockResolvedValue({ data: voices })

        const wrapper = mount(AppVoiceSelector, { props: { modelValue: '' } })
        await flushPromises()

        // Open dropdown
        await wrapper.find('.cursor-pointer').trigger('click')

        // Find the play button
        const playBtn = wrapper.find('.group button')
        await playBtn.trigger('click')

        expect(LocalAudioMock).toHaveBeenCalledWith('url1')
        expect(localMockInstance.play).toHaveBeenCalled()
    })
})
