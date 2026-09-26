import { useEffect, useState } from 'react'
import { useApp } from '@/App'
import { api } from '@/lib/api'
import { Btn, Stamp } from '@/components/ui'
import { cn } from '@/lib/utils'

function StatusCell({ label, state }: { label: string; state: 'ok' | 'down' | 'checking' }) {
  return (
    <div className="flex items-center justify-between border-b border-rule-soft py-2 last:border-0">
      <span className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-dim">{label}</span>
      <span className="flex items-center gap-1.5 font-mono text-[10px] font-semibold tracking-[0.1em]">
        <span className={cn('h-2 w-2 border border-ink',
          state === 'ok' ? 'bg-green' : state === 'down' ? 'bg-red' : 'bg-orange animate-pulse')} />
        {state === 'ok' ? 'OPERATIONAL' : state === 'down' ? 'UNAVAILABLE' : 'CHECKING…'}
      </span>
    </div>
  )
}

export default function LoginPage() {
  const { login, toast } = useApp()
  const [officerId, setOfficerId] = useState('')
  const [role, setRole] = useState('officer')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [checks, setChecks] = useState<{ ai: 'ok' | 'down' | 'checking' }>({ ai: 'checking' })

  useEffect(() => {
    api.health()
      .then(() => setChecks({ ai: 'ok' }))
      .catch(() => setChecks({ ai: 'down' }))
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!officerId.trim()) { setErr('OFFICER ID REQUIRED'); return }
    setBusy(true); setErr('')
    try {
      await login(officerId.trim(), role)
      toast('SECURE SESSION ESTABLISHED', 'ok')
    } catch (e: any) {
      setErr((e?.message || 'AUTHENTICATION FAILED').toUpperCase())
    } finally { setBusy(false) }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-5">
      <div className="grid w-full max-w-4xl border-2 border-ink bg-panel shadow-hard md:grid-cols-[1.15fr_1fr]">
        {/* left — editorial brand panel */}
        <div className="flex flex-col justify-between border-b-2 border-ink p-7 md:border-b-0 md:border-r-2">
          <div>
            <div className="flex items-center justify-between">
              <span className="sec-label">RESTRICTED SYSTEM</span>
              <span className="font-mono text-[9.5px] tracking-[0.16em] text-faint">FORM IS-01</span>
            </div>
            <h1 className="mt-6 font-grotesk text-[42px] font-black leading-[0.95] tracking-tight">
              IDENTITY<br />SHIELD <span className="text-red">AI</span>
            </h1>
            <div className="mt-2 h-1.5 w-24 bg-ink" />
            <p className="mt-4 max-w-sm font-mono text-[11px] uppercase leading-relaxed tracking-[0.06em] text-dim">
              AI-powered identity &amp; document screening. Tampering detection, biometric
              verification, liveness analysis, cross-case fraud intelligence — every action
              sealed in a tamper-evident audit chain.
            </p>
          </div>
          <div className="mt-8 border-2 border-ink px-3.5 py-1">
            <StatusCell label="AI ENGINE" state={checks.ai} />
            <StatusCell label="SECURE GATEWAY" state={checks.ai} />
            <StatusCell label="AUDIT LEDGER" state={checks.ai} />
          </div>
        </div>
        {/* right — access form */}
        <div className="p-7">
          <div className="flex items-center justify-between">
            <h2 className="font-grotesk text-lg font-extrabold uppercase tracking-tight">Secure Officer Access</h2>
            <Stamp tone="ink">AUTH</Stamp>
          </div>
          <form onSubmit={submit} className="mt-6 space-y-4" aria-label="Login form">
            <div>
              <label htmlFor="oid" className="mb-1 block font-mono text-[9.5px] tracking-[0.18em] text-dim">OFFICER ID *</label>
              <input id="oid" autoFocus value={officerId} onChange={(e) => setOfficerId(e.target.value)}
                placeholder="e.g. officer1"
                className="w-full border-2 border-ink bg-paper px-3 py-2.5 font-mono text-[13px] outline-none placeholder:text-faint focus:bg-panel" />
            </div>
            <div>
              <label htmlFor="orole" className="mb-1 block font-mono text-[9.5px] tracking-[0.18em] text-dim">CLEARANCE</label>
              <select id="orole" value={role} onChange={(e) => setRole(e.target.value)}
                className="w-full border-2 border-ink bg-paper px-3 py-2.5 font-mono text-[12px] outline-none focus:bg-panel">
                <option value="officer">OFFICER</option>
                <option value="admin">ADMIN</option>
                <option value="auditor">AUDITOR · READ-ONLY</option>
              </select>
            </div>
            <div>
              <label htmlFor="o2fa" className="mb-1 block font-mono text-[9.5px] tracking-[0.18em] text-dim">2FA CODE (OPTIONAL)</label>
              <input id="o2fa" inputMode="numeric" placeholder="······" maxLength={6} disabled
                className="w-full cursor-not-allowed border-2 border-rule-soft bg-paper-2 px-3 py-2.5 font-mono text-[13px] tracking-[0.3em] text-faint" />
            </div>
            {err && <p className="border-2 border-red bg-red-soft px-3 py-2 font-mono text-[11px] font-semibold text-red" role="alert">▲ {err}</p>}
            <Btn variant="primary" className="w-full py-3" disabled={busy}>
              {busy ? 'AUTHENTICATING…' : 'AUTHENTICATE →'}
            </Btn>
          </form>
          <p className="mt-5 border border-rule-soft bg-paper-2 px-3 py-2 font-mono text-[10px] leading-relaxed text-dim">
            DEVELOPMENT AUTH: ANY OFFICER ID. TOKENS MINTED LOCALLY, EXPIRE AUTOMATICALLY.
          </p>
        </div>
      </div>
    </div>
  )
}
