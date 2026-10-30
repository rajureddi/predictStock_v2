import { useEffect, useMemo, useRef, useState } from 'react'
import { ThinkingOrb } from 'thinking-orbs'

/* ---------- formatting ---------- */
const inr = (n?: number | null) => n == null ? '—' : '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })
const pct = (n?: number | null, d = 2) => n == null ? '—' : (n >= 0 ? '+' : '') + Number(n).toFixed(d) + '%'
const num = (n?: number | null, d = 1) => n == null ? '—' : Number(n).toFixed(d)
const crores = (n?: number | null) => n == null ? '—' : '₹' + Math.round(n / 1e7).toLocaleString('en-IN') + ' Cr'

/* ---------- price chart (hand-rolled SVG, real API data) ---------- */
const chartCache: Record<string, Promise<any>> = {}
function fetchSeries(symbol: string, exchange: string) {
  const key = `${exchange}:${symbol}`
  if (!chartCache[key]) {
    chartCache[key] = fetch(`/api/prices/${encodeURIComponent(symbol)}?days=90&exchange=${exchange}`)
      .then(r => r.json()).then(j => j.series || []).catch(() => [])
  }
  return chartCache[key]
}

function PriceChart({ symbol, exchange, predicted }: { symbol: string; exchange: string; predicted?: number }) {
  const [rows, setRows] = useState<any[] | null>(null)
  useEffect(() => {
    let on = true
    fetchSeries(symbol, exchange).then(s => { if (on) setRows(s) })
    return () => { on = false }
  }, [symbol, exchange])
  if (rows === null) return <div className="chartload"><ThinkingOrb state="working" size={20} theme="dark" />Loading price chart…</div>
  if (rows.length < 5) return <div className="chartload">Price chart unavailable for this stock.</div>
  const W = 560, H = 148, PAD = 6, EXT = predicted ? 64 : 0
  const closes = rows.map(r => r.close)
  const all = predicted ? [...closes, predicted] : closes
  const lo = Math.min(...all), hi = Math.max(...all), span = (hi - lo) || 1
  const X = (i: number) => PAD + (i / (rows.length - 1)) * (W - PAD * 2 - EXT)
  const Y = (v: number) => H - 14 - ((v - lo) / span) * (H - 28)
  const pts = closes.map((c, i) => `${X(i).toFixed(1)},${Y(c).toFixed(1)}`).join(' ')
  const area = `${PAD},${H - 8} ${pts} ${X(rows.length - 1).toFixed(1)},${H - 8}`
  const lastX = X(rows.length - 1), lastY = Y(closes[closes.length - 1])
  const up = closes[closes.length - 1] >= closes[0]
  const col = up ? '#31c774' : '#ff6b6b'
  const first = rows[0], last = rows[rows.length - 1]
  const chg = ((last.close / first.close) - 1) * 100
  return (<div className="chartbox">
    <div className="chead"><span>90-day price · {first.date} → {last.date}</span><span className={chg >= 0 ? 'pos' : 'neg'}>{pct(chg)} over period</span></div>
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }} role="img" aria-label={`${symbol} 90 day price chart`}>
      <defs>
        <linearGradient id={`ag-${symbol}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={col} stopOpacity="0.32" /><stop offset="100%" stopColor={col} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#ag-${symbol})`} />
      <polyline points={pts} fill="none" stroke={col} strokeWidth="2" strokeLinejoin="round" />
      {predicted != null && <>
        <line x1={lastX} y1={lastY} x2={W - PAD - 4} y2={Y(predicted)} stroke="#ecd27a" strokeWidth="2" strokeDasharray="5 4" />
        <circle cx={W - PAD - 4} cy={Y(predicted)} r="4.5" fill="#ecd27a" stroke="#0a1322" strokeWidth="2" />
        <text x={W - PAD - 4} y={Y(predicted) < 30 ? Y(predicted) + 18 : Y(predicted) - 10} fill="#ecd27a" fontSize="11.5" fontWeight="700" textAnchor="end" fontFamily="Space Grotesk">{inr(predicted)}</text>
      </>}
      <circle cx={lastX} cy={lastY} r="4" fill={col} stroke="#0a1322" strokeWidth="2" />
      {!(predicted != null && predicted >= hi * 0.98) && <text x={PAD} y={12} fill="#5f748e" fontSize="10.5">{inr(hi)}</text>}
      <text x={PAD} y={H - 2} fill="#5f748e" fontSize="10.5">{inr(lo)}</text>
    </svg>
  </div>)
}

