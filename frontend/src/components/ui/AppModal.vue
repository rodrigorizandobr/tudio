<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'radix-vue'
import { X } from 'lucide-vue-next'
import { computed } from 'vue'
import AppButton from './AppButton.vue'

const props = withDefaults(defineProps<{
  title?: string
  description?: string
  open?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
}>(), {
  size: 'md'
})

const emit = defineEmits(['update:open'])

const maxWidthClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'w-[90%] sm:max-w-sm' // Small (Confirmations)
    case 'lg': return 'w-[90%] md:w-[85%] max-w-6xl' // Large
    case 'xl': return 'w-[95%] max-w-7xl' // Extra Large
    case 'full': return 'w-full h-full max-w-none' // Full Screen
    default: return 'w-[90%] md:w-[75%] max-w-5xl' // Default (Standard: 75% Desktop, 90% Mobile)
  }
})
</script>

<template>
  <DialogRoot
    :open="open"
    @update:open="emit('update:open', $event)"
  >
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <DialogContent 
        :class="[
          'fixed left-[50%] top-[50%] z-[101] flex flex-col translate-x-[-50%] translate-y-[-50%] gap-0 border bg-background p-0 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg',
          'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900', // Theme colors
          'max-h-[90vh]', // Prevent modal from overflowing viewport height
          maxWidthClass
        ]"
      >
        <div class="flex items-start justify-between border-b border-zinc-100 dark:border-zinc-800/50 p-6">
          <div class="flex-1 mr-4">
            <DialogTitle class="text-lg font-semibold leading-none tracking-tight text-foreground">
              {{ title }}
            </DialogTitle>
            <DialogDescription
              v-if="description"
              class="mt-2 text-sm text-muted-foreground"
            >
              {{ description }}
            </DialogDescription>
          </div>
          <AppButton 
            variant="ghost" 
            icon-only
            size="sm"
            aria-label="Close"
            class="text-zinc-400 hover:text-zinc-900"
            @click="emit('update:open', false)"
          >
            <X :size="20" />
          </AppButton>
        </div>
        
        <div class="flex-1 overflow-y-auto p-6">
          <slot />
        </div>

        <div
          v-if="$slots.footer"
          class="flex items-center justify-end gap-3 border-t border-zinc-100 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-900/50 p-4 sm:p-6"
        >
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
