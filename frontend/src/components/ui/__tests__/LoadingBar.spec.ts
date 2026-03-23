import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LoadingBar from '../LoadingBar.vue'
import { useUIStore } from '../../../stores/ui.store'

describe('LoadingBar.vue', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('does not render when loading is false', () => {
        const wrapper = mount(LoadingBar)
        expect(wrapper.find('.loading-bar-container').exists()).toBe(false)
    })

    it('renders when loading is true', async () => {
        const uiStore = useUIStore()
        uiStore.startLoading()

        // Mount after state change or await nextTick if mounted before
        const wrapper = mount(LoadingBar)

        expect(uiStore.isGlobalLoading).toBe(true)
        expect(wrapper.find('.loading-bar-container').exists()).toBe(true)
    })
})
