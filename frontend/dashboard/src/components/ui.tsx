import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { useEffect, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

/* ---------------- Panel: hard-edged bordered module ---------------- */
export function Panel({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('border-2 border-ink bg-panel', className)} {...rest}>
      {children}
    </div>
  )
}

export function PanelHead({ no, title, right }: { no?: string; title: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex items-center gap-2 border-b-2 border-ink px-3 py-2">
      {no && <span className="sec-label">{no}</span>}
      <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em]">{title}</h3>
      {right && <div className="ml-auto flex items-center gap-2">{right}</div>}
    </div>
  )
}

/* ---------------- Stamp: status chip ---------------- */
export function Stamp({ tone = 'neutral', children, className }: { tone?: 'ok' | 'warn' | 'bad' | 'info' | 'neutral' | 'ink'; children: ReactNode; className?: string }) {
  const tones: Record<string, string> = {
    ok: 'border-green bg-green-soft text-green',
    warn: 'border-orange bg-orange-soft text-orange',
    bad: 'border-red bg-red-soft text-red',
    info: 'border-ink bg-paper-2 text-ink',
    ink: 'border-ink bg-ink text-paper',
    neutral: 'border-rule-soft bg-paper-2 text-dim',
  }
  return (
    <span className={cn('inline-flex items-center gap-1.5 border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em]', tones[tone], className)}>
      {children}
    </span>
  )
}

export function Dot({ className }: { className?: string }) {
  return <span className={cn('inline-block h-2 w-2 border border-ink', className)} />
}

/* ---------------- Button: hard shadow, mechanical press ---------------- */
export function Btn({ variant = 'ghost', className, children, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' | 'warn' }) {
  const styles = {
    primary: 'bg-ink text-paper border-ink hover:bg-dim',
    ghost: 'bg-panel text-ink border-ink hover:bg-paper-2',
    danger: 'bg-red text-paper border-red hover:bg-red/85',
    warn: 'bg-orange text-paper border-orange hover:bg-orange/85',
  }
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 border-2 px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] transition-all duration-75 active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:pointer-events-none disabled:opacity-40',
        variant === 'ghost' ? 'shadow-hard-sm' : 'shadow-hard',
        styles[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  )
}

/* ---------------- Animated number ---------------- */
export function Num({ value, decimals = 0, className }: { value: number; decimals?: number; className?: string }) {
  const mv = useMotionValue(0)
  const spring = useSpring(mv, { stiffness: 90, damping: 22 })
  const text = useTransform(spring, (v) => v.toLocaleString(undefined, { maximumFractionDigits: decimals, minimumFractionDigits: decimals }))
  useEffect(() => { mv.set(value) }, [value, mv])
  return <motion.span className={className}>{text}</motion.span>
}

/* ---------------- Metric: KPI module ---------------- */
export function Metric({ label, value, decimals = 0, tone, sub }: {
  label: string; value: number; decimals?: number; tone?: 'ok' | 'warn' | 'bad'; sub?: ReactNode
}) {
  const toneCls = tone === 'bad' ? 'text-red' : tone === 'warn' ? 'text-orange' : tone === 'ok' ? 'text-green' : 'text-ink'
  return (
    <Panel className="p-3.5">
      <div className="font-mono text-[9.5px] font-medium uppercase tracking-[0.16em] text-dim">{label}</div>
      <div className={cn('mt-1.5 font-grotesk text-[28px] font-extrabold leading-none tracking-tight', toneCls)}>
        <Num value={value} decimals={decimals} />
      </div>
      {sub && <div className="mt-1.5 font-mono text-[10px] text-faint">{sub}</div>}
    </Panel>
  )
}

/* ---------------- Empty / Error / Skeleton ---------------- */
export function Empty({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-rule-soft px-6 py-12 text-center">
      <span className="sec-label">NO DATA</span>
      <b className="font-mono text-[12px] uppercase tracking-[0.1em]">{title}</b>
      {hint && <p className="max-w-sm font-mono text-[11px] leading-relaxed text-faint">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}

export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <Panel className="border-red p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center border-2 border-red bg-red-soft font-mono text-[13px] font-bold text-red">!</span>
        <div className="min-w-0 flex-1">
          <b className="font-mono text-[12px] uppercase tracking-[0.1em] text-red">Operation failed</b>
          <p className="mt-1 break-words font-mono text-[11px] text-dim">{message}</p>
          {retry && <Btn className="mt-3" onClick={retry}>Retry</Btn>}
        </div>
      </div>
    </Panel>
  )
}

export function Skel({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} />
}

/* ---------------- Meter: horizontal threat scale ---------------- */
export function Meter({ value, tone = 'ink', label, right }: { value: number; tone?: 'ink' | 'ok' | 'warn' | 'bad'; label?: string; right?: string }) {
  const tones = { ink: 'bg-ink', ok: 'bg-green', warn: 'bg-orange', bad: 'bg-red' }
  return (
    <div>
      {(label || right) && (
        <div className="mb-1 flex items-baseline justify-between font-mono text-[10.5px]">
          <span className="uppercase tracking-[0.1em] text-dim">{label}</span>
          <span className="font-semibold">{right}</span>
        </div>
      )}
      <div className="h-3 border-2 border-ink bg-panel">
        <motion.div
          className={cn('h-full', tones[tone])}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(100, value))}%` }}
          transition={{ duration: 0.45, ease: 'circOut' }}
        />
      </div>
    </div>
  )
}
