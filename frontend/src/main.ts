import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
// Tailwind must come first
import './assets/main.css'

// Custom Theme Variables (overrides)
import './assets/css/theme.css'
import './assets/css/animations.css'
// import './assets/css/reset.css' -- Disabled (using Tailwind Preflight)
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