/* ---------- trader-score radial ---------- */
function ScoreRing({ score }: { score: number }) {
  const r = 26, c = 2 * Math.PI * r, frac = Math.max(0, Math.min(100, score)) / 100
  const col = score >= 75 ? '#31c774' : score >= 60 ? '#ecd27a' : '#f5a524'
  return (<svg width="66" height="66" viewBox="0 0 66 66">
    <circle cx="33" cy="33" r={r} fill="none" stroke="rgba(148,178,216,.18)" strokeWidth="6" />
    <circle cx="33" cy="33" r={r} fill="none" stroke={col} strokeWidth="6" strokeLinecap="round"
      strokeDasharray={`${(frac * c).toFixed(1)} ${c.toFixed(1)}`} transform="rotate(-90 33 33)" />
    <text x="33" y="38.5" textAnchor="middle" fill="#eaf1f9" fontSize="16" fontWeight="700" fontFamily="Space Grotesk">{Math.round(score)}</text>
  </svg>)
}

/* ---------- percentage bar with positive/negative color variants ---------- */
function PctBar({ val, max = 25 }: { val?: number | null; max?: number }) {
  if (val == null) return <span className="mut">—</span>
  const pos = val >= 0
  const abs = Math.abs(val)
  const widthPct = Math.min(100, Math.max(12, Math.round((abs / max) * 100)))
  return (
    <div className={`pct-bar-cell ${pos ? 'pos' : 'neg'}`} title={`${pos ? '+' : ''}${val.toFixed(2)}%`}>
      <span className="pct-bar-track">
        <span className={`pct-bar-fill ${pos ? 'pos' : 'neg'}`} style={{ width: `${widthPct}%` }} />
      </span>
      <span className={`pct-badge ${pos ? 'pos' : 'neg'}`}>{pct(val)}</span>
    </div>
  )
}

