import { describe, it, expect } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUIStore } from '../ui.store'

describe('UI Store', () => {
    setActivePinia(createPinia())

    it('manages loading state', () => {
        const store = useUIStore()
        expect(store.isGlobalLoading).toBe(false)
        store.startLoading()
        expect(store.isGlobalLoading).toBe(true)
        store.stopLoading()
        expect(store.isGlobalLoading).toBe(false)
    })

    it('shows toast', () => {
        const store = useUIStore()
        store.showToast('Test', 'success')
        store.showToast('Error', 'error')
        store.showToast('Info')
        // Just verify no crash and console log
    })
})
