import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { Panel, PanelHead, Stamp, Btn, Empty, Dot } from '@/components/ui'
import { STAGE_LABELS, cn, shortId, fmtDateTime, fmtMs, verifyLabel, decisionLabel } from '@/lib/utils'
import { useApp } from '@/App'

const STAGES = ['preprocessing', 'ocr', 'tampering_detection', 'face_verification', 'liveness_detection', 'deepfake_detection', 'anomaly_detection', 'risk_engine', 'explanation']

type StageState = 'waiting' | 'processing' | 'done' | 'review' | 'failed' | 'notrun'
const STATE_STAMP: Record<StageState, { tone: any; label: string }> = {
  waiting: { tone: 'neutral', label: 'QUEUED' },
  processing: { tone: 'info', label: 'PROCESSING' },
  done: { tone: 'ok', label: 'PASSED' },
  review: { tone: 'warn', label: 'REVIEW' },
  failed: { tone: 'bad', label: 'FAILED' },
  notrun: { tone: 'neutral', label: 'NOT RUN' },
}

function stageState(status?: string): StageState {
  switch (status) {
    case 'success': return 'done'
    case 'failed': return 'failed'
    // Skipped / unavailable stages never executed — gray NOT RUN, not orange REVIEW.
    case 'unavailable': case 'skipped': return 'notrun'
    case 'processing': case 'queued': return 'processing'
    default: return 'waiting'
  }
}

/** Risk-engine signal key → the pipeline stage whose status shows how it ran. */
const SIGNAL_STAGE: Record<string, string> = {
  tampering: 'tampering_detection',
  face_mismatch: 'face_verification',
  liveness: 'liveness_detection',
  deepfake: 'deepfake_detection',
  ocr_confidence: 'ocr',
  document_validation: 'ocr',
}

/** BUG 4: verification coverage built from the backend's executed/pending signal
 *  lists — the checklist itself is never hardcoded in the frontend. ✓ executed,
 *  ○ not run, ✗ failed. NOT RUN is never rendered as a success. */
function VerificationBreakdown({ verification, stageStatus }: { verification?: any; stageStatus: Record<string, any> }) {
  if (!verification) return null
  const rows = [...(verification.executed || []).sort(), ...(verification.pending || []).sort()]
  if (!rows.length) return null
  return (
    <div className="border border-ink bg-paper px-3 py-2">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[9px] tracking-[0.16em] text-dim">VERIFICATION COVERAGE · {verification.executed_count}/{verification.total} EXECUTED</span>
        <span className="font-mono text-[9px] text-dim">{verification.percent}%</span>
      </div>
      <div className="mt-1 h-1.5 border border-ink bg-panel" role="progressbar" aria-valuenow={verification.percent} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full bg-green" style={{ width: `${verification.percent}%` }} />
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
        {rows.map((sig: string) => {
          const st = stageStatus[SIGNAL_STAGE[sig]]?.status
          const cls = st === 'failed' ? 'text-red' : st === 'success' ? 'text-green' : 'text-dim'
          const mark = st === 'failed' ? '✗' : st === 'success' ? '✓' : '○'
          const label = st === 'failed' ? 'FAILED' : st === 'success' ? 'EXECUTED' : 'NOT RUN'
          return (
            <span key={sig} title={`${verifyLabel(sig)} — ${label}`} className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.05em]">
              <b className={cls}>{mark}</b>{verifyLabel(sig)}
            </span>
          )
        })}
      </div>
    </div>
  )
}

