<script setup lang="ts">
import { ref } from 'vue'
import AppModal from '../ui/AppModal.vue'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'

defineProps<{
  open: boolean
}>()

const emit = defineEmits(['update:open', 'success'])

const loading = ref(false)
const form = ref({
  title: '',
  artist: '',
  genre: '',
  mood: ''
})

const file = ref<File | null>(null)

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    file.value = target.files[0] || null
  }
}

async function onSubmit() {
  if (!file.value) {
    alert('Selecione um arquivo MP3.') 
    return
  }

  // Double check strict type safety
  const currentFile = file.value
  if (!currentFile) return

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('title', form.value.title)
    formData.append('artist', form.value.artist)
    formData.append('genre', form.value.genre)
    formData.append('mood', form.value.mood)
    formData.append('file', currentFile)

    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/music/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to upload music')
    }

    emit('success')
    emit('update:open', false)
    
    // Reset form
    form.value = { title: '', artist: '', genre: '', mood: '' }
    file.value = null
    // Reset input manually? difficult with declarative, but next open will be fine.

  } catch (error: any) {
    alert(error.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppModal 
    :open="open" 
    title="Adicionar Música" 
    description="Envie um arquivo MP3 para a biblioteca."
    @update:open="$emit('update:open', $event)"
  >
    <div class="space-y-4 py-4">
      <AppInput 
        id="title"
        v-model="form.title" 
        label="Título" 
        placeholder="Ex: Epic Battle" 
      />
      <AppInput 
        id="artist"
        v-model="form.artist" 
        label="Artista" 
        placeholder="Ex: Hans Zimmer" 
      />
      <AppInput 
        id="genre"
        v-model="form.genre" 
        label="Gênero" 
        placeholder="Ex: Cinematic" 
      />
      <AppInput 
        id="mood"
        v-model="form.mood" 
        label="Clima" 
        placeholder="Ex: Dramatic" 
      />
      
      <div class="space-y-2">
        <label class="text-sm font-medium">Arquivo MP3</label>
        <input
          type="file"
          accept=".mp3"
          class="block w-full text-sm text-zinc-500
          file:mr-4 file:py-2 file:px-4
          file:rounded-full file:border-0
          file:text-sm file:font-semibold
          file:bg-indigo-50 file:text-indigo-700
          hover:file:bg-indigo-100
        "
          @change="onFileChange"
        >
      </div>
    </div>

    <template #footer>
      <AppButton
        variant="secondary"
        :disabled="loading"
        @click="$emit('update:open', false)"
      >
        Cancelar
      </AppButton>
      <AppButton
        :loading="loading"
        @click="onSubmit"
      >
        Salvar Música
      </AppButton>
    </template>
  </AppModal>
</template>
