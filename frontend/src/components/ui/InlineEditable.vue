<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { Loader2, Pencil } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: string
  multiline?: boolean
  placeholder?: string
  label?: string
  saving?: boolean
  disabled?: boolean
  validation?: (value: string) => boolean | string
}>()

const emit = defineEmits(['update:modelValue', 'save', 'cancel'])

const isEditing = ref(false)
const editValue = ref('')
const inputRef = ref<HTMLInputElement | HTMLTextAreaElement | null>(null)
const error = ref<string | null>(null)

// Sync with prop when not editing
watch(() => props.modelValue, (newVal) => {
  if (!isEditing.value) {
    editValue.value = newVal
  }
}, { immediate: true })

const startEditing = async () => {
  if (props.disabled || props.saving) return
  
  editValue.value = props.modelValue
  isEditing.value = true
  error.value = null
  
  await nextTick()
  inputRef.value?.focus()
}

const cancelEditing = () => {
  isEditing.value = false
  editValue.value = props.modelValue
  error.value = null
  emit('cancel')
}

const save = () => {
  error.value = null
  
  if (props.validation) {
    const result = props.validation(editValue.value)
    if (result !== true) {
      error.value = typeof result === 'string' ? result : 'Inválido'
      return
    }
  }

  // Always emit save if value changed, or if we want to force consistency
  if (editValue.value !== props.modelValue) {
    emit('update:modelValue', editValue.value)
    emit('save', editValue.value)
  }
  isEditing.value = false
}

const handleBlur = () => {
    // Small timeout to allow click events on buttons (like cancel) to fire first
    setTimeout(() => {
        if (isEditing.value) save()
    }, 150)
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
      e.stopPropagation()
      cancelEditing()
      return
  }
  
  if (e.key === 'Enter' && !e.shiftKey && !props.multiline) {
      e.preventDefault()
      save()
  }
}
</script>

<template>
  <div
    class="inline-editable group/editable"
    :class="{ 'is-editing': isEditing, 'is-saving': saving, 'is-disabled': disabled }"
  >
    <!-- DISPLAY MODE -->
    <div 
      v-if="!isEditing"
      class="display-value relative cursor-text rounded transition-colors hover:bg-black/5 dark:hover:bg-white/5 p-1 -m-1"
      tabindex="0"
      @click="startEditing"
      @keydown.enter="startEditing"
    >
      <div
        v-if="modelValue"
        class="content-wrapper"
      >
        <span class="text-content whitespace-pre-wrap break-words w-full block">{{ modelValue }}</span>
        <div
          v-if="!disabled && !saving"
          class="edit-hint absolute top-0 right-0 p-1 opacity-0 group-hover/editable:opacity-100 transition-opacity text-primary"
        >
          <Pencil :size="12" />
        </div>
      </div>
      <span
        v-else
        class="placeholder-text italic text-muted-foreground/60 flex items-center gap-1 select-none"
      >
        {{ placeholder || 'Clique para editar...' }}
        <Pencil
          :size="12"
          class="opacity-0 group-hover/editable:opacity-100 transition-opacity"
        />
      </span>
        
      <div
        v-if="saving"
        class="saving-indicator absolute right-0 top-1/2 -translate-y-1/2 flex items-center gap-1 text-xs text-primary bg-background/80 px-2 rounded-full shadow-sm border border-primary/20"
      >
        <Loader2
          :size="12"
          class="animate-spin"
        />
        <span>Salvando...</span>
      </div>
    </div>

    <!-- EDIT MODE -->
    <div
      v-else
      class="edit-input-wrapper relative"
    >
      <textarea
        v-if="multiline"
        ref="inputRef"
        v-model="editValue"
        class="editable-input flex w-full rounded-md border border-primary bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 min-h-[80px]"
        :placeholder="placeholder"
        rows="3"
        @blur="handleBlur"
        @keydown="handleKeydown"
      />
      <input
        v-else
        ref="inputRef"
        v-model="editValue"
        type="text"
        class="editable-input flex h-10 w-full rounded-md border border-primary bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        :placeholder="placeholder"
        @blur="handleBlur"
        @keydown="handleKeydown"
      >
        
      <div
        v-if="error"
        class="error-msg text-[10px] text-red-500 mt-1 absolute -bottom-5 left-0 font-bold bg-white dark:bg-zinc-900 px-1 rounded shadow-sm border border-red-200"
      >
        {{ error }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.inline-editable {
    width: 100%;
}
</style>
