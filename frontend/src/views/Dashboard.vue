<script setup lang="ts">
import { onMounted, reactive, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import StatCard from '../components/StatCard.vue'
import { api, type BuildRow, type Summary, type TsPoint, type UserStat, type PlatStat } from '../api'

const router = useRouter()
const rangeDays = ref(30)
const summary = ref<Summary | null>(null)
const series = ref<TsPoint[]>([])
const userStats = ref<UserStat[]>([])
const platStats = ref<PlatStat[]>([])

const filters = reactive({
  user: '', platform: '', exit_code: '' as '' | string, status: '' as '' | string,
})
const distinct = ref<{ users: string[]; platforms: string[] }>({ users: [], platforms: [] })

const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const items = ref<BuildRow[]>([])
const loading = ref(false)

async function loadStats() {
  const d = rangeDays.value
  ;[summary.value, series.value, userStats.value, platStats.value] = await Promise.all([
    api.summary(d), api.timeseries(d), api.byUser(d), api.byPlatform(d),
  ])
}

async function loadBuilds() {
  loading.value = true
  try {
    const r = await api.builds({
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
      user: filters.user || undefined,
      platform: filters.platform || undefined,
      exit_code: filters.exit_code === '' ? undefined : filters.exit_code,
      status: filters.status || undefined,
    })
    total.value = r.total
    items.value = r.items
  } finally { loading.value = false }
}

onMounted(async () => {
  distinct.value = await api.distinct()
  await loadStats()
  await loadBuilds()
})

watch(rangeDays, loadStats)
watch([() => filters.user, () => filters.platform, () => filters.exit_code, () => filters.status], () => {
  page.value = 1
  loadBuilds()
})
watch([page, pageSize], loadBuilds)

const tsOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['Total', 'Success', 'Avg time (s)'] },
  grid: { left: 40, right: 50, top: 40, bottom: 30 },
  xAxis: { type: 'category', data: series.value.map(p => p.day) },
  yAxis: [
    { type: 'value', name: 'Builds' },
    { type: 'value', name: 'Sec' },
  ],
  series: [
    { name: 'Total',   type: 'bar',  data: series.value.map(p => p.total),     itemStyle: { color: '#409eff' } },
    { name: 'Success', type: 'bar',  data: series.value.map(p => p.success),   itemStyle: { color: '#67c23a' } },
    { name: 'Avg time (s)', type: 'line', yAxisIndex: 1, data: series.value.map(p => Math.round(p.avg_total || 0)), itemStyle: { color: '#e6a23c' } },
  ],
}))

const userOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 140, right: 30, top: 20, bottom: 30 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: userStats.value.map(u => u.user).reverse(), axisLabel: { width: 130, overflow: 'truncate' } },
  series: [{ type: 'bar', data: userStats.value.map(u => u.total).reverse(), itemStyle: { color: '#409eff' } }],
}))

const platOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: platStats.value.map(p => ({ name: p.platform, value: p.total })),
  }],
}))

function fmtTs(ts: number | null) {
  if (ts == null) return '-'
  return new Date(ts * 1000).toLocaleString()
}
function fmtSec(s: number | null) {
  if (s == null) return '-'
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60), sec = s % 60
  if (m < 60) return `${m}m${sec}s`
  const h = Math.floor(m / 60)
  return `${h}h${m % 60}m`
}
function rowClass({ row }: { row: BuildRow }) {
  if (row.status === 'running') return 'row-running'
  if (row.exit_code === 0) return ''
  return row.exit_code === null ? '' : 'row-fail'
}
function statusType(s: string | null) {
  if (s === 'running') return 'warning'
  if (s === 'finished') return 'info'
  return 'info'
}
</script>

