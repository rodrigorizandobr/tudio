<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useUIStore } from '../../stores/ui.store'
import api from '../../lib/axios'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import { Upload, Lock, Globe, EyeOff, AlertCircle, CheckSquare, Square, Monitor, Smartphone } from 'lucide-vue-next'

const props = defineProps<{
    modelValue: boolean
    video: any
}>()

const emit = defineEmits(['update:modelValue', 'published', 'uploadStarted'])

const ui = useUIStore()
const isLoading = ref(false)
const channels = ref<any[]>([])
const selectedChannelId = ref<number | null>(null)

// Multi-format selection
const availableFormats = computed(() => {
    if (!props.video?.outputs) return []
    return Object.keys(props.video.outputs).map(ratio => ({
        ratio,
        url: props.video.outputs[ratio],
        label: ratio === '16:9' ? 'Horizontal (16:9)' : 'Vertical (9:16)',
        icon: ratio === '16:9' ? Monitor : Smartphone,
        desc: ratio === '16:9' ? 'YouTube / Desktop' : 'YouTube Shorts / Reels'
    }))
})

const selectedFormats = ref<string[]>([])

const toggleFormat = (ratio: string) => {
    const idx = selectedFormats.value.indexOf(ratio)
    if (idx === -1) {
        selectedFormats.value.push(ratio)
    } else {
        selectedFormats.value.splice(idx, 1)
    }
}

// Form Data
const formData = ref({
    title: '',
    description: '',
    privacy: 'private',
    tags: ''
})

// Privacy Options
const privacyOptions = [
    { value: 'private', label: 'Privado', icon: Lock, desc: 'Apenas você pode ver' },
    { value: 'unlisted', label: 'Não Listado', icon: EyeOff, desc: 'Qualquer pessoa com o link' },
    { value: 'public', label: 'Público', icon: Globe, desc: 'Todos podem ver' },
]

// Initialize
watch(() => props.modelValue, async (isOpen) => {
    if (isOpen) {
        let desc = props.video.description || ''
        if (props.video.timestamps_index) {
            desc += `\n\n${props.video.timestamps_index}`
        }

        formData.value = {
            title: props.video.title?.slice(0, 100) || '',
            description: desc,
            privacy: 'private',
            tags: props.video.tags || ''
        }

        // Auto-select all available formats by default
        selectedFormats.value = availableFormats.value.map(f => f.ratio)

        await fetchChannels()
    }
})

const fetchChannels = async () => {
    try {
        isLoading.value = true
        const { data } = await api.get('/social/channels')
        channels.value = data
        if (channels.value.length > 0 && !selectedChannelId.value) {
            selectedChannelId.value = channels.value[0].id
        }
    } catch (error) {
        console.error('Failed to load channels', error)
        ui.showToast('Erro ao carregar canais do YouTube.', 'error')
    } finally {
        isLoading.value = false
    }
}

const handlePublish = async () => {
    if (!selectedChannelId.value) {
        ui.showToast('Selecione um canal para publicar.', 'error')
        return
    }
    if (selectedFormats.value.length === 0) {
        ui.showToast('Selecione pelo menos um formato para publicar.', 'error')
        return
    }

    try {
        isLoading.value = true

        const tagsList = formData.value.tags
            .split(',')
            .map(t => t.trim())
            .filter(t => t.length > 0)

        // Fire upload for each selected format sequentially (backend handles async)
        const uploads: Array<{ ratio: string; jobId?: string }> = []
        for (const ratio of selectedFormats.value) {
            const response = await api.post('/social/upload', {
                video_id: props.video.id,
                channel_id: selectedChannelId.value,
                title: formData.value.title,
                description: formData.value.description,
                privacy: formData.value.privacy,
                tags: tagsList,
                format: ratio
            })
            uploads.push({ ratio, jobId: response.data?.job_id })
        }

        // Close modal first
        emit('update:modelValue', false)
        emit('published')

        // Emit event with upload jobs info for floating progress tracker
        emit('uploadStarted', {
            videoTitle: formData.value.title || props.video.title,
            formats: selectedFormats.value,
            uploads,
            channelId: selectedChannelId.value
        })

    } catch (error: any) {
        console.error('Upload error', error)
        ui.showToast(error.response?.data?.detail || 'Erro ao publicar vídeo.', 'error')
    } finally {
        isLoading.value = false
    }
}
</script>

