<script setup lang="ts">
import { computed } from 'vue'
import { Loader2 } from 'lucide-vue-next'

interface Props {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  block?: boolean
  loading?: boolean
  disabled?: boolean
  href?: string
  iconOnly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  block: false,
  loading: false,
  disabled: false,
  iconOnly: false,
})

const classes = computed(() => {
  return [
    'app-button',
    `variant-${props.variant}`,
    `size-${props.size}`,
    { 'w-full': props.block },
    { 'is-loading': props.loading },
    { 'icon-only': props.iconOnly },
  ]
})

const componentTag = computed(() => (props.href ? 'a' : 'button'))
</script>

<template>
  <!-- @vue-ignore -->
  <component
    :is="componentTag"
    v-bind="$attrs"
    :href="href"
    :class="classes"
    :disabled="disabled || loading"
  >
    <Loader2
      v-if="loading"
      class="spinner"
    />
    <span
      class="button-content"
      :class="{ 'opacity-0': loading }"
    >
      <slot />
    </span>
  </component>
</template>

<style scoped>
.app-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  user-select: none;
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
}

/* Sizes */
.size-sm {
  height: 32px;
  padding: 0 0.75rem;
  font-size: 0.75rem;
}
.size-md {
  height: 40px;
  padding: 0 1.25rem;
  font-size: 0.875rem;
}
.size-lg {
  height: 48px;
  padding: 0 1.75rem;
  font-size: 1rem;
}

/* Icon Only overrides */
.icon-only {
  padding: 0 !important;
  aspect-ratio: 1 / 1;
}
.icon-only.size-sm { width: 32px; }
.icon-only.size-md { width: 40px; }
.icon-only.size-lg { width: 48px; }

/* Variants */
.variant-primary {
  background: var(--primary-base);
  color: white;
  border-color: var(--primary-base);
  box-shadow: 0 1px 2px rgba(139, 92, 246, 0.2);
}
.variant-primary:hover:not(:disabled) {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}

.variant-secondary {
  background: var(--color-zinc-100);
  color: var(--color-zinc-900);
  border: 1px solid var(--border-subtle);
}
.variant-secondary:hover:not(:disabled) {
  background: var(--color-zinc-200);
  border-color: var(--border-active);
}

.variant-outline {
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
}
.variant-outline:hover:not(:disabled) {
  border-color: var(--primary-base);
  color: var(--primary-base);
  background: rgba(139, 92, 246, 0.05);
}

.variant-ghost {
  background: transparent;
  color: var(--text-secondary);
}
.variant-ghost:hover:not(:disabled) {
  background: rgba(0,0,0,0.05);
  color: var(--text-primary);
}

.variant-danger {
  background: #ef4444;
  color: white;
}
.variant-danger:hover:not(:disabled) {
  background: #dc2626;
}

/* Spinner */
.spinner {
  animation: spin 1s linear infinite;
  width: 1.25rem; /* ~20px fallback */
  height: 1.25rem;
}

.size-sm .spinner { width: 1rem; height: 1rem; }
.size-md .spinner { width: 1.25rem; height: 1.25rem; }
.size-lg .spinner { width: 1.5rem; height: 1.5rem; }

.app-button:not(.icon-only) .spinner {
  margin-right: 0.5rem;
}

.button-content {
  display: flex;
  align-items: center;
  gap: inherit;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
