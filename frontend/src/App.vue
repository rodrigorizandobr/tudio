<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth.store'
import VideoDownloadPip from './components/video/VideoDownloadPip.vue'

const authStore = useAuthStore()

onMounted(() => {
  if (authStore.token) {
    authStore.fetchUser()
  }
})
</script>

<template>
  <router-view />
  <VideoDownloadPip />
</template>

<style>
/* Global styles if needed, but we use reset.css and theme.css */
</style>
