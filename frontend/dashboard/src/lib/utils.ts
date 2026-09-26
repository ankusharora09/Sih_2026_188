import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)) }

export type Risk = 'low' | 'medium' | 'high' | 'review_required' | 'unknown'

export const RISK_META: Record<string, { label: string; cls: string; dot: string }> = {
  low: { label: 'LOW', cls: 'text-ok bg-ok-soft border-ok/30', dot: 'bg-ok' },
  medium: { label: 'MEDIUM', cls: 'text-warn bg-warn-soft border-warn/30', dot: 'bg-warn' },
  high: { label: 'HIGH', cls: 'text-bad bg-bad-soft border-bad/30', dot: 'bg-bad' },
  critical: { label: 'CRITICAL', cls: 'text-bad bg-bad-soft border-bad/30', dot: 'bg-bad' },
  review_required: { label: 'REVIEW', cls: 'text-warn bg-warn-soft border-warn/30', dot: 'bg-warn' },
  unknown: { label: '—', cls: 'text-ink-dim bg-white/5 border-line', dot: 'bg-ink-faint' },
}

export const STAGE_LABELS: Record<string, string> = {
  preprocessing: 'Preprocessing',
  ocr: 'OCR Extraction',
  liveness_detection: 'Liveness',
  tampering_detection: 'Tampering',
  face_verification: 'Face Verification',
  deepfake_detection: 'Deepfake',
  anomaly_detection: 'Anomaly',
  risk_engine: 'Risk Engine',
  explanation: 'Explanation',
}

export function riskMeta(k?: string | null) {
  return RISK_META[(k || 'unknown').toLowerCase()] ?? RISK_META.unknown
}

export function fmtTime(iso?: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? String(iso) : d.toLocaleTimeString([], { hour12: false })
}

export function fmtDateTime(iso?: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime())
    ? String(iso)
    : d.toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })
}

export function shortHash(h?: string | null, n = 10) {
  if (!h) return '—'
  return h.length <= n ? h : h.slice(0, n) + '…'
}

export function shortId(id?: string | null, n = 8) {
  if (!id) return '—'
  return id.length <= n ? id : id.slice(0, n) + '…'
}

export function pct(x: number | null | undefined, digits = 1) {
  return x == null ? '—' : (x * 100).toFixed(digits) + '%'
}

/** Deterministic pseudo-random in [0,1) from a string seed — stable across renders. */
export function seeded(s: string) {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) }
  return ((h >>> 0) % 10000) / 10000
}

/** BUG 3: honest timing. A stage that executed measures real work — sub-ms renders
 *  '<1MS'; a stage that never ran has no duration (null) and renders '—'. */
export function fmtMs(ms?: number | null): string {
  if (ms == null) return '—'
  return ms < 1 ? '<1MS' : `${ms}MS`
}

/** Labels for the risk engine's decisive verification signals (BUG 4 breakdown). */
const VERIFY_LABELS: Record<string, string> = {
  tampering: 'Tampering',
  face_mismatch: 'Face Verification',
  liveness: 'Liveness',
  deepfake: 'Deepfake',
  ocr_confidence: 'OCR',
  document_validation: 'Document Validation',
}
export function verifyLabel(k?: string | null): string {
  return VERIFY_LABELS[String(k || '')] || String(k || '').replace(/_/g, ' ')
}

/** Officer-facing decision label — internal codes never reach the UI. */
export function decisionLabel(status?: string | null): string {
  const s = String(status || '').toUpperCase()
  return s ? s.replace(/_/g, ' ') : '—'
}
