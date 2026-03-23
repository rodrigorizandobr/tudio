<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'

interface Option {
  label: string
  value: string | number
}

interface Props {
  modelValue: string | number
  label?: string
  options: Option[]
  id: string
  error?: string
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
}>()

const handleChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
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
    
    <div class="select-wrapper">
      <select
        :id="id"
        :value="modelValue"
        class="app-select"
        @change="handleChange"
      >
        <option
          v-for="opt in options"
          :key="opt.value"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>
      <div class="select-icon">
        <ChevronDown :size="16" />
      </div>
    </div>

    <span
      v-if="error"
      class="error-text"
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

.select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.app-select {
  width: 100%;
  height: 40px;
  padding: 0 2.5rem 0 0.875rem;
  background: var(--bg-input, #ffffff);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.925rem;
  appearance: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.app-select:focus {
  outline: none;
  border-color: var(--primary-base);
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2);
}

.select-icon {
  position: absolute;
  right: 0.875rem;
  pointer-events: none;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-text {
  font-size: 0.75rem;
  color: #ef4444;
  margin-top: -0.25rem;
}
</style>
