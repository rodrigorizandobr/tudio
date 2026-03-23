<script setup lang="ts">
// Props could include user info later
</script>

<template>
  <header class="app-header">
    <div class="user-profile">
      <div class="avatar">
        <span>R</span>
      </div>
      <div class="user-info">
        <span class="name">Rodrigo Silva</span>
        <span class="role">Admin</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 64px;
  background: rgba(9, 9, 11, 0.8); /* Glass effect */
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  position: sticky;
  top: 0;
  z-index: 40;
}

.page-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-zinc-50);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-zinc-800);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-zinc-300);
  font-weight: 600;
  border: 1px solid var(--border-subtle);
}

.user-info {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-zinc-100);
}

.role {
  font-size: 0.75rem;
  color: var(--color-zinc-500);
}
</style>