<template>
  <div class="filter-bar">
    <el-radio-group v-model="rangeDays" size="small">
      <el-radio-button :value="1">1d</el-radio-button>
      <el-radio-button :value="7">7d</el-radio-button>
      <el-radio-button :value="14">14d</el-radio-button>
      <el-radio-button :value="30">30d</el-radio-button>
      <el-radio-button :value="90">90d</el-radio-button>
    </el-radio-group>
  </div>

  <el-row :gutter="12" class="cards">
    <el-col :span="3"><StatCard label="Total"        :value="summary?.total ?? '-'" /></el-col>
    <el-col :span="3"><StatCard label="Success rate" :value="(summary?.success_rate ?? 0) + '%'" tone="ok" /></el-col>
    <el-col :span="3"><StatCard label="Failures"     :value="summary?.fail ?? '-'" tone="fail" /></el-col>
    <el-col :span="3"><StatCard label="In-flight"    :value="summary?.running ?? '-'" tone="warn" /></el-col>
    <el-col :span="4"><StatCard label="Avg total"    :value="fmtSec(summary?.avg_total_time ?? null)" /></el-col>
    <el-col :span="4"><StatCard label="RBE hit %"    :value="(summary?.rbe_hit_rate ?? 0) + '%'" tone="ok" /></el-col>
    <el-col :span="4"><StatCard label="ccache hit %" :value="(summary?.ccache_hit_rate ?? 0) + '%'" tone="ok" /></el-col>
  </el-row>

  <el-row :gutter="12" class="charts">
    <el-col :span="14">
      <el-card><div class="chart-title">Builds per day</div><VChart :option="tsOption" autoresize style="height:300px" /></el-card>
    </el-col>
    <el-col :span="10">
      <el-card><div class="chart-title">Platform mix</div><VChart :option="platOption" autoresize style="height:300px" /></el-card>
    </el-col>
  </el-row>

  <el-row :gutter="12" class="charts">
    <el-col :span="24">
      <el-card><div class="chart-title">Top users by build count</div><VChart :option="userOption" autoresize style="height:320px" /></el-card>
    </el-col>
  </el-row>

  <el-card class="builds-card">
    <div class="builds-header">
      <span class="chart-title">Builds</span>
      <el-select v-model="filters.user" placeholder="user" clearable size="small" style="width: 180px">
        <el-option v-for="u in distinct.users" :key="u" :label="u" :value="u" />
      </el-select>
      <el-select v-model="filters.platform" placeholder="platform" clearable size="small" style="width: 160px">
        <el-option v-for="p in distinct.platforms" :key="p" :label="p" :value="p" />
      </el-select>
      <el-select v-model="filters.status" placeholder="status" clearable size="small" style="width: 120px">
        <el-option label="running" value="running" />
        <el-option label="finished" value="finished" />
      </el-select>
      <el-select v-model="filters.exit_code" placeholder="exit" clearable size="small" style="width: 110px">
        <el-option label="success" value="0" />
        <el-option label="fail" value="1" />
      </el-select>
      <el-button size="small" @click="loadBuilds">Refresh</el-button>
    </div>

    <el-table :data="items" v-loading="loading" :row-class-name="rowClass"
              @row-click="(row: BuildRow) => router.push(`/builds/${row.id}`)" stripe size="small">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="Started" width="170">
        <template #default="{ row }: { row: BuildRow }">{{ fmtTs(row.started_ts ?? row.ts) }}</template>
      </el-table-column>
      <el-table-column label="Status" width="100">
        <template #default="{ row }: { row: BuildRow }">
          <el-tag size="small" :type="statusType(row.status)">{{ row.status ?? '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="user_email" label="User" width="200" show-overflow-tooltip />
      <el-table-column prop="platform" label="Platform" width="120" />
      <el-table-column prop="build_type" label="Type" width="90" />
      <el-table-column prop="target" label="Target" min-width="160" show-overflow-tooltip />
      <el-table-column label="Total" width="90">
        <template #default="{ row }: { row: BuildRow }">{{ fmtSec(row.total_time) }}</template>
      </el-table-column>
      <el-table-column label="Ninja" width="90">
        <template #default="{ row }: { row: BuildRow }">{{ fmtSec(row.ninja_time) }}</template>
      </el-table-column>
      <el-table-column label="Exit" width="70">
        <template #default="{ row }: { row: BuildRow }">
          <el-tag v-if="row.exit_code !== null" size="small" :type="row.exit_code === 0 ? 'success' : 'danger'">
            {{ row.exit_code }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="RBE" width="100">
        <template #default="{ row }: { row: BuildRow }">
          {{ (row.rbe_hits ?? 0) + '/' + ((row.rbe_hits ?? 0) + (row.rbe_misses ?? 0)) }}
        </template>
      </el-table-column>
      <el-table-column label="ccache" width="120">
        <template #default="{ row }: { row: BuildRow }">
          {{ (row.ccache_direct_hit ?? 0) + ' / ' + (row.ccache_miss ?? 0) }}
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      background layout="total, sizes, prev, pager, next"
      :total="total"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[20, 50, 100, 200]" />
  </el-card>
</template>

<style scoped>
.filter-bar { margin-bottom: 12px; }
.cards { margin-bottom: 12px; }
.charts { margin-bottom: 12px; }
.chart-title { font-weight: 600; margin-bottom: 8px; display: block; }
.builds-card { margin-bottom: 24px; }
.builds-header { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.pager { margin-top: 12px; justify-content: flex-end; }
:deep(.row-fail) { background-color: #fef0f0 !important; }
:deep(.row-running) { background-color: #fdf6ec !important; }
:deep(.el-table__row) { cursor: pointer; }
</style>
