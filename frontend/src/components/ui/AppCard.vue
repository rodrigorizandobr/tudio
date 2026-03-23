<script setup lang="ts">
interface Props {
  title?: string
}

defineProps<Props>()
</script>

<template>
  <div class="app-card premium-card">
    <div
      v-if="title || $slots.title || $slots['header-actions']"
      class="card-header"
    >
      <div
        v-if="$slots.title"
        class="card-title-wrapper"
      >
        <slot name="title" />
      </div>
      <h3
        v-else-if="title"
        class="card-title"
      >
        {{ title }}
      </h3>
      <div class="card-actions">
        <slot name="header-actions" />
      </div>
    </div>

    
    <div class="card-content">
      <slot />
    </div>
    
    <div
      v-if="$slots.footer"
      class="card-footer"
    >
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.app-card {
  /* Inherits styles from .premium-card in theme.css */
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  font-weight: 600;
  color: var(--text-primary);
}

.card-title-wrapper {
  flex: 1;
}


.card-content {
  color: var(--text-primary);
}

.card-footer {
  margin-top: auto;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
</style>
