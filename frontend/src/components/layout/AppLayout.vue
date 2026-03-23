<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import LoadingBar from '../ui/LoadingBar.vue'
</script>

<template>
  <div class="app-layout">
    <LoadingBar />
    <Sidebar />
    
    <div class="main-content-wrapper">
      <Header />
      <main class="main-content">
        <div class="container">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-app);
}

.main-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 260px; /* Sidebar width */
  min-width: 0;
}

.main-content {
  flex: 1;
  padding: 2rem 0;
}
</style>
