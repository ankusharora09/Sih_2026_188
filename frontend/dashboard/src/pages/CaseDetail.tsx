import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, fetchBlob } from '@/lib/api'
import { Panel, PanelHead, Stamp, Btn, Empty, ErrorBox, Skel, Dot } from '@/components/ui'
import { fmtDateTime, fmtTime, shortHash, riskMeta, STAGE_LABELS, fmtMs, verifyLabel, decisionLabel, cn } from '@/lib/utils'
import { useApp } from '@/App'

/** Module 1+2+3 evidence: document type, extracted fields, validation verdicts, metadata. */
function ValidationSummary({ ocrResult, tamperingResult }: { ocrResult?: any; tamperingResult?: any }) {
  const val = ocrResult?.validation
  const meta = tamperingResult?.metadata
  if (!val && !meta) return null
  const vTone = val?.summary?.verdict === 'pass' ? 'ok' : val?.summary?.verdict === 'fail' ? 'bad' : 'warn'
  const mTone = meta?.risk_level === 'high' ? 'bad' : meta?.risk_level === 'medium' || meta?.risk_level === 'low' ? 'warn' : 'ok'
  const fields = Object.entries(val?.fields || {}).filter(([, v]) => v != null && v !== false)
  // Fields graded ok-but-fuzzy show LOW CONFIDENCE, never MISSING.
  const lowConf = new Set((val?.checks || []).filter((c: any) => c.low_confidence && c.status === 'ok').map((c: any) => c.field))
  return (
    <div className="space-y-2 border-b-2 border-ink bg-paper p-3.5">
      <div className="flex flex-wrap items-center gap-1.5">
        {val && <Stamp tone="ink">{String(val.document_type || 'unknown').replace(/_/g, ' ')}</Stamp>}
        {val && <Stamp tone={vTone as any}>VALIDATION {String(val.summary?.verdict || '—').toUpperCase()}</Stamp>}
        {meta?.risk_level && <Stamp tone={mTone as any}>METADATA {String(meta.risk_level).toUpperCase()}</Stamp>}
      </div>
      {fields.length > 0 && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono text-[10.5px] md:grid-cols-3">
          {fields.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-2">
              <span className="text-dim">{String(k).replace(/_/g, ' ')}</span>
              <span className="flex min-w-0 items-center gap-1">
                {lowConf.has(String(k)) && <span className="shrink-0 border border-orange px-1 font-mono text-[8px] uppercase text-orange">low conf</span>}
                <span className="truncate font-bold">{String(v).replace(/\?$/, '')}</span>
              </span>
            </div>
          ))}
        </div>
      )}
      {(val?.checks || []).some((c: any) => c.status !== 'ok' || c.low_confidence) && (
        <div className="flex flex-wrap gap-1.5">
          {val.checks.filter((c: any) => c.status !== 'ok' || c.low_confidence).map((c: any, i: number) => (
            <Stamp key={i} tone={c.low_confidence && c.status === 'ok' ? 'warn' : c.status === 'missing' ? 'neutral' : 'bad'}>
              {c.field.replace(/_/g, ' ')} {(c.low_confidence && c.status === 'ok' ? 'low confidence' : c.status).replace(/_/g, ' ')}
            </Stamp>
          ))}
        </div>
      )}
      {meta?.signals?.length > 0 && (
        <p className="font-mono text-[9.5px] leading-relaxed text-dim">EXIF: {meta.signals.join(' · ')}</p>
      )}
    </div>
  )
}

