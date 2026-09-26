import { useApp } from '@/App'
import { Panel, PanelHead, Stamp, Btn } from '@/components/ui'

export default function Settings() {
  const { user, logout } = useApp()
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="border-b-2 border-ink pb-3">
        <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 08 / CONFIGURATION</div>
        <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">Settings & Session</h1>
      </div>

      <Panel>
        <PanelHead no="C1" title="Session Record" right={<Stamp tone="ink">AUTHENTICATED</Stamp>} />
        <div className="grid gap-0 sm:grid-cols-2">
          {[
            ['OFFICER', user?.id?.toUpperCase() || '—'],
            ['ROLE', (user?.role || '—').toUpperCase()],
            ['TOKEN', 'IN-MEMORY · CLEARED ON EXIT'],
            ['AUDIT', 'ALL ACTIONS RECORDED'],
          ].map(([k, v]) => (
            <div key={k} className="border-b border-rule-soft p-3.5 sm:odd:border-r">
              <div className="font-mono text-[9px] tracking-[0.18em] text-dim">{k}</div>
              <div className="mt-1 font-mono text-[12px] font-bold">{v}</div>
            </div>
          ))}
        </div>
        <div className="flex justify-end border-t-2 border-ink p-3.5">
          <Btn variant="danger" onClick={logout}>SIGN OUT</Btn>
        </div>
      </Panel>

      <Panel>
        <PanelHead no="C2" title="Operating Points" right={<Stamp tone="warn">READ-ONLY</Stamp>} />
        <div className="space-y-2.5 p-4 font-mono text-[10.5px] leading-relaxed text-dim">
          <p>▸ FACE MATCH THRESHOLD, CALIBRATION AND RISK WEIGHTS LIVE IN <span className="font-bold text-ink">BACKEND/CONFIG.PY</span> AND THE RISK ENGINE — DELIBERATE, DOCUMENTED CHOICES.</p>
          <p>▸ DEEPFAKE DETECTOR IS A SPECTRAL HEURISTIC; LIVENESS IS A SHARPNESS/ENTROPY PROXY. BOTH ARE LABELLED AS SUCH WHEREVER THEY APPEAR.</p>
          <p>▸ THEME: CONSOLE LIGHT (PAPER) — HIGH-CONTRAST FORENSIC WORKSTATION.</p>
        </div>
      </Panel>
    </div>
  )
}
