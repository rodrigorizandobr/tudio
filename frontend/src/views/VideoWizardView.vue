<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useVideoStore } from '../stores/video.store'
import AppLayout from '../components/layout/AppLayout.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppInput from '../components/ui/AppInput.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppTextarea from '../components/ui/AppTextarea.vue'
import AppSelect from '../components/ui/AppSelect.vue'
import { agentService, type Agent } from '../services/agent.service'
import { ArrowLeft, Wand2, FileText, Sparkles, Image as ImageIcon, Mic2, Globe, Clock, Layout, Music } from 'lucide-vue-next'

const router = useRouter()
const videoStore = useVideoStore()

const isScriptMode = ref(false)

const languageOptions = [
  { label: 'Português (BR)', value: 'pt-br' },
  { label: 'Inglês (US)', value: 'en-us' },
  { label: 'Espanhol', value: 'es' }
]

const imageSourceOptions = [
  { label: 'Manual (Escolher depois)', value: 'none', icon: Layout },
  { label: 'Unsplash (Artístico)', value: 'unsplash', icon: ImageIcon },
  { label: 'Google Images', value: 'google', icon: Globe },
  { label: 'Bing Images', value: 'bing', icon: Globe }
]

const form = ref({
  prompt: '',
  script_content: '',
  language: 'pt-br',
  agent_id: '',
  target_duration_minutes: 5,
  auto_image_source: 'none',
  auto_generate_narration: false,
  audio_transition_padding: 0.5,
  aspect_ratios: ['16:9'] as string[]
})

const agents = ref<Agent[]>([])
const loadingAgents = ref(false)

const fetchAgents = async () => {
  loadingAgents.value = true
  try {
    agents.value = await agentService.list()
    // Pre-select default agent
    const defaultAgent = agents.value.find(a => a.is_default)
    if (defaultAgent && !form.value.agent_id) {
      form.value.agent_id = defaultAgent.id || ''
    }
  } catch (e) {
    console.error("Failed to load agents", e)
  } finally {
    loadingAgents.value = false
  }
}

const agentOptions = computed(() => {
  return agents.value.map(a => ({
    label: a.name,
    value: a.id || ''
  }))
})

onMounted(() => {
  fetchAgents()
})

const toggleRatio = (ratio: string) => {
  const index = form.value.aspect_ratios.indexOf(ratio)
  if (index === -1) {
    form.value.aspect_ratios.push(ratio)
  } else {
    // Ensure at least one is selected
    if (form.value.aspect_ratios.length > 1) {
      form.value.aspect_ratios.splice(index, 1)
    }
  }
}

const goBack = () => router.back()

const handleSubmit = async () => {
  if (!form.value.prompt) return
  if (isScriptMode.value && !form.value.script_content) return
  if (form.value.aspect_ratios.length === 0) return

  const payload = {
    prompt: form.value.prompt,
    language: form.value.language,
    agent_id: form.value.agent_id || undefined,
    target_duration_minutes: Number(form.value.target_duration_minutes),
    auto_image_source: form.value.auto_image_source,
    auto_generate_narration: form.value.auto_generate_narration,
    audio_transition_padding: form.value.audio_transition_padding,
    aspect_ratios: form.value.aspect_ratios,
    script_content: isScriptMode.value ? form.value.script_content : undefined
  }

  const id = await videoStore.createVideo(payload)

  if (id) {
    router.push(`/panel/videos/${id}`)
  }
}
</script>

