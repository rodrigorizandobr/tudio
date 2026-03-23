<script setup lang="ts">
import { useVideoDownloadStore } from '../../stores/videoDownload'
import { X, Minimize2, Maximize2, AlertCircle, Download, CheckCircle2 } from 'lucide-vue-next'
import { ref } from 'vue'

const store = useVideoDownloadStore()
const isMinimized = ref(false)

const formatProgress = (val: number) => Math.round(val) + '%'

const toggleMinimize = () => {
  isMinimized.value = !isMinimized.value
}
</script>

<template>
  <div
    v-if="store.isVisible"
    class="pip-container"
    :class="{ minimized: isMinimized }"
  >
    <!-- Header -->
    <div class="pip-header">
      <div class="header-info">
        <component 
          :is="store.isCompleted ? CheckCircle2 : (store.isError ? AlertCircle : Download)" 
          class="status-icon"
          :class="store.status"
        />
        <span
          class="title"
          :title="store.videoMeta?.title"
        >
          {{ store.isDownloading ? 'Baixando...' : (store.isCompleted ? 'Concluído' : 'Erro') }}
        </span>
      </div>
      
      <div class="header-actions">
        <button
          class="action-btn"
          :title="isMinimized ? 'Expandir' : 'Minimizar'"
          @click="toggleMinimize"
        >
          <component
            :is="isMinimized ? Maximize2 : Minimize2"
            :size="14"
          />
        </button>
        <button
          class="action-btn close"
          title="Fechar"
          @click="store.closePip()"
        >
          <X :size="14" />
        </button>
      </div>
    </div>

    <!-- Body (Visible only if not minimized) -->
    <div
      v-show="!isMinimized"
      class="pip-body"
    >
      <!-- Downloading State -->
      <div
        v-if="store.isDownloading"
        class="download-state"
      >
        <div class="thumbnail-wrapper">
          <img
            v-if="store.videoMeta?.thumbnail"
            :src="store.videoMeta.thumbnail"
            alt="thumbnail"
          >
        </div>
        <div class="progress-section">
          <div class="progress-bar-bg">
            <div
              class="progress-fill"
              :style="{ width: store.progress + '%' }"
            />
          </div>
          <span class="progress-text">{{ formatProgress(store.progress) }}</span>
        </div>
        <p class="meta-title">
          {{ store.videoMeta?.title }}
        </p>
      </div>

      <!-- Verified/Completed State (Player) -->
      <div
        v-else-if="store.isCompleted && store.localUrl"
        class="player-state"
      >
        <video
          controls
          autoplay
          preload="none"
          :src="store.localUrl"
          class="video-player"
        />
      </div>

      <!-- Error State -->
      <div
        v-else-if="store.isError"
        class="error-state"
      >
        <p class="error-msg">
          {{ store.errorMessage }}
        </p>
        <button
          class="retry-btn"
          @click="store.reset()"
        >
          Fechar
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pip-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 320px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: slideIn 0.3s ease-out;
}

.pip-container.minimized {
  width: 200px;
}

@keyframes slideIn {
  from { transform: translateY(100px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* Header */
.pip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.status-icon {
  width: 16px;
  height: 16px;
}

.status-icon.downloading { color: var(--color-violet-500); animation: pulse 2s infinite; }
.status-icon.completed { color: #10b981; }
.status-icon.error { color: #ef4444; }

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.action-btn:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.action-btn.close:hover {
  background: #fef2f2;
  color: #ef4444;
}

/* Body */
.pip-body {
  background: var(--bg-card);
  padding: 0;
}

/* Download State */
.download-state {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thumbnail-wrapper {
  width: 100%;
  aspect-ratio: 16/9;
  background: black;
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-bottom: 4px;
}

.thumbnail-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.7;
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar-bg {
  flex: 1;
  height: 6px;
  background: var(--bg-subtle);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-base);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  width: 32px;
  text-align: right;
}

.meta-title {
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Player State */
.player-state {
  width: 100%;
  aspect-ratio: 16/9;
  background: black;
}

.video-player {
  width: 100%;
  height: 100%;
  outline: none;
}

/* Error State */
.error-state {
  padding: 16px;
  text-align: center;
}

.error-msg {
  font-size: 0.85rem;
  color: #ef4444;
  margin-bottom: 12px;
}

.retry-btn {
  font-size: 0.8rem;
  padding: 6px 12px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-primary);
}
</style>
