<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const props = defineProps<{ id: string }>()
const router = useRouter()
const data = ref<Record<string, unknown> | null>(null)
const err = ref<string | null>(null)

onMounted(async () => {
  try {
    data.value = await api.build(Number(props.id))
  } catch (e) {
    err.value = String(e)
  }
})

function fmtTs(ts: unknown) {
  if (typeof ts !== 'number') return String(ts ?? '-')
  return new Date(ts * 1000).toLocaleString()
}
</script>

<template>
  <el-page-header @back="router.back()" content="Build detail" />

  <el-alert v-if="err" :title="err" type="error" :closable="false" class="mt" />

  <div v-else-if="data">
    <el-descriptions class="mt" :column="3" border>
      <el-descriptions-item label="ID">{{ data.id }}</el-descriptions-item>
      <el-descriptions-item label="Status">
        <el-tag :type="data.status === 'running' ? 'warning' : 'info'">{{ data.status ?? '-' }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="Exit code">
        <el-tag v-if="data.exit_code !== null" :type="data.exit_code === 0 ? 'success' : 'danger'">{{ data.exit_code }}</el-tag>
        <span v-else>-</span>
      </el-descriptions-item>
      <el-descriptions-item label="Started">{{ fmtTs(data.started_ts ?? data.ts) }}</el-descriptions-item>
      <el-descriptions-item label="Finished">{{ fmtTs(data.finished_ts) }}</el-descriptions-item>
      <el-descriptions-item label="User">{{ data.user_email ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="Platform">{{ data.platform ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="Build type">{{ data.build_type ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="Reclient">{{ data.reclient_enabled ? 'on' : 'off' }}</el-descriptions-item>
      <el-descriptions-item label="Target" :span="3">{{ data.target ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="Total time (s)">{{ data.total_time ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="Ninja time (s)">{{ data.ninja_time ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="ncpu">{{ data.ncpu ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="Args" :span="3">{{ data.args ?? '-' }}</el-descriptions-item>
      <el-descriptions-item label="Output dir" :span="3">{{ data.output_dir ?? '-' }}</el-descriptions-item>
    </el-descriptions>

    <el-row :gutter="12" class="mt">
      <el-col :span="12">
        <el-card><div class="t">RBE</div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="hits">{{ data.rbe_hits ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="misses">{{ data.rbe_misses ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="local fallback">{{ data.rbe_local_fallback ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="total actions">{{ data.rbe_total_actions ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card><div class="t">ccache</div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="direct hit">{{ data.ccache_direct_hit ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="preproc hit">{{ data.ccache_preproc_hit ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="miss">{{ data.ccache_miss ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="size (KiB)">{{ data.ccache_size_kib ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="mt"><div class="t">Raw payload</div>
      <pre class="raw">{{ JSON.stringify(data.raw, null, 2) }}</pre>
    </el-card>
  </div>
</template>

<style scoped>
.mt { margin-top: 12px; }
.t { font-weight: 600; margin-bottom: 8px; }
.raw { background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 4px; max-height: 480px; overflow: auto; font-size: 12px; }
</style>