<template>
  <AppLayout>
    <div class="wizard-container animate-fade-in">
      <div class="wizard-header">
        <AppButton
          variant="ghost"
          size="sm"
          class="back-btn"
          @click="goBack"
        >
          <ArrowLeft :size="16" />
        </AppButton>
        <div class="header-text">
          <h1>Criar Novo Vídeo</h1>
          <p>Transforme suas ideias em conteúdo visual de alta qualidade com IA.</p>
        </div>
      </div>

      <div class="wizard-grid">
        <!-- Main Form Column -->
        <div class="main-column">
          <AppCard class="content-card">
            <div class="mode-toggle-container">
              <div class="mode-toggle-wrapper">
                <button 
                  type="button"
                  class="mode-toggle-btn"
                  :class="{ 'active': !isScriptMode }"
                  @click="isScriptMode = false"
                >
                  <Sparkles :size="16" />
                  Tenho uma Ideia
                </button>
                <button 
                  type="button"
                  class="mode-toggle-btn"
                  :class="{ 'active': isScriptMode }"
                  @click="isScriptMode = true"
                >
                  <FileText :size="16" />
                  Tenho um Roteiro
                </button>
              </div>
            </div>

            <form
              class="wizard-form"
              @submit.prevent="handleSubmit"
            >
              <div
                v-if="!isScriptMode"
                class="form-section animate-slide-up"
              >
                <AppTextarea
                  id="prompt"
                  v-model="form.prompt"
                  label="Sobre o que é o seu vídeo?"
                  placeholder="ex: Um documentário emocionante sobre a história do café, desde as plantações na Etiópia até as cafeterias modernas..."
                  required
                  autofocus
                  :rows="6"
                />
              </div>

              <div
                v-else
                class="form-section animate-slide-up"
              >
                <AppInput
                  id="topic"
                  v-model="form.prompt"
                  label="Título ou Tema do Vídeo"
                  placeholder="ex: Oração da Manhã"
                  required
                />
                  
                <AppTextarea
                  id="script"
                  v-model="form.script_content"
                  label="Seu Roteiro"
                  placeholder="Cole aqui seu texto já pronto. O sistema organizará cada parágrafo em uma cena..."
                  required
                  :rows="12"
                />
                <p class="section-hint">
                  <Sparkles :size="12" class="text-violet-500" />
                  A IA otimizará seu texto para o formato de vídeo automaticamente.
                </p>
              </div>
            </form>
          </AppCard>
        </div>

        <!-- Sidebar Options Column -->
        <div class="options-column">
          <AppCard title="Configurações" class="sticky-card">
            <div class="options-sections">
              <!-- Language & Duration -->
              <div class="options-group">
                <AppSelect
                  id="language"
                  v-model="form.language"
                  label="Idioma do Conteúdo"
                  :options="languageOptions"
                />

                <AppSelect
                  id="agent"
                  v-model="form.agent_id"
                  label="Agente (Persona)"
                  :options="agentOptions"
                  :disabled="loadingAgents"
                />

                <AppInput
                  v-if="!isScriptMode"
                  id="duration"
                  v-model="form.target_duration_minutes"
                  label="Duração Alvo (min)"
                  type="number"
                  min="0"
                  max="180"
                  required
                />
                <div v-else class="duration-auto">
                    <Clock :size="14" />
                    <span>Duração automática via Roteiro</span>
                </div>
              </div>

              <!-- Aspect Ratio -->
              <div class="options-group">
                <label class="app-label mb-2 block">Formato do Vídeo</label>
                <div class="aspect-ratio-grid">
                  <button 
                    type="button"
                    class="ratio-card"
                    :class="{ 'active': form.aspect_ratios.includes('16:9') }"
                    @click="toggleRatio('16:9')"
                  >
                    <div class="ratio-preview horizontal"></div>
                    <span>Horizontal (16:9)</span>
                  </button>
                  <button 
                    type="button"
                    class="ratio-card"
                    :class="{ 'active': form.aspect_ratios.includes('9:16') }"
                    @click="toggleRatio('9:16')"
                  >
                    <div class="ratio-preview vertical"></div>
                    <span>Vertical (9:16)</span>
                  </button>
                </div>
              </div>

              <!-- Visual Style -->
              <div class="options-group">
                <label class="app-label mb-2 block">Fonte de Imagens</label>
                <div class="image-source-grid">
                  <button
                    v-for="opt in imageSourceOptions"
                    :key="opt.value"
                    type="button"
                    class="source-card"
                    :class="{ 'active': form.auto_image_source === opt.value }"
                    @click="form.auto_image_source = opt.value"
                  >
                    <component :is="opt.icon" :size="18" />
                    <span>{{ opt.label.split(' ')[0] }}</span>
                  </button>
                </div>
              </div>

              <!-- Narration Toggle -->
              <div class="options-group">
                <div 
                  class="narration-card"
                  :class="{ 'active': form.auto_generate_narration }"
                  @click="form.auto_generate_narration = !form.auto_generate_narration"
                >
                  <div class="narration-info">
                    <Mic2 :size="20" />
                    <div>
                      <span class="block font-semibold">Narração IA</span>
                      <span class="text-xs opacity-80">Voz ultra-realista</span>
                    </div>
                  </div>
                  <div class="premium-switch">
                    <div class="switch-dot"></div>
                  </div>
                </div>
              </div>

              <!-- Audio Padding -->
              <div class="options-group">
                <div class="audio-padding-container">
                  <div class="flex items-center justify-between mb-3">
                    <label for="audio_padding" class="app-label !mb-0 flex items-center gap-2">
                      <Music :size="16" class="text-primary" />
                      Padding de Áudio
                    </label>
                    <span class="text-xs font-bold text-primary font-mono bg-violet-100 dark:bg-violet-900/30 px-2 py-0.5 rounded">{{ form.audio_transition_padding }}s</span>
                  </div>
                  <div class="flex items-center gap-4">
                    <input
                      v-model.number="form.audio_transition_padding"
                      type="range"
                      min="0.3"
                      max="5"
                      step="0.1"
                      class="flex-1 h-2 bg-zinc-200 dark:bg-zinc-800 rounded-full appearance-none cursor-pointer accent-violet-600"
                    />
                    <input 
                      id="audio_padding"
                      v-model.number="form.audio_transition_padding" 
                      type="number" 
                      step="0.1"
                      min="0.3"
                      max="5"
                      class="app-input h-10 w-20 text-center font-bold !bg-white dark:!bg-zinc-950"
                    />
                  </div>
                  <p class="text-[10px] text-zinc-400 mt-2 italic">Ajuste o tempo de silêncio entre as transições de áudio.</p>
                </div>
              </div>
              
              <div class="form-actions-sidebar">
                <AppButton
                  type="button"
                  variant="primary"
                  block
                  size="lg"
                  :loading="videoStore.isCreating"
                  @click="handleSubmit"
                >
                  <Wand2 :size="18" />
                  <span>Gerar Vídeo</span>
                </AppButton>
              </div>
            </div>
          </AppCard>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.wizard-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.wizard-header {
  margin-bottom: 2.5rem;
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
}

