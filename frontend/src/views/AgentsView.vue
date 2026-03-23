<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Edit2, Trash2, Bot } from 'lucide-vue-next'
import AppButton from '../components/ui/AppButton.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppLoadingBar from '../components/ui/LoadingBar.vue'
import AgentModal from '../components/agents/AgentModal.vue'
import AppModal from '../components/ui/AppModal.vue'
import AppLayout from '../components/layout/AppLayout.vue'
import { agentService, type Agent } from '../services/agent.service'
import { getIconComponent } from '../utils/agent-icons'



const agents = ref<Agent[]>([])
const loading = ref(true)
const isModalOpen = ref(false)
const selectedAgent = ref<Agent | null>(null)

// Delete confirmation
const isDeleteModalOpen = ref(false)
const agentToDelete = ref<Agent | null>(null)

const fetchAgents = async () => {
    loading.value = true
    try {
        agents.value = await agentService.list()
    } catch (e) {
        console.error("Failed to load agents", e)
    } finally {
        loading.value = false
    }
}

const openCreateModal = () => {
    selectedAgent.value = null
    isModalOpen.value = true
}

const openEditModal = async (agent: Agent) => {
    selectedAgent.value = agent // Show immediate (stale) data first
    isModalOpen.value = true
    
    // Fetch fresh data (Strong Consistency)
    if (agent.id) {
        try {
            const freshAgent = await agentService.get(agent.id)
            if (freshAgent) {
                selectedAgent.value = freshAgent
                // Update list item too
                const index = agents.value.findIndex(a => a.id === agent.id)
                if (index !== -1) {
                    agents.value[index] = freshAgent
                }
            }
        } catch (e) {
            console.error("Failed to refresh agent data", e)
        }
    }
}

const confirmDelete = (agent: Agent) => {
    agentToDelete.value = agent
    isDeleteModalOpen.value = true
}

const handleDelete = async () => {
    if (!agentToDelete.value?.id) return
    
    try {
        await agentService.delete(agentToDelete.value.id)
        await fetchAgents()
    } catch (e) {
        console.error("Failed to delete agent", e)
    } finally {
        isDeleteModalOpen.value = false
        agentToDelete.value = null
    }
}

const handleSave = async (agent: Agent) => {
    try {
        if (agent.id) {
            await agentService.update(agent.id, agent)
        } else {
            await agentService.create(agent)
        }
        isModalOpen.value = false
        await fetchAgents()
    } catch (e) {
        console.error("Failed to save agent", e)
    }
}

const handleAutoSave = async (agent: Agent) => {
    if (!agent.id) return
    try {
        // Silent update
        await agentService.update(agent.id, agent)
        // We do NOT fetchAgents() here to avoid re-rendering list/modal state weirdness if not needed
        // Ideally we update the local list item to match
        const index = agents.value.findIndex(a => a.id === agent.id)
        if (index !== -1) {
            agents.value[index] = { ...agent }
        }
    } catch (e) {
        console.error("Failed to auto-save agent", e)
        throw e // Propagate error so Modal knows it failed
    }
}


onMounted(() => {
    fetchAgents()
})


</script>


