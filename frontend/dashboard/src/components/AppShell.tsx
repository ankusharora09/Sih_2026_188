import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { cn, fmtTime, shortId } from '@/lib/utils'
import { Stamp } from '@/components/ui'
import { api } from '@/lib/api'
import { useApp } from '@/App'

const NAV = [
  { to: '/', label: 'Command', no: '01', end: true },
  { to: '/screening', label: 'Screening', no: '02' },
  { to: '/cases', label: 'Cases', no: '03' },
  { to: '/intelligence', label: 'Investigations', no: '04' },
  { to: '/audit', label: 'Audit Ledger', no: '05' },
  { to: '/analytics', label: 'Reports', no: '06' },
  { to: '/system', label: 'System', no: '07' },
  { to: '/settings', label: 'Settings', no: '08' },
]

function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('')
  const nav = useNavigate()
  useEffect(() => { if (open) setQ('') }, [open])
  if (!open) return null
  const items = NAV.filter((n) => n.label.toLowerCase().includes(q.toLowerCase()))
  return (
    <div className="fixed inset-0 z-[80] bg-ink/50 pt-[14vh]" onClick={onClose}>
      <div
        className="mx-auto w-full max-w-lg border-2 border-ink bg-panel shadow-hard"
        onClick={(e) => e.stopPropagation()}
        role="dialog" aria-label="Command palette"
      >
        <div className="flex items-center gap-2.5 border-b-2 border-ink px-3">
          <span className="sec-label">CMD</span>
          <input
            autoFocus value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="TYPE TO SEARCH MODULES…"
            className="w-full bg-transparent py-3 font-mono text-[12px] uppercase tracking-[0.08em] outline-none placeholder:text-faint"
            aria-label="Search commands"
          />
          <kbd className="border border-rule-soft px-1.5 py-0.5 font-mono text-[9.5px] text-dim">ESC</kbd>
        </div>
        <div className="max-h-72 overflow-auto p-1.5">
          {items.map((n) => (
            <button key={n.to}
              className="flex w-full items-center gap-3 px-3 py-2.5 text-left font-mono text-[12px] uppercase tracking-[0.08em] hover:bg-paper-2"
              onClick={() => { nav(n.to); onClose() }}
            >
              <span className="sec-label">{n.no}</span> {n.label}
            </button>
          ))}
          {!items.length && <p className="px-3 py-6 text-center font-mono text-[11px] text-faint">NO MATCHES</p>}
        </div>
      </div>
    </div>
  )
}

