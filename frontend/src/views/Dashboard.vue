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
const seriesFull = ref<TsPoint[]>([])
const seriesInc = ref<TsPoint[]>([])
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
const tableEl = ref<any>()
const topScrollEl = ref<HTMLElement>()
const tableInnerWidth = ref(0)
let _bodyWrap: HTMLElement | null = null
let _syncing = false

function _findBodyWrap(): HTMLElement | null {
  const root = tableEl.value?.$el as HTMLElement | undefined
  if (!root) return null
  return (root.querySelector('.el-scrollbar__wrap') ||
          root.querySelector('.el-table__body-wrapper')) as HTMLElement | null
}

function _measure() {
  if (!_bodyWrap) return
  const inner = _bodyWrap.querySelector('table') as HTMLElement | null
  tableInnerWidth.value = inner ? inner.scrollWidth : _bodyWrap.scrollWidth
}

function _onBodyScroll() {
  if (_syncing || !_bodyWrap || !topScrollEl.value) return
  _syncing = true
  topScrollEl.value.scrollLeft = _bodyWrap.scrollLeft
  _syncing = false
}
function _onTopScroll() {
  if (_syncing || !_bodyWrap || !topScrollEl.value) return
  _syncing = true
  _bodyWrap.scrollLeft = topScrollEl.value.scrollLeft
  _syncing = false
}

function setupTopScroll() {
  _bodyWrap = _findBodyWrap()
  if (!_bodyWrap) { setTimeout(setupTopScroll, 100); return }
  _measure()
  _bodyWrap.addEventListener('scroll', _onBodyScroll, { passive: true })
  topScrollEl.value?.addEventListener('scroll', _onTopScroll, { passive: true })
  const inner = _bodyWrap.querySelector('table') as HTMLElement | null
  if (inner && 'ResizeObserver' in window) {
    new ResizeObserver(_measure).observe(inner)
  }
  window.addEventListener('resize', _measure)
}

async function loadStats() {
  const d = rangeDays.value
  ;[summary.value, series.value, seriesFull.value, seriesInc.value, userStats.value, platStats.value] = await Promise.all([
    api.summary(d),
    api.timeseries(d),
    api.timeseries(d, "full"),
    api.timeseries(d, "incremental"),
    api.byUser(d),
    api.byPlatform(d),
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
  setupTopScroll()
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

function makeTsOption(rows: TsPoint[]) {
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Total', 'Success', 'Avg time (s)'] },
    grid: { left: 40, right: 40, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: rows.map(r => r.day) },
    yAxis: [{ type: 'value', name: 'Builds' }, { type: 'value', name: 'Avg s' }],
    series: [
      { name: 'Total',   type: 'bar', data: rows.map(r => r.total) },
      { name: 'Success', type: 'bar', data: rows.map(r => r.success) },
      { name: 'Avg time (s)', type: 'line', yAxisIndex: 1, smooth: true,
        data: rows.map(r => r.avg_total ? Math.round(r.avg_total) : 0) },
    ],
  }
}
const tsFullOption = computed(() => makeTsOption(seriesFull.value))
const tsIncOption  = computed(() => makeTsOption(seriesInc.value))

const userOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 140, right: 30, top: 20, bottom: 30 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: userStats.value.map(u => u.user).reverse(), axisLabel: { width: 130, overflow: 'truncate' } },
  series: [{ type: 'bar', data: userStats.value.map(u => u.total).reverse(), itemStyle: { color: '#409eff' } }],
}))

const PLATFORM_COLORS: Record<string, string> = {
  'darwin-arm64': '#00d4ff',
  'darwin-x86_64': '#00a0c4',
  'mingw-x86_64': '#ff8c42',
  'mingw-arm64': '#ff6a00',
  'linux-x86_64': '#a78bfa',
  'linux-arm64': '#7c3aed',
}
const PLATFORM_FALLBACKS = ['#67c23a', '#f56c6c', '#e6a23c', '#909399', '#3aa1ff']

const platOption = computed(() => {
  let fbIdx = 0
  const data = platStats.value.map(p => {
    const color = PLATFORM_COLORS[p.platform] ?? PLATFORM_FALLBACKS[(fbIdx++) % PLATFORM_FALLBACKS.length]
    return { name: p.platform, value: p.total, itemStyle: { color } }
  })
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['40%', '70%'], data }],
  }
})

