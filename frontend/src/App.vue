<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
</script>

<template>
  <el-container class="root">
    <el-header class="header">
      <RouterLink to="/" class="brand">Build Telemetry</RouterLink>
      <span class="sub">Chromium build stats</span>
    </el-header>
    <el-main class="main">
      <RouterView />
    </el-main>
  </el-container>
</template>

<style>
html, body, #app { height: 100%; margin: 0; }
.root { min-height: 100vh; background: #f5f7fa; }
.header {
  background: #1f2937; color: #fff; display: flex; align-items: center; gap: 16px;
}
.brand { color: #fff; font-weight: 600; font-size: 18px; text-decoration: none; }
.sub { color: #9ca3af; font-size: 13px; }
.main { padding: 16px 24px; }
</style>
