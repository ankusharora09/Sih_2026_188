import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { Panel, PanelHead, Stamp, Empty, ErrorBox, Skel, Btn } from '@/components/ui'
import { shortId, seeded, cn } from '@/lib/utils'

const TYPE_STYLE: Record<string, { fill: string; stroke: string; label: string }> = {
  case: { fill: '#F2F0EA', stroke: '#101010', label: 'CASE' },
  person: { fill: '#E9E6DE', stroke: '#101010', label: 'PERSON' },
  document: { fill: '#E7F2E9', stroke: '#1E7A38', label: 'DOC' },
  id_number: { fill: '#FCEDE4', stroke: '#E8590C', label: 'ID' },
}

function layout(nodes: any[]) {
  const W = 900, H = 540
  const byType: Record<string, any[]> = {}
  for (const n of nodes) (byType[n.type] ||= []).push(n)
  const rings = ['case', 'person', 'document', 'id_number']
  const pos: Record<string, { x: number; y: number }> = {}
  rings.forEach((t, ri) => {
    const arr = byType[t] || []
    const radius = 72 + ri * 62
    arr.forEach((n, i) => {
      const a = (i / Math.max(arr.length, 1)) * Math.PI * 2 + ri * 0.5
      const r = radius + (seeded(n.id) - 0.5) * 24
      pos[n.id] = { x: W / 2 + Math.cos(a) * r, y: H / 2 + Math.sin(a) * r * 0.8 }
    })
  })
  const known = new Set(rings)
  const rest = nodes.filter((n) => !known.has(n.type))
  rest.forEach((n, i) => {
    const a = (i / Math.max(rest.length, 1)) * Math.PI * 2
    pos[n.id] = { x: W / 2 + Math.cos(a) * 300, y: H / 2 + Math.sin(a) * 230 }
  })
  return { pos, W, H }
}

