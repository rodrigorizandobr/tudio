import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AppCard from '../AppCard.vue'

describe('AppCard.vue', () => {
    it('renders title from prop', () => {
        const wrapper = mount(AppCard, {
            props: {
                title: 'Card Title'
            }
        })
        expect(wrapper.find('.card-title').text()).toBe('Card Title')
    })

    it('renders default slot content', () => {
        const wrapper = mount(AppCard, {
            slots: {
                default: '<div class="content">Main Content</div>'
            }
        })
        expect(wrapper.find('.content').exists()).toBe(true)
        expect(wrapper.text()).toContain('Main Content')
    })

    it('renders header actions slot', () => {
        const wrapper = mount(AppCard, {
            slots: {
                'header-actions': '<button>Action</button>'
            }
        })
        expect(wrapper.find('.card-actions').exists()).toBe(true)
        expect(wrapper.find('button').text()).toBe('Action')
    })

    it('renders footer slot', () => {
        const wrapper = mount(AppCard, {
            slots: {
                footer: '<footer>Footer Content</footer>'
            }
        })
        expect(wrapper.find('.card-footer').exists()).toBe(true)
        expect(wrapper.text()).toContain('Footer Content')
    })
})