export default function AppShell({ children, health }: { children: ReactNode; health: 'ok' | 'down' }) {
  const [palette, setPalette] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const { user, logout } = useApp()
  const nav = useNavigate()

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPalette((v) => !v) }
      if (e.key === 'Escape') setPalette(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (!notifOpen) return
    api.activity(12).then(setEvents).catch(() => setEvents([]))
  }, [notifOpen])

  return (
    <div className="flex min-h-screen">
      {/* sidebar — hard rail */}
      <aside className="fixed inset-y-0 left-0 z-40 flex w-[212px] flex-col border-r-2 border-ink bg-panel">
        <div className="flex h-[52px] items-center gap-2 border-b-2 border-ink px-3">
          <span className="grid h-7 w-7 place-items-center border-2 border-ink bg-ink font-grotesk text-[13px] font-black text-paper">IS</span>
          <div className="leading-none">
            <div className="font-grotesk text-[13.5px] font-extrabold tracking-tight">IDENTITYSHIELD</div>
            <div className="mt-0.5 font-mono text-[8.5px] tracking-[0.22em] text-dim">SIH 26188 · FORENSICS</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-2" aria-label="Primary">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} title={n.label}
              className={({ isActive }) => cn(
                'mb-0.5 flex items-center gap-2.5 border-2 px-2.5 py-2 font-mono text-[11.5px] font-semibold uppercase tracking-[0.1em] transition-colors duration-75',
                isActive ? 'border-ink bg-ink text-paper' : 'border-transparent text-dim hover:border-ink hover:bg-paper-2 hover:text-ink',
              )}>
              <span className={cn('px-1 py-px text-[9px]', ({ isActive }: any) => '')}>{n.no}</span>
              <span className="truncate">{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t-2 border-ink p-3">
          <div className="font-mono text-[9px] leading-relaxed tracking-[0.1em] text-faint">
            SESSION · {user?.id?.toUpperCase()}<br />
            ROLE · {(user?.role || '—').toUpperCase()}<br />
            BUILD · 2.1.0-FORENSIC
          </div>
        </div>
      </aside>

      {/* main column */}
      <div className="flex min-h-screen flex-1 flex-col md:ml-[212px]">
        {/* topbar — technical strip */}
        <header className="sticky top-0 z-30 flex h-[52px] items-center gap-3 border-b-2 border-ink bg-paper">
          <button
            onClick={() => setPalette(true)}
            className="flex flex-1 items-center gap-2 border-2 border-ink bg-panel px-3 py-1.5 font-mono text-[11px] text-dim hover:bg-paper-2"
            aria-label="Open command palette"
          >
            <span className="sec-label">⌕</span>
            <span className="flex-1 text-left uppercase tracking-[0.08em]">Search modules</span>
            <kbd className="border border-rule-soft px-1.5 py-0.5 text-[9.5px]">CTRL K</kbd>
          </button>
          <Stamp tone={health === 'ok' ? 'ok' : 'bad'} className="hidden sm:inline-flex">
            <span className={cn('h-2 w-2 border border-ink', health === 'ok' ? 'bg-green' : 'bg-red animate-pulse')} />
            {health === 'ok' ? 'AI ENGINE ONLINE' : 'AI ENGINE DOWN'}
          </Stamp>
          <div className="relative">
            <button onClick={() => setNotifOpen((v) => !v)}
              className="grid h-8 w-8 place-items-center border-2 border-ink bg-panel font-mono text-[12px] font-bold hover:bg-paper-2"
              aria-label="Event log">
              ≡
            </button>
            {notifOpen && (
              <div className="absolute right-0 top-10 w-80 border-2 border-ink bg-panel shadow-hard" role="dialog" aria-label="Recent events">
                <div className="border-b-2 border-ink bg-ink px-3 py-1.5 font-mono text-[10px] font-semibold tracking-[0.14em] text-paper">EVENT LOG · LIVE</div>
                <div className="max-h-80 overflow-auto">
                  {events.length === 0 && <p className="px-3 py-6 text-center font-mono text-[11px] text-faint">NO EVENTS</p>}
                  {events.map((ev) => (
                    <div key={ev.id} className="border-b border-rule-soft px-3 py-2 last:border-0 hover:bg-paper-2">
                      <div className="flex items-center justify-between gap-2 font-mono text-[10.5px]">
                        <span className="truncate font-semibold uppercase">{(ev.action || ev.event_type || '').replace(/_/g, ' ')}</span>
                        <span className="text-faint">{fmtTime(ev.timestamp)}</span>
                      </div>
                      {ev.case_id && <button className="mt-0.5 font-mono text-[9.5px] text-dim underline hover:text-ink" onClick={() => { nav(`/cases/${ev.case_id}`); setNotifOpen(false) }}>CASE {shortId(ev.case_id)}</button>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 border-2 border-ink bg-panel px-2 py-1">
            <span className="grid h-6 w-6 place-items-center bg-ink font-grotesk text-[10px] font-black text-paper">
              {(user?.id || 'O').slice(0, 2).toUpperCase()}
            </span>
            <div className="hidden leading-none sm:block">
              <div className="font-mono text-[10px] font-bold">{user?.id}</div>
              <div className="mt-0.5 font-mono text-[8.5px] tracking-[0.14em] text-dim">{(user?.role || '').toUpperCase()}</div>
            </div>
            <button onClick={logout} className="ml-1 border border-rule-soft px-1.5 py-0.5 font-mono text-[9px] tracking-[0.1em] text-dim hover:border-red hover:text-red" aria-label="Sign out">EXIT</button>
          </div>
        </header>
        <main className="flex-1 p-4">{children}</main>
        <footer className="border-t-2 border-ink px-4 py-2 font-mono text-[9px] tracking-[0.14em] text-faint">
          IDENTITYSHIELD FORENSIC WORKSTATION · SIH 26188 · ALL ACTIONS AUDIT-LOGGED · TAMPER-EVIDENT CHAIN ACTIVE
        </footer>
      </div>

      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  )
}
