<script setup lang="ts">
/**
 * UploadProgressToast
 * Ultra-premium floating notification for YouTube upload progress.
 * Consumes the singleton state from useUploadToast composable.
 */
import { Youtube, CheckCircle2, XCircle, X, ChevronDown, ChevronUp, Loader2, Monitor, Smartphone } from 'lucide-vue-next'
import {
    uploadJobs,
    isToastMinimized,
    isToastVisible,
    allUploadsDone,
    hasUploadError,
    overallUploadProgress
} from '../../composables/useUploadToast'
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-from-class="translate-y-6 opacity-0 scale-95"
      enter-active-class="transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
      leave-to-class="translate-y-4 opacity-0 scale-95"
      leave-active-class="transition-all duration-300 ease-in"
    >
      <div
        v-if="isToastVisible"
        class="fixed bottom-6 right-6 z-[9999] w-[400px] max-w-[calc(100vw-2rem)]"
      >
        <!-- Glass Card -->
        <div class="relative rounded-2xl overflow-hidden shadow-[0_30px_80px_rgba(0,0,0,0.5)] border border-white/10">
          <!-- Backgrounds -->
          <div class="absolute inset-0 bg-gradient-to-br from-zinc-900 via-zinc-950 to-black" />
          <div class="absolute inset-0 bg-gradient-to-tr from-violet-900/15 via-transparent to-red-900/10" />

          <!-- Scanning top line (while uploading) -->
          <div
            v-if="!allUploadsDone"
            class="absolute top-0 left-0 right-0 h-[2px] overflow-hidden"
          >
            <div class="w-1/2 h-full bg-gradient-to-r from-transparent via-violet-400 to-transparent scanning-line" />
          </div>

          <!-- Content -->
          <div class="relative z-10">
            <!-- Header -->
            <div class="flex items-center gap-3 px-5 pt-4 pb-3">
              <div class="relative shrink-0">
                <div
                  class="w-10 h-10 rounded-xl flex items-center justify-center transition-colors duration-500"
                  :class="hasUploadError ? 'bg-red-500/20' : allUploadsDone ? 'bg-green-500/20' : 'bg-red-600/20'"
                >
                  <CheckCircle2 v-if="allUploadsDone && !hasUploadError" :size="22" class="text-green-400" />
                  <XCircle v-else-if="allUploadsDone && hasUploadError" :size="22" class="text-red-400" />
                  <Youtube v-else :size="22" class="text-red-500" />
                </div>
                <div
                  v-if="!allUploadsDone"
                  class="absolute -top-0.5 -right-0.5 w-3 h-3 bg-violet-500 rounded-full border-2 border-zinc-950 animate-pulse"
                />
              </div>

              <div class="flex-1 min-w-0">
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">
                  {{ allUploadsDone ? (hasUploadError ? 'Falha no upload' : 'Publicado com sucesso!') : 'Publicando no YouTube' }}
                </p>
                <p class="text-sm font-bold text-white truncate mt-0.5">
                  {{ uploadJobs.length > 1 ? `${uploadJobs.length} formatos` : (uploadJobs[0]?.label || 'Vídeo') }}
                </p>
              </div>

              <div class="flex items-center gap-1.5 shrink-0">
                <button
                  class="w-7 h-7 flex items-center justify-center rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-all"
                  :title="isToastMinimized ? 'Expandir' : 'Minimizar'"
                  @click="isToastMinimized = !isToastMinimized"
                >
                  <ChevronDown v-if="!isToastMinimized" :size="15" />
                  <ChevronUp v-else :size="15" />
                </button>
                <button
                  v-if="allUploadsDone"
                  class="w-7 h-7 flex items-center justify-center rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-all"
                  title="Fechar"
                  @click="uploadJobs = []"
                >
                  <X :size="15" />
                </button>
              </div>
            </div>

            <!-- Overall progress bar -->
            <div class="px-5 pb-3">
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-[9px] font-black uppercase tracking-[0.25em] text-zinc-500">Progresso total</span>
                <span class="text-[12px] font-mono font-black text-white">{{ overallUploadProgress }}%</span>
              </div>
              <div class="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-700 ease-out"
                  :class="hasUploadError
                    ? 'bg-red-500'
                    : allUploadsDone
                    ? 'bg-gradient-to-r from-green-500 to-emerald-400'
                    : 'bg-gradient-to-r from-violet-600 via-fuchsia-500 to-red-500'"
                  :style="{ width: `${overallUploadProgress}%` }"
                />
              </div>
            </div>

            <!-- Per-job details -->
            <Transition
              enter-from-class="opacity-0"
              enter-active-class="transition-opacity duration-300"
              leave-to-class="opacity-0"
              leave-active-class="transition-opacity duration-200"
            >
              <div
                v-if="!isToastMinimized"
                class="px-5 pb-5 pt-1 space-y-3 border-t border-white/5"
              >
                <div
                  v-for="job in uploadJobs"
                  :key="job.id"
                  class="flex items-center gap-3"
                >
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors"
                    :class="{
                      'bg-green-500/15': job.status === 'done',
                      'bg-red-500/15': job.status === 'error',
                      'bg-violet-500/10': job.status === 'uploading' || job.status === 'pending'
                    }"
                  >
                    <CheckCircle2 v-if="job.status === 'done'" :size="16" class="text-green-400" />
                    <XCircle v-else-if="job.status === 'error'" :size="16" class="text-red-400" />
                    <Loader2 v-else :size="16" class="text-violet-400 animate-spin" />
                  </div>

                  <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between mb-1.5">
                      <span class="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
                        <Monitor v-if="job.format === '16:9'" :size="11" class="text-zinc-400" />
                        <Smartphone v-else :size="11" class="text-zinc-400" />
                        {{ job.label }}
                      </span>
                      <span
                        class="text-[10px] font-mono tabular-nums"
                        :class="{
                          'text-green-400': job.status === 'done',
                          'text-red-400': job.status === 'error',
                          'text-zinc-400': job.status !== 'done' && job.status !== 'error'
                        }"
                      >
                        {{ job.status === 'done' ? '✓ Publicado' : job.status === 'error' ? '✗ Erro' : job.status === 'pending' ? 'Aguardando...' : `${Math.round(job.progress)}%` }}
                      </span>
                    </div>
                    <div class="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all duration-600 ease-out"
                        :class="{
                          'bg-green-500': job.status === 'done',
                          'bg-red-500': job.status === 'error',
                          'bg-gradient-to-r from-violet-500 to-fuchsia-500': job.status === 'uploading',
                          'bg-zinc-600': job.status === 'pending'
                        }"
                        :style="{ width: job.status === 'done' ? '100%' : `${job.progress}%` }"
                      />
                    </div>
                    <p
                      v-if="job.error"
                      class="text-[10px] text-red-400 mt-1 truncate"
                    >
                      {{ job.error }}
                    </p>
                    <p
                      v-if="job.youtubeVideoId && job.status === 'done'"
                      class="text-[10px] text-green-400/80 mt-1"
                    >
                      ID: {{ job.youtubeVideoId }}
                    </p>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.scanning-line {
  animation: scan 2s ease-in-out infinite;
}
@keyframes scan {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(300%); }
}
</style>
