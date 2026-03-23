import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LoginView from '../../views/LoginView.vue'
import { useAuthStore } from '../../stores/auth.store'

// Mock router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
    useRouter: () => ({
        push: mockPush
    }),
    RouterLink: { template: '<a><slot/></a>' }
}))

describe('LoginView.vue', () => {
    beforeEach(() => {
        // Mock localStorage
        const localStorageMock = (() => {
            let store: Record<string, string> = {}
            return {
                getItem: vi.fn((key: string) => store[key] || null),
                setItem: vi.fn((key: string, value: string) => {
                    store[key] = value.toString()
                }),
                removeItem: vi.fn((key: string) => {
                    delete store[key]
                }),
                clear: vi.fn(() => {
                    store = {}
                }),
                key: vi.fn((index: number) => Object.keys(store)[index] || null),
                length: 0
            }
        })()

        Object.defineProperty(window, 'localStorage', {
            value: localStorageMock,
            writable: true
        })

        setActivePinia(createPinia())
        mockPush.mockClear()
    })

    it('renders login form', () => {
        const wrapper = mount(LoginView)
        expect(wrapper.text()).toContain('TudioV2')
        expect(wrapper.text()).toContain('AI Video Generation Platform')

        // Inputs might be inside AppInput components, so finding inputs works if AppInput renders input
        expect(wrapper.find('input[type="email"]').exists()).toBe(true)
        expect(wrapper.find('input[type="password"]').exists()).toBe(true)
        expect(wrapper.find('button').text()).toContain('Entrar')
    })

    it('calls auth store login on submit', async () => {
        const wrapper = mount(LoginView)
        const authStore = useAuthStore()
        // Mock login action
        authStore.login = vi.fn().mockResolvedValue(true)

        await wrapper.find('input[type="email"]').setValue('user@test.com')
        await wrapper.find('input[type="password"]').setValue('password')
        await wrapper.find('form').trigger('submit.prevent')

        expect(authStore.login).toHaveBeenCalledWith('user@test.com', 'password')
        expect(mockPush).toHaveBeenCalledWith('/')
    })

    it('displays error on login failure', async () => {
        const wrapper = mount(LoginView)
        const authStore = useAuthStore()
        authStore.login = vi.fn().mockResolvedValue(false)

        // Simulate error state in store (since we mock useAuthStore locally/globally, we access the instance)
        // Note: Pinia state mutation needs to be reactive. 
        // But here we just mock login return false. The view likely reads authStore.error.
        // We need to set it.
        authStore.error = 'Invalid credentials'

        await wrapper.find('input[type="email"]').setValue('user@test.com')
        await wrapper.find('input[type="password"]').setValue('wrong')
        await wrapper.find('form').trigger('submit.prevent')

        await wrapper.vm.$nextTick()

        expect(mockPush).not.toHaveBeenCalled()
        expect(wrapper.text()).toContain('Invalid credentials')
    })
})
