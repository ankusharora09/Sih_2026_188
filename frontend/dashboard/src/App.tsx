import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { api, setToken, getToken, getRole } from '@/lib/api'
import AppShell from '@/components/AppShell'
import LoginPage from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Screening from '@/pages/Screening'
import Cases from '@/pages/Cases'
import CaseDetail from '@/pages/CaseDetail'
import AuditLedger from '@/pages/AuditLedger'
import Intelligence from '@/pages/Intelligence'
import Analytics from '@/pages/Analytics'
import SystemHealth from '@/pages/SystemHealth'
import Settings from '@/pages/Settings'

type Toast = { id: number; msg: string; tone: 'ok' | 'err' | 'warn' }
type Ctx = {
  user: { id: string; role: string } | null
  login: (id: string, role: string) => Promise<void>
  logout: () => void
  toast: (msg: string, tone?: Toast['tone']) => void
  toasts: Toast[]
}
const AppCtx = createContext<Ctx>(null as any)
export const useApp = () => useContext(AppCtx)

export { api }

function Toasts({ items }: { items: Toast[] }) {
  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-[90] flex flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto rounded-lg border px-4 py-2.5 text-[12px] font-medium shadow-panel backdrop-blur-md ${
            t.tone === 'ok' ? 'border-ok/40 bg-ok-soft text-ok'
            : t.tone === 'err' ? 'border-bad/40 bg-bad-soft text-bad'
            : 'border-warn/40 bg-warn-soft text-warn'
          }`}
          role="status"
        >
          {t.msg}
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState<{ id: string; role: string } | null>(
    getToken() ? { id: sessionStorage.getItem('is_user') || 'officer', role: getRole() } : null,
  )
  const [toasts, setToasts] = useState<Toast[]>([])
  const location = useLocation()

  const toast = (msg: string, tone: Toast['tone'] = 'ok') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, msg, tone }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3600)
  }

  const login = async (id: string, role: string) => {
    const res = await api.devToken(id, role)
    setToken(res.access_token, role)
    sessionStorage.setItem('is_user', id)
    setUser({ id, role })
  }

  const logout = () => {
    setToken('')
    setUser(null)
  }

  // keep topbar status honest: probe once on load
  const [health, setHealth] = useState<'ok' | 'down'>('ok')
  useEffect(() => {
    api.health().then(() => setHealth('ok')).catch(() => setHealth('down'))
  }, [user])

  return (
    <AppCtx.Provider value={{ user, login, logout, toast, toasts }}>
      {user ? (
        <AppShell health={health}>
          <Routes location={location}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/screening" element={<Screening />} />
            <Route path="/cases" element={<Cases />} />
            <Route path="/cases/:caseId" element={<CaseDetail />} />
            <Route path="/audit" element={<AuditLedger />} />
            <Route path="/intelligence" element={<Intelligence />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/system" element={<SystemHealth />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      ) : (
        <LoginPage />
      )}
      <Toasts items={toasts} />
    </AppCtx.Provider>
  )
}
