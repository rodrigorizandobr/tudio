<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import AppButton from '../components/ui/AppButton.vue'
import AppInput from '../components/ui/AppInput.vue'
import AppCard from '../components/ui/AppCard.vue'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')

const handleLogin = async () => {
  if (!email.value || !password.value) return

  const success = await auth.login(email.value, password.value)
  if (success) {
    router.push('/')
  }
}
</script>

<template>
  <div class="login-view">
    <div class="login-container animate-fade-in">
      <div class="brand-header">
        <h1>Tudio<span class="highlight">V2</span></h1>
        <p class="subtitle">
          AI Video Generation Platform
        </p>
      </div>

      <AppCard class="login-card animate-slide-up delay-100">
        <template #default>
          <form
            class="login-form"
            @submit.prevent="handleLogin"
          >
            <AppInput
              id="email"
              v-model="email"
              label="Endereço de Email"
              placeholder="nome@empresa.com"
              type="email"
              required
            />
            
            <AppInput
              id="password"
              v-model="password"
              label="Senha"
              placeholder="••••••••"
              type="password"
              required
            />

            <div
              v-if="auth.error"
              class="error-message"
            >
              {{ auth.error }}
            </div>

            <div class="recaptcha-placeholder">
              Este site é protegido pelo reCAPTCHA e as
              <a href="#">Políticas de Privacidade</a> e <a href="#">Termos de Serviço</a> do Google se aplicam.
            </div>

            <AppButton
              block
              size="lg"
              variant="primary"
              type="submit"
              :loading="auth.isLoading"
              data-testid="btn-login"
            >
              Entrar
            </AppButton>
          </form>
        </template>
        
        <template #footer>
          <div class="footer-links">
            <a
              href="#"
              class="link"
            >Esqueceu sua senha?</a>
          </div>
        </template>
      </AppCard>
    </div>
  </div>
</template>

<style scoped>
.login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top right, var(--color-violet-100), var(--bg-app) 60%);
}

.login-container {
  width: 100%;
  max-width: 400px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.brand-header {
  text-align: center;
}

.brand-header h1 {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.05em;
  color: var(--text-primary);
}

.highlight {
  color: var(--primary-base);
}

.subtitle {
  color: var(--text-secondary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.error-message {
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  background: rgba(220, 38, 38, 0.1);
  color: #ef4444;
  font-size: 0.875rem;
  text-align: center;
}

.recaptcha-placeholder {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin: 0.5rem 0 1rem;
  line-height: 1.4;
}

.recaptcha-placeholder a {
  color: var(--text-secondary);
  text-decoration: underline;
}

.footer-links {
  width: 100%;
  text-align: center;
}

.link {
  font-size: 0.875rem;
  color: var(--primary-base);
}
.link:hover {
  text-decoration: underline;
}
</style>
