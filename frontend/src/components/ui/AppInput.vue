<script setup lang="ts">


interface Props {
  modelValue: string | number
  label?: string
  type?: string
  placeholder?: string
  error?: string
  id: string
}

withDefaults(defineProps<Props>(), {
  type: 'text',
  placeholder: '',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
}>()

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
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
      <input
        :id="id"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :class="['app-input', { 'has-error': error }]"
        v-bind="$attrs"
        @input="handleInput"
      >
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
  color: var(--text-secondary); /* Darker zinc from theme.css */
}

.input-wrapper {
  position: relative;
}

.app-input {
  width: 100%;
  height: 40px;
  padding: 0 0.875rem;
  background: var(--bg-input, #ffffff);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.925rem;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.app-input:focus {
  outline: none;
  border-color: var(--color-violet-500);
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2);
}

.app-input::placeholder {
  color: var(--color-zinc-600);
}

.app-input.has-error {
  border-color: #ef4444;
}

.app-input.has-error:focus {
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.error-text {
  font-size: 0.75rem;
  color: #ef4444;
  margin-top: -0.25rem;
}
</style>
