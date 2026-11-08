import { useEffect, useState } from 'react'
import { ArrowsClockwise } from '@phosphor-icons/react'

type SectorRow = {
  sector: string
  rank: number
  ret_1w_pct: number | null
  ret_1m_pct: number | null
  rs_1w_pct: number | null
  rs_1m_pct: number | null
  above_50dma: boolean
  trend: 'Leading' | 'Neutral' | 'Lagging'
}
type HeatmapData = {
  as_of?: string
  nifty_ret_1w_pct?: number | null
  nifty_ret_1m_pct?: number | null
  sectors: SectorRow[]
  picks: { symbol: string; name?: string; sector?: string; sector_index?: string | null }[]
}
type Metric = 'rs_1m_pct' | 'rs_1w_pct' | 'ret_1m_pct' | 'ret_1w_pct'

const METRICS: { key: Metric; label: string }[] = [
  { key: 'rs_1m_pct', label: '1 month vs NIFTY' },
  { key: 'rs_1w_pct', label: '1 week vs NIFTY' },
  { key: 'ret_1m_pct', label: '1 month return' },
  { key: 'ret_1w_pct', label: '1 week return' },
]

function cellColor(v: number | null, scale: number) {
  if (v == null) return 'rgba(128,128,128,0.08)'
  const norm = Math.min(1, Math.abs(v) / Math.max(scale, 1))
  const a = (norm * 0.22 + 0.08).toFixed(3)
  return v >= 0 ? `rgba(16, 185, 129, ${a})` : `rgba(239, 68, 68, ${a})`
}

function cellBorder(v: number | null) {
  if (v == null) return '1px solid var(--line)'
  return v >= 0 ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid rgba(239, 68, 68, 0.35)'
}
const signed = (v: number | null | undefined) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`)

export default function SectorHeatmap() {
  const [data, setData] = useState<HeatmapData | null>(null)
  const [metric, setMetric] = useState<Metric>('rs_1m_pct')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async (refresh = false) => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`/api/sectors/heatmap${refresh ? '?refresh=true' : ''}`)
      const d = await res.json()
      if (!res.ok || !d?.sectors) throw new Error(d?.error || `status ${res.status}`)
      setData(d)
    } catch (e: any) {
      setError(`Could not load sector data: ${e?.message || e}`)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  const rows = data?.sectors ?? []
  const vals = rows.map(r => r[metric]).filter((v): v is number => v != null)
  const scale = Math.max(2, ...vals.map(Math.abs))
  const sorted = [...rows].sort((a, b) => (b[metric] ?? -999) - (a[metric] ?? -999))
  const picksBySector: Record<string, string[]> = {}
  for (const p of data?.picks ?? []) if (p.sector_index) (picksBySector[p.sector_index] ||= []).push(p.symbol)
  const leading = rows.filter(r => r.trend === 'Leading').length
  const above = rows.filter(r => r.above_50dma).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <section className="panel" style={{ padding: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
          <div>
            <h3 style={{ margin: 0 }}>Sector Heatmap</h3>
            <p className="hint" style={{ margin: '4px 0 0' }}>
              Official NSE sector indices. Green sectors are outperforming; swing trades work best in green sectors.
              {data?.as_of && <> Data as of <b className="num">{data.as_of}</b>.</>}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {METRICS.map(m => (
              <button key={m.key} className={`btn ${metric === m.key ? 'dark' : 'ghost'}`} onClick={() => setMetric(m.key)}>{m.label}</button>
            ))}
            <button className="btn ghost" disabled={loading} onClick={() => load(true)} aria-label="Refresh sector data">
              <ArrowsClockwise size={15} weight="bold" />
            </button>
          </div>
        </div>
        {data && <div className="note" style={{ marginTop: 12 }}>
          NIFTY: <b className="num">{signed(data.nifty_ret_1w_pct)}</b> this week, <b className="num">{signed(data.nifty_ret_1m_pct)}</b> this month ·
          {' '}<b>{leading}</b> of {rows.length} sectors leading · <b>{above}</b> of {rows.length} above their 50-DMA
          {rows.length > 0 && above / rows.length < 0.4 && <> · <b className="neg">Weak market: most sectors are in a downtrend, so be selective.</b></>}
        </div>}
      </section>

      {loading && !data ? <section className="panel emptystate" style={{ padding: 40, textAlign: 'center' }}>Loading sector data…</section>
        : error && !data ? <section className="panel emptystate" style={{ padding: 40, textAlign: 'center' }}>
          <p>{error}</p><button className="btn dark" onClick={() => load(true)}>Retry</button>
        </section>
        : <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
          {sorted.map(r => {
            const v = r[metric]
            const picks = picksBySector[r.sector] || []
            return (
              <div key={r.sector} className="panel" style={{ padding: 14, background: cellColor(v, scale), border: picks.length ? '2px solid var(--accent)' : cellBorder(v) }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <b style={{ fontSize: 14 }}>{r.sector}</b>
                  <span style={{ fontSize: 10.5, fontWeight: 700, color: (v ?? 0) >= 0 ? '#10B981' : '#EF4444' }}>{r.trend.toUpperCase()}</span>
                </div>
                <div className="num" style={{ fontSize: 22, fontWeight: 700, margin: '6px 0', color: (v ?? 0) >= 0 ? '#10B981' : '#EF4444' }}>{signed(v)}</div>
                <div style={{ fontSize: 11.5, opacity: 0.9, lineHeight: 1.5 }}>
                  1W {signed(r.ret_1w_pct)} · 1M {signed(r.ret_1m_pct)}<br />
                  {r.above_50dma ? 'Above 50-DMA' : 'Below 50-DMA'}
                </div>
                {picks.length > 0 && <div style={{ marginTop: 6, fontSize: 11.5, fontWeight: 700 }}>This week's picks: {picks.join(', ')}</div>}
              </div>
            )
          })}
        </section>}

      {data && data.picks.length > 0 && <section className="panel" style={{ padding: 16 }}>
        <h3 style={{ marginTop: 0 }}>This week's picks vs their sector</h3>
        {data.picks.map(p => {
          const row = rows.find(r => r.sector === p.sector_index)
          const against = row && (row.trend === 'Lagging')
          return <div key={p.symbol} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--line)', fontSize: 13 }}>
            <span><b>{p.symbol}</b> <span className="mut">{p.name}</span></span>
            <span>
              {row ? <>{row.sector}: <b className={(row.rs_1m_pct ?? 0) >= 0 ? 'pos' : 'neg'}>{signed(row.rs_1m_pct)}</b> vs NIFTY · {against ? <b className="neg">Fighting a weak sector</b> : <b className="pos">Sector supports the trade</b>}</>
                : <span className="mut">Sector unknown</span>}
            </span>
          </div>
        })}
      </section>}
    </div>
  )
}
