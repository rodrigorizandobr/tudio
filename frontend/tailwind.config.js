/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                primary: {
                    base: 'var(--primary-base)',
                    hover: 'var(--primary-hover)',
                    active: 'var(--primary-hover)',
                    text: 'var(--primary-text)',
                },
                border: {
                    subtle: 'var(--border-subtle)',
                    active: 'var(--border-active)',
                    focus: 'var(--border-focus)',
                },
                bg: {
                    card: 'var(--bg-card)',
                    subtle: 'var(--bg-app)',
                    input: 'var(--bg-input)',
                },
                // Map Zinc to Theme Variables for consistency
                zinc: {
                    50: 'var(--color-zinc-50)',
                    100: 'var(--color-zinc-100)',
                    200: 'var(--color-zinc-200)',
                    300: 'var(--color-zinc-300)',
                    400: 'var(--color-zinc-400)',
                    500: 'var(--color-zinc-500)',
                    600: 'var(--color-zinc-600)',
                    700: 'var(--color-zinc-700)',
                    800: 'var(--color-zinc-800)',
                    900: 'var(--color-zinc-900)',
                    950: 'var(--color-zinc-950)',
                },
                // Map Violet to Theme Variables (since theme uses Violet as primary base often)
                violet: {
                    50: 'var(--color-violet-50)',
                    100: 'var(--color-violet-100)',
                    200: 'var(--color-violet-200)',
                    300: 'var(--color-violet-300)',
                    400: 'var(--color-violet-400)',
                    500: 'var(--color-violet-500)',
                    600: 'var(--color-violet-600)',
                    700: 'var(--color-violet-700)',
                    800: 'var(--color-violet-800)',
                    900: 'var(--color-violet-900)',
                    950: 'var(--color-violet-950)',
                }
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            }
        },
    },
    plugins: [],
}