export default function Intelligence() {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['graph'], queryFn: api.graph })
  const [sel, setSel] = useState<any>(null)
  const [focusCase, setFocusCase] = useState<string | null>(null)
  const nav = useNavigate()

  const graph = useMemo(() => {
    const allNodes: any[] = data?.nodes || []
    const allEdges: any[] = data?.edges || []
    let nodes = allNodes, edges = allEdges
    if (focusCase) {
      const keep = new Set<string>([focusCase])
      for (let hop = 0; hop < 2; hop++) {
        for (const e of edges) {
          if (keep.has(e.source)) keep.add(e.target)
          if (keep.has(e.target)) keep.add(e.source)
        }
      }
      nodes = allNodes.filter((n) => keep.has(n.id))
      edges = allEdges.filter((e) => keep.has(e.source) && keep.has(e.target))
    } else if (allNodes.length > 90) {
      const recent = new Set(allNodes.filter((n) => n.type === 'case').slice(0, 24).map((n: any) => n.id))
      nodes = allNodes.filter((n) => n.type !== 'case' || recent.has(n.id))
      const ids = new Set(nodes.map((n) => n.id))
      edges = allEdges.filter((e) => ids.has(e.source) && ids.has(e.target))
    }
    return { nodes, edges, ...layout(nodes) }
  }, [data, focusCase])

  if (error) return <ErrorBox message={String((error as Error).message)} retry={refetch} />

  const signalEdges = graph.edges.filter((e: any) => e.relation === 'REUSED_ID')
  const neighbors = (id: string) => graph.edges.filter((e: any) => e.source === id || e.target === id)

  return (
    <div className="space-y-4">
      <div className="border-b-2 border-ink pb-3">
        <div className="font-mono text-[9.5px] tracking-[0.22em] text-dim">SECTION 04 / INVESTIGATIONS</div>
        <h1 className="mt-1 font-grotesk text-[30px] font-black uppercase leading-none tracking-tight">Identity Intelligence Graph</h1>
        <p className="mt-2 max-w-3xl font-mono text-[10.5px] uppercase leading-relaxed tracking-[0.03em] text-dim">
          Cases, subjects, documents and extracted ID numbers. Orange dashed links are
          <span className="font-bold text-orange"> repeated identity signals</span> — shared attributes warrant review, not automatic guilt.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
        <Panel className="overflow-hidden">
          <PanelHead
            no="G1" title="Entity Network"
            right={
              <div className="flex items-center gap-2">
                {focusCase && <Btn className="px-2 py-0.5 text-[9.5px]" onClick={() => { setFocusCase(null); setSel(null) }}>SHOW ALL</Btn>}
                <Stamp tone="neutral">{graph.nodes.length}N · {graph.edges.length}E</Stamp>
              </div>
            }
          />
          {isLoading ? <div className="p-4"><Skel className="h-96" /></div>
            : graph.nodes.length === 0 ? <Empty title="No entities yet" hint="Screen cases to populate the intelligence graph." />
            : (
            <div className="overflow-auto p-2">
              <svg viewBox={`0 0 ${graph.W} ${graph.H}`} className="h-[520px] w-full" role="img" aria-label="Entity relationship graph">
                {graph.edges.map((e: any, i: number) => {
                  const a = graph.pos[e.source], b = graph.pos[e.target]
                  if (!a || !b) return null
                  const signal = e.relation === 'REUSED_ID'
                  const active = sel && (e.source === sel.id || e.target === sel.id)
                  return (
                    <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                      stroke={signal ? '#E8590C' : active ? '#101010' : '#C8C4BA'}
                      strokeWidth={signal || active ? 2 : 1}
                      strokeDasharray={signal ? '6 4' : undefined} />
                  )
                })}
                {graph.nodes.map((n: any) => {
                  const p = graph.pos[n.id]
                  if (!p) return null
                  const st = TYPE_STYLE[n.type] || TYPE_STYLE.document
                  const active = sel?.id === n.id
                  const deg = neighbors(n.id).length
                  const s = 13 + Math.min(deg, 8)
                  return (
                    <g key={n.id} transform={`translate(${p.x},${p.y})`} className="cursor-pointer"
                      onClick={() => setSel(n)} onMouseEnter={() => setSel(n)}>
                      {active && <rect x={-s - 5} y={-s - 5} width={2 * (s + 5)} height={2 * (s + 5)} fill="none" stroke="#101010" strokeWidth={1.2} strokeDasharray="3 3" />}
                      <rect x={-s} y={-s} width={2 * s} height={2 * s} fill={st.fill} stroke={st.stroke} strokeWidth={active ? 2.5 : 1.6} />
                      <text y={4} textAnchor="middle" fontSize="9" fontWeight="700" fill={st.stroke === '#101010' ? '#101010' : st.stroke} fontFamily="JetBrains Mono">
                        {st.label.slice(0, 3)}
                      </text>
                      <text y={s + 13} textAnchor="middle" fontSize="8.5" fill={active ? '#101010' : '#57544D'} fontFamily="JetBrains Mono">
                        {n.type === 'case' ? shortId(n.label?.replace('CASE ', '') || n.id, 8) : n.label?.slice(0, 14)}
                      </text>
                    </g>
                  )
                })}
                <g transform={`translate(16,${graph.H - 16})`}>
                  <line x1="0" y1="0" x2="28" y2="0" stroke="#E8590C" strokeWidth="2" strokeDasharray="6 4" />
                  <text x="34" y="3.5" fontSize="9.5" fill="#57544D" fontFamily="JetBrains Mono">REUSED ID — REQUIRES REVIEW</text>
                </g>
              </svg>
            </div>
          )}
        </Panel>

        {/* inspector */}
        <Panel className="self-start">
          <PanelHead no="G2" title="Entity Inspector" />
          <div className="p-3.5">
            {!sel ? (
              <Empty title="No selection" hint="Hover or click a node to inspect relationships." />
            ) : (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                <div className="flex items-center gap-2">
                  <Stamp tone={sel.type === 'id_number' ? 'warn' : 'ink'}>{(TYPE_STYLE[sel.type]?.label || sel.type).toUpperCase()}</Stamp>
                  <span className="truncate font-mono text-[11.5px] font-bold">{sel.label}</span>
                </div>
                {sel.status && <div className="font-mono text-[10px] uppercase text-dim">STATUS · {String(sel.status).replace(/_/g, ' ')}</div>}
                {sel.content_hash && <div className="font-mono text-[9.5px] text-faint">SHA256 {sel.content_hash}…</div>}
                <div>
                  <div className="mb-1.5 font-mono text-[9px] tracking-[0.16em] text-dim">RELATIONSHIPS ({neighbors(sel.id).length})</div>
                  <div className="max-h-48 space-y-1 overflow-auto">
                    {neighbors(sel.id).map((e: any, i: number) => {
                      const other = e.source === sel.id ? e.target : e.source
                      const node = graph.nodes.find((n: any) => n.id === other)
                      return (
                        <button key={i} onClick={() => node && setSel(node)}
                          className="flex w-full items-center gap-2 border border-ink bg-paper px-2.5 py-1.5 text-left hover:bg-paper-2">
                          <span className="font-mono text-[9px] uppercase text-dim">{e.relation.replace(/_/g, ' ')}</span>
                          <span className={cn('ml-auto truncate font-mono text-[9.5px] font-bold', e.relation === 'REUSED_ID' && 'text-orange')}>{node?.label?.slice(0, 16) || shortId(other, 8)}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
                {sel.type === 'case' && (
                  <>
                    <Btn variant="primary" className="w-full" onClick={() => nav(`/cases/${sel.id.replace('case:', '')}`)}>OPEN INVESTIGATION →</Btn>
                    {!focusCase && <Btn className="w-full" onClick={() => { setFocusCase(sel.id); setSel(null) }}>FOCUS SUBGRAPH</Btn>}
                  </>
                )}
              </motion.div>
            )}
          </div>
        </Panel>
      </div>

      {signalEdges.length > 0 && (
        <Panel className="border-orange">
          <PanelHead no="G3" title="Repeated Identity Signals" right={<Stamp tone="warn">{signalEdges.length}</Stamp>} />
          <div className="grid gap-2 p-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {signalEdges.map((e: any, i: number) => (
              <button key={i} onClick={() => setSel(graph.nodes.find((n: any) => n.id === e.target) || graph.nodes.find((n: any) => n.id === e.source))}
                className="border-2 border-orange bg-orange-soft px-3 py-2 text-left transition-colors hover:bg-orange hover:text-paper">
                <div className="font-mono text-[9.5px] font-bold uppercase tracking-[0.1em]">ID LINK · POTENTIAL ANOMALY</div>
                <div className="mt-1 font-mono text-[10px]">{shortId(e.source.replace('case:', ''), 8)} ↔ {shortId(e.target.replace('case:', ''), 8)}</div>
              </button>
            ))}
          </div>
          <div className="border-t-2 border-orange px-3.5 py-2 font-mono text-[9px] uppercase tracking-[0.08em] text-dim">
            A SHARED ATTRIBUTE ALONE IS NOT GUILT — FLAGGED FOR REVIEW ONLY.
          </div>
        </Panel>
      )}
    </div>
  )
}
