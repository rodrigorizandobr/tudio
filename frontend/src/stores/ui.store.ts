import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
    const isGlobalLoading = ref(false)

    const startLoading = () => { isGlobalLoading.value = true }
    const stopLoading = () => { isGlobalLoading.value = false }

    // Mock toast for now (can be expanded with a real Toast component)
    const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
        console.log(`[TOAST ${type.toUpperCase()}]: ${message}`)
        // TODO: Implement actual visual toast
    }

    return {
        isGlobalLoading,
        startLoading,
        stopLoading,
        showToast
    }
})
