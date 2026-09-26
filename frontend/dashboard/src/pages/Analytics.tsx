import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar as RBar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '@/lib/api'
import { Panel, PanelHead, Metric, Stamp, Empty, ErrorBox, Skel, Meter } from '@/components/ui'
import { riskMeta, cn, STAGE_LABELS } from '@/lib/utils'

const TOOLTIP = { background: '#fff', border: '2px solid #101010', borderRadius: 0, fontSize: 11, fontFamily: 'JetBrains Mono' }

export default function Analytics() {
  const [days, setDays] = useState(30)
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['analytics', days], queryFn: () => api.analytics(days) })

  if (error) return <ErrorBox message={String((error as Error).message)} retry={refetch} />

  const dist = data?.risk_distribution || {}
  const lat = data?.avg_stage_latency_ms || {}
  const conf = data?.avg_stage_confidence || {}
  const stageRows = Object.keys(lat).map((k) => ({ stage: (STAGE_LABELS[k] || k).toUpperCase(), ms: lat[k] }))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-ink pb-3">
        <div>
          <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 06 / REPORTS</div>
          <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">Analytics</h1>
          <p className="mt-1.5 font-mono text-[10.5px] uppercase tracking-[0.04em] text-dim">COMPILED FROM REAL SCREENING ROWS · NO SAMPLED DATA</p>
        </div>
        <select value={days} onChange={(e) => setDays(+e.target.value)} aria-label="Time window"
          className="border-2 border-ink bg-panel px-2 py-1.5 font-mono text-[11px] uppercase outline-none">
          <option value={7}>7 DAYS</option><option value={30}>30 DAYS</option><option value={90}>90 DAYS</option>
        </select>
      </div>

      {isLoading ? <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">{Array.from({ length: 6 }).map((_, i) => <Skel key={i} className="h-[92px]" />)}</div> : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Metric label="Cases" value={data?.total_cases ?? 0} />
          <Metric label="Screened Runs" value={data?.screened_runs ?? 0} />
          <Metric label="Avg Risk" value={data?.average_risk_score ?? 0} decimals={1} />
          <Metric label="Avg Duration" value={data?.average_screening_seconds ?? 0} decimals={1} sub="SECONDS" />
          <Metric label="Review Req." value={dist.review_required ?? 0} tone={(dist.review_required ?? 0) > 0 ? 'warn' : 'ok'} />
          <Metric label="High Risk" value={dist.high ?? 0} tone={(dist.high ?? 0) > 0 ? 'bad' : 'ok'} />
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <PanelHead no="A1" title="Risk Mix" right={<Stamp tone="neutral">{days}-DAY WINDOW</Stamp>} />
          <div className="space-y-3 p-4">
            {(['low', 'medium', 'high', 'review_required'] as const).map((k) => {
              const total = Object.values(dist).reduce((a: number, b: any) => a + (b || 0), 0) || 1
              return (
                <Meter key={k} value={(dist[k] || 0) / total * 100}
                  tone={k === 'low' ? 'ok' : k === 'medium' ? 'warn' : 'bad'}
                  label={riskMeta(k).label} right={String(dist[k] || 0)} />
              )
            })}
          </div>
        </Panel>

        <Panel>
          <PanelHead no="A2" title="Daily Volume" right={<Stamp tone="neutral">CASES / DAY</Stamp>} />
          <div className="h-56 p-3">
            {(data?.daily_volume || []).length === 0 ? <Empty title="No data in window" /> : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.daily_volume || []} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
                  <CartesianGrid stroke="#C8C4BA" strokeDasharray="2 4" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: '#8B877D', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickFormatter={(d: string) => d.slice(5)} axisLine={{ stroke: '#101010' }} tickLine={false} />
                  <YAxis tick={{ fill: '#8B877D', fontSize: 9, fontFamily: 'JetBrains Mono' }} allowDecimals={false} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP} cursor={{ fill: 'rgba(16,16,16,0.05)' }} />
                  <RBar dataKey="cases" fill="#101010" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHead no="A3" title="Stage Latency" right={<Stamp tone="neutral">AVG MS</Stamp>} />
          <div className="h-64 p-3">
            {stageRows.length === 0 ? <Empty title="No timing data" hint="Timings appear after the first screening run." /> : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stageRows} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 30 }}>
                  <CartesianGrid stroke="#C8C4BA" strokeDasharray="2 4" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#8B877D', fontSize: 9, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#101010' }} tickLine={false} />
                  <YAxis type="category" dataKey="stage" width={120} tick={{ fill: '#101010', fontSize: 9, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP} cursor={{ fill: 'rgba(16,16,16,0.05)' }} />
                  <RBar dataKey="ms" fill="#D9202C" barSize={13} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHead no="A4" title="Confidence Register" right={<Stamp tone="ink">WHERE REPORTED</Stamp>} />
          <div className="p-4">
            {Object.keys(conf).length === 0 ? (
              <Empty title="No confidence data" hint="Stages report confidence as they run." />
            ) : Object.entries(conf).map(([k, v]: any) => (
              <div key={k} className="mb-2.5 last:mb-0">
                <Meter value={v * 100} tone={v >= 0.7 ? 'ok' : v >= 0.4 ? 'warn' : 'bad'}
                  label={(STAGE_LABELS[k] || k).toUpperCase()} right={`${(v * 100).toFixed(0)}%`} />
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
