import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../lib/axios'


interface User {
    email: string
    is_active: boolean
    groups: string[]
}

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(
        localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')!) : null
    )
    const token = ref<string | null>(localStorage.getItem('token'))
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const isAuthenticated = computed(() => !!token.value)

    const login = async (username: string, password: string): Promise<boolean> => {
        isLoading.value = true
        error.value = null
        try {
            const params = new URLSearchParams()
            params.append('username', username)
            params.append('password', password)

            const response = await api.post('/auth/login', params.toString(), {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            })

            const accessToken = response.data.access_token
            token.value = accessToken
            localStorage.setItem('token', accessToken)

            // Fetch actual full user profile after login
            await fetchUser()

            return true
        } catch (e: any) {
            console.error(e)
            error.value = e.response?.data?.detail || 'Login failed'
            return false
        } finally {
            isLoading.value = false
        }
    }

    const fetchUser = async () => {
        if (!token.value) return
        try {
            const response = await api.get('/users/me')
            user.value = response.data
            localStorage.setItem('user', JSON.stringify(user.value))
        } catch (e) {
            console.error('Failed to fetch user profile:', e)
            logout()
        }
    }

    const logout = () => {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
    }

    return {
        user,
        token,
        isLoading,
        error,
        isAuthenticated,
        login,
        logout,
        fetchUser
    }
})
