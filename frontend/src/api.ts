const BASE = ''

async function http<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export interface BuildRow {
  id: number
  ts: number
  started_ts: number | null
  finished_ts: number | null
  status: string | null
  user_email: string | null
  platform: string | null
  build_type: string | null
  browser_type: string | null
  target: string | null
  total_time: number | null
  ninja_time: number | null
  exit_code: number | null
  reclient_enabled: number | null
  rbe_hits: number | null
  rbe_misses: number | null
  rbe_remote_executions: number | null
  rbe_local_fallback: number | null
  rbe_local_failures: number | null
  ccache_direct_hit: number | null
  ccache_miss: number | null
}

export interface BuildList {
  total: number
  items: BuildRow[]
}

export interface Summary {
  days: number
  total: number
  success: number
  fail: number
  running: number
  success_rate: number
  avg_total_time: number
  avg_ninja_time: number
  rbe_hit_rate: number
  ccache_hit_rate: number
}

export interface TsPoint { day: string; total: number; success: number; avg_total: number }
export interface UserStat { user: string; total: number; success: number; avg_total: number }
export interface PlatStat { platform: string; total: number }

export const api = {
  summary:    (days = 30)  => http<Summary>(`/api/stats/summary?days=${days}`),
  timeseries: (days = 14) => http<TsPoint[]>(`/api/stats/timeseries?days=${days}`),
  byUser:     (days = 14) => http<UserStat[]>(`/api/stats/by_user?days=${days}`),
  byPlatform: (days = 14) => http<PlatStat[]>(`/api/stats/by_platform?days=${days}`),
  distinct:   ()          => http<{ users: string[]; platforms: string[] }>(`/api/stats/distinct`),
  builds: (params: Record<string, string | number | undefined>) => {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
    }
    return http<BuildList>(`/api/builds?${q.toString()}`)
  },
  build: (id: number) => http<Record<string, unknown>>(`/api/builds/${id}`),
}