function StageRow({ idx, stage }: { idx: number; stage: any }) {
  const [open, setOpen] = useState(false)
  const notRun = stage.status === 'skipped' || stage.status === 'unavailable'
  const tone = stage.status === 'success' ? 'ok' : stage.status === 'failed' ? 'bad' : 'neutral'
  const label = stage.status === 'success' ? 'PASSED' : stage.status === 'failed' ? 'FAILED' : notRun ? 'NOT RUN' : String(stage.status).toUpperCase()
  const meta = stage.metadata || stage.meta || {}
  const model = meta.model || meta.model_name || meta.engine || meta.adapter
  return (
    <div className="border-b border-rule-soft last:border-0">
      <button className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left hover:bg-paper-2" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="sec-label">{String(idx + 1).padStart(2, '0')}</span>
        <span className="min-w-0 flex-1 truncate font-mono text-[11px] font-bold uppercase tracking-[0.06em]">{STAGE_LABELS[stage.stage] || stage.stage}</span>
        {model && <span className="hidden font-mono text-[9px] text-dim sm:inline">{String(model)}</span>}
        {stage.processing_time_ms != null
          ? <span className="font-mono text-[10px] text-dim">{fmtMs(stage.processing_time_ms)}</span>
          : <span className="font-mono text-[10px] text-faint">—</span>}
        <Stamp tone={tone as any}>{label}</Stamp>
      </button>
      {/* NOT RUN stages always show their reason — never silently gray. */}
      {notRun && (stage.result?.reason || stage.errors) && (
        <p className="border-t border-rule-soft bg-paper-2 px-3.5 py-1.5 font-mono text-[9.5px] uppercase tracking-[0.06em] text-dim">
          REASON: {String(stage.result?.reason || stage.errors).slice(0, 140)}
        </p>
      )}
      {open && (
        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="overflow-hidden border-t border-rule-soft bg-paper">
          <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-[9.5px] leading-relaxed text-dim">
            {JSON.stringify(stage.result ?? stage.errors ?? {}, null, 2)}
          </pre>
        </motion.div>
      )}
    </div>
  )
}

