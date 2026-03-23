import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import * as parserVue from 'vue-eslint-parser'
import tseslint from 'typescript-eslint'
import globals from 'globals'

export default [
    js.configs.recommended,
    ...pluginVue.configs['flat/recommended'],
    ...tseslint.configs.recommended,
    {
        files: ['**/*.{js,mjs,cjs,ts,vue}'],
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node,
                Audio: 'readonly',
                HTMLAudioElement: 'readonly',
            },
            parser: parserVue,
            parserOptions: {
                parser: tseslint.parser,
                sourceType: 'module',
                ecmaVersion: 'latest',
            },
        },
        rules: {
            'vue/multi-word-component-names': 'off',
            '@typescript-eslint/no-explicit-any': 'warn',
            '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
        },
    },
    {
        ignores: ['dist/', 'node_modules/', '*.config.ts', '.vite/'],
    },
]
