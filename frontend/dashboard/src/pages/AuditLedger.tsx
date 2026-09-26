import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { Panel, PanelHead, Stamp, Btn, Empty, ErrorBox, Skel } from '@/components/ui'
import { fmtDateTime, shortHash, cn } from '@/lib/utils'

export default function AuditLedger() {
  const { data: events, isLoading, error, refetch } = useQuery({ queryKey: ['global-audit'], queryFn: () => api.activity(80) })
  const [verifying, setVerifying] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, boolean>>({})

  const verify = async (caseId: string) => {
    setVerifying(caseId)
    try {
      const res = await api.verifyChain(caseId)
      const ok = res?.valid !== false && res?.status !== 'invalid'
      setResults((r) => ({ ...r, [caseId]: ok }))
    } catch { setResults((r) => ({ ...r, [caseId]: false })) } finally { setVerifying(null) }
  }

  if (error) return <ErrorBox message={String((error as Error).message)} retry={refetch} />

  const byCase = new Map<string, any[]>()
  for (const ev of events || []) {
    if (!ev.case_id) continue
    if (!byCase.has(ev.case_id)) byCase.set(ev.case_id, [])
    byCase.get(ev.case_id)!.push(ev)
  }
  const cases = [...byCase.entries()].slice(0, 10)

  return (
    <div className="space-y-4">
      <div className="border-b-2 border-ink pb-3">
        <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 05 / INTEGRITY</div>
        <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">Tamper-Evident Audit Ledger</h1>
        <p className="mt-2 max-w-3xl font-mono text-[10.5px] uppercase leading-relaxed tracking-[0.03em] text-dim">
          Each event is sealed with the previous event's hash. Verification re-computes the entire chain —
          any historical modification breaks it. The ledger proves logs are unmodified; it does not assert a document is genuine.
        </p>
      </div>

      {/* chains */}
      <Panel>
        <PanelHead no="C1" title="Chains by Case" right={<Stamp tone="ink">HASH-SEALED</Stamp>} />
        {isLoading ? (
          <div className="space-y-2 p-3">{Array.from({ length: 4 }).map((_, i) => <Skel key={i} className="h-16" />)}</div>
        ) : cases.length === 0 ? (
          <Empty title="No audit events yet" hint="Events appear as cases are created and screened." />
        ) : (
          <div className="divide-y-2 divide-rule-soft">
            {cases.map(([cid, evs]) => {
              const checked = results[cid]
              return (
                <div key={cid} className="p-3.5">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="sec-label">BLOCK 0</span>
                    <span className="font-mono text-[11.5px] font-bold">{shortHash(cid, 12)}</span>
                    <Stamp tone="neutral">{evs.length} EVENTS</Stamp>
                    {checked === true && <Stamp tone="ok">✓ CHAIN VERIFIED</Stamp>}
                    {checked === false && <Stamp tone="bad">✗ COMPROMISED</Stamp>}
                    <Btn className="ml-auto px-2 py-0.5 text-[9.5px]" disabled={verifying === cid} onClick={() => verify(cid)}>
                      {verifying === cid ? 'VERIFYING…' : 'VERIFY INTEGRITY'}
                    </Btn>
                  </div>
                  {/* block strip */}
                  <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1">
                    {evs.slice(0, 16).map((ev: any, i: number) => (
                      <motion.div key={ev.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.015 }}
                        title={`${(ev.action || '').replace(/_/g, ' ')} · ${fmtDateTime(ev.timestamp)} · HASH ${shortHash(ev.hash, 12)}`}
                        className="group relative h-10 w-10 shrink-0 cursor-help border-2 border-ink bg-paper transition-transform hover:-translate-y-0.5">
                        <span className="absolute inset-x-0 top-0.5 text-center font-mono text-[8px] font-bold text-dim">{String(i + 1).padStart(2, '0')}</span>
                        <span className="absolute inset-x-0 bottom-1 text-center font-mono text-[7px] text-faint">#{shortHash(ev.hash, 4)}</span>
                      </motion.div>
                    ))}
                    {evs.length > 16 && <span className="grid h-10 place-items-center px-2 font-mono text-[9.5px] text-faint">+{evs.length - 16}</span>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Panel>

      {/* raw stream */}
      <Panel>
        <PanelHead no="C2" title="Event Stream" right={<Stamp tone="neutral">NEWEST FIRST</Stamp>} />
        <div className="max-h-[400px] overflow-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead className="sticky top-0 bg-paper-2">
              <tr className="border-b-2 border-ink font-mono text-[9.5px] uppercase tracking-[0.16em] text-dim">
                <th className="px-3.5 py-2 font-semibold">TIME</th>
                <th className="px-3.5 py-2 font-semibold">EVENT</th>
                <th className="px-3.5 py-2 font-semibold">CASE</th>
                <th className="px-3.5 py-2 font-semibold">HASH</th>
              </tr>
            </thead>
            <tbody>
              {(events || []).map((ev: any) => (
                <tr key={ev.id} className="border-b border-rule-soft last:border-0 hover:bg-paper-2">
                  <td className="whitespace-nowrap px-3.5 py-2 font-mono text-[10px] text-dim">{fmtDateTime(ev.timestamp)}</td>
                  <td className={cn('px-3.5 py-2 font-mono text-[10.5px] font-bold uppercase', (ev.action || '').includes('fail') ? 'text-red' : '')}>
                    {(ev.action || '').replace(/_/g, ' ')}
                  </td>
                  <td className="px-3.5 py-2 font-mono text-[10px]">{ev.case_id ? shortHash(ev.case_id, 8) : '—'}</td>
                  <td className="px-3.5 py-2 font-mono text-[9px] text-faint">{shortHash(ev.hash, 14)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