function fmtTs(ts: number | null) {
  if (ts == null) return '-'
  return new Date(ts * 1000).toLocaleString()
}
function fmtSec(s: number | null) {
  if (s == null) return '-'
  const r3 = (x: number) => Number(x.toFixed(1))
  if (s < 60) return `${r3(s)}s`
  const m = Math.floor(s / 60), sec = r3(s - m * 60)
  if (m < 60) return `${m}m${sec}s`
  const h = Math.floor(m / 60)
  return `${h}h${m % 60}m${sec}s`
}
function fmtCcSpace(used_kib: number | null, maxsz: string | null): string {
  if (used_kib == null && !maxsz) return '-'
  const used_g = used_kib != null ? (used_kib / 1024 / 1024) : null
  // parse '96GiB', '100G', '5000000K' etc -> GiB
  let max_g: number | null = null
  if (maxsz) {
    const m = maxsz.trim().match(/^(\d+(?:\.\d+)?)\s*([KMGT]i?B?)?$/i)
    if (m) {
      const n = parseFloat(m[1])
      const u = (m[2] || 'G').toUpperCase()
      const mult: Record<string, number> = {
        K: 1/1024/1024, KB: 1/1024/1024, KIB: 1/1024/1024,
        M: 1/1024, MB: 1/1024, MIB: 1/1024,
        G: 1, GB: 1, GIB: 1,
        T: 1024, TB: 1024, TIB: 1024,
      }
      max_g = n * (mult[u] ?? 1)
    }
  }
  if (used_g == null) return max_g != null ? `- / ${max_g.toFixed(0)}G` : '-'
  if (max_g == null) return `${used_g.toFixed(1)}G`
  const pct = max_g > 0 ? (used_g / max_g * 100) : 0
  return `${used_g.toFixed(1)} / ${max_g.toFixed(0)}G (${pct.toFixed(1)}%)`
}

