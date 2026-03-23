<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  loading: boolean
  progress?: number
}>()

const width = computed(() => {
  if (props.progress !== undefined) return `${props.progress}%`
  return props.loading ? '30%' : '0%'
})
</script>

<template>
  <div class="progress-bar-container" :class="{ active: loading }">
    <div 
      class="progress-bar-fill"
      :style="{ width: width }"
      :class="{ indeterminate: loading && progress === undefined }"
    ></div>
  </div>
</template>

<style scoped>
.progress-bar-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: transparent;
  z-index: 9999;
  pointer-events: none;
  overflow: hidden;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.progress-bar-container.active {
  opacity: 1;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6, #d946ef, #8b5cf6);
  background-size: 200% 100%;
  transition: width 0.4s ease;
}

.indeterminate {
  animation: progress-indeterminate 1.5s infinite linear, gradient-slide 2s infinite linear;
}

@keyframes progress-indeterminate {
  0% { transform: translateX(-100%) scaleX(0.2); }
  50% { transform: translateX(0%) scaleX(0.5); }
  100% { transform: translateX(100%) scaleX(0.2); }
}

@keyframes gradient-slide {
  0% { background-position: 0% 50%; }
  100% { background-position: 100% 50%; }
}
</style>
