import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { Panel, PanelHead, Stamp, Empty, ErrorBox, Skel, Dot } from '@/components/ui'
import { fmtTime, cn } from '@/lib/utils'

const COMPONENTS = [
  { key: 'api', label: 'API GATEWAY' },
  { key: 'database', label: 'DATABASE' },
  { key: 'ocr', label: 'OCR ENGINE' },
  { key: 'face', label: 'FACE ENGINE' },
  { key: 'risk', label: 'RISK ENGINE' },
  { key: 'ledger', label: 'AUDIT LEDGER' },
]

function statusOf(health: any, key: string): 'ok' | 'degraded' | 'down' {
  const c = health?.components?.[key] ?? health?.[key]
  if (c == null) return 'ok'
  const s = String(c.status || c).toLowerCase()
  return s.includes('operational') || s === 'ok' || s === 'up' ? 'ok' : s.includes('degrad') ? 'degraded' : 'down'
}

export default function SystemHealth() {
  const { data: health, isLoading, error, refetch } = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 15_000 })
  const { data: events } = useQuery({ queryKey: ['sys-events'], queryFn: () => api.activity(30), refetchInterval: 8_000 })

  if (error) return <ErrorBox message={String((error as Error).message)} retry={refetch} />

  return (
    <div className="space-y-4">
      <div className="border-b-2 border-ink pb-3">
        <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 07 / SYSTEM</div>
        <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">System Board</h1>
        <p className="mt-1.5 font-mono text-[10.5px] uppercase tracking-[0.04em] text-dim">LIVE COMPONENT STATUS FROM THE HEALTH ENDPOINT</p>
      </div>

      {isLoading ? <div className="grid grid-cols-2 gap-3 md:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skel key={i} className="h-24" />)}</div> : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {COMPONENTS.map((c) => {
            const st = statusOf(health, c.key)
            return (
              <Panel key={c.key} className={cn(st === 'down' && 'border-red', st === 'degraded' && 'border-orange')}>
                <div className="flex items-center justify-between border-b-2 border-ink px-3 py-1.5">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-[0.12em]">{c.label}</span>
                  <Stamp tone={st === 'ok' ? 'ok' : st === 'degraded' ? 'warn' : 'bad'}>
                    <Dot className={cn(st === 'ok' ? 'bg-green' : st === 'degraded' ? 'bg-orange' : 'bg-red animate-pulse')} />
                    {st.toUpperCase()}
                  </Stamp>
                </div>
                <div className="px-3 py-2.5 font-mono text-[9.5px] leading-relaxed text-dim">
                  {health?.components?.[c.key]?.model || health?.[c.key]?.model || 'MONITORED VIA /HEALTH'}
                  {health?.components?.[c.key]?.note && <><br />{String(health.components[c.key].note).toUpperCase()}</>}
                </div>
              </Panel>
            )
          })}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Panel>
          <PanelHead no="S1" title="Stage Timings" right={<Stamp tone="neutral">AVG MS</Stamp>} />
          <div className="grid grid-cols-2 gap-2 p-3.5 sm:grid-cols-3">
            {Object.entries(health?.stage_latency_ms || {}).slice(0, 9).map(([k, v]: any) => (
              <div key={k} className="border-2 border-ink px-3 py-2.5">
                <div className="truncate font-mono text-[9.5px] uppercase tracking-[0.08em] text-dim">{k.replace(/_/g, ' ')}</div>
                <div className="mt-0.5 font-grotesk text-[20px] font-black leading-none">{v}<span className="ml-1 font-mono text-[9px] text-faint">MS</span></div>
              </div>
            ))}
            {!Object.keys(health?.stage_latency_ms || {}).length && <div className="col-span-full"><Empty title="No stage timings" /></div>}
          </div>
        </Panel>

        <Panel>
          <PanelHead no="S2" title="Event Stream" right={<Stamp tone="ok"><Dot className="bg-green" /> LIVE</Stamp>} />
          <div className="max-h-80 overflow-auto">
            {!events?.length && <Empty title="Quiet" hint="No recent events." />}
            {events?.map((ev: any) => (
              <motion.div key={ev.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex items-baseline gap-2.5 border-b border-rule-soft px-3 py-1.5 font-mono text-[10px] last:border-0">
                <span className="text-faint">{fmtTime(ev.timestamp)}</span>
                <span className={cn('font-bold uppercase', (ev.action || '').includes('fail') ? 'text-red' : '')}>{(ev.action || '').replace(/_/g, ' ')}</span>
              </motion.div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