function rowClass({ row }: { row: BuildRow }) {
  if (row.status === 'running') return 'row-running'
  if (row.exit_code === 0) return ''
  return row.exit_code === null ? '' : 'row-fail'
}
function statusType(s: string | null) {
  if (s === 'running') return 'warning'
  if (s === 'finished') return 'info'
  if (s === 'timeout') return 'info'
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
    <el-col :span="4"><StatCard label="Total"                     :value="summary?.total ?? '-'" /></el-col>
    <el-col :span="4"><StatCard label="All Builds Success rate"   :value="(summary?.success_rate ?? 0) + '%'" tone="ok" /></el-col>
    <el-col :span="4"><StatCard label="Full Builds Success rate"  :value="(summary?.full_builds_success_rate ?? 0) + '%'" tone="ok" /></el-col>
    <el-col :span="4"><StatCard label="All Failures"              :value="summary?.fail ?? '-'" tone="fail" /></el-col>
    <el-col :span="4"><StatCard label="Full Builds Failures"      :value="summary?.full_builds_failures ?? '-'" tone="fail" /></el-col>
    <el-col :span="4"><StatCard label="In-flight"                 :value="summary?.running ?? '-'" tone="warn" /></el-col>
  </el-row>
  <el-row :gutter="12" class="cards">
    <el-col :span="6"><StatCard label="Avg Full Builds - Total"   :value="fmtSec(summary?.avg_full_build_time ?? null)" /></el-col>
    <el-col :span="6"><StatCard label="Avg Full Builds - Ninja"   :value="fmtSec(summary?.avg_full_ninja_time ?? null)" /></el-col>
    <el-col :span="6"><StatCard label="Max Full Builds - Total"   :value="fmtSec(summary?.max_full_build_time ?? null)" /></el-col>
    <el-col :span="6"><StatCard label="Max Full Builds - Ninja"   :value="fmtSec(summary?.max_full_ninja_time ?? null)" /></el-col>
  </el-row>
  <el-row :gutter="12" class="cards">
    <el-col :span="6"><StatCard label="All RBE hit %"    :value="(summary?.rbe_hit_rate ?? 0) + '%'" tone="ok" /></el-col>
    <el-col :span="6"><StatCard label="Full Builds RBE hit %"   :value="(summary?.full_rbe_hit_rate ?? 0) + '%'" tone="ok" /></el-col>
    <el-col :span="6"><StatCard label="All ccache hit %" :value="(summary?.ccache_hit_rate ?? 0) + '%'" tone="ok" /></el-col>
    <el-col :span="6"><StatCard label="Full Builds ccache hit %":value="(summary?.full_ccache_hit_rate ?? 0) + '%'" tone="ok" /></el-col>
  </el-row>

  <el-row :gutter="12" class="charts">
    <el-col :span="14">
      <el-card><div class="chart-title">Full Builds per day</div><VChart :option="tsFullOption" autoresize style="height:300px" /></el-card>
    </el-col>
    <el-col :span="10">
      <el-card><div class="chart-title">Platform mix</div><VChart :option="platOption" autoresize style="height:300px" /></el-card>
    </el-col>
  </el-row>

  <el-row :gutter="12" class="charts">
    <el-col :span="12">
      <el-card><div class="chart-title">Incremental Builds per day</div><VChart :option="tsIncOption" autoresize style="height:300px" /></el-card>
    </el-col>
    <el-col :span="12">
      <el-card><div class="chart-title">All Builds per day</div><VChart :option="tsOption" autoresize style="height:300px" /></el-card>
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
        <el-option label="timeout" value="timeout" />
      </el-select>
      <el-select v-model="filters.exit_code" placeholder="exit" clearable size="small" style="width: 110px">
        <el-option label="success" value="0" />
        <el-option label="fail" value="1" />
      </el-select>
      <el-button size="small" @click="loadBuilds">Refresh</el-button>
    </div>

    <div class="top-scroll" ref="topScrollEl">
      <div :style="{ width: tableInnerWidth + 'px', height: '1px' }"></div>
    </div>
    <el-table ref="tableEl" :data="items" v-loading="loading" :row-class-name="rowClass"
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
      <el-table-column label="Exit" width="70">
        <template #default="{ row }: { row: BuildRow }">
          <el-tag v-if="row.exit_code !== null" size="small" :type="row.exit_code === 0 ? 'success' : 'danger'">
            {{ row.exit_code }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="Total" width="90">
        <template #default="{ row }: { row: BuildRow }">{{ fmtSec(row.total_time) }}</template>
      </el-table-column>
      <el-table-column label="Ninja" width="90">
        <template #default="{ row }: { row: BuildRow }">{{ fmtSec(row.ninja_time) }}</template>
      </el-table-column>
      <el-table-column label="LocalFB" width="90">
        <template #default="{ row }: { row: BuildRow }">{{ row.rbe_local_fallback ?? "-" }}</template>
      </el-table-column>
      <el-table-column label="LocalFail" width="90">
        <template #default="{ row }: { row: BuildRow }">{{ row.rbe_local_failures ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="Remote" width="90">
        <template #default="{ row }: { row: BuildRow }">{{ row.rbe_remote_executions ?? "-" }}</template>
      </el-table-column>
      <el-table-column label="RBE hits" width="100">
        <template #default="{ row }: { row: BuildRow }">
          {{ ((row.rbe_hits ?? 0) + (row.rbe_misses ?? 0)) === 0 ? '-' : (row.rbe_hits ?? 0) + '/' + ((row.rbe_hits ?? 0) + (row.rbe_misses ?? 0)) }}
        </template>
      </el-table-column>
      <el-table-column label="ccache hits" width="120">
        <template #default="{ row }: { row: BuildRow }">
          {{ ((row.ccache_direct_hit ?? 0) + (row.ccache_preproc_hit ?? 0) + (row.ccache_miss ?? 0)) === 0 ? '-' : ((row.ccache_direct_hit ?? 0) + (row.ccache_preproc_hit ?? 0)) + ' / ' + ((row.ccache_direct_hit ?? 0) + (row.ccache_preproc_hit ?? 0) + (row.ccache_miss ?? 0)) }}
        </template>
      </el-table-column>
      <el-table-column label="ccache space" width="180">
        <template #default="{ row }: { row: BuildRow }">{{ fmtCcSpace(row.ccache_size_kib, row.ccache_maxsize) }}</template>
      </el-table-column>
      <el-table-column prop="platform" label="Platform" width="120" />
      <el-table-column prop="build_type" label="Type" width="90" />
      <el-table-column prop="target" label="Target" min-width="160" show-overflow-tooltip />
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
.top-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  height: 12px;
  margin-bottom: 4px;
}
:deep(.el-table__row) { cursor: pointer; }
</style>
