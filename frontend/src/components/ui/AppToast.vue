
<script setup lang="ts">
import { CheckCircle, AlertCircle, X, Info } from 'lucide-vue-next'
import { onMounted } from 'vue'

const props = defineProps<{
  message: string
  type?: 'success' | 'error' | 'info' | 'warning'
  duration?: number
  visible: boolean
}>()

const emit = defineEmits(['close'])

onMounted(() => {
  if (props.duration && props.duration > 0) {
    setTimeout(() => {
      emit('close')
    }, props.duration)
  }
})
</script>

<template>
  <Transition name="toast-fade">
    <div
      v-if="visible"
      class="app-toast"
      :class="type || 'info'"
    >
      <div class="icon-wrapper">
        <CheckCircle
          v-if="type === 'success'"
          :size="20"
        />
        <AlertCircle
          v-else-if="type === 'error'"
          :size="20"
        />
        <Info
          v-else
          :size="20"
        />
      </div>
      <div class="content">
        <p>{{ message }}</p>
      </div>
      <button
        class="close-btn"
        @click="$emit('close')"
      >
        <X :size="16" />
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.app-toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  max-width: 400px;
  color: var(--text-primary);
}

.app-toast.success {
  border-left: 4px solid var(--color-success);
}

.app-toast.error {
  border-left: 4px solid var(--color-error);
}

.app-toast.info {
  border-left: 4px solid var(--color-info);
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.success .icon-wrapper { color: var(--color-success); }
.error .icon-wrapper { color: var(--color-error); }
.info .icon-wrapper { color: var(--color-info); }

.content {
  flex: 1;
  font-size: 0.875rem;
}

.close-btn {
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color 0.2s;
}

.close-btn:hover {
  color: var(--text-primary);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(1rem);
}
</style>