export default function CaseDetail() {
  const { caseId } = useParams()
  const { toast } = useApp()
  const qc = useQueryClient()
  const [docUrl, setDocUrl] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const { data: detail, isLoading, error, refetch } = useQuery({ queryKey: ['case', caseId], queryFn: () => api.caseDetail(caseId!), enabled: !!caseId })
  const { data: run } = useQuery({ queryKey: ['run', caseId], queryFn: () => api.latestRun(caseId!), enabled: !!caseId, retry: false })
  const { data: audit } = useQuery({ queryKey: ['audit', caseId], queryFn: () => api.caseAudit(caseId!), enabled: !!caseId })

  useEffect(() => {
    let dead = false
    const f = detail?.files?.[0]
    if (caseId && f?.file_id) {
      fetchBlob(api.fileContentUrl(caseId, f.file_id))
        .then((u) => { if (!dead) setDocUrl(u) })
        .catch(() => { if (!dead) setDocUrl(null) })
    } else { setDocUrl(null) }
    return () => { dead = true }
  }, [caseId, detail?.files?.[0]?.file_id])

  if (error) return <ErrorBox message={String((error as Error).message)} retry={refetch} />
  if (isLoading) return <div className="space-y-3">{[...Array(4)].map((_, i) => <Skel key={i} className="h-24" />)}</div>

  const stages = run?.stage_results || []
  const riskStage = stages.find((s: any) => s.stage === 'risk_engine')?.result || {}
  const risk = detail?.risk_level
  const score = riskStage.risk_score
  const details = riskStage.contribution_details || []
  // Officer-facing evidence lists, with a legacy-run fallback.
  const factors: any[] = riskStage.risk_factors
    || details.filter((d: any) => !['skipped', 'unavailable', 'failed'].includes(d.status))
      .map((d: any) => ({ signal: d.signal, contribution: d.contribution, text: String(d.officer_reason || d.reason || '').replace(/_/g, ' ') }))
  const gaps: any[] = riskStage.verification_gaps
    || details.filter((d: any) => ['skipped', 'unavailable', 'failed'].includes(d.status))
      .map((d: any) => ({ signal: d.signal, status: d.status, text: String(d.officer_reason || d.reason || '').replace(/_/g, ' ') }))
  const review = riskStage.review_required
  const riskBadge = String(risk || '').toLowerCase().includes('review') ? 'warn' : risk === 'low' ? 'ok' : risk === 'medium' ? 'warn' : risk === 'high' ? 'bad' : 'neutral'

  const decide = async (action: string) => {
    setBusy(true)
    try {
      const res = await api.decision(caseId!, action, 'Decided from investigation workspace')
      toast(`DECISION RECORDED: ${res.status}`, 'ok')
      refetch()
      qc.invalidateQueries({ queryKey: ['audit', caseId] })
    } catch (e: any) { toast(e.message, 'err') } finally { setBusy(false) }
  }

  const verifyChain = async () => {
    try {
      const res = await api.verifyChain(caseId!)
      const ok = res?.valid !== false && res?.status !== 'invalid'
      toast(ok ? 'CHAIN VERIFIED' : 'CHAIN COMPROMISED', ok ? 'ok' : 'err')
    } catch (e: any) { toast(e.message, 'err') }
  }

  return (
    <div className="space-y-4">
      <Link to="/cases" className="inline-block border-2 border-ink bg-panel px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-[0.1em] shadow-hard-sm hover:bg-paper-2">← REGISTER</Link>

      {/* case header */}
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-4 p-4">
          <div>
            <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">CASE FILE / {String(caseId || '').slice(0, 8).toUpperCase()}</div>
            <h1 className="mt-1 font-grotesk text-[26px] font-black uppercase leading-none tracking-tight">{detail?.subject_name || 'UNNAMED SUBJECT'}</h1>
            <p className="mt-1.5 font-mono text-[10.5px] text-dim">
              ID {caseId} · OPENED {fmtDateTime(detail?.created_at)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Stamp tone={riskBadge as any}>{riskMeta(risk).label}</Stamp>
            {review && detail?.status !== risk && <Stamp tone="warn">OFFICER REVIEW PENDING</Stamp>}
            <Stamp tone={detail?.status === 'verified' ? 'ok' : detail?.status === 'rejected' ? 'bad' : 'neutral'}>
              {(detail?.status || '—').replace(/_/g, ' ')}
            </Stamp>
            {score != null && (
              <div className="border-2 border-ink px-2.5 py-1">
                <span className="font-mono text-[8.5px] tracking-[0.14em] text-dim">INDEX </span>
                <span className={cn('font-grotesk text-[20px] font-black leading-none', score >= 60 ? 'text-red' : score >= 30 ? 'text-orange' : 'text-green')}>{String(score).padStart(3, '0')}</span>
                <span className="font-mono text-[10px] text-faint">/100</span>
              </div>
            )}
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          {/* evidence */}
          <Panel>
            <PanelHead no="E1" title="Document Evidence" right={
              <div className="flex items-center gap-2">
                {/* BUG 2: presentation-only label — demo data, never a real government document. */}
                <Stamp tone="warn">SYNTHETIC / DEMO DOCUMENT</Stamp>
                <Stamp tone="neutral">AUTHORIZED FETCH · HASH SEALED</Stamp>
              </div>
            } />
            <ValidationSummary ocrResult={stages.find((s: any) => s.stage === 'ocr')?.result} tamperingResult={stages.find((s: any) => s.stage === 'tampering_detection')?.result} />
            <div className="grid gap-4 p-4 sm:grid-cols-[230px_1fr]">
              {docUrl ? (
                <img src={docUrl} alt="Document" className="max-h-52 w-full border-2 border-ink object-contain" />
              ) : (
                <div className="grid h-40 place-items-center border-2 border-dashed border-rule-soft font-mono text-[10px] uppercase tracking-[0.14em] text-faint">NO PREVIEW</div>
              )}
              <div className="space-y-2">
                {(detail?.files || []).map((f: any) => (
                  <div key={f.file_id} className="border border-ink bg-paper px-3 py-2">
                    <div className="flex items-center justify-between gap-2 font-mono text-[10.5px] font-bold">
                      <span className="truncate">{f.filename}</span>
                      <Stamp tone="neutral">{f.file_type}</Stamp>
                    </div>
                    <div className="mt-1 font-mono text-[9.5px] text-dim">SHA256 {shortHash(f.content_hash, 20)} · {f.size_bytes ? `${(f.size_bytes / 1024).toFixed(1)} KB` : '—'}</div>
                  </div>
                ))}
                {!detail?.files?.length && <p className="font-mono text-[10.5px] uppercase text-faint">NO FILES ATTACHED</p>}
              </div>
            </div>
          </Panel>

          {/* stages dossier */}
          <Panel>
            <PanelHead no="E2" title="AI Stage Dossier" right={<span className="font-mono text-[9.5px] tracking-[0.1em] text-dim">{stages.length} STAGES · CLICK FOR RAW EVIDENCE</span>} />
            {stages.length === 0 ? (
              <div className="p-4"><Empty title="Not screened" hint="Run screening from the bench to populate AI findings."
                action={<Link to="/screening" className="font-mono text-[11px] font-bold uppercase underline">OPEN SCREENING →</Link>} /></div>
            ) : stages.map((s: any, i: number) => <StageRow key={s.stage} idx={i} stage={s} />)}
          </Panel>
        </div>

        {/* right rail */}
        <div className="space-y-4">
          {/* risk index */}
          <Panel className={cn(riskBadge === 'bad' && 'border-red', riskBadge === 'warn' && 'border-orange')}>
            <PanelHead no="R1" title="Risk Assessment" right={
              <span className="flex items-center gap-1.5">
                {riskStage.verification && <Stamp tone="neutral">{riskStage.verification.executed_count} / {riskStage.verification.total} VERIFIED</Stamp>}
                <Stamp tone={riskBadge as any}>{riskMeta(risk).label}</Stamp>
              </span>
            } />
            <div className="p-3.5">
              {score != null && (
                <div className="mb-3 flex items-baseline gap-1">
                  <span className={cn('font-grotesk text-[52px] font-black leading-none tracking-tight', score >= 60 ? 'text-red' : score >= 30 ? 'text-orange' : 'text-green')}>{String(score).padStart(3, '0')}</span>
                  <span className="font-mono text-[12px] text-faint">/100</span>
                </div>
              )}
              {/* BUG 5: confidence / verification / decision kept separate from the risk index. */}
              <div className="mb-3 grid grid-cols-3 gap-2 border-2 border-ink bg-paper px-2.5 py-2">
                <div>
                  <div className="font-mono text-[8.5px] tracking-[0.12em] text-dim">CONFIDENCE</div>
                  <div className="font-grotesk text-[15px] font-black leading-tight">{riskStage.confidence_score != null ? `${riskStage.confidence_score}%` : '—'}</div>
                </div>
                <div>
                  <div className="font-mono text-[8.5px] tracking-[0.12em] text-dim">VERIFICATION</div>
                  <div className="font-grotesk text-[15px] font-black leading-tight">{riskStage.verification ? `${riskStage.verification.executed_count} / ${riskStage.verification.total}` : '—'}</div>
                </div>
                <div>
                  <div className="font-mono text-[8.5px] tracking-[0.12em] text-dim">DECISION</div>
                  <div className="font-grotesk text-[15px] font-black leading-tight">{decisionLabel(riskStage.decision_status)}</div>
                </div>
              </div>
              <div className="space-y-2">
                {factors.length === 0 && gaps.length === 0 && <p className="font-mono text-[10.5px] uppercase text-faint">NO FACTORS RECORDED</p>}
                {factors.map((f: any, i: number) => (
                  <div key={i} className="flex items-start justify-between gap-2 border-b border-rule-soft pb-1.5 last:border-0">
                    <div className="min-w-0">
                      <div className="font-mono text-[10.5px] font-bold uppercase tracking-[0.06em]">{String(f.signal || 'factor').replace(/_/g, ' ')}</div>
                      <p className="mt-0.5 font-mono text-[9.5px] leading-relaxed text-dim">{String(f.text || '—').slice(0, 110)}</p>
                    </div>
                    <span className={cn('shrink-0 font-mono text-[11px] font-bold', (f.contribution || 0) > 0 ? 'text-red' : 'text-faint')}>
                      {(f.contribution || 0) > 0 ? `+${Number(f.contribution).toFixed(2)}` : '—'}
                    </span>
                  </div>
                ))}
                {gaps.length > 0 && (
                  <div className="border border-rule-soft bg-paper-2 px-2.5 py-2">
                    <div className="font-mono text-[9px] tracking-[0.14em] text-dim">VERIFICATION GAPS · NOT COUNTED AS FRAUD</div>
                    <ul className="mt-1 space-y-0.5">
                      {gaps.map((g: any, i: number) => (
                        <li key={i} className="font-mono text-[9.5px] leading-snug text-dim">· {String(g.text || g.signal)}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </Panel>

          {/* WHY REVIEW — plain-language reasons for the human decision (BUG 5). */}
          {review && (() => {
            const reasons: string[] = []
            for (const f of riskStage.missing_mandatory_fields || []) {
              reasons.push(`${String(f).replace(/_/g, ' ').toUpperCase()} is a mandatory identity field and was not extracted — officer must validate it`)
            }
            for (const g of gaps) reasons.push(String(g.text || g.signal))
            if (!reasons.length) return null
            return (
              <Panel className="border-orange">
                <PanelHead no="W" title="Why Review?" right={<Stamp tone="warn">EVIDENCE GAPS · NOT FRAUD POINTS</Stamp>} />
                <ul className="space-y-1 p-3.5">
                  {reasons.map((r, i) => (
                    <li key={i} className="flex gap-1.5 font-mono text-[10.5px] leading-snug"><b className="text-orange">!</b><span>{r}</span></li>
                  ))}
                </ul>
              </Panel>
            )
          })()}

          {/* decision */}
          <Panel>
            <PanelHead no="R2" title="Officer Decision" right={<Stamp tone="ink">FINAL CALL</Stamp>} />
            <div className="grid grid-cols-3 gap-2 p-3.5">
              <Btn variant="primary" disabled={busy} onClick={() => decide('verify')}>{busy ? '···' : 'VERIFY'}</Btn>
              <Btn variant="warn" disabled={busy} onClick={() => decide('review')}>REVIEW</Btn>
              <Btn variant="danger" disabled={busy} onClick={() => decide('reject')}>REJECT</Btn>
            </div>
            <div className="border-t-2 border-ink px-3.5 py-2 font-mono text-[9px] leading-relaxed tracking-[0.08em] text-dim">
              AI PROVIDES EVIDENCE — THE OFFICER DECIDES. EVERY ACTION IS HASH-SEALED IN THE LEDGER.
            </div>
          </Panel>

          {/* audit chain */}
          <Panel>
            <PanelHead no="R3" title="Audit Chain"
              right={<Btn className="px-2 py-0.5 text-[9.5px]" onClick={verifyChain}>VERIFY</Btn>} />
            <div className="max-h-72 overflow-auto">
              {!audit?.length && <p className="p-3.5 font-mono text-[10.5px] uppercase text-faint">NO EVENTS</p>}
              {(audit || []).map((ev: any, i: number) => (
                <motion.div key={ev.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }} className="relative flex gap-2.5 border-b border-rule-soft px-3.5 py-2 last:border-0">
                  {i < (audit?.length || 0) - 1 && <span className="absolute left-[19px] top-6 h-full w-0.5 bg-rule-soft" aria-hidden />}
                  <span className="mt-0.5 h-3.5 w-3.5 shrink-0 border-2 border-ink bg-paper-2"><Dot className="h-2 w-2 bg-ink" /></span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="font-mono text-[10.5px] font-bold uppercase tracking-[0.04em]">{(ev.event_type || '').replace(/_/g, ' ')}</span>
                      <span className="font-mono text-[9px] text-faint">{fmtTime(ev.timestamp)}</span>
                    </div>
                    <div className="mt-0.5 font-mono text-[8.5px] tracking-[0.06em] text-dim">{ev.actor_id} · HASH {shortHash(ev.current_hash, 10)}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