.wizard-header h1 {
  font-size: 2.25rem;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.04em;
  margin-bottom: 0.5rem;
}

.wizard-header p {
  color: var(--text-secondary);
  font-size: 1.125rem;
  max-width: 600px;
}

.back-btn {
  margin-top: 0.5rem;
}

/* Grid Layout */
.wizard-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 2.5rem;
  align-items: start;
}

@media (max-width: 1024px) {
  .wizard-grid {
    grid-template-columns: 1fr;
  }
}

/* Content Card */
.content-card {
  padding: 2rem;
  min-height: 500px;
}

.mode-toggle-container {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 2.5rem;
}

.mode-toggle-wrapper {
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  padding: 0.375rem;
  border-radius: var(--radius-lg);
  display: flex;
  gap: 0.375rem;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}

.mode-toggle-btn {
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  font-size: 0.925rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  background: transparent;
  color: var(--text-secondary);
  border: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.mode-toggle-btn:hover {
  color: var(--text-primary);
}

.mode-toggle-btn.active {
  background: var(--color-white);
  color: var(--primary-base);
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06), 0 0 0 1px var(--border-subtle);
}

.section-hint {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    color: var(--text-muted);
    margin-top: 1rem;
}

/* Options Sidebar */
.sticky-card {
  position: sticky;
  top: 2rem;
}

.options-sections {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.options-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.duration-auto {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: var(--bg-app);
    border: 1px dashed var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-muted);
    font-size: 0.875rem;
}

/* Image Source Grid */
.image-source-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.source-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-secondary);
}

.source-card:hover {
  border-color: var(--primary-base);
  background: var(--color-white);
  color: var(--primary-base);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.source-card.active {
  border-color: var(--primary-base);
  background: var(--color-violet-50);
  color: var(--primary-base);
  box-shadow: 0 0 0 1px var(--primary-base);
}

.source-card span {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Narration Card */
.narration-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
}

.narration-card:hover {
  border-color: var(--primary-base);
  background: var(--color-white);
}

.narration-card.active {
  border-color: var(--primary-base);
  background: var(--color-violet-50);
}

.narration-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: var(--text-primary);
}

.narration-card.active .narration-info {
    color: var(--primary-base);
}

/* Premium Switch Simulation */
.premium-switch {
  width: 44px;
  height: 24px;
  background: var(--color-zinc-300);
  border-radius: var(--radius-full);
  padding: 2px;
  transition: all 0.3s ease;
  position: relative;
}

.narration-card.active .premium-switch {
  background: var(--primary-base);
}

.switch-dot {
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.narration-card.active .switch-dot {
  transform: translateX(20px);
}

.form-actions-sidebar {
  margin-top: 1rem;
}

/* Animations */
.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}

.animate-slide-up {
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Aspect Ratio Grid */
.aspect-ratio-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.ratio-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--text-secondary);
}

.ratio-card:hover {
  border-color: var(--primary-base);
  background: var(--color-white);
  color: var(--primary-base);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.ratio-card.active {
  border-color: var(--primary-base);
  background: var(--color-violet-50);
  color: var(--primary-base);
  box-shadow: 0 0 0 1px var(--primary-base);
}

.ratio-card span {
    font-size: 0.75rem;
    font-weight: 600;
}

.ratio-preview {
  background: var(--color-zinc-300);
  border-radius: 4px;
  transition: all 0.2s ease;
}

.ratio-card.active .ratio-preview {
  background: var(--primary-base);
}

.ratio-preview.horizontal {
  width: 48px;
  height: 27px; /* 16:9 */
}

.ratio-preview.vertical {
  width: 27px;
  height: 48px; /* 9:16 */
}

.audio-padding-container {
  padding: 1.25rem;
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  transition: all 0.2s ease;
}

.audio-padding-container:focus-within {
  border-color: var(--primary-base);
  background: var(--color-white);
  box-shadow: var(--shadow-sm);
}
</style>
