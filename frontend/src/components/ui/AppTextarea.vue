<script setup lang="ts">

interface Props {
  modelValue: string | number
  label?: string
  placeholder?: string
  error?: string
  id: string
  rows?: number
}

withDefaults(defineProps<Props>(), {
  placeholder: '',
  rows: 4
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
}>()

const handleInput = (event: Event) => {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <div class="app-input-group">
    <label
      v-if="label"
      :for="id"
      class="app-label"
    >
      {{ label }}
    </label>
    
    <div class="input-wrapper">
      <textarea
        :id="id"
        :value="modelValue"
        :placeholder="placeholder"
        :rows="rows"
        :class="['app-textarea', { 'has-error': error }]"
        v-bind="$attrs"
        @input="handleInput"
      />
    </div>

    <span
      v-if="error"
      class="error-text animate-slide-up"
    >{{ error }}</span>
  </div>
</template>

<style scoped>
.app-input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.app-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.input-wrapper {
  position: relative;
}

.app-textarea {
  width: 100%;
  padding: 0.75rem 0.875rem;
  background: var(--bg-input, #ffffff);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.925rem;
  line-height: 1.5;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: inherit;
  resize: vertical;
}

.app-textarea:focus {
  outline: none;
  border-color: var(--primary-base);
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2);
}

.app-textarea::placeholder {
  color: var(--text-muted);
}

.app-textarea.has-error {
  border-color: #ef4444;
}

.app-textarea.has-error:focus {
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.error-text {
  font-size: 0.75rem;
  color: #ef4444;
  margin-top: -0.25rem;
}
</style>
