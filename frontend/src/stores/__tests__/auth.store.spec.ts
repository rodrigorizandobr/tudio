import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth.store'
import api from '../../lib/axios'

// Mock api directly
vi.mock('../../lib/axios', () => ({
    default: {
        post: vi.fn(),
        get: vi.fn()
    }
}))

// Mock localStorage
const localStorageMock = (() => {
    let store: Record<string, string> = {}
    return {
        getItem: vi.fn((key: string) => store[key] || null),
        setItem: vi.fn((key: string, value: string) => { store[key] = value.toString() }),
        clear: vi.fn(() => { store = {} }),
        removeItem: vi.fn((key: string) => { delete store[key] })
    }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('Auth Store', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        localStorageMock.clear()
        vi.clearAllMocks()
        vi.spyOn(console, 'error').mockImplementation(() => { })
    })

    it('initializes with token from localStorage', () => {
        localStorageMock.getItem.mockImplementation((key: string) => {
            if (key === 'token') return 'stored-token'
            return null
        })
        const store = useAuthStore()
        expect(store.token).toBe('stored-token')
        expect(store.isAuthenticated).toBe(true)
    })

    it('initializes without token', () => {
        localStorageMock.getItem.mockReturnValue(null)
        const store = useAuthStore()
        expect(store.token).toBe(null)
        expect(store.isAuthenticated).toBe(false)
    })

    it('login success sets token and user', async () => {
        const store = useAuthStore()
        vi.mocked(api.post).mockResolvedValue({
            data: { access_token: 'new-token' }
        })
        vi.mocked(api.get).mockResolvedValue({
            data: { id: 1, email: 'test@test.com' }
        })

        const success = await store.login('test@test.com', 'password')

        expect(success).toBe(true)
        expect(store.token).toBe('new-token')
        expect(store.user).toEqual({ id: 1, email: 'test@test.com' })
        expect(localStorageMock.setItem).toHaveBeenCalledWith('token', 'new-token')
    })

    it('login failure handles error', async () => {
        const store = useAuthStore()
        vi.mocked(api.post).mockRejectedValue(new Error('Auth failed'))

        const success = await store.login('test@test.com', 'wrong')

        expect(success).toBe(false)
        expect(store.token).toBe(null)
        expect(store.error).toBe('Login failed') // Fallback message
    })

    it('fetchUser without token returns early', async () => {
        const store = useAuthStore()
        store.token = null

        await store.fetchUser()

        expect(api.get).not.toHaveBeenCalled()
    })

    it('fetchUser success updates user', async () => {
        const store = useAuthStore()
        store.token = 'valid-token'
        vi.mocked(api.get).mockResolvedValue({
            data: { id: 1, email: 'fetched@test.com' }
        })

        await store.fetchUser()

        expect(store.user).toEqual({ id: 1, email: 'fetched@test.com' })
    })
})