export default function Screening() {
  const { toast } = useApp()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [caseId, setCaseId] = useState<string | null>(null)
  const [stageStatus, setStageStatus] = useState<Record<string, any>>({})
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [docUrl, setDocUrl] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const pick = (f: File | null) => {
    setFile(f); setResult(null); setStageStatus({})
    if (docUrl) URL.revokeObjectURL(docUrl)
    setDocUrl(f ? URL.createObjectURL(f) : null)
  }

  const createCase = async () => {
    setCreating(true)
    try {
      const c = await api.createCase(null)
      setCaseId(c.case_id)
      toast(`CASE ${shortId(c.case_id)} OPENED`, 'ok')
    } catch (e: any) { toast(e.message, 'err') } finally { setCreating(false) }
  }

  const begin = async () => {
    if (!caseId) { toast('OPEN A CASE FIRST', 'warn'); return }
    if (!file) { toast('ATTACH A DOCUMENT FIRST', 'warn'); return }
    setRunning(true); setResult(null); setStageStatus({})
    try {
      await api.uploadFile(caseId, file, 'document')
      const run = await api.startScreening(caseId)
      poll(caseId)
    } catch (e: any) { toast(e.message, 'err'); setRunning(false) }
  }

  const poll = async (cid: string) => {
    for (let i = 0; i < 150; i++) {
      await new Promise((r) => setTimeout(r, 700))
      try {
        const st = await api.latestRun(cid)
        const map: Record<string, any> = {}
        for (const s of st.stage_results || []) map[s.stage] = s
        setStageStatus(map)
        if (st.status === 'completed' || st.status === 'failed') {
          const riskStage = (st.stage_results || []).find((s: any) => s.stage === 'risk_engine')
          setResult({ ...st, ...(riskStage?.result || {}) })
          setRunning(false)
          qc.invalidateQueries({ queryKey: ['analytics'] })
          return
        }
      } catch { /* keep polling */ }
    }
    setRunning(false)
    toast('TIMED OUT — CHECK CASE REGISTER', 'warn')
  }

  const decision = async (action: string) => {
    if (!caseId) return
    try {
      const res = await api.decision(caseId, action, 'From screening bench')
      toast(`DECISION RECORDED: ${res.status}`, 'ok')
      qc.invalidateQueries()
    } catch (e: any) { toast(e.message, 'err') }
  }

  const rows = STAGES.map((s) => ({ key: s, res: stageStatus[s] }))
  const doneCount = rows.filter((r) => r.res?.status).length
  const riskLevel = String(result?.risk_level || '')
  const verdictTone = riskLevel.includes('review') ? 'warn' : riskLevel === 'low' ? 'ok' : riskLevel === 'medium' ? 'warn' : 'bad'
  // Officer-facing evidence lists, with a legacy-run fallback.
  const factors: any[] = result?.risk_factors
    || (result?.contribution_details || []).filter((d: any) => !['skipped', 'unavailable', 'failed'].includes(d.status))
      .map((d: any) => ({ signal: d.signal, contribution: d.contribution, text: String(d.officer_reason || d.reason || '').replace(/_/g, ' ') }))
  const gaps: any[] = result?.verification_gaps
    || (result?.contribution_details || []).filter((d: any) => ['skipped', 'unavailable', 'failed'].includes(d.status))
      .map((d: any) => ({ signal: d.signal, status: d.status, text: String(d.officer_reason || d.reason || '').replace(/_/g, ' ') }))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-ink pb-3">
        <div>
          <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 02 / SCREENING BENCH</div>
          <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">Screening Workspace</h1>
        </div>
        {caseId && <Stamp tone="info" className="font-mono">CASE {shortId(caseId, 10)}</Stamp>}
      </div>

      <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
        {/* intake */}
        <div className="space-y-4">
          <Panel>
            <PanelHead no="A" title="Document Intake" />
            <div className="space-y-3 p-3.5">
              <div
                role="button" tabIndex={0} aria-label="Upload document"
                onClick={() => fileRef.current?.click()}
                onKeyDown={(e) => { if (e.key === 'Enter') fileRef.current?.click() }}
                className="flex cursor-pointer flex-col items-center gap-1.5 border-2 border-dashed border-ink bg-paper px-5 py-8 text-center transition-colors hover:bg-paper-2"
              >
                <span className="font-grotesk text-[26px] font-black leading-none">↑</span>
                <b className="font-mono text-[11px] font-bold uppercase tracking-[0.1em]">Drop document</b>
                <span className="font-mono text-[9.5px] tracking-[0.06em] text-dim">JPEG / PNG / PDF</span>
                <input ref={fileRef} type="file" accept=".jpg,.jpeg,.png,.pdf,.tif,.tiff" hidden onChange={(e) => pick(e.target.files?.[0] ?? null)} />
              </div>
              {file && (
                <div className="flex items-center justify-between border border-ink bg-paper-2 px-2.5 py-1.5 font-mono text-[10px]">
                  <span className="truncate">{file.name}</span>
                  <span className="ml-2 shrink-0 text-dim">{(file.size / 1024).toFixed(1)}KB</span>
                </div>
              )}
              {!caseId ? (
                <Btn variant="primary" className="w-full" onClick={createCase} disabled={creating}>
                  {creating ? 'OPENING…' : '1 · OPEN CASE'}
                </Btn>
              ) : (
                <Btn variant="primary" className="w-full" onClick={begin} disabled={running || !file}>
                  {running ? 'RUNNING…' : '2 · BEGIN SCREENING'}
                </Btn>
              )}
            </div>
          </Panel>

          {/* scan preview */}
          <Panel className="overflow-hidden">
            <PanelHead no="B" title="Scan Window"
              right={
                <div className="flex items-center gap-2">
                  {/* BUG 2: presentation-only label — demo data, never a real government document. */}
                  <Stamp tone="warn">SYNTHETIC / DEMO DOCUMENT</Stamp>
                  {running && <Stamp tone="info"><Dot className="bg-ink animate-pulse" /> SCANNING</Stamp>}
                </div>
              } />
            <div className="relative grid min-h-[170px] place-items-center overflow-hidden p-3">
              {docUrl ? (
                <>
                  <img src={docUrl} alt="Document preview" className="max-h-56 border border-ink object-contain" />
                  {running && <div className="pointer-events-none absolute inset-x-3 h-6 animate-scanline border-y-2 border-ink bg-red/10" aria-hidden />}
                </>
              ) : (
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">NO DOCUMENT LOADED</p>
              )}
            </div>
          </Panel>
        </div>

        {/* stage ledger */}
        <div className="space-y-4">
          <Panel>
            <PanelHead no="C" title="Processing Ledger"
              right={<span className="font-mono text-[10px] tracking-[0.1em] text-dim">{doneCount}/{STAGES.length} STAGES REPORTED</span>} />
            <div className="p-3.5">
              {!caseId && <Empty title="Bench idle" hint="Open a case, attach a document and begin screening." />}
              <ol>
                {rows.map((r, i) => {
                  const st = stageState(r.res?.status)
                  const sm = STATE_STAMP[st]
                  return (
                    <li key={r.key} className="relative flex gap-3 pb-3 last:pb-0">
                      {i < STAGES.length - 1 && <span className="absolute left-[7px] top-5 h-full w-0.5 bg-ink" aria-hidden />}
                      <motion.span
                        animate={st === 'processing' ? { opacity: [1, 0.35, 1] } : { opacity: 1 }}
                        transition={st === 'processing' ? { repeat: Infinity, duration: 0.9 } : { duration: 0.1 }}
                        className={cn('relative z-10 mt-0.5 h-4 w-4 shrink-0 border-2 border-ink',
                          st === 'done' ? 'bg-green' : st === 'failed' ? 'bg-red' : st === 'review' ? 'bg-orange' : st === 'processing' ? 'bg-ink' : 'bg-panel')}
                      />
                      <div className="min-w-0 flex-1 border-b border-rule-soft pb-2.5">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <span className="font-mono text-[11.5px] font-bold uppercase tracking-[0.08em]">
                            {String(i + 1).padStart(2, '0')} / {STAGE_LABELS[r.key]}
                          </span>
                          <span className="flex items-center gap-2">
                            {r.res && (
                              <span className={cn('font-mono text-[10px]', r.res.processing_time_ms != null ? 'text-dim' : 'text-faint')}>
                                {fmtMs(r.res.processing_time_ms)}
                              </span>
                            )}
                            <Stamp tone={sm.tone}>{sm.label}</Stamp>
                          </span>
                        </div>
                        <AnimatePresence>
                          {r.res && (
                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="overflow-hidden">
                              <div className="mt-1 flex flex-wrap items-center gap-2 font-mono text-[10px] text-dim">
                                {r.res.confidence != null && <span>CONF {r.res.confidence}</span>}
                                {r.res?.result?.reason && <span>· {String(r.res.result.reason)}</span>}
                                {r.res?.result?.note && <span>· {String(r.res.result.note).slice(0, 90)}</span>}
                              </div>
                              {/* OCR: document type + validation verdict */}
                              {r.key === 'ocr' && stageStatus['ocr']?.result?.validation && (() => {
                                const v = stageStatus['ocr'].result.validation
                                const vTone = v.summary?.verdict === 'pass' ? 'ok' : v.summary?.verdict === 'fail' ? 'bad' : 'warn'
                                return (
                                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                                    <Stamp tone="ink">{String(v.document_type || 'unknown').replace(/_/g, ' ')}</Stamp>
                                    <Stamp tone={vTone as any}>VALIDATION {String(v.summary?.verdict || '—').toUpperCase()}</Stamp>
                                {(v.checks || []).filter((c: any) => c.status !== 'ok' || c.low_confidence).slice(0, 3).map((c: any, i: number) => (
                                  <span key={i} className={cn('border px-1.5 py-0.5 font-mono text-[9px] uppercase',
                                    c.low_confidence && c.status === 'ok' ? 'border-orange text-orange'
                                      : c.status === 'missing' ? 'border-rule-soft text-faint' : 'border-red text-red')}>
                                    {c.field.replace(/_/g, ' ')}: {(c.low_confidence && c.status === 'ok' ? 'low confidence' : c.status).replace(/_/g, ' ')}
                                  </span>
                                ))}
                                  </div>
                                )
                              })()}
                              {/* Tampering: metadata forensics verdict */}
                              {r.key === 'tampering_detection' && stageStatus['tampering_detection']?.result?.metadata?.risk_level && (
                                <div className="mt-1.5">
                                  <Stamp tone={stageStatus['tampering_detection'].result.metadata.risk_level === 'high' ? 'bad' : stageStatus['tampering_detection'].result.metadata.risk_level === 'medium' ? 'warn' : stageStatus['tampering_detection'].result.metadata.risk_level === 'low' ? 'warn' : 'ok'}>
                                    METADATA {String(stageStatus['tampering_detection'].result.metadata.risk_level).toUpperCase()}
                                  </Stamp>
                                </div>
                              )}
                              {r.res?.errors && <p className="mt-1 font-mono text-[10px] text-red">{String(r.res.errors).slice(0, 140)}</p>}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </li>
                  )
                })}
              </ol>
            </div>
          </Panel>

          {/* verdict */}
          {result && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <Panel className={verdictTone === 'bad' ? 'border-red' : verdictTone === 'warn' ? 'border-orange' : 'border-green'}>
                <PanelHead no="D" title="Verdict · Risk Engine Output"
                  right={
                    <div className="flex items-center gap-2">
                      {result.risk_score != null && (
                        <span className="font-grotesk text-[22px] font-black leading-none">{String(result.risk_score).padStart(2, '0')}<span className="font-mono text-[11px] text-faint">/100</span></span>
                      )}
                      <Stamp tone={verdictTone as any}>{String(riskLevel || '—').toUpperCase()}</Stamp>
                    </div>
                  } />
                <div className="grid gap-4 p-3.5 md:grid-cols-[1fr_170px]">
                  <div className="space-y-2">
                    {/* BUG 5: four separate concepts — low fraud signal ≠ fully verified. */}
                    <div className="border border-ink bg-paper px-3 py-2">
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 font-mono sm:grid-cols-4">
                        <div>
                          <div className="text-[8.5px] tracking-[0.14em] text-dim">RISK SCORE</div>
                          <div className="font-grotesk text-[16px] font-black leading-tight">
                            {result.risk_score != null ? String(result.risk_score).padStart(2, '0') : '—'}<span className="font-mono text-[9px] font-normal text-faint"> /100</span>
                          </div>
                        </div>
                        <div>
                          <div className="text-[8.5px] tracking-[0.14em] text-dim">CONFIDENCE</div>
                          <div className={cn('font-grotesk text-[16px] font-black leading-tight',
                            result.confidence_score == null ? '' : result.confidence_score < 50 ? 'text-red' : result.confidence_score < 80 ? 'text-orange' : 'text-green')}>
                            {result.confidence_score != null ? `${result.confidence_score}%` : '—'}
                          </div>
                        </div>
                        <div>
                          <div className="text-[8.5px] tracking-[0.14em] text-dim">VERIFICATION</div>
                          <div className="font-grotesk text-[16px] font-black leading-tight">
                            {result.verification ? `${result.verification.executed_count} / ${result.verification.total}` : '—'}
                          </div>
                        </div>
                        <div>
                          <div className="text-[8.5px] tracking-[0.14em] text-dim">DECISION</div>
                          <div className="font-grotesk text-[16px] font-black leading-tight">{decisionLabel(result.decision_status)}</div>
                        </div>
                      </div>
                    </div>
                    <VerificationBreakdown verification={result.verification} stageStatus={stageStatus} />
                    {/* extracted document fields (Module 1) */}
                    {(() => {
                      const val = stageStatus['ocr']?.result?.validation
                      const fields = val?.fields || {}
                      const shown = Object.entries(fields).filter(([, v]) => v != null && v !== false)
                      if (!shown.length) return null
                      return (
                        <div className="border border-ink bg-paper px-3 py-2">
                          <div className="font-mono text-[9px] tracking-[0.16em] text-dim">EXTRACTED · {String(val.document_type || '').toUpperCase()}</div>
                          <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono text-[10.5px]">
                            {shown.map(([k, v]) => (
                              <div key={k} className="flex justify-between gap-2">
                                <span className="text-dim">{String(k).replace(/_/g, ' ')}</span>
                                <span className="truncate font-bold">{String(v)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    })()}
                    {/* WHY REVIEW — plain-language reasons, from gap/missing-field data only. */}
                    {(result.decision_status === 'REVIEW_REQUIRED' || result.decision_status === 'REVIEW') && (() => {
                      const reasons: string[] = []
                      for (const f of result.missing_mandatory_fields || []) {
                        reasons.push(`${String(f).replace(/_/g, ' ').toUpperCase()} is a mandatory identity field and was not extracted — officer must validate it`)
                      }
                      for (const g of gaps) reasons.push(String(g.text || g.signal))
                      if (!reasons.length) return null
                      return (
                        <div className="border-2 border-orange bg-orange-soft px-3 py-2">
                          <div className="font-mono text-[9px] tracking-[0.16em] text-dim">WHY REVIEW? · EVIDENCE GAPS, NOT FRAUD POINTS</div>
                          <ul className="mt-1 space-y-0.5">
                            {reasons.map((r, i) => (
                              <li key={i} className="flex gap-1.5 font-mono text-[10.5px] leading-snug"><b className="text-orange">!</b><span>{r}</span></li>
                            ))}
                          </ul>
                        </div>
                      )
                    })()}
                    {/* RISK FACTORS — fraud evidence only */}
                    {factors.length > 0 && (
                      <div className="border border-ink bg-paper px-3 py-2">
                        <div className="font-mono text-[9px] tracking-[0.16em] text-dim">RISK FACTORS · FRAUD EVIDENCE</div>
                        <div className="mt-1.5 space-y-1">
                          {factors.map((f: any, i: number) => (
                            <div key={i} className="flex items-start justify-between gap-3">
                              <p className="font-mono text-[10.5px] leading-snug">{String(f.text || '—')}</p>
                              <span className={cn('shrink-0 font-mono text-[11px] font-bold', (f.contribution || 0) > 0 ? 'text-red' : 'text-faint')}>
                                {(f.contribution || 0) > 0 ? `+${Number(f.contribution).toFixed(2)}` : '—'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {/* VERIFICATION GAPS — missing evidence, never scored as guilt */}
                    {gaps.length > 0 && (
                      <div className="border border-rule-soft bg-paper px-3 py-2">
                        <div className="font-mono text-[9px] tracking-[0.16em] text-dim">VERIFICATION GAPS · NOT COUNTED AS FRAUD</div>
                        <div className="mt-1.5 flex flex-wrap gap-1.5">
                          {gaps.map((g: any, i: number) => (
                            <span key={i} title={g.signal} className="border border-rule-soft px-1.5 py-0.5 font-mono text-[9.5px] text-dim">
                              {String(g.text || g.signal).toUpperCase()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {factors.length === 0 && gaps.length === 0 && <p className="font-mono text-[11px] text-dim">NO RISK FACTORS RECORDED.</p>}
                  </div>
                  <div className="flex flex-col gap-2">
                    <span className="font-mono text-[9px] tracking-[0.18em] text-dim">OFFICER DECISION</span>
                    <Btn variant="primary" onClick={() => decision('verify')}>VERIFY</Btn>
                    <Btn variant="warn" onClick={() => decision('review')}>REVIEW</Btn>
                    <Btn variant="danger" onClick={() => decision('reject')}>REJECT</Btn>
                  </div>
                </div>
                {/* validation rule verdicts (Module 2) */}
                {(() => {
                  const checks = stageStatus['ocr']?.result?.validation?.checks || []
                  if (!checks.length) return null
                  return (
                    <div className="border-t-2 border-ink px-3.5 py-2.5">
                      <div className="font-mono text-[9px] tracking-[0.16em] text-dim">VALIDATION RULES · {checks.length} APPLIED</div>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {checks.map((c: any, i: number) => {
                          const tone = c.status === 'ok' ? (c.low_confidence ? 'warn' : 'ok') : c.status === 'missing' ? 'neutral' : 'bad'
                          const label = `${c.field.replace(/_/g, ' ')} ${(c.low_confidence && c.status === 'ok' ? 'low confidence' : c.status).replace(/_/g, ' ')}`
                          return <Stamp key={i} tone={tone as any}>{label}</Stamp>
                        })}
                      </div>
                    </div>
                  )
                })()}
                <div className="border-t-2 border-ink px-3.5 py-2 font-mono text-[9.5px] tracking-[0.1em] text-dim">
                  RUN {shortId(result.screening_run_id || result.id, 8)} · COMPLETED {fmtDateTime(result.completed_at)}
                </div>
              </Panel>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}
