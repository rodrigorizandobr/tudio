<script setup lang="ts">
import { ref } from 'vue'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'

const props = defineProps<{
  open: boolean
  trackId: number | null
  trackTitle: string
}>()

const emit = defineEmits(['update:open', 'confirm'])

const loading = ref(false)

async function onConfirm() {
  if (!props.trackId) return
  
  loading.value = true
  try {
    emit('confirm', props.trackId)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppModal 
    :open="open" 
    title="Excluir Música" 
    description="Tem certeza que deseja remover esta música da sua biblioteca? Esta ação não pode ser desfeita."
    @update:open="$emit('update:open', $event)"
  >
    <div class="py-4">
      <p class="text-zinc-500">
        Você está prestes a excluir a faixa <span class="font-semibold text-zinc-900">"{{ trackTitle }}"</span>.
      </p>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3">
        <AppButton
          variant="ghost"
          @click="$emit('update:open', false)"
        >
          Cancelar
        </AppButton>
        <AppButton 
          variant="danger" 
          :loading="loading"
          @click="onConfirm"
        >
          Excluir Música
        </AppButton>
      </div>
    </template>
  </AppModal>
</template>
