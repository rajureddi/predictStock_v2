import { createContext, useContext } from 'react'
import { Warning } from '@phosphor-icons/react'

/* ---------- theme ---------- */
export type Theme = 'light' | 'dark'
export const ThemeCtx = createContext<Theme>('light')
/** Orb theme for the current surface; `onInk` is for orbs sitting on an ink-filled button. */
export const useOrb = (onInk = false): Theme => {
  const t = useContext(ThemeCtx)
  return onInk ? (t === 'light' ? 'dark' : 'light') : t
}
const PALETTES = {
  light: { ink: '#0A0A0C', mut: '#5E636C', faint: '#9A9EA6', up: '#1E9E5A', down: '#D64545', accent: '#FF5500', amber: '#C47C00', line: 'rgba(10,10,12,.09)', surface: '#FFFFFF', tip: '#0A0A0C', track: 'rgba(10,10,12,.08)' },
  dark: { ink: '#ECEDEF', mut: '#9298A2', faint: '#6B7079', up: '#3CCB7F', down: '#F06363', accent: '#FF6A1F', amber: '#E0A03A', line: 'rgba(255,255,255,.08)', surface: '#141518', tip: '#2A2D33', track: 'rgba(255,255,255,.1)' },
}
export const applyPalette = (t: Theme) => Object.assign(C, PALETTES[t])

/* ---------- formatting ---------- */
export const inr = (n?: number | null) => n == null ? '—' : '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })
export const pct = (n?: number | null, d = 2) => n == null ? '—' : (n >= 0 ? '+' : '') + Number(n).toFixed(d) + '%'
export const num = (n?: number | null, d = 1) => n == null ? '—' : Number(n).toFixed(d)
export const crores = (n?: number | null) => n == null ? '—' : '₹' + Math.round(n / 1e7).toLocaleString('en-IN') + ' Cr'

export const C = { ...PALETTES.light }

/* ---------- price series (real API data, cached per symbol) ---------- */
const chartCache: Record<string, Promise<any[]>> = {}
export function fetchSeries(symbol: string, exchange: string): Promise<any[]> {
  const key = `${exchange}:${symbol}`
  if (!chartCache[key]) {
    chartCache[key] = fetch(`/api/prices/${encodeURIComponent(symbol)}?days=90&exchange=${exchange}`)
      .then(r => r.json()).then(j => j.series || []).catch(() => [])
  }
  return chartCache[key]
}

/* ---------- trader-score radial ---------- */
export function ScoreRing({ score, size = 66 }: { score: number; size?: number }) {
  const r = 26, c = 2 * Math.PI * r, frac = Math.max(0, Math.min(100, score)) / 100
  const col = score >= 75 ? C.up : score >= 60 ? C.ink : '#B86E00'
  return (<svg width={size} height={size} viewBox="0 0 66 66" aria-hidden="true">
    <circle cx="33" cy="33" r={r} fill="none" stroke={C.track} strokeWidth="5" />
    <circle cx="33" cy="33" r={r} fill="none" stroke={col} strokeWidth="5" strokeLinecap="round"
      strokeDasharray={`${(frac * c).toFixed(1)} ${c.toFixed(1)}`} transform="rotate(-90 33 33)" />
    <text x="33" y="38.5" textAnchor="middle" fill={C.ink} fontSize="16" fontWeight="500" fontFamily="Geist Mono Variable">{Math.round(score)}</text>
  </svg>)
}

/* ---------- likely-range bar ---------- */
export function RangeBar({ p }: { p: any }) {
  const marks = [
    { v: p.stop_loss, lbl: 'Stop-loss', col: C.down },
    { v: p.range_low, lbl: 'Range low', col: '#A3A7AF' },
    { v: p.current_price, lbl: 'Now', col: C.ink },
    { v: p.predicted_price, lbl: 'Predicted', col: C.accent },
    { v: p.target, lbl: 'Target', col: C.up },
    { v: p.range_high, lbl: 'Range high', col: '#A3A7AF' },
  ].filter(m => m.v != null)
  if (marks.length < 3) return null
  const lo = Math.min(...marks.map(m => m.v)), hi = Math.max(...marks.map(m => m.v))
  const pad = (hi - lo) * 0.06 || 1
  const pos = (v: number) => Math.max(2, Math.min(98, ((v - (lo - pad)) / ((hi + pad) - (lo - pad))) * 100))
  // stagger labels onto two rows so close markers (Now vs Range low,
  // Target vs Predicted) never collide
  const placed = marks.map(m => ({ ...m, x: pos(m.v), row: 0 })).sort((a, b) => a.x - b.x)
  const lastOnRow = [-100, -100]
  placed.forEach(m => { m.row = (m.x - lastOnRow[0] >= 15) ? 0 : 1; lastOnRow[m.row] = m.x })
  const twoRows = placed.some(m => m.row === 1)
  return (<div className="rangewrap" style={{ paddingBottom: twoRows ? 58 : 38 }}><div className="rangebar"><div className="track">
    {placed.map((m, i) => <span key={i}>
      <span className="mark" style={{ left: `${m.x}%`, background: m.col }} />
      <span className="marklbl" style={{ left: `${m.x}%`, top: m.row === 0 ? 14 : 34 }}>{m.lbl}<b className="num">{inr(m.v)}</b></span>
    </span>)}
  </div></div></div>)
}

