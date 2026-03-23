<script setup lang="ts">

import { useRouter, useRoute } from 'vue-router'
import { FileText, Settings, LogOut, Users, Bot, Mic2, Share2, Music, Wand2 } from 'lucide-vue-next'

import { useAuthStore } from '../../stores/auth.store'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { name: 'Criar Vídeo', path: '/panel/videos/new', icon: Wand2 },
  { name: 'Vídeos', path: '/panel/videos', icon: FileText },
  { name: 'Agentes', path: '/panel/agents', icon: Bot },
  { name: 'Vozes', path: '/panel/voices', icon: Mic2 },
  { name: 'Músicas', path: '/panel/music', icon: Music },
  { name: 'Redes Sociais', path: '/panel/social', icon: Share2 },
  { name: 'Configurações', path: '/panel/settings', icon: Settings },

  // TODO: Only show if admin (simplified for MVP)
  { name: 'Grupos de Acesso', path: '/panel/admin/groups', icon: Users },
]

const isActive = (path: string) => route.path === path || (path !== '/panel' && route.path.startsWith(path))

const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <aside class="app-sidebar">
    <div class="sidebar-header">
      <div class="logo">
        Tudio<span class="highlight">V2</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <ul>
        <li
          v-for="item in navItems"
          :key="item.path"
        >
          <router-link
            :to="item.path"
            class="nav-link"
            :class="{ active: isActive(item.path) }"
          >
            <component
              :is="item.icon"
              class="icon"
            />
            <span>{{ item.name }}</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <div class="sidebar-footer">
      <button
        class="nav-link logout-btn"
        @click="logout"
      >
        <LogOut class="icon" />
        <span>Sair</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: 260px;
  height: 100vh;
  background: var(--bg-card);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 50;
}

.sidebar-header {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  border-bottom: 1px solid var(--border-subtle);
}

.logo {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
}

.highlight {
  color: var(--primary-base);
}

.sidebar-nav {
  flex: 1;
  padding: 1.5rem 1rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  color: var(--text-secondary);
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.nav-link:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.nav-link.active {
  background: rgba(124, 58, 237, 0.1);
  color: var(--primary-base);
}

.icon {
  width: 1.25rem;
  height: 1.25rem;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid var(--border-subtle);
}

.logout-btn {
  width: 100%;
  color: #ef4444;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}
</style>
