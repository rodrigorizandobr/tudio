import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AppButton from '../AppButton.vue'

describe('AppButton.vue', () => {
    it('renders the slot content', () => {
        const wrapper = mount(AppButton, {
            slots: {
                default: 'Click Me'
            }
        })
        expect(wrapper.text()).toContain('Click Me')
    })

    it('applies correct variant class', () => {
        const wrapper = mount(AppButton, {
            props: {
                variant: 'danger'
            }
        })
        const button = wrapper.find('.app-button')
        expect(button.classes()).toContain('variant-danger')
    })

    it('shows loader when loading prop is true', () => {
        const wrapper = mount(AppButton, {
            props: {
                loading: true
            }
        })
        expect(wrapper.find('.spinner').exists()).toBe(true)
        // Verify disabled attribute presence (empty string means present in boolean attrs)
        const button = wrapper.find('.app-button')
        expect(button.attributes('disabled')).toBeDefined()
    })
})
