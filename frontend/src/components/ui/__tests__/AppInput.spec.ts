import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AppInput from '../AppInput.vue'

describe('AppInput.vue', () => {
    it('renders label when provided', () => {
        const wrapper = mount(AppInput, {
            props: {
                id: 'test-input',
                modelValue: '',
                label: 'Test Label'
            }
        })
        expect(wrapper.find('label').text()).toBe('Test Label')
    })

    it('emits update:modelValue on input', async () => {
        const wrapper = mount(AppInput, {
            props: {
                id: 'test-input',
                modelValue: ''
            }
        })
        const input = wrapper.find('input')
        await input.setValue('new value')
        expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['new value'])
    })

    it('displays error message and applies error class', () => {
        const wrapper = mount(AppInput, {
            props: {
                id: 'test-input',
                modelValue: '',
                error: 'Invalid input'
            }
        })
        expect(wrapper.find('.error-text').text()).toBe('Invalid input')
        expect(wrapper.find('.app-input').classes()).toContain('has-error')
    })
})
