<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'
import { Check, X } from 'lucide-vue-next'
import api from '../../lib/axios'

interface Props {
  open: boolean
  imageUrl: string
  videoId?: number
  sceneId?: string
}

interface Emits {
  (e: 'update:open', value: boolean): void
  (e: 'cropSaved', croppedUrl: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const cropper = ref<InstanceType<typeof Cropper>>()
const selectedRatio = ref<'16:9' | '9:16'>('16:9')
const isSaving = ref(false)
const showError = ref(false)
const errorMsg = ref('')

// Aspect ratio configuration
const aspectRatios = {
  '16:9': 16 / 9,
  '9:16': 9 / 16
}

const currentAspectRatio = computed(() => aspectRatios[selectedRatio.value])

// Watch for ratio changes
watch(selectedRatio, () => {
  if (cropper.value) {
    cropper.value.refresh()
  }
})

// Sanity check for empty/invalid image URL
watch(() => props.imageUrl, (newUrl) => {
  if (props.open && newUrl) {
      if (newUrl.endsWith('/') || newUrl.includes('/api/storage//') || newUrl === '/api/storage/' || newUrl.includes('/null') || newUrl.includes('/undefined')) {
          errorMsg.value = 'Erro: A imagem não foi carregada corretamente pelo servidor (URL inválida).'
          showError.value = true
      }
  }
}, { immediate: true })

const stencilProps = computed(() => ({
  aspectRatio: currentAspectRatio.value
}))

const handleCrop = async () => {
  if (!cropper.value || !props.videoId || !props.sceneId) return
  
  isSaving.value = true
  
  try {
    const { coordinates } = cropper.value.getResult()
    
    if (!coordinates) {
      errorMsg.value = 'Selecione uma área para cortar'
      showError.value = true
      isSaving.value = false
      return
    }

    // Validate dimensions > 0
    if (Math.round(coordinates.width) <= 0 || Math.round(coordinates.height) <= 0) {
      errorMsg.value = 'A área selecionada é inválida (largura ou altura igual a 0). Por favor, ajuste a seleção.'
      showError.value = true
      isSaving.value = false
      return
    }
    
    // Call backend crop endpoint
    const response = await api.post('/images/crop', {
      video_id: props.videoId,
      scene_id: props.sceneId,
      x: Math.round(coordinates.left),
      y: Math.round(coordinates.top),
      width: Math.round(coordinates.width),
      height: Math.round(coordinates.height),
      aspect_ratio: selectedRatio.value
    })
    
    // Emit success
    emit('cropSaved', response.data.cropped_image_url)
    emit('update:open', false)
    

  } catch (error: any) {
    console.error('Crop failed:', error)
    
    let msg = error.message
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail
      if (typeof detail === 'string') {
        msg = detail
      } else if (Array.isArray(detail)) {
        // Handle Pydantic validation errors or other interactions
        // Filter out any unparsable items first
        msg = detail.map((e: any) => {
             if (e && typeof e === 'object' && e.msg) return e.msg;
             if (typeof e === 'string') return e;
             return JSON.stringify(e);
        }).join(', ')
      } else if (typeof detail === 'object') {
        msg = JSON.stringify(detail)
      }
    }
    
    errorMsg.value = `Erro ao cortar imagem: ${msg}`
    showError.value = true
  } finally {
    isSaving.value = false
  }
}

const handleClose = () => {
  emit('update:open', false)
}
</script>

<template>
  <AppModal
    :open="open"
    title="Editar Crop da Imagem"
    size="lg"
    @update:open="handleClose"
  >
    <div class="crop-editor">
      <!-- Aspect Ratio Selector -->
      <div class="ratio-selector">
        <button
          :class="['ratio-btn', { active: selectedRatio === '16:9' }]"
          @click="selectedRatio = '16:9'"
        >
          16:9 (Landscape)
        </button>
        <button
          :class="['ratio-btn', { active: selectedRatio === '9:16' }]"
          @click="selectedRatio = '9:16'"
        >
          9:16 (Portrait)
        </button>
      </div>

      <!-- Cropper -->
      <div class="cropper-container">
        <Cropper
          ref="cropper"
          :src="imageUrl"
          :stencil-props="stencilProps"
          class="cropper"
        />
      </div>

      <!-- Actions -->
      <div class="crop-actions">
        <AppButton
          variant="ghost"
          title="Cancelar"
          @click="handleClose"
        >
          <X :size="16" />
        </AppButton>
        <AppButton
          variant="primary"
          :loading="isSaving"
          title="Salvar Crop"
          @click="handleCrop"
        >
          <Check :size="16" />
        </AppButton>
      </div>
    </div>
  </AppModal>

  <!-- Error Modal -->
  <AppModal
    v-model:open="showError"
    title="Erro"
    description=""
  >
    <div class="error-content">
      <p>{{ errorMsg }}</p>
      <div
        class="modal-actions"
        style="margin-top: 1.5rem; display: flex; justify-content: flex-end;"
      >
        <AppButton
          variant="primary"
          @click="showError = false"
        >
          Entendi
        </AppButton>
      </div>
    </div>
  </AppModal>
</template>

<style scoped>
.crop-editor {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-height: 500px;
}

.ratio-selector {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.ratio-btn {
  padding: 0.5rem 1.5rem;
  background: var(--bg-card);
  border: 2px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
  font-weight: 500;
}

.ratio-btn:hover {
  border-color: var(--primary-base);
  color: var(--text-primary);
}

.ratio-btn.active {
  background: var(--primary-base);
  border-color: var(--primary-base);
  color: white;
}

.cropper-container {
  flex: 1;
  min-height: 400px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-app);
}

.cropper {
  max-height: 500px;
}

.crop-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-subtle);
}
</style>