<template>
  <AppModal
    :open="modelValue"
    title="Publicar no YouTube"
    width="640px"
    @update:open="$emit('update:modelValue', $event)"
  >
    <div
      v-if="isLoading && channels.length === 0"
      class="py-12 text-center"
    >
      <div class="animate-spin w-10 h-10 border-4 border-primary-base border-t-transparent rounded-full mx-auto mb-4" />
      <p class="text-sm text-gray-500 font-medium">
        Carregando seus canais...
      </p>
    </div>

    <div
      v-else
      class="space-y-6"
    >
      <!-- Channel Selection -->
      <div class="space-y-3">
        <label class="text-sm font-semibold text-gray-800 dark:text-gray-200 flex items-center justify-between">
          Canal de Destino
          <span
            v-if="channels.length > 0"
            class="text-xs font-normal text-muted-foreground"
          >{{ channels.length }} canais encontrados</span>
        </label>

        <div
          v-if="channels.length === 0"
          class="p-4 bg-orange-500/10 border border-orange-500/20 rounded-xl flex items-start gap-3"
        >
          <AlertCircle
            class="text-orange-500 shrink-0 mt-0.5"
            :size="20"
          />
          <div>
            <p class="text-sm font-bold text-orange-700 dark:text-orange-400">
              Nenhum canal conectado
            </p>
            <p class="text-xs text-orange-600/80 dark:text-orange-400/80 mt-1 mb-2">
              Você precisa conectar uma conta do YouTube para publicar.
            </p>
            <router-link
              to="/panel/social"
              class="text-xs font-semibold text-primary-base hover:underline flex items-center gap-1"
            >
              Conectar conta agora <span aria-hidden="true">&rarr;</span>
            </router-link>
          </div>
        </div>

        <div
          v-else
          class="grid grid-cols-1 gap-2 max-h-[160px] overflow-y-auto pr-2 custom-scrollbar"
        >
          <button
            v-for="channel in channels"
            :key="channel.id"
            class="relative flex items-center gap-4 p-3 rounded-xl border-2 transition-all text-left group outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary-base"
            :class="selectedChannelId === channel.id
              ? 'bg-red-50 dark:bg-red-900/10 border-red-500 shadow-sm'
              : 'bg-white dark:bg-zinc-800 border-transparent hover:border-gray-200 dark:hover:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800/80'"
            @click="selectedChannelId = channel.id"
          >
            <div
              class="w-12 h-12 rounded-full overflow-hidden bg-gray-100 shrink-0 ring-2 ring-offset-2 ring-transparent transition-all"
              :class="{ 'ring-red-500': selectedChannelId === channel.id }"
            >
              <img
                :src="channel.thumbnail_url"
                class="w-full h-full object-cover"
              >
            </div>
            <div class="flex-1 min-w-0">
              <h4 class="font-bold truncate text-gray-900 dark:text-gray-100 text-sm mb-0.5">
                {{ channel.title }}
              </h4>
              <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <span class="flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-red-500" />
                  Youtube
                </span>
                <span>•</span>
                <span>{{ channel.subscriber_count }} inscritos</span>
              </div>
            </div>
            <div
              v-if="selectedChannelId === channel.id"
              class="absolute right-3 top-1/2 -translate-y-1/2"
            >
              <div class="w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center shadow-md animate-in zoom-in duration-200">
                <svg
                  class="w-3.5 h-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="3"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Format Selection (Multi-format) -->
      <div
        v-if="channels.length > 0 && availableFormats.length > 0"
        class="space-y-2.5"
      >
        <label class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center justify-between">
          Formatos para Publicar
          <span class="text-xs font-normal text-muted-foreground">{{ selectedFormats.length }} de {{ availableFormats.length }} selecionados</span>
        </label>
        <div :class="availableFormats.length === 1 ? 'grid-cols-1' : 'grid-cols-2'" class="grid gap-3">
          <button
            v-for="fmt in availableFormats"
            :key="fmt.ratio"
            class="relative flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left outline-none"
            :class="selectedFormats.includes(fmt.ratio)
              ? 'bg-violet-50 dark:bg-violet-900/10 border-violet-500 shadow-sm'
              : 'bg-white dark:bg-zinc-800 border-transparent hover:border-gray-200 dark:hover:border-zinc-700'"
            @click="toggleFormat(fmt.ratio)"
          >
            <component
              :is="fmt.icon"
              :size="22"
              :class="selectedFormats.includes(fmt.ratio) ? 'text-violet-500' : 'text-muted-foreground'"
            />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-bold" :class="selectedFormats.includes(fmt.ratio) ? 'text-violet-700 dark:text-violet-300' : 'text-foreground'">{{ fmt.label }}</p>
              <p class="text-[10px] text-muted-foreground mt-0.5">{{ fmt.desc }}</p>
            </div>
            <div class="shrink-0">
              <CheckSquare v-if="selectedFormats.includes(fmt.ratio)" :size="18" class="text-violet-500" />
              <Square v-else :size="18" class="text-muted-foreground/40" />
            </div>
          </button>
        </div>
      </div>

      <div
        v-if="channels.length > 0"
        class="animate-in fade-in slide-in-from-bottom-2 duration-300"
      >
        <!-- Metadata Form -->
        <div class="space-y-5 pt-5 border-t border-gray-100 dark:border-zinc-700">
          <div class="grid gap-5">
            <AppInput
              id="video-title"
              v-model="formData.title"
              label="Título do Vídeo"
              placeholder="Digite um título chamativo..."
              :maxlength="100"
            />

            <div class="space-y-1.5">
              <label class="text-sm font-semibold text-gray-700 dark:text-gray-300">Descrição</label>
              <textarea
                v-model="formData.description"
                rows="4"
                class="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                placeholder="Conte sobre o que é este vídeo..."
              />
              <p class="text-[10px] text-muted-foreground text-right">
                {{ formData.description.length }} caracteres
              </p>
            </div>

            <AppInput
              id="video-tags"
              v-model="formData.tags"
              label="Tags (separadas por vírgula)"
              placeholder="ex: motivação, oração, reflexão"
            />
          </div>

          <!-- Privacy -->
          <div class="space-y-2.5">
            <label class="text-sm font-semibold text-gray-700 dark:text-gray-300">Visibilidade</label>
            <div class="grid grid-cols-3 gap-3">
              <button
                v-for="opt in privacyOptions"
                :key="opt.value"
                class="relative flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all outline-none focus:ring-2 focus:ring-offset-1 focus:ring-primary-base"
                :class="formData.privacy === opt.value
                  ? 'bg-primary-base/5 border-primary-base text-primary-base shadow-sm'
                  : 'bg-white dark:bg-zinc-800 border-transparent hover:border-gray-200 dark:hover:border-zinc-700 text-muted-foreground hover:bg-gray-50 dark:hover:bg-zinc-700/50'"
                @click="formData.privacy = opt.value"
              >
                <component
                  :is="opt.icon"
                  :size="24"
                  :class="formData.privacy === opt.value ? 'text-primary-base' : 'text-muted-foreground/70'"
                />
                <span class="text-xs font-bold">{{ opt.label }}</span>
                <span
                  v-if="formData.privacy === opt.value"
                  class="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary-base"
                />
              </button>
            </div>
            <p class="text-xs text-muted-foreground text-center mt-1 flex items-center justify-center gap-1.5">
              <component
                :is="privacyOptions.find(o => o.value === formData.privacy)?.icon"
                :size="12"
              />
              {{ privacyOptions.find(o => o.value === formData.privacy)?.desc }}
            </p>
          </div>
        </div>
      </div>

      <!-- Actions (moved to #footer slot below) -->
    </div>

    <template #footer>
      <AppButton
        variant="ghost"
        @click="$emit('update:modelValue', false)"
      >
        Cancelar
      </AppButton>
      <AppButton
        variant="primary"
        :disabled="isLoading || channels.length === 0 || !selectedChannelId || selectedFormats.length === 0"
        :loading="isLoading"
        class="bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 border-none shadow-lg shadow-red-500/20 px-8"
        @click="handlePublish"
      >
        <template #icon>
          <Upload :size="18" />
        </template>
        {{ isLoading ? 'Iniciando...' : `Iniciar Upload${selectedFormats.length > 1 ? ` (${selectedFormats.length} formatos)` : ''}` }}
      </AppButton>
    </template>
  </AppModal>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
    width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgba(156, 163, 175, 0.3);
    border-radius: 20px;
}
</style>
