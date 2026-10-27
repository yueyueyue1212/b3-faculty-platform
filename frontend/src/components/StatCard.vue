<template>
  <div class="stat-card" :class="accent ? `accent-${accent}` : ''">
    <div class="stat-top">
      <span>{{ label }}</span>
      <el-icon v-if="icon"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-value">
      {{ value }}<small v-if="unit">{{ unit }}</small>
    </div>
    <div class="stat-sub">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  unit?: string
  sub?: string
  icon?: string
  accent?: 'success' | 'warning' | 'danger' | 'info'
}>()
</script>