/* ---------- fundamentals / news ---------- */
function flagClass(f: string) {
  const t = f.toLowerCase()
  if (/(strong roe|growth \+|revenue growth)/.test(t)) return 'flag good'
  if (/(loss-making|high debt|very high)/.test(t)) return 'flag bad'
  return 'flag warn'
}
export function Fundamentals({ f }: { f: any }) {
  if (!f) return <div><h4 className="subhead">Fundamentals</h4><div className="mut">Fundamentals data unavailable for this stock.</div></div>
  return (<div>
    <h4 className="subhead">Fundamentals check</h4>
    <div className="fscore"><span className="n num">{num(f.score, 0)}</span><span className="mut">/ 100 quality score</span>
      <span className="track"><span className="fill" style={{ width: `${f.score ?? 0}%`, display: 'block' }} /></span></div>
    <div className="tiles">
      <div className="tile"><div className="k">P/E ratio</div><div className="v num">{num(f.pe)}</div></div>
      <div className="tile"><div className="k">ROE</div><div className="v num">{f.roe == null ? '—' : pct(f.roe * 100, 1)}</div></div>
      <div className="tile"><div className="k">Debt / Equity</div><div className="v num">{num(f.debt_to_equity, 2)}</div></div>
      <div className="tile"><div className="k">Earnings growth</div><div className="v num">{f.earnings_growth == null ? '—' : pct(f.earnings_growth * 100, 1)}</div></div>
      <div className="tile"><div className="k">Revenue growth</div><div className="v num">{f.revenue_growth == null ? '—' : pct(f.revenue_growth * 100, 1)}</div></div>
      <div className="tile"><div className="k">Market cap</div><div className="v num">{crores(f.market_cap)}</div></div>
    </div>
    {(f.flags || []).length > 0 && <div className="flags">{f.flags.map((x: string, i: number) => <div key={i} className={flagClass(x)}>{x}</div>)}</div>}
  </div>)
}
export function NewsPanel({ n }: { n: any }) {
  if (!n || !(n.headlines || []).length) return <div><h4 className="subhead">Latest news</h4><div className="mut">No significant news found in the last 14 days.</div></div>
  const cls = n.sentiment_label === 'Positive' ? 'pos' : n.sentiment_label === 'Negative' ? 'neg' : 'neu'
  return (<div>
    <h4 className="subhead">Latest news <span className={`sentchip ${cls}`}>{n.sentiment_label} · {n.sentiment_score > 0 ? '+' : ''}{n.sentiment_score}</span></h4>
    {n.veto && <div className="flags" style={{ margin: '0 0 8px' }}><div className="flag bad"><Warning size={15} weight="bold" /> Veto headline: {n.veto_reason}</div></div>}
    {n.headlines.map((h: any, i: number) => <a key={i} className="newsitem" href={h.url} target="_blank" rel="noreferrer">
      <div className="t">{h.title}</div><div className="m">{h.source || 'Google News'}{h.date ? ` · ${h.date}` : ''}</div></a>)}
  </div>)
}

/* ---------- portfolio storage (browser only) ---------- */
export type Holding = { symbol: string; exchange: string; name: string; shares: number; buy: number; added: string; predicted?: number; target?: number; stop?: number }
const PKEY = 'marketmind.portfolio.v1'
export const loadHoldings = (): Holding[] => { try { return JSON.parse(localStorage.getItem(PKEY) || '[]') } catch { return [] } }
export const saveHoldings = (h: Holding[]) => { try { localStorage.setItem(PKEY, JSON.stringify(h)) } catch { /* storage full or blocked */ } }
export const holdingFromPick = (p: any, shares: number, buy: number): Holding => ({
  symbol: p.symbol, exchange: p.exchange, name: p.name, shares, buy,
  added: new Date().toISOString().slice(0, 10),
  predicted: p.predicted_price ?? undefined, target: p.target ?? undefined, stop: p.stop_loss ?? undefined,
})
