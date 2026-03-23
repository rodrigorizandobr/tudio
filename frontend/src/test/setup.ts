import { vi } from 'vitest'

// Silence console logs during tests to keep output clean
if (typeof window !== 'undefined') {
    vi.spyOn(console, 'error').mockImplementation(() => { })
    vi.spyOn(console, 'warn').mockImplementation(() => { })
    vi.spyOn(console, 'log').mockImplementation(() => { })
}
