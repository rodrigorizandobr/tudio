import api from '../lib/axios'


export interface Agent {
    id?: string
    name: string
    description: string
    icon?: string


    prompt_init: string
    prompt_chapters: string
    prompt_subchapters: string
    prompt_scenes: string
    is_default: boolean
    created_at?: string
    updated_at?: string
}

export const agentService = {
    async list(): Promise<Agent[]> {
        const response = await api.get('/agents/')
        return response.data || []
    },

    async create(agent: Agent): Promise<Agent> {
        const response = await api.post('/agents/', agent)
        return response.data
    },

    async get(id: string): Promise<Agent> {
        const response = await api.get(`/agents/${id}`)
        return response.data
    },

    async update(id: string, agent: Agent): Promise<Agent> {
        const response = await api.put(`/agents/${id}`, agent)
        return response.data
    },

    async delete(id: string): Promise<void> {
        await api.delete(`/agents/${id}`)
    }
}
