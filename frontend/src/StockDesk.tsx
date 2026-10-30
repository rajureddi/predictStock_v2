import { useEffect, useMemo, useRef, useState } from 'react'
import { ThinkingOrb } from 'thinking-orbs'
import {
  ArrowLeft, CaretLeft, CaretRight, ChartBar, CheckCircle, ClockCounterClockwise, DiceFive,
  Lightning, Plus, ShieldCheck, Warning, XCircle, Briefcase,
} from '@phosphor-icons/react'
import { C, Fundamentals, Holding, NewsPanel, RangeBar, ScoreRing, fetchSeries, inr, num, pct, useOrb } from './lib'

function useSeries(symbol: string, exchange: string) {
  const [rows, setRows] = useState<any[] | null>(null)
  useEffect(() => {
    let on = true
    setRows(null)
    fetchSeries(symbol, exchange).then(s => { if (on) setRows(s) })
    return () => { on = false }
  }, [symbol, exchange])
  return rows
}

const sma = (v: number[], n: number) => v.map((_, i) => i < n - 1 ? null : v.slice(i - n + 1, i + 1).reduce((s, x) => s + x, 0) / n)
const shortDate = (d: string) => { const t = new Date(d); return isNaN(+t) ? d : t.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) }

/* ---------- desk chart: close, 20-DMA, forecast cone ---------- */
function DeskChart({ p, rows, range, targetDate }: { p: any; rows: any[]; range: '1M' | '3M'; targetDate?: string }) {
  const [hover, setHover] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const allCloses = rows.map(r => r.close)
  const allDma = sma(allCloses, 20)
  const start = range === '1M' ? Math.max(0, rows.length - 22) : 0
  const view = rows.slice(start), closes = allCloses.slice(start), dma = allDma.slice(start)
  const n = view.length, F = 5
  const W = 960, H = 340, L = 8, R = 78, T = 16, B = 30
  const last = closes[n - 1]
  const pred: number | null = p.predicted_price ?? null
  const hiBand: number | null = p.range_high ?? p.simulation?.expected_p95 ?? null
  const loBand: number | null = p.range_low ?? p.simulation?.expected_p5 ?? null
  const near = (v: any) => v != null && Math.abs(v / last - 1) < 0.25
  const dom = [...closes, ...dma.filter(v => v != null) as number[], ...[pred, hiBand, loBand, p.target, p.stop_loss].filter(near) as number[]]
  const lo0 = Math.min(...dom), hi0 = Math.max(...dom), padv = (hi0 - lo0) * 0.08 || 1
  const lo = lo0 - padv, hi = hi0 + padv
  const plotW = W - L - R, histW = pred != null ? plotW * 0.84 : plotW
  const steps = pred != null ? n - 1 + F : n - 1
  const X = (i: number) => i <= n - 1 ? L + (i / Math.max(1, n - 1)) * histW : L + histW + ((i - n + 1) / F) * (plotW - histW)
  const Y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B)
  const up = last >= closes[0]
  const col = up ? C.up : C.down
  const line = closes.map((c, i) => `${X(i).toFixed(1)},${Y(c).toFixed(1)}`).join(' ')
  const area = `${X(0)},${H - B} ${line} ${X(n - 1).toFixed(1)},${H - B}`
  const dmaPts = dma.map((v, i) => v == null ? null : `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).filter(Boolean).join(' ')
  const marks = [p.target, p.stop_loss].filter(near).map((v: number) => Y(v))
  const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * (i + 0.5)) / 5).filter(t => marks.every(m => Math.abs(Y(t) - m) > 14))
  const xt = Array.from({ length: pred != null ? 5 : 6 }, (_, i) => Math.round((i * (n - 1)) / 5))
  const stopY = near(p.stop_loss) && near(p.target) && Math.abs(Y(p.stop_loss) - Y(p.target)) < 13 ? Y(p.target) + 13 : near(p.stop_loss) ? Y(p.stop_loss) : 0
  const lx = X(n - 1), ly = Y(last), ex = X(steps)
  const hRow = hover != null ? view[hover] : null

  const onMove = (e: React.PointerEvent) => {
    const r = svgRef.current!.getBoundingClientRect()
    const sx = ((e.clientX - r.left) / r.width) * W
    const i = Math.round(((sx - L) / histW) * (n - 1))
    setHover(i >= 0 && i < n ? i : null)
  }

  return (<svg ref={svgRef} className="deskchart" viewBox={`0 0 ${W} ${H}`} role="img"
    aria-label={`${p.symbol} ${range} price chart with forecast to ${inr(pred)}`}
    onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
    <defs>
      <linearGradient id="dk-area" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={col} stopOpacity="0.16" /><stop offset="100%" stopColor={col} stopOpacity="0" />
      </linearGradient>
    </defs>
    {ticks.map((t, i) => <g key={i}>
      <line x1={L} x2={W - R} y1={Y(t)} y2={Y(t)} stroke={C.line} />
      <text x={W - R + 8} y={Y(t) + 4} className="ax">{inr(Math.round(t))}</text>
    </g>)}
    {xt.map((i, k) => <text key={k} x={X(i)} y={H - 9} className="ax" textAnchor={k === 0 ? 'start' : 'middle'}>{shortDate(view[i].date)}</text>)}
    {pred != null && <>
      <rect x={lx} y={T} width={ex - lx} height={H - T - B} fill="rgba(255,85,0,.035)" />
      <text x={ex} y={H - 9} className="ax acc" textAnchor="end">{targetDate ? shortDate(targetDate) : 'Target'}</text>
    </>}
    {near(p.target) && <g><line x1={L} x2={W - R} y1={Y(p.target)} y2={Y(p.target)} stroke={C.up} strokeDasharray="2 5" opacity=".7" />
      <text x={W - R + 8} y={Y(p.target) + 4} className="ax up">Target</text></g>}
    {near(p.stop_loss) && <g><line x1={L} x2={W - R} y1={Y(p.stop_loss)} y2={Y(p.stop_loss)} stroke={C.down} strokeDasharray="2 5" opacity=".7" />
      <text x={W - R + 8} y={stopY + 4} className="ax dn">Stop</text></g>}
    <polygon points={area} fill="url(#dk-area)" />
    {dmaPts && <polyline points={dmaPts} fill="none" stroke={C.amber} strokeWidth="1.6" strokeDasharray="4 4" />}
    <polyline points={line} fill="none" stroke={col} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
    {pred != null && <>
      {near(hiBand) && near(loBand) && <polygon points={`${lx},${ly} ${ex},${Y(hiBand!)} ${ex},${Y(loBand!)}`} fill="rgba(255,85,0,.12)" stroke="rgba(255,85,0,.35)" strokeWidth="1" />}
      <line x1={lx} y1={ly} x2={ex} y2={Y(pred)} stroke={C.accent} strokeWidth="2.2" strokeDasharray="6 5" />
      {Array.from({ length: F }, (_, k) => {
        const f = (k + 1) / F
        return <circle key={k} cx={lx + (ex - lx) * f} cy={ly + (Y(pred) - ly) * f} r={k === F - 1 ? 5 : 3} fill={C.accent} stroke={C.surface} strokeWidth="1.5" />
      })}
      <text x={ex - 8} y={Y(pred) < 40 ? Y(pred) + 22 : Y(pred) - 12} className="ax acc strong" textAnchor="end">{inr(pred)}</text>
    </>}
    <circle cx={lx} cy={ly} r="4.5" fill={col} stroke={C.surface} strokeWidth="2" />
    {hRow && <g pointerEvents="none">
      <line x1={X(hover!)} x2={X(hover!)} y1={T} y2={H - B} stroke={C.faint} />
      <circle cx={X(hover!)} cy={Y(closes[hover!])} r="4" fill={C.ink} stroke={C.surface} strokeWidth="2" />
      <g transform={`translate(${Math.min(X(hover!) + 10, W - R - 150)},${T + 6})`}>
        <rect width="140" height={dma[hover!] != null ? 56 : 40} rx="8" fill={C.tip} />
        <text x="10" y="17" className="tt mut">{shortDate(hRow.date)}</text>
        <text x="10" y="33" className="tt">Close {inr(closes[hover!])}</text>
        {dma[hover!] != null && <text x="10" y="48" className="tt amb">20-DMA {inr(Math.round(dma[hover!]! * 100) / 100)}</text>}
      </g>
    </g>}
  </svg>)
}

/* ---------- evidence checklist for "why this stock" ---------- */
function evidence(p: any) {
  const e: { ok: boolean | null; t: string }[] = []
  if (p.quality_pass != null) e.push({ ok: !!p.quality_pass, t: p.quality_pass ? 'Beat the naive baseline in a walk-forward backtest' : 'Did not beat the naive baseline' })
  if (p.backtest?.best_dir_acc != null) e.push({ ok: p.backtest.best_dir_acc >= 55, t: `${p.backtest.best_dir_acc}% direction accuracy in backtest · MAPE ${p.backtest.best_mape ?? '—'}%` })
  if (p.simulation) e.push({ ok: p.simulation.win_probability_pct >= p.simulation.loss_probability_pct, t: `${p.simulation.win_probability_pct}% target odds vs ${p.simulation.loss_probability_pct}% stop-loss risk over ${p.simulation.replays?.toLocaleString() ?? '—'} replays` })
  if (p.fundamentals?.score != null) e.push({ ok: p.fundamentals.score >= 50, t: `Fundamentals quality score ${num(p.fundamentals.score, 0)} / 100` })
  if (p.news) e.push({ ok: p.news.veto ? false : p.news.sentiment_label === 'Negative' ? null : true, t: p.news.veto ? `News veto: ${p.news.veto_reason}` : `News sentiment ${p.news.sentiment_label ?? 'neutral'}, no severe headlines` })
  if (p.risk_reward != null) e.push({ ok: p.risk_reward >= 1.5, t: `Risk : reward of 1 : ${p.risk_reward}` })
  if (p.volume_ratio != null) e.push({ ok: p.volume_ratio >= 1, t: `Volume at ${p.volume_ratio}× its average` })
  return e
}

/* ---------- the desk ---------- */
export default function StockDesk({ list, idx, targetDate, holding, onSelect, onBack, onSaveHolding, onRemoveHolding, backLabel }: {
  list: any[]; idx: number; targetDate?: string; holding?: Holding
  onSelect: (i: number) => void; onBack: () => void
  onSaveHolding: (p: any, shares: number, buy: number) => void; onRemoveHolding: (symbol: string) => void
  backLabel?: string
}) {
  const p = list[idx]
  const orb = useOrb()
  const rows = useSeries(p.symbol, p.exchange)
  const [range, setRange] = useState<'1M' | '3M'>('3M')
  const [shares, setShares] = useState('')
  const [buy, setBuy] = useState('')
  useEffect(() => {
    setShares(String(holding?.shares ?? p.shares ?? 1))
    setBuy(String(holding?.buy ?? p.current_price ?? ''))
  }, [p.symbol, holding?.shares, holding?.buy])
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'smooth' }) }, [idx])

  const day = useMemo(() => {
    if (!rows || rows.length < 2) return null
    const a = rows[rows.length - 2].close, b = rows[rows.length - 1].close
    return { abs: b - a, pct: (b / a - 1) * 100 }
  }, [rows])
  const up = (p.predicted_return_pct ?? 0) >= 0
  const winning = p.simulation && p.simulation.win_probability_pct >= p.simulation.loss_probability_pct
  const ev = evidence(p)
  const sh = Number(shares), bp = Number(buy)
  const valid = sh > 0 && bp > 0

  return (<div className="desk">
    <div className="desk-bar">
      <button className="btn ghost" onClick={onBack}><ArrowLeft size={15} weight="bold" /> {backLabel || 'All picks'}</button>
      {list.length > 1 ? (
        <div className="desk-step num">
          <button className="iconbtn" onClick={() => onSelect((idx - 1 + list.length) % list.length)} aria-label="Previous pick"><CaretLeft size={15} weight="bold" /></button>
          Pick {idx + 1} of {list.length}
          <button className="iconbtn" onClick={() => onSelect((idx + 1) % list.length)} aria-label="Next pick"><CaretRight size={15} weight="bold" /></button>
        </div>
      ) : (
        <div className="desk-step num">5-Day ML Prediction Desk</div>
      )}
    </div>

    <div className="desk-grid">
      <section className="panel desk-main" aria-label={`${p.name} chart`}>
        <div className="desk-head">
          <div className="desk-id">
            <h2>{p.name}</h2>
            <div className="chips">
              <span className="chip exch">{p.symbol} · {p.exchange}</span>
              {p.quality_pass && <span className="chip pass"><CheckCircle size={13} weight="bold" /> Quality pass</span>}
              {p.news?.veto && <span className="chip neg"><Warning size={13} weight="bold" /> News veto</span>}
              {(p.patterns || []).map((x: string, j: number) => <span key={j} className="chip pat">{x}</span>)}
            </div>
          </div>
          <div className="desk-price">
            <span className="big num">{inr(p.current_price)}</span>
            {day && <span className={`retpill sm num ${day.pct >= 0 ? 'up' : 'dn'}`}>{pct(day.pct)} 1D</span>}
          </div>
        </div>
        <div className="desk-sub num">
          <span>Predicted <b className="acc">{inr(p.predicted_price)}</b> <span className={up ? 'pos' : 'neg'}>({pct(p.predicted_return_pct)})</span></span>
          {p.atr != null && <span>ATR {inr(p.atr)}</span>}
          <span>Model {p.model_used || '—'}</span>
        </div>

        {(p.actual_price != null || p.live_price != null) && (
          <div className="hist-perf-strip">
            <div className="hp-cell">
              <span className="hp-label">Was Price (Entry)</span>
              <span className="hp-val num">{inr(p.current_price)}</span>
              <span className="hp-sub">{p.run_date ? `Week of ${p.run_date}` : 'Initial Price'}</span>
            </div>
            <div className="hp-cell">
              <span className="hp-label">5-Day Target</span>
              <span className="hp-val num acc">{inr(p.predicted_price)}</span>
              <span className={`hp-sub ${up ? 'pos' : 'neg'}`}>{pct(p.predicted_return_pct)} expected</span>
            </div>
            <div className="hp-cell">
              <span className="hp-label">{p.actual_price != null ? '5-Day Actual Close' : 'Live Tracking Price'}</span>
              <span className="hp-val num">{inr(p.actual_price ?? p.live_price)}</span>
              <span className={`hp-sub ${(p.actual_return_pct ?? p.live_return_pct ?? 0) >= 0 ? 'pos' : 'neg'}`}>
                {p.actual_return_pct != null ? pct(p.actual_return_pct) : pct(p.live_return_pct) + ' live'}
              </span>
            </div>
            <div className="hp-cell">
              <span className="hp-label">5-Day Net Delta</span>
              <span className={`hp-val num ${((p.actual_price ?? p.live_price) - p.current_price) >= 0 ? 'pos' : 'neg'}`}>
                {inr((p.actual_price ?? p.live_price) - p.current_price)}
              </span>
              <span className="hp-sub">Per share outcome</span>
            </div>
            <div className="hp-cell">
              <span className="hp-label">Forecast Outcome</span>
              <span className={`hitmiss ${p.actual_price != null ? (Math.sign(p.actual_return_pct) === Math.sign(p.predicted_return_pct) ? 'hit' : 'miss') : 'pend'}`}>
                {p.actual_price != null ? (Math.sign(p.actual_return_pct) === Math.sign(p.predicted_return_pct) ? '✓ TARGET HIT' : '✗ STOP / MISS') : '⏳ PENDING'}
              </span>
              <span className="hp-sub">{targetDate ? `Target ${targetDate}` : '5-day outcome'}</span>
            </div>
          </div>
        )}

        <div className="desk-tools">
          <div className="legend">
            <span><i style={{ background: up ? C.up : C.down }} />Close</span>
            <span><i className="dash" style={{ borderColor: C.amber }} />20-DMA</span>
            <span><i className="dash" style={{ borderColor: C.accent }} />Forecast</span>
            <span><i className="cone" />Likely range</span>
          </div>
          <div className="seg" role="group" aria-label="Chart range">
            {(['1M', '3M'] as const).map(r => <button key={r} className={range === r ? 'on' : ''} aria-pressed={range === r} onClick={() => setRange(r)}>{r}</button>)}
          </div>
        </div>
        {rows === null
          ? <div className="chartload tall"><ThinkingOrb state="working" size={32} theme={orb} />Loading price history…</div>
          : rows.length < 5 ? <div className="chartload tall">Price chart unavailable for this stock.</div>
            : <DeskChart p={p} rows={rows} range={range} targetDate={targetDate} />}

        <div className="metrics">
          <div><span className="k">Expected gain</span><span className={`v num ${up ? 'pos' : 'neg'}`}>{pct(p.predicted_return_pct)}</span></div>
          <div><span className="k">Expected range</span><span className="v num">{inr(p.range_low)} – {inr(p.range_high)}</span></div>
          <div><span className="k">Support</span><span className="v num">{inr(p.support)}</span></div>
          <div><span className="k">Resistance</span><span className="v num">{inr(p.resistance)}</span></div>
          <div><span className="k">P/E</span><span className="v num">{num(p.fundamentals?.pe)}</span></div>
          <div><span className="k">ROE</span><span className="v num">{p.fundamentals?.roe == null ? '—' : pct(p.fundamentals.roe * 100, 1)}</span></div>
          <div><span className="k">Debt / Equity</span><span className="v num">{num(p.fundamentals?.debt_to_equity, 2)}</span></div>
          <div><span className="k">Revenue growth</span><span className="v num">{p.fundamentals?.revenue_growth == null ? '—' : pct(p.fundamentals.revenue_growth * 100, 1)}</span></div>
        </div>
      </section>

      <aside className="desk-side">
        <section className="panel forecast">
          <h3>7-day forecast</h3>
          <div className="fc-target">
            <span className="k">Predicted price</span>
            <span className="v num">{inr(p.predicted_price)}</span>
            <span className="r num">Range {inr(p.range_low)} – {inr(p.range_high)}</span>
          </div>
          <div className="fc-grid">
            <div><span className="k">Direction</span><span className={`dirchip ${up ? 'up' : 'dn'}`}>{up ? 'Bullish' : 'Bearish'}</span></div>
            <div className="ring"><ScoreRing score={p.trader_score ?? 0} size={48} /><span className="k">Trader score</span></div>
            <div><span className="k">Backtest accuracy</span><span className="v num">{p.backtest?.best_dir_acc ?? '—'}%</span></div>
            <div><span className="k">Risk : reward</span><span className="v num">1 : {p.risk_reward ?? '—'}</span></div>
            <div><span className="k">Stop-loss</span><span className="v num neg">{inr(p.stop_loss)}</span></div>
            <div><span className="k">Target 1 / 2</span><span className="v num pos">{inr(p.target)} <small>/ {inr(p.target2)}</small></span></div>
          </div>
          <div className="pf-add">
            <div className="pf-fields">
              <label><span>Shares</span><input type="number" min="1" value={shares} onChange={e => setShares(e.target.value)} /></label>
              <label><span>Buy price</span><input type="number" min="0" step="0.05" value={buy} onChange={e => setBuy(e.target.value)} /></label>
            </div>
            <button className="btn dark wide" disabled={!valid} onClick={() => onSaveHolding(p, sh, bp)}>
              {holding ? <><Briefcase size={15} weight="bold" /> Update holding</> : <><Plus size={15} weight="bold" /> Add to portfolio</>}
            </button>
            {holding && <button className="btn ghost wide" onClick={() => onRemoveHolding(p.symbol)}>Remove from portfolio</button>}
            {valid && <div className="pf-calc num">Cost {inr(sh * bp)} · at prediction {inr(sh * (p.predicted_price ?? bp))}</div>}
          </div>
        </section>
      </aside>
    </div>

    <section className="panel why">
      <div className="why-reasons">
        <h3>Why we chose {p.symbol}</h3>
        <ul className="reasons">{(p.reasons || []).map((r: string, j: number) => <li key={j}>{r}</li>)}</ul>
        {!(p.reasons || []).length && <p className="mut">No trader reasons were recorded for this pick.</p>}
        <RangeBar p={p} />
      </div>
      <div className="why-evidence">
        <h3>Evidence checks</h3>
        <ul className="evid">{ev.map((x, j) => <li key={j} className={x.ok === true ? 'ok' : x.ok === false ? 'bad' : 'warn'}>
          {x.ok === true ? <ShieldCheck size={16} weight="bold" /> : x.ok === false ? <XCircle size={16} weight="bold" /> : <Warning size={16} weight="bold" />}
          <span>{x.t}</span>
        </li>)}</ul>
        <div className="tiles">
          <div className="tile"><div className="k">RSI · ADX</div><div className="v num">{p.rsi ?? '—'} · {p.adx ?? '—'}</div></div>
          <div className="tile"><div className="k">Volume vs avg</div><div className="v num">{p.volume_ratio ?? '—'}×</div></div>
          <div className="tile"><div className="k">Delivery %</div><div className="v num">{p.delivery_pct == null ? '—' : num(p.delivery_pct) + '%'}</div></div>
          <div className="tile"><div className="k">52-week high</div><div className="v num">{inr(p.high52)}</div></div>
        </div>
      </div>
    </section>

    <div className="desk-lower">
      {p.simulation && <section className="panel sim-panel">
        <div className="sim-head">
          <span className="title"><ClockCounterClockwise size={16} weight="bold" /> Time Machine Simulation ({p.simulation.replays?.toLocaleString()} Replays)</span>
          <span className="method-tag">{p.simulation.method?.includes('5-minute')
            ? <><Lightning size={12} weight="bold" /> 5-min Intraday</>
            : <><ChartBar size={12} weight="bold" /> 5-Day Swing</>}</span>
          <span className={`verdict-badge ${winning ? 'pos' : 'neg'}`}>{p.simulation.verdict}</span>
        </div>
        <div className="sim-grid">
          <div className="sim-item"><span className="k"><DiceFive size={12} weight="bold" /> Target Win Odds</span><span className="v num pos">{p.simulation.win_probability_pct}%</span></div>
          <div className="sim-item"><span className="k">Stop-Loss Risk Odds</span><span className="v num neg">{p.simulation.loss_probability_pct}%</span></div>
          <div className="sim-item"><span className="k">Median Expected</span><span className="v num">{inr(p.simulation.median_close)}</span></div>
          <div className="sim-item"><span className="k">90% Price Range</span><span className="v num" style={{ fontSize: 12.5 }}>{inr(p.simulation.expected_p5)} to {inr(p.simulation.expected_p95)}</span></div>
          {p.orb && <div className="sim-item"><span className="k">Opening Breakout (ORB)</span>
            <span className={`v ${p.orb.status === 'triggered' ? 'pos' : 'mut'}`} style={{ fontSize: 13 }}>
              {p.orb.status === 'triggered' ? `Triggered (${inr(p.orb.trigger_price)})` : (p.orb.status?.toUpperCase() || 'FORMING')}
            </span></div>}
        </div>
      </section>}
      <section className="panel pad"><Fundamentals f={p.fundamentals} /></section>
      <section className="panel pad"><NewsPanel n={p.news} /></section>
    </div>
  </div>)
}