/* ---------- likely-range bar ---------- */
function RangeBar({ p }: { p: any }) {
  const marks = [
    { v: p.stop_loss, lbl: 'Stop-loss', col: '#ff6b6b' },
    { v: p.range_low, lbl: 'Range low', col: '#93a9c0' },
    { v: p.current_price, lbl: 'Now', col: '#ecd27a' },
    { v: p.predicted_price, lbl: 'Predicted', col: '#31c774' },
    { v: p.target, lbl: 'Target', col: '#5cc8e6' },
    { v: p.range_high, lbl: 'Range high', col: '#93a9c0' },
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
  return (<div className="rangewrap" style={{ paddingBottom: twoRows ? 56 : 36 }}><div className="rangebar"><div className="track">
    {placed.map((m, i) => <span key={i}>
      <span className="mark" style={{ left: `${m.x}%`, background: m.col }} />
      <span className="marklbl" style={{ left: `${m.x}%`, top: m.row === 0 ? 14 : 33 }}>{m.lbl}<b className="num">{inr(m.v)}</b></span>
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
function Fundamentals({ f }: { f: any }) {
  if (!f) return <div><h4 className="subhead">Fundamentals</h4><div className="mut">Fundamentals data unavailable for this stock.</div></div>
  return (<div>
    <h4 className="subhead">Fundamentals check</h4>
    <div className="fscore"><span className="n num">{num(f.score, 0)}</span><span className="mut">/ 100 quality score</span>
      <span className="track"><span className="fill" style={{ width: `${f.score ?? 0}%`, display: 'block' }} /></span></div>
    <div className="tiles" style={{ marginTop: 0 }}>
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
function NewsPanel({ n }: { n: any }) {
  if (!n || !(n.headlines || []).length) return <div><h4 className="subhead">Latest news</h4><div className="mut">No significant news found in the last 14 days.</div></div>
  const cls = n.sentiment_label === 'Positive' ? 'pos' : n.sentiment_label === 'Negative' ? 'neg' : 'neu'
  return (<div>
    <h4 className="subhead">Latest news <span className={`sentchip ${cls}`} style={{ marginLeft: 8 }}>{n.sentiment_label} · {n.sentiment_score > 0 ? '+' : ''}{n.sentiment_score}</span></h4>
    {n.veto && <div className="flags" style={{ margin: '0 0 8px' }}><div className="flag bad">⚠ Veto headline: {n.veto_reason}</div></div>}
    {n.headlines.map((h: any, i: number) => <a key={i} className="newsitem" href={h.url} target="_blank" rel="noreferrer">
      <div className="t">{h.title}</div><div className="m">{h.source || 'Google News'}{h.date ? ` · ${h.date}` : ''}</div></a>)}
  </div>)
}

/* ---------- pick card ---------- */
function PickCard({ p, i }: { p: any; i: number }) {
  const up = (p.predicted_return_pct ?? 0) >= 0
  return (<article className="pick">
    <div className="pick-top">
      <div className="rankbadge">{i + 1}</div>
      <div className="pick-id">
        <h2>{p.name}</h2>
        <div className="chips">
          <span className="chip exch">{p.symbol} · {p.exchange}</span>
          {p.quality_pass && <span className="chip pass">✓ QUALITY PASS — beat baseline in backtest</span>}
          {p.simulation && (
            <span className={`chip ${p.simulation.win_probability_pct >= p.simulation.loss_probability_pct ? 'pass' : 'pat'}`}>
              🎲 {p.simulation.win_probability_pct}% Simulation Win Odds
            </span>
          )}
          {p.news?.veto && <span className="chip neg">⚠ NEWS VETO</span>}
          {(p.patterns || []).map((x: string, j: number) => <span key={j} className="chip pat">{x}</span>)}
        </div>
      </div>
      <div className="scorebox"><ScoreRing score={p.trader_score ?? 0} /><div className="lbl">Trader score</div></div>
      <div className="accbadge">
        <div className="big num">{p.backtest?.best_dir_acc ?? '—'}%</div>
        <div className="lbl">Backtest direction<br />accuracy · MAPE {p.backtest?.best_mape ?? '—'}%</div>
      </div>
    </div>
    <div className="pick-main">
      <div className="pick-left">
        <div className="priceflow">
          <div className="cur"><div className="k">Current price</div><div className="v num">{inr(p.current_price)}</div></div>
          <div className="arrow">➜</div>
          <div className="pred"><div className="k">Predicted · target date</div><div className="v num">{inr(p.predicted_price)}</div></div>
          <span className={`retpill ${up ? 'up' : 'dn'}`}>{pct(p.predicted_return_pct)}</span>
        </div>
        <RangeBar p={p} />
        <div className="tiles">
          <div className="tile"><div className="k">Stop-loss</div><div className="v num neg">{inr(p.stop_loss)}</div></div>
          <div className="tile"><div className="k">Target 1 / 2</div><div className="v num pos">{inr(p.target)} <span style={{ color: '#5f748e', fontSize: 12 }}>/ {inr(p.target2)}</span></div></div>
          <div className="tile"><div className="k">Risk : Reward</div><div className="v num">1 : {p.risk_reward ?? '—'}</div></div>
          <div className="tile"><div className="k">RSI · ADX</div><div className="v num">{p.rsi ?? '—'} · {p.adx ?? '—'}</div></div>
          <div className="tile"><div className="k">Volume vs avg</div><div className="v num">{p.volume_ratio ?? '—'}×</div></div>
          <div className="tile"><div className="k">Delivery %</div><div className="v num">{p.delivery_pct == null ? '—' : num(p.delivery_pct) + '%'}{p.delivery_avg5 != null && <span style={{ color: '#5f748e', fontSize: 11.5 }}> · 5d {num(p.delivery_avg5)}%</span>}</div></div>
          <div className="tile"><div className="k">Support</div><div className="v num">{inr(p.support)}</div></div>
          <div className="tile"><div className="k">Resistance</div><div className="v num">{inr(p.resistance)}</div></div>
          <div className="tile"><div className="k">52-week high</div><div className="v num">{inr(p.high52)}</div></div>
          <div className="tile"><div className="k">Model</div><div className="v" style={{ fontSize: 12.5 }}>{p.model_used || '—'}</div></div>
        </div>
        {p.shares != null && <div className="allocline">
          <span>Shares for your budget: <b>{p.shares}</b></span>
          <span>Invested: <b>{inr(p.invested)}</b></span>
          <span>Expected value: <b>{inr(p.expected_value)}</b></span>
          <span>Expected profit: <b className="pos">{inr(p.expected_profit)}</b></span>
        </div>}
      </div>
      <div className="pick-right">
        <PriceChart symbol={p.symbol} exchange={p.exchange} predicted={p.predicted_price} />
        <h4 className="subhead" style={{ marginTop: 14 }}>Why this stock — trader's reasons</h4>
        <ul className="reasons">{(p.reasons || []).map((r: string, j: number) => <li key={j}>{r}</li>)}</ul>
      </div>
    </div>
    {p.simulation && (
      <div className="sim-panel">
        <div className="sim-head">
          <span className="title">⏱️ Time Machine Simulation ({p.simulation.replays?.toLocaleString()} Replays)</span>
          <span className="method-tag">{p.simulation.method?.includes('5-minute') ? '⚡ 5-min Intraday' : '📊 5-Day Swing'}</span>
          <span className={`verdict-badge ${p.simulation.win_probability_pct >= p.simulation.loss_probability_pct ? 'pos' : 'neg'}`}>
            {p.simulation.verdict}
          </span>
        </div>
        <div className="sim-grid">
          <div className="sim-item">
            <span className="k">Target Win Odds</span>
            <span className="v pos">{p.simulation.win_probability_pct}%</span>
          </div>
          <div className="sim-item">
            <span className="k">Stop-Loss Risk Odds</span>
            <span className="v neg">{p.simulation.loss_probability_pct}%</span>
          </div>
          <div className="sim-item">
            <span className="k">Median Expected</span>
            <span className="v num">{inr(p.simulation.median_close)}</span>
          </div>
          <div className="sim-item">
            <span className="k">90% Price Range</span>
            <span className="v num" style={{ fontSize: 12.5 }}>{inr(p.simulation.expected_p5)} ➜ {inr(p.simulation.expected_p95)}</span>
          </div>
          {p.orb && (
            <div className="sim-item">
              <span className="k">Opening Breakout (ORB)</span>
              <span className={`v ${p.orb.status === 'triggered' ? 'pos' : 'mut'}`} style={{ fontSize: 13 }}>
                {p.orb.status === 'triggered' ? `✓ Triggered (${inr(p.orb.trigger_price)})` : (p.orb.status?.toUpperCase() || 'FORMING')}
              </span>
            </div>
          )}
        </div>
      </div>
    )}
    <div className="pick-sub">
      <Fundamentals f={p.fundamentals} />
      <NewsPanel n={p.news} />
    </div>
  </article>)
}

/* ---------- main app ---------- */
type SortKey = 'symbol' | 'current_price' | 'trader_score' | 'delivery_pct' | 'rsi' | 'ret21_pct'
export default function App() {
  const [tab, setTab] = useState<'picks' | 'scanned' | 'history' | '3d'>('picks')
  const [report, setReport] = useState<any>(null)
  const [scanned, setScanned] = useState<any>(null)
  const [history, setHistory] = useState<any>(null)
  const [budget, setBudget] = useState<string>('')
  const [savedBudget, setSavedBudget] = useState<number | null>(null)
  const [scan, setScan] = useState<any>(null)
  const [scanNote, setScanNote] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [savingBudget, setSavingBudget] = useState(false)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<{ k: SortKey; dir: 1 | -1 }>({ k: 'trader_score', dir: -1 })
  const wasRunning = useRef(false)

  const load = async () => {
    try {
      const r = await (await fetch('/api/picks/latest')).json(); setReport(r)
      const b = await (await fetch('/api/screen/budget')).json()
      setSavedBudget(b.budget_inr); if (b.budget_inr != null) setBudget(String(b.budget_inr))
      setScanned(await (await fetch('/api/scanned')).json())
      setHistory(await (await fetch('/api/history')).json())
    } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])
  useEffect(() => {
    if (tab === 'history') {
      fetch('/api/history').then(r => r.json()).then(h => setHistory(h)).catch(() => {})
    }
  }, [tab])
  const checkScan = async () => {
    try { const s = await (await fetch('/api/scan/status')).json(); setScan(s); return s } catch { return null }
  }
  useEffect(() => {
    let alive = true
    const tick = async () => {
      const s = await checkScan(); if (!alive || !s) return
      if (wasRunning.current && !s.running && s.stage === 'done') {
        setScanNote(`Scan complete — new picks below. Run date ${s.summary?.run_date || '—'} · Target date ${s.summary?.target_date || '—'}.`)
        load()
      }
      wasRunning.current = !!s.running
    }
    tick()
    const t = setInterval(tick, 4000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  const startScan = async () => {
    setScanNote('')
    try {
      const r = await (await fetch('/api/scan/start', { method: 'POST' })).json()
      if (r.started || r.reason === 'already_running') { wasRunning.current = true; checkScan() }
    } catch { /* status polling will surface the state */ }
  }
  const saveBudget = async (v: number | null) => {
    setSavingBudget(true)
    try {
      await fetch('/api/screen/budget', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ budget_inr: v }) })
      await load()
    } finally { setSavingBudget(false) }
  }
  const picks: any[] = report?.picks || []
  const vetoed: any[] = report?.vetoed || []
  const demoted: any[] = report?.red_flag_demoted || []
  const a = report?.allocation
  const sc = report?.stage_counts || {}

  const scannedRows = useMemo(() => {
    let rows = (scanned?.top50 || []).filter((s: any) =>
      !query || s.symbol.toLowerCase().includes(query.toLowerCase()) || (s.name || '').toLowerCase().includes(query.toLowerCase()))
    rows = [...rows].sort((x: any, y: any) => {
      const xv = x[sort.k], yv = y[sort.k]
      if (xv == null) return 1; if (yv == null) return -1
      return (typeof xv === 'string' ? xv.localeCompare(yv) : xv - yv) * sort.dir
    })
    return rows
  }, [scanned, query, sort])
  const sortBy = (k: SortKey) => setSort(s => ({ k, dir: s.k === k ? (s.dir === 1 ? -1 : 1) : -1 }))
  const arrow = (k: SortKey) => sort.k === k ? (sort.dir === -1 ? ' ↓' : ' ↑') : ''

  return (<div>
    <header className="topbar">
      <div className="brand">
        <div className="logo">◆</div>
        <div><h1>MARKETMIND <em>PRO</em></h1><div className="sub">Institutional-grade weekly stock prediction · NSE + BSE</div></div>
      </div>
      <nav className="tabs">
        <button className={tab === 'picks' ? 'on' : ''} onClick={() => setTab('picks')}>This Week's Picks</button>
        <button className={tab === 'scanned' ? 'on' : ''} onClick={() => setTab('scanned')}>All Scanned Stocks</button>
        <button className={tab === 'history' ? 'on' : ''} onClick={() => setTab('history')}>Past Weeks</button>
        <button className={tab === '3d' ? 'on' : ''} onClick={() => setTab('3d')}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
            <ThinkingOrb state={tab === '3d' ? 'working' : 'breathing'} size={20} theme="dark" />
            3D Prediction Space
          </span>
        </button>
      </nav>
    </header>
    <main>
      {loading ? <div className="loadpanel"><ThinkingOrb state="connecting" size={64} theme="dark" /><div className="loadtxt">Connecting to market data…</div></div> : <>
      {tab === 'picks' && <>
        <div className="weekstrip">
          <div className="stat hero"><div className="k">Prediction week</div><div className="v num">{report?.run_date || '—'} ➜ {report?.target_date || '—'}</div><div className="s">7-day horizon · prices as of {report?.data_as_of || '—'}</div></div>
          <div className="stat"><div className="k">Universe</div><div className="v num">{sc.universe?.toLocaleString('en-IN') ?? '—'}</div><div className="s">NSE {report?.universe_counts?.nse?.toLocaleString('en-IN') ?? '—'} · BSE {report?.universe_counts?.bse?.toLocaleString('en-IN') ?? '—'}</div></div>
          <div className="stat"><div className="k">With official data</div><div className="v num">{sc.with_data?.toLocaleString('en-IN') ?? '—'}</div><div className="s">NSE {sc.nse_with_data?.toLocaleString('en-IN') ?? '—'} · BSE {sc.bse_with_data?.toLocaleString('en-IN') ?? '—'}</div></div>
          <div className="stat"><div className="k">Liquid stocks</div><div className="v num">{sc.liquid?.toLocaleString('en-IN') ?? '—'}</div><div className="s">Passed ₹50L/day traded value</div></div>
          <div className="stat"><div className="k">Deep-backtested</div><div className="v num">{sc.stage2 ?? '—'}</div><div className="s">ML + walk-forward tested</div></div>
          <div className="stat"><div className="k">Quality-passed</div><div className="v num">{sc.quality_passed ?? '—'}</div><div className="s">Beat the naive baseline</div></div>
        </div>

        <div className="command">
          <div className="panel">
            <h3>▶ Scan the market</h3>
            <div className="hint">Re-scans all ~7,987 NSE + BSE stocks on official exchange (Bhavcopy) data, deep-backtests the top 150, checks fundamentals &amp; news, then publishes a fresh set of 5–7 picks here automatically.</div>
            <button className="scanbtn" disabled={!!scan?.running} onClick={startScan}>{scan?.running
              ? <span className="orbinline"><ThinkingOrb state="working" size={20} theme="dark" />Scanning…</span>
              : '🔍 Scan Market'}</button>
            {scan?.running && <div className="scanpanel">
              <div className="spinrow"><ThinkingOrb state={scan.stage === 'stage2' ? 'solving' : scan.stage === 'stage1' ? 'searching' : 'connecting'} size={64} theme="dark" /><b>{scan.stage === 'stage2'
                ? 'Deep analysis — training & backtesting the top stocks…'
                : `Scanning the full market — batch ${scan.stage1?.done_batches ?? 0} of ${scan.stage1?.total_batches ?? 80}${scan.stage1 ? ` · ${scan.stage1.results.toLocaleString('en-IN')} stocks checked · ${scan.stage1.liquid.toLocaleString('en-IN')} passed liquidity` : ''}`}</b></div>
              {scan.stage === 'stage2'
                ? <div className="note">Stage 1 complete. A model is now trained and walk-forward backtested for each top stock — this stage takes a while. Leave this page open; the new picks appear here automatically.</div>
                : scan.stage1 && <div className="bar"><div className="barfill" style={{ width: `${Math.min(100, Math.round(100 * scan.stage1.done_batches / scan.stage1.total_batches))}%` }} /></div>}
            </div>}
          </div>
          <div className="panel">
            <h3>₹ Your budget</h3>
            <div className="hint">Set a budget and every pick below gets whole-share counts that fit it.</div>
            <div className="budgetrow">
              <input type="number" min="0" placeholder="e.g. 50000" value={budget} onChange={e => setBudget(e.target.value)} />
              <button className="btn" disabled={savingBudget} onClick={() => saveBudget(budget === '' ? null : Number(budget))}>{savingBudget ? <span className="orbinline"><ThinkingOrb state="working" size={20} theme="dark" />Saving…</span> : 'Save budget'}</button>
              {savedBudget != null && <button className="btn ghost" disabled={savingBudget} onClick={() => { setBudget(''); saveBudget(null) }}>Clear</button>}
            </div>
            {a ? <div className="allocgrid">
              <div className="ag"><div className="k">Invested</div><div className="v num">{inr(a.total_invested)}</div></div>
              <div className="ag"><div className="k">Leftover</div><div className="v num">{inr(a.leftover)}</div></div>
              <div className="ag"><div className="k">Expected value</div><div className="v num">{inr(a.expected_value)}</div></div>
              <div className="ag"><div className="k">Expected profit</div><div className="v num pos">{inr(a.expected_profit)}</div></div>
            </div> : <div className="note">No budget set — picks are ranked only. Set a budget to see share counts.</div>}
          </div>
        </div>

        {scanNote && <div className="banner ok">✓ {scanNote}</div>}
        {scan && !scan.running && scan.stage === 'failed' && <div className="banner bad">
          <span>The last scan finished without producing a new report.</span>
          <button className="scanbtn" onClick={startScan}>Retry — 🔍 Scan Market</button>
        </div>}

        {picks.length === 0 && <div className="empty"><div className="orbcenter"><ThinkingOrb state="breathing" size={64} theme="dark" /></div>No picks yet. The weekly pipeline writes the first report here after its run — or press <b>Scan Market</b> above.</div>}
        {picks.map((p, i) => <PickCard key={p.symbol + i} p={p} i={i} />)}

        {(vetoed.length > 0 || demoted.length > 0 || (report?.simulation_rejected || []).length > 0) && <section className="veto-sec">
          <h3>⛔ Excluded by safety & simulation checks</h3>
          {(report?.simulation_rejected || []).map((s: any, i: number) => <div className="vetocard" key={'sim' + i}>
            <div className="vt">{s.name || s.symbol} <span className="chip exch">{s.symbol} · {s.exchange}</span> <span className="chip neg">MONTE CARLO VETO</span></div>
            <div className="vr">Blocked by Time Machine: <b>Stop-loss risk ({s.risk}%) exceeds win odds ({s.win_odds ?? 0}%)</b> across 1,000 historical replays. Excluded to protect capital from high stop-out rates.</div>
          </div>)}
          {vetoed.map((v, i) => <div className="vetocard" key={'v' + i}>
            <div className="vt">{v.name} <span className="chip exch">{v.symbol} · {v.exchange}</span> <span className="chip neg">NEWS VETO</span></div>
            <div className="vr">Blocked headline: <b>“{v.reason}”</b> — this stock passed the technical screen (predicted {pct(v.predicted_return_pct)}) but was excluded because of severe negative news.</div>
          </div>)}
          {demoted.map((v, i) => <div className="vetocard" key={'d' + i}>
            <div className="vt">{v.name} <span className="chip exch">{v.symbol} · {v.exchange}</span> <span className="chip neg">RED-FLAG DEMOTED</span></div>
            <div className="vr">Excluded on fundamentals: {(v.flags || []).join(' · ') || 'Severe debt + shrinking earnings.'}</div>
          </div>)}
        </section>}

        <footer className="disc">How to read this: every pick first had to beat the naive baseline in a walk-forward backtest on its own history — the accuracy shown is measured, not promised. Prices come from official NSE/BSE Bhavcopy data; fundamentals and news are checked before a stock can be picked, and severe news (fraud, default, SEBI action) vetoes it openly above. Predictions are for the target date's close, not guarantees. This is analysis software, not investment advice.</footer>
      </>}
      {tab === 'scanned' && <>
        {scanned === null && <div className="loadpanel"><ThinkingOrb state="working" size={64} theme="dark" /><div className="loadtxt">Loading scanned stocks…</div></div>}
        <div className="weekstrip">
          <div className="stat"><div className="k">Universe</div><div className="v num">{scanned?.stage_counts?.universe?.toLocaleString('en-IN') ?? '—'}</div></div>
          <div className="stat"><div className="k">With data</div><div className="v num">{scanned?.stage_counts?.with_data?.toLocaleString('en-IN') ?? '—'}</div><div className="s">NSE {scanned?.stage_counts?.nse_with_data?.toLocaleString('en-IN') ?? '—'} · BSE {scanned?.stage_counts?.bse_with_data?.toLocaleString('en-IN') ?? '—'}</div></div>
          <div className="stat"><div className="k">Liquid</div><div className="v num">{scanned?.stage_counts?.liquid?.toLocaleString('en-IN') ?? '—'}</div></div>
          <div className="stat"><div className="k">Deep-evaluated</div><div className="v num">{scanned?.stage_counts?.stage2 ?? '—'}</div></div>
          <div className="stat hero"><div className="k">Run ➜ Target</div><div className="v num" style={{ fontSize: 15.5 }}>{scanned?.run_date || '—'} ➜ {scanned?.target_date || '—'}</div></div>
        </div>
        <div className="tabletools">
          <input placeholder="🔎 Search symbol or company…" value={query} onChange={e => setQuery(e.target.value)} />
          <span className="mut">Top {scannedRows.length} liquid stocks by trader score · click a column to sort</span>
        </div>
        <div className="tablewrap"><table><thead><tr>
          <th>#</th>
          <th className="sortable" onClick={() => sortBy('symbol')}>Stock{arrow('symbol')}</th>
          <th>Exchange</th>
          <th className="sortable" onClick={() => sortBy('current_price')}>Price{arrow('current_price')}</th>
          <th className="sortable" onClick={() => sortBy('trader_score')}>Trader score{arrow('trader_score')}</th>
          <th className="sortable" onClick={() => sortBy('delivery_pct')}>Delivery %{arrow('delivery_pct')}</th>
          <th className="sortable" onClick={() => sortBy('rsi')}>RSI{arrow('rsi')}</th>
          <th className="sortable" onClick={() => sortBy('ret21_pct')}>21-day return{arrow('ret21_pct')}</th>
          <th>Top reasons</th>
        </tr></thead>
          <tbody>{scannedRows.map((s: any, i: number) => <tr key={i}><td className="num">{i + 1}</td>
            <td><b>{s.symbol}</b><div style={{ color: '#5f748e', fontSize: 12 }}>{s.name}</div></td>
            <td>{s.exchange}</td><td className="num">{inr(s.current_price)}</td>
            <td className="num"><span className="scorebar"><i style={{ width: `${s.trader_score}%` }} /></span>{s.trader_score}</td>
            <td className="num">{s.delivery_pct == null ? '—' : num(s.delivery_pct) + '%'}</td>
            <td className="num">{s.rsi}</td>
            <td className={`num ${s.ret21_pct >= 0 ? 'pos' : 'neg'}`}>{pct(s.ret21_pct)}</td>
            <td style={{ fontSize: 12, color: '#93a9c0' }}>{(s.reasons || []).join(' · ')}</td></tr>)}</tbody></table></div>
      </>}
      {tab === 'history' && <>
        {history === null && <div className="loadpanel"><ThinkingOrb state="working" size={64} theme="dark" /><div className="loadtxt">Loading past weeks &amp; live prices…</div></div>}
        {history !== null && (history?.weeks || []).length === 0 && <div className="empty">No past weeks yet — history builds up as each Monday run completes and target dates pass.</div>}
        {(history?.weeks || []).map((w: any, i: number) => <div className="weekcard" key={i}>
          <h2>
            <span>Week of {w.run_date} <span style={{ color: '#c9a227' }}>➜</span> target {w.target_date}</span>
            <span className="live-badge-indicator"><span className="live-pulse-dot" /> Live Market Tracking</span>
          </h2>
          <div className="tablewrap" style={{ border: 0, background: 'transparent' }}><table><thead><tr>
            <th>Stock</th>
            <th>Was</th>
            <th style={{ textAlign: 'right' }}>Live Price</th>
            <th>Predicted</th>
            <th>Predicted %</th>
            <th>Actual</th>
            <th>Actual %</th>
            <th>Result</th>
          </tr></thead>
            <tbody>{w.picks.map((p: any, j: number) => {
              const done = p.actual_price != null || p.actual_return_pct != null
              const hit = done && Math.sign(p.actual_return_pct) === Math.sign(p.predicted_return_pct)
              const livePrice = p.live_price ?? p.current_price
              const liveReturn = p.live_return_pct ?? (p.current_price && livePrice ? ((livePrice - p.current_price) / p.current_price) * 100 : null)
              return <tr key={j}>
                <td>
                  <b>{p.symbol}</b>
                  {p.exchange && <span className="chip exch" style={{ marginLeft: 6, fontSize: 10, padding: '1px 5px' }}>{p.exchange}</span>}
                  {p.name && <div style={{ color: '#5f748e', fontSize: 11.5 }}>{p.name}</div>}
                </td>
                <td className="num">{inr(p.current_price)}</td>
                <td className="num">
                  <div className="live-price-cell">
                    <span className="live-price-val num">{inr(livePrice)}</span>
                    {liveReturn != null && (
                      <span className={`live-ret-pill ${liveReturn >= 0 ? 'pos' : 'neg'}`}>
                        <span className="live-dot" />
                        {pct(liveReturn)}
                      </span>
                    )}
                  </div>
                </td>
                <td className="num">{inr(p.predicted_price)}</td>
                <td>
                  <PctBar val={p.predicted_return_pct} />
                </td>
                <td className="num">{done ? inr(p.actual_price) : <span className="mut" style={{ fontSize: 12 }}>Pending</span>}</td>
                <td>{done ? <PctBar val={p.actual_return_pct} /> : <span className="mut">—</span>}</td>
                <td><span className={`hitmiss ${done ? (hit ? 'hit' : 'miss') : 'pend'}`}>{done ? (hit ? '✓ HIT' : '✗ MISS') : 'PENDING'}</span></td>
              </tr>
            })}</tbody></table></div>
        </div>)}
      </>}
      {tab === '3d' && (
        <div className="space-3d-container">
          <div className="space-3d-header">
            <div className="space-3d-info">
              <ThinkingOrb state="working" size={32} theme="dark" />
              <div>
                <h3>Interactive 3D Stock Market Prediction Space</h3>
                <p>Curved trading corridors, real-time NSE/BSE prediction cards, and the signature MARKETMIND PRO aerial resolve.</p>
              </div>
            </div>
            <div className="space-3d-actions">
              <a href="/marketmind-3d.html" target="_blank" rel="noreferrer" className="btn">
                Open Fullscreen ↗
              </a>
              <a href="/marketmind-pro-3d.mp4" download="marketmind-pro-3d.mp4" className="btn ghost">
                Download 1080p MP4 (20s) ↓
              </a>
            </div>
          </div>
          <iframe
            src="/marketmind-3d.html"
            className="space-3d-iframe"
            title="MarketMind Pro 3D Prediction Space"
          />
        </div>
      )}
      </>}
    </main>
  </div>)
}
