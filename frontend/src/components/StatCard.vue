<script setup lang="ts">
defineProps<{ label: string; value: string | number; sub?: string; tone?: 'ok' | 'warn' | 'fail' }>()
</script>

<template>
  <el-card shadow="hover" class="stat" :class="tone">
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
  </el-card>
</template>

<style scoped>
.stat { border-left: 4px solid #409eff; }
.stat.ok { border-left-color: #67c23a; }
.stat.warn { border-left-color: #e6a23c; }
.stat.fail { border-left-color: #f56c6c; }
.label { color: #6b7280; font-size: 13px; }
.value { font-size: 28px; font-weight: 600; margin-top: 4px; color: #111827; }
.sub { color: #9ca3af; font-size: 12px; margin-top: 4px; }
</style>
