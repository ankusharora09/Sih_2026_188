import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { Panel, PanelHead, Stamp, Empty, ErrorBox, Skel, Btn } from '@/components/ui'
import { fmtDateTime, riskMeta, cn, shortId } from '@/lib/utils'

export default function Cases() {
  const [q, setQ] = useState('')
  const [risk, setRisk] = useState('all')
  const [status, setStatus] = useState('all')
  const nav = useNavigate()
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['cases'], queryFn: api.cases })

  const rows = useMemo(() => {
    let r = data || []
    if (q) r = r.filter((c: any) => (c.case_id + ' ' + (c.subject_name || '')).toLowerCase().includes(q.toLowerCase()))
    if (risk !== 'all') r = r.filter((c: any) => (c.risk_level || 'unknown') === risk)
    if (status !== 'all') r = r.filter((c: any) => (c.status || '').toLowerCase() === status)
    return r
  }, [data, q, risk, status])

  if (error) return <ErrorBox message={String((error as Error).message)} retry={refetch} />

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-ink pb-3">
        <div>
          <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 03 / CASE REGISTER</div>
          <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">Cases</h1>
          <p className="mt-1.5 font-mono text-[11px] uppercase tracking-[0.04em] text-dim">{data?.length ?? 0} ON FILE · SELECT A ROW TO OPEN THE INVESTIGATION</p>
        </div>
        <Btn variant="primary" onClick={() => nav('/screening')}>+ NEW SCREENING</Btn>
      </div>

      <Panel>
        <PanelHead
          no="R" title="Register"
          right={
            <div className="flex flex-wrap items-center gap-2">
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="SEARCH…" aria-label="Search cases"
                className="w-36 border-2 border-ink bg-paper px-2 py-1 font-mono text-[10.5px] uppercase outline-none placeholder:text-faint" />
              <select value={risk} onChange={(e) => setRisk(e.target.value)} aria-label="Filter by risk"
                className="border-2 border-ink bg-paper px-1.5 py-1 font-mono text-[10.5px] uppercase outline-none">
                <option value="all">RISK · ALL</option>
                <option value="low">LOW</option><option value="medium">MEDIUM</option>
                <option value="high">HIGH</option><option value="review_required">REVIEW</option>
              </select>
              <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status"
                className="border-2 border-ink bg-paper px-1.5 py-1 font-mono text-[10.5px] uppercase outline-none">
                <option value="all">STATUS · ALL</option>
                <option value="created">CREATED</option>
                <option value="review_required">REVIEW REQUIRED</option>
                <option value="verified">VERIFIED</option>
                <option value="rejected">REJECTED</option>
              </select>
            </div>
          }
        />
        {isLoading ? (
          <div className="space-y-2 p-3">{Array.from({ length: 6 }).map((_, i) => <Skel key={i} className="h-10" />)}</div>
        ) : rows.length === 0 ? (
          <Empty title="No screening cases yet" hint="Open a case and upload a document to begin AI screening."
            action={<Btn variant="primary" onClick={() => nav('/screening')}>START NEW SCREENING</Btn>} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left">
              <thead>
                <tr className="border-b-2 border-ink bg-paper-2 font-mono text-[9.5px] uppercase tracking-[0.16em] text-dim">
                  <th className="px-3.5 py-2 font-semibold">CASE ID</th>
                  <th className="px-3.5 py-2 font-semibold">SUBJECT</th>
                  <th className="px-3.5 py-2 font-semibold">STATUS</th>
                  <th className="px-3.5 py-2 font-semibold">RISK</th>
                  <th className="px-3.5 py-2 font-semibold">CREATED</th>
                  <th className="px-3.5 py-2" />
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 100).map((c: any) => (
                  <tr key={c.case_id}
                    className="cursor-pointer border-b border-rule-soft transition-colors last:border-0 hover:bg-paper-2"
                    onClick={() => nav(`/cases/${c.case_id}`)}>
                    <td className="px-3.5 py-2.5 font-mono text-[11px] font-bold">{shortId(c.case_id)}</td>
                    <td className="px-3.5 py-2.5 font-mono text-[11px]">{c.subject_name || <span className="text-faint">—</span>}</td>
                    <td className="px-3.5 py-2.5">
                      <Stamp tone={c.status === 'verified' ? 'ok' : c.status === 'rejected' ? 'bad' : c.status === 'review_required' ? 'warn' : 'neutral'}>
                        {(c.status || '—').replace(/_/g, ' ')}
                      </Stamp>
                    </td>
                    <td className="px-3.5 py-2.5">
                      <span className={cn('font-mono text-[10.5px] font-bold uppercase',
                        c.risk_level === 'high' ? 'text-red' : c.risk_level === 'medium' ? 'text-orange' : c.risk_level === 'low' ? 'text-green' : 'text-faint')}>
                        {riskMeta(c.risk_level).label}
                      </span>
                    </td>
                    <td className="px-3.5 py-2.5 font-mono text-[10px] text-dim">{fmtDateTime(c.created_at)}</td>
                    <td className="px-3.5 py-2.5 text-right font-mono text-[11px]">→</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
