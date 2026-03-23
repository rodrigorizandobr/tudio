import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { useUIStore } from '../stores/ui.store'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import VideoWizardView from '../views/VideoWizardView.vue'
import VideoDetailsView from '../views/VideoDetailsView.vue'
import GroupListView from '../views/GroupListView.vue'
import SettingsView from '../views/SettingsView.vue'
import AgentsView from '../views/AgentsView.vue'
import VoicesView from '../views/VoicesView.vue'
import SocialNetworksView from '../views/SocialNetworksView.vue'


const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: LoginView,
            meta: { guest: true }
        },
        {
            path: '/panel',
            redirect: '/panel/videos'
        },
        {
            path: '/panel/videos',
            name: 'videos',
            component: DashboardView,
            alias: '/panel/dashboard',
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/videos/new',
            name: 'video-create',
            component: VideoWizardView,
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/videos/:id',
            name: 'video-details',
            component: VideoDetailsView,
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/admin/groups',
            name: 'group-list',
            component: GroupListView,
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/settings',
            name: 'settings',
            component: SettingsView,
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/agents',
            name: 'agents',
            component: AgentsView,
            alias: '/panel/agents',
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/voices',
            name: 'voices',
            component: VoicesView,
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/social',
            name: 'social-networks',
            component: SocialNetworksView,
            alias: '/panel/social-networks',
            meta: { requiresAuth: true }
        },
        {
            path: '/panel/music',
            name: 'music-library',
            component: () => import('../views/MusicView.vue'),
            alias: '/panel/library',
            meta: { requiresAuth: true }
        },
        {
            path: '/',
            redirect: '/panel'
        }

    ],
})

router.beforeEach((to, _from, next) => {
    const auth = useAuthStore()
    const ui = useUIStore()

    ui.startLoading()

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
        next('/login')
    } else if (to.meta.guest && auth.isAuthenticated) {
        next('/panel')
    } else {
        next()
    }
})

router.afterEach(() => {
    const ui = useUIStore()
    ui.stopLoading()
})

export default router
