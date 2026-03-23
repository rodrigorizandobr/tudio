<script setup lang="ts">
import { useUIStore } from '../../stores/ui.store'

const uiStore = useUIStore()
</script>

<template>
  <div
    v-if="uiStore.isGlobalLoading"
    class="loading-bar-container"
  >
    <div class="loading-bar-progress" />
  </div>
</template>

<style scoped>
.loading-bar-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  z-index: 9999;
  background: transparent;
  pointer-events: none;
}

.loading-bar-progress {
  height: 100%;
  background: linear-gradient(90deg, var(--color-violet-500), var(--color-indigo-500));
  width: 0;
  animation: loading-progress 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  box-shadow: 0 0 10px rgba(124, 58, 237, 0.5);
}

@keyframes loading-progress {
  0% {
    width: 0;
    margin-left: 0;
  }
  50% {
    width: 70%;
    margin-left: 0;
  }
  100% {
    width: 0;
    margin-left: 100%;
  }
}
</style>
