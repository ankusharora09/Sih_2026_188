import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '@/lib/api'
import { Panel, PanelHead, Metric, Stamp, Skel, Empty, ErrorBox, Meter, Dot } from '@/components/ui'
import { fmtTime, shortId, riskMeta, STAGE_LABELS, cn } from '@/lib/utils'

export default function Dashboard() {
  const { data: analytics, isLoading: la, error: ea, refetch: ra } = useQuery({ queryKey: ['analytics'], queryFn: () => api.analytics(30) })
  const { data: events, isLoading: le } = useQuery({ queryKey: ['activity'], queryFn: () => api.activity(14), refetchInterval: 10_000 })

  if (ea) return <ErrorBox message={String((ea as Error).message)} retry={ra} />

  const dist = analytics?.risk_distribution || {}
  const total = Object.values(dist).reduce((a: number, b: any) => a + (b || 0), 0) || 1
  const risk = analytics?.average_risk_score ?? 0
  const riskTone = risk >= 60 ? 'bad' : risk >= 30 ? 'warn' : 'ok'
  const lat = analytics?.avg_stage_latency_ms || {}
  const conf = analytics?.avg_stage_confidence || {}
  const stageOrder = ['preprocessing', 'ocr', 'tampering_detection', 'face_verification', 'liveness_detection', 'deepfake_detection', 'anomaly_detection', 'risk_engine']

  return (
    <div className="space-y-4">
      {/* masthead */}
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-ink pb-3">
        <div>
          <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 01 / FORENSIC COMMAND</div>
          <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">Screening Command Center</h1>
          <p className="mt-1.5 font-mono text-[11px] uppercase tracking-[0.04em] text-dim">
            {analytics?.total_cases ?? '··'} CASES ON FILE · EVERY FIGURE FROM THE SCREENING DATABASE
          </p>
        </div>
        <Link to="/screening" className="border-2 border-ink bg-ink px-4 py-2.5 font-mono text-[11.5px] font-bold uppercase tracking-[0.12em] text-paper shadow-hard transition-colors hover:bg-dim">
          + NEW SCREENING
        </Link>
      </div>

      {/* KPI row */}
      {la ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => <Skel key={i} className="h-[92px]" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Metric label="Total Cases" value={analytics?.total_cases ?? 0} />
          <Metric label="Screened Runs" value={analytics?.screened_runs ?? 0} />
          <Metric label="Review Req." value={(dist.review_required ?? 0) + (dist.high ?? 0)} tone={(dist.review_required ?? 0) + (dist.high ?? 0) > 0 ? 'warn' : 'ok'} />
          <Metric label="Avg Risk Index" value={risk} decimals={1} tone={riskTone as any} />
          <Metric label="Avg Screening" value={analytics?.average_screening_seconds ?? 0} decimals={1} sub="SECONDS END-TO-END" />
          <Metric label="Face Verify" value={analytics?.avg_stage_latency_ms?.face_verification ?? 0} sub="MS / VERIFICATION" />
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        {/* pipeline table */}
        <Panel>
          <PanelHead no="02" title="AI Pipeline · Stage Profile" right={<Stamp tone="info">AVG LATENCY / CONFIDENCE</Stamp>} />
          <div className="grid md:grid-cols-2">
            {la && Array.from({ length: 6 }).map((_, i) => <div key={i} className="border-b border-rule-soft p-3"><Skel className="h-9" /></div>)}
            {!la && stageOrder.filter((k) => lat[k] != null).map((k, i) => (
              <motion.div key={k} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                className="flex items-center gap-3 border-b border-rule-soft px-3.5 py-2.5 last:border-0 md:odd:border-r md:[&:nth-last-child(2)]:border-r-0">
                <span className="sec-label">{String(i + 1).padStart(2, '0')}</span>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-mono text-[11.5px] font-semibold uppercase tracking-[0.06em]">{STAGE_LABELS[k]}</div>
                  <div className="mt-1 h-1.5 w-full bg-paper-2">
                    <motion.div className={cn('h-full', lat[k] > 400 ? 'bg-orange' : 'bg-ink')}
                      initial={{ width: 0 }} animate={{ width: `${Math.min(100, (lat[k] || 0) / 10)}%` }}
                      transition={{ duration: 0.5, ease: 'circOut' }} />
                  </div>
                </div>
                <div className="text-right font-mono text-[10.5px]">
                  <div className="font-bold">{lat[k]?.toFixed(0)}<span className="text-faint">MS</span></div>
                  <div className="text-faint">{conf[k] != null ? `${(conf[k] * 100).toFixed(0)}% CONF` : '—'}</div>
                </div>
              </motion.div>
            ))}
            {!la && Object.keys(lat).length === 0 && <div className="p-3 md:col-span-2"><Empty title="No pipeline data" hint="Run a screening to populate stage statistics." /></div>}
          </div>
        </Panel>

        {/* risk index module */}
        <Panel>
          <PanelHead no="03" title="Risk Index · Fleet" right={<Stamp tone={riskTone === 'bad' ? 'bad' : riskTone === 'warn' ? 'warn' : 'ok'}>{riskTone === 'bad' ? 'HIGH' : riskTone === 'warn' ? 'ELEVATED' : 'NOMINAL'}</Stamp>} />
          <div className="p-4">
            <div className="flex items-baseline gap-1">
              <span className={cn('font-grotesk text-[64px] font-black leading-none tracking-tight', riskTone === 'bad' ? 'text-red' : riskTone === 'warn' ? 'text-orange' : 'text-green')}>
                {String(Math.round(risk)).padStart(3, '0')}
              </span>
              <span className="font-mono text-[13px] text-faint">/100</span>
            </div>
            {/* threat scale */}
            <div className="mt-3 flex h-4 border-2 border-ink">
              <div className="flex-1 bg-green-soft" /><div className="flex-1 bg-orange-soft" /><div className="flex-1 bg-red-soft" />
              <motion.div className="absolute h-4 border-x-2 border-ink bg-ink/80" style={{ width: 2 }}
                initial={{ marginLeft: 0 }} animate={{ marginLeft: `calc(${Math.min(100, risk)}% - 1px)` }}
                transition={{ duration: 0.8, ease: 'circOut' }} />
            </div>
            <div className="mt-1 flex justify-between font-mono text-[8.5px] tracking-[0.1em] text-faint">
              <span>0 SAFE</span><span>50 ELEVATED</span><span>100 CRITICAL</span>
            </div>
            <div className="mt-5 space-y-2.5">
              {(['low', 'medium', 'high', 'review_required'] as const).map((k) => (
                <Meter key={k} value={(dist[k] || 0) / total * 100}
                  tone={k === 'low' ? 'ok' : k === 'medium' ? 'warn' : 'bad'}
                  label={riskMeta(k).label} right={String(dist[k] || 0)} />
              ))}
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        {/* volume */}
        <Panel>
          <PanelHead no="04" title="Screening Volume · 30 Days" right={<Stamp tone="neutral">CASES / DAY</Stamp>} />
          <div className="h-52 p-3">
            {la ? <Skel className="h-full" /> : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics?.daily_volume || []} margin={{ top: 6, right: 6, bottom: 0, left: -22 }}>
                  <defs>
                    <linearGradient id="volB" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#101010" stopOpacity={0.55} />
                      <stop offset="100%" stopColor="#101010" stopOpacity={0.03} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fill: '#8B877D', fontSize: 9.5, fontFamily: 'JetBrains Mono' }} tickFormatter={(d: string) => d.slice(5)} axisLine={{ stroke: '#101010' }} tickLine={false} />
                  <YAxis tick={{ fill: '#8B877D', fontSize: 9.5, fontFamily: 'JetBrains Mono' }} allowDecimals={false} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#fff', border: '2px solid #101010', borderRadius: 0, fontSize: 11, fontFamily: 'JetBrains Mono' }} />
                  <Area type="stepAfter" dataKey="cases" stroke="#101010" strokeWidth={2} fill="url(#volB)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </Panel>

        {/* live feed */}
        <Panel>
          <PanelHead no="05" title="Event Feed" right={<Stamp tone="ok"><Dot className="bg-green" /> LIVE</Stamp>} />
          <div className="max-h-64 overflow-auto">
            {le && <div className="space-y-2 p-3">{Array.from({ length: 5 }).map((_, i) => <Skel key={i} className="h-9" />)}</div>}
            {!le && (events?.length ?? 0) === 0 && <Empty title="No events" hint="Audit events appear as cases are processed." />}
            {!le && events?.map((ev, i) => (
              <motion.div key={ev.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }}
                className="flex items-center gap-2.5 border-b border-rule-soft px-3 py-2 last:border-0">
                <span className={cn('h-2 w-2 shrink-0 border border-ink',
                  (ev.action || ev.event_type || '').includes('fail') ? 'bg-red' : (ev.action || ev.event_type || '').includes('decision') ? 'bg-orange' : 'bg-green')} />
                <span className="min-w-0 flex-1 truncate font-mono text-[10.5px] font-semibold uppercase tracking-[0.04em]">
                  {(ev.action || ev.event_type || 'event').replace(/_/g, ' ')}
                </span>
                <span className="font-mono text-[9.5px] text-faint">{fmtTime(ev.timestamp)}</span>
                {ev.case_id && <span className="font-mono text-[9.5px] text-dim">{shortId(ev.case_id, 6)}</span>}
              </motion.div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