<template>
  <AppLayout>
    <div class="view-container">
      <AppLoadingBar :loading="loading" />

      <header class="view-header">
        <div>
          <h1 class="view-title">
            Agentes
          </h1>
          <p class="view-subtitle">
            Gerencie os templates de prompt para geração de roteiros.
          </p>
        </div>
        <AppButton @click="openCreateModal">
          <Plus
            :size="18"
            class="mr-2"
          />
          Novo Agente
        </AppButton>
      </header>

      <div
        v-if="loading"
        class="loading-state"
      >
        Carregando...
      </div>

      <div
        v-else
        class="content-grid"
      >
        <AppCard
          v-for="agent in agents"
          :key="agent.id"
          class="agent-card group"
        >
          <template #title>
            <div class="card-header-wrapper">
              <div class="agent-icon-wrapper">
                <component
                  :is="getIconComponent(agent.icon || 'Bot')"
                  :size="20"
                  class="agent-icon"
                />
              </div>
              <div>
                <div class="agent-name">
                  {{ agent.name }}
                </div>
                <div class="agent-id">
                  ID: {{ agent.id?.substring(0, 8) }}...
                </div>
              </div>
            </div>
          </template>
            
          <template #header-actions>
            <div class="card-actions">
              <AppButton
                variant="ghost"
                size="sm"
                title="Editar"
                @click="openEditModal(agent)"
              >
                <Edit2
                  :size="16"
                  class="action-icon"
                />
              </AppButton>
              <AppButton
                variant="ghost"
                size="sm"
                class="text-error"
                title="Excluir"
                @click="confirmDelete(agent)"
              >
                <Trash2 :size="16" />
              </AppButton>
            </div>
          </template>

          <div class="agent-content">
            <div class="agent-description-wrapper">
              <p
                v-if="agent.description"
                class="agent-description"
              >
                {{ agent.description }}
              </p>
              <span
                v-else
                class="agent-description-empty"
              >Sem descrição.</span>
            </div>




            <div class="agent-footer">
              <span
                v-if="agent.is_default"
                class="badge-default"
              >
                <span class="badge-dot" />
                Padrão
              </span>
              <span v-else /> <!-- Spacer -->
                    
              <span class="version-text">v1.0</span>
            </div>
          </div>
        </AppCard>



        <!-- Empty State -->
        <div
          v-if="agents.length === 0"
          class="empty-state"
        >
          <Bot
            :size="48"
            class="text-muted mb-4"
          />
          <p>Nenhum agente encontrado.</p>
        </div>
      </div>

      <!-- Agent Modal -->
      <AgentModal 
        v-model:open="isModalOpen" 
        :agent="selectedAgent"
        @save="handleSave"
        @auto-save="handleAutoSave"
      />


      <!-- Delete Confirmation -->
      <AppModal
        :open="isDeleteModalOpen"
        title="Excluir Agente"
        description="Tem certeza que deseja excluir este agente? Esta ação não pode ser desfeita."
        confirm-label="Excluir"
        cancel-label="Cancelar"
        is-destructive
        @confirm="handleDelete"
        @cancel="isDeleteModalOpen = false"
      />
    </div>
  </AppLayout>
</template>


<style scoped>
.view-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.view-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
  margin-bottom: 0.5rem;
}

.view-subtitle {
  color: var(--text-secondary);
}

.content-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
}

.agent-card {
    transition: all 0.2s ease;
    border: 1px solid var(--border-subtle);
}

.agent-card:hover {
    transform: translateY(-2px);
    border-color: var(--primary-base);
    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
}

.agent-card:hover .card-actions {
    opacity: 1;
}

.card-header-wrapper {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.card-actions {
    display: flex;
    gap: 0.25rem;
    opacity: 0;
    transition: opacity 0.2s;
}

/* On mobile/touch devices or explicitly, ensure actions are visible if hover isn't supported */
@media (hover: none) {
    .card-actions {
        opacity: 1;
    }
}

.agent-icon-wrapper {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--primary-base) 0%, var(--primary-hover) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 6px -1px rgba(124, 58, 237, 0.2);
}

.agent-icon {
    color: white;
}

.agent-name {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 0.95rem;
}

.agent-id {
    font-size: 0.70rem;
    color: var(--text-muted);
    font-family: monospace;
}

.agent-description-wrapper {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    min-height: 40px;
}

.agent-description {
    font-size: 0.875rem;
    color: var(--text-secondary);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.agent-description-empty {
    font-size: 0.875rem;
    color: var(--text-muted);
    font-style: italic;
}

.agent-footer {
    margin-top: 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.badge-default {
    background: rgba(124, 58, 237, 0.1);
    color: var(--primary-base);
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    border: 1px solid rgba(124, 58, 237, 0.2);
}

.badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: var(--primary-base);
    margin-right: 0.5rem;
}

.version-text {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: monospace;
}

.action-icon {
    color: var(--text-muted);
    transition: color 0.2s;
}

.action-icon:hover {
    color: var(--text-primary);
}

.variable-highlight {
    color: var(--primary-base);
    font-family: monospace;
    font-weight: 600;
    background: rgba(124, 58, 237, 0.1);
    padding: 0 2px;
    border-radius: 4px;
}



</style>
