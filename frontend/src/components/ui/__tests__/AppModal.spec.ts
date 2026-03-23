import { describe, it, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import AppModal from '../AppModal.vue'

const RadixStub = { template: '<div><slot /></div>' }
const DialogContentStub = {
    template: '<div class="dialog-content"><slot /></div>'
}
const DialogCloseStub = {
    template: '<button @click="$emit(\'click\')"><slot /></button>'
}

describe('AppModal.vue', () => {
    it('renders correctly when open', () => {
        const wrapper = mount(AppModal, {
            props: {
                open: true,
                title: 'Test Modal',
                description: 'Test Description'
            },
            global: {
                stubs: {
                    DialogRoot: RadixStub,
                    DialogPortal: RadixStub,
                    DialogOverlay: RadixStub,
                    DialogContent: DialogContentStub,
                    DialogTitle: RadixStub,
                    DialogDescription: RadixStub,
                    DialogClose: DialogCloseStub,
                    X: true
                }
            }
        })

        expect(wrapper.text()).toContain('Test Modal')
        expect(wrapper.text()).toContain('Test Description')
    })

    test.each([
        ['sm', 'sm:max-w-sm'],
        ['lg', 'max-w-6xl'],
        ['xl', 'max-w-7xl'],
        ['full', 'w-full h-full'],
        [undefined, 'max-w-5xl'] // default
    ])('computes max width class based on size prop %s', (size: string | undefined, expectedClass: string) => {
        const wrapper = mount(AppModal, {
            props: { open: true, size: size as any },
            global: {
                stubs: {
                    DialogRoot: RadixStub,
                    DialogPortal: RadixStub,
                    DialogOverlay: RadixStub,
                    DialogContent: DialogContentStub,
                    DialogTitle: RadixStub,
                    DialogDescription: RadixStub,
                    X: true
                }
            }
        })
        expect((wrapper.vm as any).maxWidthClass).toContain(expectedClass)
    })

    it('emits update:open false when close button clicked', async () => {
        const wrapper = mount(AppModal, {
            props: { open: true },
            global: {
                stubs: {
                    DialogRoot: RadixStub,
                    DialogPortal: RadixStub,
                    DialogOverlay: RadixStub,
                    DialogContent: DialogContentStub, // Uses <slot /> so original button is rendered
                    DialogTitle: RadixStub,
                    DialogDescription: RadixStub,
                    // DialogClose is not used in the template, removing stub to avoid confusion if it was
                    X: true
                }
            }
        })

        // The original button has aria-label="Close"
        const closeBtn = wrapper.find('button[aria-label="Close"]')
        expect(closeBtn.exists()).toBe(true)

        await closeBtn.trigger('click')
        expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
    })
})
