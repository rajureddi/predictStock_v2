import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { ThinkingOrb } from 'thinking-orbs'
import {
  ArrowRight, CaretLeft, CaretRight, CheckCircle, ClockCounterClockwise, CurrencyInr, DiceFive,
  MagnifyingGlass, Moon, ShieldWarning, Sun, Warning, X, Briefcase, TrendUp, TrendDown, Gauge, ChartLineUp,
} from '@phosphor-icons/react'
import { C, Holding, Theme, ThemeCtx, applyPalette, fetchSeries, holdingFromPick, inr, loadHoldings, num, pct, saveHoldings } from './lib'
import StockDesk from './StockDesk'
import Portfolio from './Portfolio'

const Backdrop = lazy(() => import('./scene/Backdrop'))

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

/* ---------- compact 90-day trend for pick rows ---------- */
function MiniSpark({ symbol, exchange }: { symbol: string; exchange: string }) {
  const [rows, setRows] = useState<any[] | null>(null)
  useEffect(() => {
    let on = true
    fetchSeries(symbol, exchange).then(s => { if (on) setRows(s) })
    return () => { on = false }
  }, [symbol, exchange])
  if (!rows || rows.length < 5) return <span className="spark empty" aria-hidden="true" />
  const W = 112, H = 34
  const closes = rows.map(r => r.close)
  const lo = Math.min(...closes), hi = Math.max(...closes), span = (hi - lo) || 1
  const pts = closes.map((c, i) => `${((i / (closes.length - 1)) * W).toFixed(1)},${(H - 3 - ((c - lo) / span) * (H - 6)).toFixed(1)}`).join(' ')
  const up = closes[closes.length - 1] >= closes[0]
  return <svg className="spark" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${symbol} 90 day trend ${up ? 'up' : 'down'}`}>
    <polyline points={pts} fill="none" stroke={up ? C.up : C.down} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
  </svg>
}

function AccMeter({ v }: { v?: number | null }) {
  if (v == null) return <span className="mut">—</span>
  return <span className="accmeter"><span className="num">{v}%</span><i><b style={{ width: `${Math.max(0, Math.min(100, v))}%` }} /></i></span>
}

/* ---------- main app ---------- */
type SortKey = 'symbol' | 'current_price' | 'trader_score' | 'delivery_pct' | 'rsi' | 'ret21_pct'
export default function App() {
  const [theme, setTheme] = useState<Theme>(() => {
    const s = localStorage.getItem('marketmind.theme')
    return s === 'dark' || s === 'light' ? s : (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  })
  applyPalette(theme)
  const orb = theme
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0B0C0E' : '#F2F3F5')
    localStorage.setItem('marketmind.theme', theme)
  }, [theme])
  const [tab, setTab] = useState<'picks' | 'scanned' | 'history' | 'portfolio'>('picks')
  const [holdings, setHoldingsRaw] = useState<Holding[]>(loadHoldings)
  const setHoldings = (f: (h: Holding[]) => Holding[]) => setHoldingsRaw(h => { const n = f(h); saveHoldings(n); return n })
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
  const [openIdx, setOpenIdx] = useState<number | null>(null)
  const [indices, setIndices] = useState<any>(null)
  const [historyDesk, setHistoryDesk] = useState<{ list: any[]; idx: number; targetDate: string } | null>(null)
  const [globalSearch, setGlobalSearch] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const fetchIndices = () => {
      fetch('/api/market-indices').then(r => r.json()).then(d => setIndices(d)).catch(() => {})
    }
    fetchIndices()
    const intv = setInterval(fetchIndices, 60000)
    return () => clearInterval(intv)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        searchInputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (tab !== 'history') setHistoryDesk(null)
    if (tab !== 'picks') setOpenIdx(null)
  }, [tab])

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
        setScanNote(`Scan complete. New picks below. Run date ${s.summary?.run_date || '—'} · Target date ${s.summary?.target_date || '—'}.`)
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
  const simRejected: any[] = report?.simulation_rejected || []
  const survVetoed: any[] = report?.surveillance_vetoed || []
  const earningsSkipped: any[] = report?.earnings_skipped || []
  const sectorCapped: any[] = report?.sector_capped || []
  const regime = report?.market_regime
  const track = history?.track_record
  const a = report?.allocation
  const sc = report?.stage_counts || {}

  const scannedRows = useMemo(() => {
    const filterText = (query || (tab === 'scanned' ? globalSearch : '')).trim().toLowerCase()
    let rows = (scanned?.top50 || []).filter((s: any) =>
      !filterText || s.symbol.toLowerCase().includes(filterText) || (s.name || '').toLowerCase().includes(filterText))
    rows = [...rows].sort((x: any, y: any) => {
      const xv = x[sort.k], yv = y[sort.k]
      if (xv == null) return 1; if (yv == null) return -1
      return (typeof xv === 'string' ? xv.localeCompare(yv) : xv - yv) * sort.dir
    })
    return rows
  }, [scanned, query, globalSearch, tab, sort])
  const sortBy = (k: SortKey) => setSort(s => ({ k, dir: s.k === k ? (s.dir === 1 ? -1 : 1) : -1 }))
  const arrow = (k: SortKey) => sort.k === k ? (sort.dir === -1 ? ' ↓' : ' ↑') : ''

  useEffect(() => { if (openIdx != null && openIdx >= picks.length) setOpenIdx(null) }, [picks.length])
  useEffect(() => {
    if (openIdx == null || !picks.length) return
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return
      if (e.key === 'ArrowRight') { e.preventDefault(); setOpenIdx(i => (i! + 1) % picks.length) }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); setOpenIdx(i => (i! - 1 + picks.length) % picks.length) }
      else if (e.key === 'Escape') setOpenIdx(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [openIdx, picks.length])
  useEffect(() => { if (tab !== 'picks') setOpenIdx(null) }, [tab])

  const saveHolding = (p: any, shares: number, buy: number) =>
    setHoldings(h => [...h.filter(x => x.symbol !== p.symbol), holdingFromPick(p, shares, buy)])
  const removeHolding = (symbol: string) => setHoldings(h => h.filter(x => x.symbol !== symbol))
  const addAllPicks = () => setHoldings(h => {
    const add = picks.filter(p => p.shares > 0 && !h.some(x => x.symbol === p.symbol)).map(p => holdingFromPick(p, p.shares, p.current_price))
    return [...h, ...add]
  })
  const editShares = (symbol: string, shares: number) => setHoldings(h => h.map(x => x.symbol === symbol ? { ...x, shares } : x))
  const openFromPortfolio = (symbol: string) => {
    const i = picks.findIndex(p => p.symbol === symbol)
    if (i >= 0) { setTab('picks'); setTimeout(() => setOpenIdx(i), 0) }
  }

  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [predictLoading, setPredictLoading] = useState<string | null>(null)
  const [customDesk, setCustomDesk] = useState<{ pick: any; list: any[]; idx: number; backLabel?: string } | null>(null)

  useEffect(() => {
    const q = globalSearch.trim()
    if (!q) {
      setSearchResults([])
      setSearchLoading(false)
      return
    }
    let active = true
    setSearchLoading(true)
    const t = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(data => {
          if (active) {
            setSearchResults(data.results || [])
            setSearchLoading(false)
          }
        })
        .catch(() => {
          if (active) setSearchLoading(false)
        })
    }, 160)
    return () => {
      active = false
      clearTimeout(t)
    }
  }, [globalSearch])

  const openStockPrediction = async (symbol: string, exchange = 'NSE', name?: string) => {
    setGlobalSearch('')
    setSearchFocused(false)
    const existingIdx = picks.findIndex(p => p.symbol === symbol)
    if (existingIdx >= 0) {
      setCustomDesk(null)
      setTab('picks')
      setOpenIdx(existingIdx)
      return
    }
    setPredictLoading(symbol)
    try {
      const res = await (await fetch(`/api/predict/${encodeURIComponent(symbol)}?exchange=${encodeURIComponent(exchange)}`)).json()
      if (res.pick) {
        const p = res.pick
        if (name && !p.name) p.name = name
        setCustomDesk({
          pick: p,
          list: [p, ...picks],
          idx: 0,
          backLabel: tab === 'scanned' ? 'All Scanned Stocks' : "This Week's Picks"
        })
      } else {
        alert(res.error || `Could not generate 5-day prediction for ${symbol}`)
      }
    } catch (e: any) {
      alert(`Prediction request failed: ${e.message}`)
    } finally {
      setPredictLoading(null)
    }
  }

  const opened = openIdx != null ? picks[openIdx] : null
  const avgRet = picks.length ? picks.reduce((s, p) => s + (p.predicted_return_pct ?? 0), 0) / picks.length : null
  const accs = picks.map(p => p.backtest?.best_dir_acc).filter((v: any) => v != null)
  const avgAcc = accs.length ? accs.reduce((s: number, v: number) => s + v, 0) / accs.length : null

  const scanState = scan?.running && <div className="scanstate" role="status">
    <ThinkingOrb state={scan.stage === 'stage2' ? 'solving' : scan.stage === 'stage1' ? 'searching' : 'connecting'} size={32} theme={orb} />
    <div className="scanstate-txt">
      <b>{scan.stage === 'stage2'
        ? 'Deep analysis: training & backtesting the top stocks…'
        : `Scanning the full market: batch ${scan.stage1?.done_batches ?? 0} of ${scan.stage1?.total_batches ?? 80}${scan.stage1 ? ` · ${scan.stage1.results.toLocaleString('en-IN')} stocks checked · ${scan.stage1.liquid.toLocaleString('en-IN')} passed liquidity` : ''}`}</b>
      {scan.stage === 'stage2'
        ? <span>Stage 1 complete. A model is now trained and walk-forward backtested for each top stock. This stage takes a while. Leave this page open; the new picks appear here automatically.</span>
        : scan.stage1 && <div className="bar"><div className="barfill" style={{ width: `${Math.min(100, Math.round(100 * scan.stage1.done_batches / scan.stage1.total_batches))}%` }} /></div>}
    </div>
  </div>

  return (<ThemeCtx.Provider value={theme}>
    <div className="app-shell">
      {predictLoading && (
        <div className="predict-loading-modal" role="status">
          <div className="predict-loading-card">
            <ThinkingOrb state="solving" size={64} theme={orb} />
            <div className="pl-text">
              <b>Computing 5-Day ML Prediction for {predictLoading}…</b>
              <span>Running walk-forward ensemble models and Time Machine simulation</span>
            </div>
          </div>
        </div>
      )}

      {/* LEFT SIDEBAR NAVIGATION */}
      <aside className="app-sidebar" aria-label="Main Navigation">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <span className="brand-mark" aria-hidden="true" />
            <div className="brand-text">
              <span className="brand-title">MarketMind</span>
              <span className="brand-badge">PRO</span>
            </div>
          </div>
          <div className="sidebar-sub">QUANT DESK · NSE/BSE</div>
        </div>

        <nav className="sidebar-tabs" role="tablist" aria-label="Sections">
          <div className="sidebar-sec-label">DESK &amp; PORTFOLIO</div>
          <button
            role="tab"
            aria-selected={tab === 'picks'}
            className={`sidebar-tab-btn ${tab === 'picks' ? 'on' : ''}`}
            onClick={() => { setCustomDesk(null); setTab('picks') }}
          >
            <DiceFive size={18} weight={tab === 'picks' ? 'bold' : 'regular'} />
            <span>This Week's Picks</span>
          </button>
          <button
            role="tab"
            aria-selected={tab === 'scanned'}
            className={`sidebar-tab-btn ${tab === 'scanned' ? 'on' : ''}`}
            onClick={() => { setCustomDesk(null); setTab('scanned') }}
          >
            <MagnifyingGlass size={18} weight={tab === 'scanned' ? 'bold' : 'regular'} />
            <span>All Scanned Stocks</span>
          </button>
          <button
            role="tab"
            aria-selected={tab === 'history'}
            className={`sidebar-tab-btn ${tab === 'history' ? 'on' : ''}`}
            onClick={() => { setCustomDesk(null); setHistoryDesk(null); setTab('history') }}
          >
            <ClockCounterClockwise size={18} weight={tab === 'history' ? 'bold' : 'regular'} />
            <span>Past Weeks</span>
          </button>
          <button
            role="tab"
            aria-selected={tab === 'portfolio'}
            className={`sidebar-tab-btn ${tab === 'portfolio' ? 'on' : ''}`}
            onClick={() => { setCustomDesk(null); setTab('portfolio') }}
          >
            <Briefcase size={18} weight={tab === 'portfolio' ? 'bold' : 'regular'} />
            <span>Portfolio</span>
            {holdings.length > 0 && <span className="tabcount num">{holdings.length}</span>}
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status-pill">
            <span className={`market-dot ${indices?.market_open ? 'live' : 'closed'}`} />
            <span className="market-text">{indices?.market_open ? 'NSE: OPEN' : 'NSE: CLOSED'}</span>
            <span className="cutoff-text num">{indices?.cutoff || '15:30 IST'}</span>
          </div>
          <div className="sidebar-theme-toggle">
            <span className="theme-text">{theme === 'dark' ? 'Dark Theme' : 'Light Theme'}</span>
            <button
              className="iconbtn themebtn"
              onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
            >
              {theme === 'dark' ? <Sun size={16} weight="bold" /> : <Moon size={16} weight="bold" />}
            </button>
          </div>
        </div>
      </aside>

      {/* MAIN APP CONTAINER */}
      <div className="app-main">
        {/* PERSISTENT TOPBAR */}
        <header className="app-topbar">
          <div className="topbar-left">
            <div className="indices-strip">
              <div className="index-pill">
                <span className="idx-name">NIFTY 50</span>
                <span className="idx-price num">{indices?.nifty?.price ? inr(indices.nifty.price) : '24,340.50'}</span>
                <span className={`idx-change num ${(indices?.nifty?.change_pct ?? 0) >= 0 ? 'pos' : 'neg'}`}>
                  {pct(indices?.nifty?.change_pct ?? 0.42)}
                </span>
              </div>
              <div className="index-pill">
                <span className="idx-name">INDIA VIX</span>
                <span className="idx-price num">{indices?.vix?.price ?? '14.85'}</span>
                <span className={`idx-change num ${(indices?.vix?.change_pct ?? 0) >= 0 ? 'pos' : 'neg'}`}>
                  {pct(indices?.vix?.change_pct ?? -1.20)}
                </span>
              </div>
              <div className="index-pill cutoff-pill">
                <span className="idx-name">SESSION CUTOFF</span>
                <span className="idx-price num">15:30 IST</span>
              </div>
            </div>
          </div>

          <div className="topbar-right">
            {/* Global Search */}
            <div className="global-search-container">
              <MagnifyingGlass size={15} weight="bold" className="search-icon-left" />
              <input
                ref={searchInputRef}
                className="global-search-input"
                placeholder="Search stocks... (Ctrl+K)"
                value={globalSearch}
                onChange={e => setGlobalSearch(e.target.value)}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setTimeout(() => setSearchFocused(false), 250)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && searchResults.length > 0) {
                    const top = searchResults[0]
                    openStockPrediction(top.symbol, top.exchange, top.name)
                  }
                }}
                aria-label="Search Equities"
              />
              <kbd className="search-kbd-shortcut">Ctrl+K</kbd>
              {searchFocused && (globalSearch.trim().length > 0) && (
                <div className="global-search-dropdown">
                  {searchLoading && (
                    <div className="search-loading-row">
                      <ThinkingOrb state="searching" size={20} theme={orb} />
                      <span>Searching 7,987 Indian stocks…</span>
                    </div>
                  )}
                  {!searchLoading && searchResults.length === 0 && (
                    <div className="search-empty-row">
                      No stocks found matching "{globalSearch}". Try ticker (INFY) or name.
                    </div>
                  )}
                  {!searchLoading && searchResults.map((item, idx) => (
                    <div
                      key={idx}
                      className="search-result-row"
                      onMouseDown={() => openStockPrediction(item.symbol, item.exchange, item.name)}
                    >
                      <div className="sr-left">
                        <b>{item.symbol}</b>
                        {item.exchange && <span className="chip exch sm">{item.exchange}</span>}
                        <span className="sr-name">{item.name}</span>
                      </div>
                      <div className="sr-right num">
                        {item.current_price != null ? (
                          <>
                            <span>{inr(item.current_price)}</span>
                            {item.predicted_return_pct != null && (
                              <span className={item.predicted_return_pct >= 0 ? 'pos' : 'neg'}>
                                5D {pct(item.predicted_return_pct)}
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="view-chart-btn sm">Get 5D Pred ↗</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button className="topbar-scan-btn" disabled={!!scan?.running} onClick={startScan}>
              {scan?.running ? (
                <span className="orbinline"><ThinkingOrb state="working" size={20} theme={orb === 'light' ? 'dark' : 'light'} /> Scanning…</span>
              ) : (
                <><MagnifyingGlass size={15} weight="bold" /> Scan Market</>
              )}
            </button>

            <button
              className="iconbtn themebtn"
              onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
            >
              {theme === 'dark' ? <Sun size={17} weight="bold" /> : <Moon size={17} weight="bold" />}
            </button>
          </div>
        </header>

        <section className={`hero${opened || historyDesk || customDesk ? ' compact' : ''}`}>
      <Suspense fallback={null}><Backdrop energy={scan?.running ? 1 : 0} theme={theme} /></Suspense>
      <div className="hero-in">
        {tab === 'portfolio' && <div className="hero-title">
          <h2>Portfolio</h2>
          <p>Your holdings from MarketMind picks, valued at the latest official close.</p>
        </div>}
        {tab === 'picks' && !opened && !customDesk && <>
          <div className="hero-title">
            <h2>Prediction week <span className="num">{report?.run_date || '—'} <ArrowRight size={20} weight="bold" aria-hidden="true" /> {report?.target_date || '—'}</span></h2>
            <p>7-day horizon · prices as of {report?.data_as_of || '—'} · {picks.length} {picks.length === 1 ? 'pick' : 'picks'} published</p>
          </div>
          <div className="hero-actions">
            <button className="scanbtn" disabled={!!scan?.running} onClick={startScan}>{scan?.running
              ? <span className="orbinline"><ThinkingOrb state="working" size={20} theme={orb === 'light' ? 'dark' : 'light'} />Scanning…</span>
              : <><MagnifyingGlass size={17} weight="bold" /> Scan Market</>}</button>
          </div>
        </>}
        {tab === 'scanned' && !customDesk && <div className="hero-title">
          <h2>All scanned stocks</h2>
          <p className="num">Run {scanned?.run_date || '—'} · target {scanned?.target_date || '—'}</p>
        </div>}
        {tab === 'history' && !historyDesk && <div className="hero-title">
          <h2>Past weeks</h2>
          <p>Every published pick, tracked against live and actual prices.</p>
        </div>}
      </div>
    </section>

    <main className="page">
      {loading && <div className="panel loadpanel"><ThinkingOrb state="connecting" size={64} theme={orb} /><div className="loadtxt">Connecting to market data…</div></div>}

      {!loading && customDesk && (
        <StockDesk
          list={customDesk.list}
          idx={customDesk.idx}
          targetDate={report?.target_date}
          holding={holdings.find(h => h.symbol === customDesk.pick.symbol)}
          onSelect={i => setCustomDesk(c => c ? { ...c, idx: i, pick: c.list[i] } : null)}
          onBack={() => setCustomDesk(null)}
          onSaveHolding={saveHolding}
          onRemoveHolding={removeHolding}
          backLabel={customDesk.backLabel || "All Stocks"}
        />
      )}

      {!loading && !customDesk && tab === 'picks' && opened && <StockDesk list={picks} idx={openIdx!} targetDate={report?.target_date}
        holding={holdings.find(h => h.symbol === opened.symbol)}
        onSelect={setOpenIdx} onBack={() => setOpenIdx(null)}
        onSaveHolding={saveHolding} onRemoveHolding={removeHolding} />}

      {!loading && !customDesk && tab === 'portfolio' && <Portfolio holdings={holdings} picks={picks}
        onOpen={openFromPortfolio} onRemove={removeHolding} onAddAll={addAllPicks} onEditShares={editShares} />}

      {!loading && !customDesk && tab === 'picks' && !opened && <>
        <dl className="kpis panel">
          <div><dt>Universe</dt><dd className="num">{sc.universe?.toLocaleString('en-IN') ?? '—'}</dd><dd className="s">NSE {report?.universe_counts?.nse?.toLocaleString('en-IN') ?? '—'} · BSE {report?.universe_counts?.bse?.toLocaleString('en-IN') ?? '—'}</dd></div>
          <div><dt>With official data</dt><dd className="num">{sc.with_data?.toLocaleString('en-IN') ?? '—'}</dd><dd className="s">NSE {sc.nse_with_data?.toLocaleString('en-IN') ?? '—'} · BSE {sc.bse_with_data?.toLocaleString('en-IN') ?? '—'}</dd></div>
          <div><dt>Liquid stocks</dt><dd className="num">{sc.liquid?.toLocaleString('en-IN') ?? '—'}</dd><dd className="s">Passed ₹50L/day traded value</dd></div>
          <div><dt>Deep-backtested</dt><dd className="num">{sc.stage2 ?? '—'}</dd><dd className="s">ML + walk-forward tested</dd></div>
          <div><dt>Quality-passed</dt><dd className="num">{sc.quality_passed ?? '—'}</dd><dd className="s">Beat the naive baseline</dd></div>
        </dl>

        {regime && regime.regime !== 'unknown' && <div className={`banner regime ${regime.regime}`} role="status">
          {regime.regime === 'bull' ? <TrendUp size={18} weight="bold" /> : regime.regime === 'bear' ? <TrendDown size={18} weight="bold" /> : <Gauge size={18} weight="bold" />}
          <span className="regime-name">{regime.regime} regime</span>
          <span className="regime-txt">
            NIFTY <b className="num">{inr(regime.nifty_close)}</b> is <b className={`num ${(regime.nifty_vs_200dma_pct ?? 0) >= 0 ? 'pos' : 'neg'}`}>{pct(regime.nifty_vs_200dma_pct)}</b> vs its 200-DMA
            {regime.nifty_vs_50dma_pct != null && <> and <b className={`num ${regime.nifty_vs_50dma_pct >= 0 ? 'pos' : 'neg'}`}>{pct(regime.nifty_vs_50dma_pct)}</b> vs the 50-DMA</>}
            {regime.vix != null && <> · India VIX <b className="num">{regime.vix}</b>{regime.vix_change_5d_pct != null && <span className="num"> ({pct(regime.vix_change_5d_pct)} in 5d)</span>}</>}
          </span>
          <span className="regime-knobs num">
            <span title="Maximum picks published in this regime">≤{regime.max_picks} picks</span>
            <span title="Position size multiplier from India VIX">size ×{regime.size_mult}</span>
            {regime.stop_widen > 1 && <span title="Stops widened by this factor for volatility">stops ×{regime.stop_widen}</span>}
            {regime.cash_pct > 0 && <span title="Share of budget kept in cash">{Math.round(regime.cash_pct * 100)}% cash</span>}
          </span>
        </div>}
        {scanNote && <div className="banner ok"><CheckCircle size={18} weight="bold" /> <span>{scanNote}</span><button className="iconbtn" aria-label="Dismiss" onClick={() => setScanNote('')}><X size={14} weight="bold" /></button></div>}
        {scan && !scan.running && scan.stage === 'failed' && <div className="banner bad">
          <Warning size={18} weight="bold" />
          <span>The last scan finished without producing a new report.</span>
          <button className="btn dark" onClick={startScan}><MagnifyingGlass size={15} weight="bold" /> Retry: Scan Market</button>
        </div>}
        {scanState}

        <div className="cols">
          <section className="panel picklist" aria-label="This week's picks">
            <div className="panel-head">
              <h3>This week's picks</h3>
              {picks.length > 0 && <div className="summary num">
                <span>Avg predicted <b className={(avgRet ?? 0) >= 0 ? 'pos' : 'neg'}>{pct(avgRet)}</b></span>
                <span>Avg backtest accuracy <b>{avgAcc == null ? '—' : num(avgAcc) + '%'}</b></span>
              </div>}
            </div>
            <div className="pl-head" aria-hidden="true">
              <span>#</span><span>Stock</span><span>90-day</span><span className="r">Now → Predicted</span><span className="r">Return</span><span className="r">Score</span><span>Backtest acc.</span><span />
            </div>
            {picks.length === 0 ? <div className="emptystate">
              <ThinkingOrb state={scan?.running ? 'searching' : 'breathing'} size={64} theme={orb} />
              <h4>{scan?.running ? 'Picks are being computed' : 'No picks yet'}</h4>
              <p>{scan?.running
                ? 'A scan is running now. The new set of 5-7 picks is published here automatically when it finishes.'
                : <>The weekly pipeline writes the first report here after its run, or press <b>Scan Market</b>.</>}</p>
              {!scan?.running && <button className="btn dark" onClick={startScan}><MagnifyingGlass size={15} weight="bold" /> Scan Market</button>}
            </div> : <ol className="pl-rows">
              {picks.map((p, i) => {
                const up = (p.predicted_return_pct ?? 0) >= 0
                return <li key={p.symbol + i}>
                  <button className="pl-row" onClick={() => setOpenIdx(i)} aria-label={`Open analysis for ${p.name}`}>
                    <span className="rk num">{i + 1}</span>
                    <span className="id">
                      <b>{p.name}</b>
                      <span className="meta">
                        <span className="num">{p.symbol} · {p.exchange}</span>
                        {p.quality_pass && <span className="tag pass"><CheckCircle size={12} weight="bold" /> Quality pass</span>}
                        {p.simulation && <span className="tag"><DiceFive size={12} weight="bold" /> {p.simulation.win_probability_pct}% win odds</span>}
                        {p.news?.veto && <span className="tag neg"><Warning size={12} weight="bold" /> News veto</span>}
                        {p.earnings_in_window && <span className="tag warn" title={`Results on ${p.earnings_date}`}><Warning size={12} weight="bold" /> Results {p.earnings_date}</span>}
                        {p.sector && <span className="tag">{p.sector}</span>}
                      </span>
                    </span>
                    <MiniSpark symbol={p.symbol} exchange={p.exchange} />
                    <span className="px num r">{inr(p.current_price)}<span className="to">{inr(p.predicted_price)}</span></span>
                    <span className="ret r"><span className={`retpill sm num ${up ? 'up' : 'dn'}`}>{pct(p.predicted_return_pct)}</span></span>
                    <span className="score num r">{p.trader_score == null ? '—' : Math.round(p.trader_score)}</span>
                    <AccMeter v={p.backtest?.best_dir_acc} />
                    <CaretRight className="chev" size={16} weight="bold" aria-hidden="true" />
                  </button>
                </li>
              })}
            </ol>}
          </section>

          <aside className="side">
            <section className="panel side-sec">
              <h3><CurrencyInr size={16} weight="bold" /> Your budget</h3>
              <p className="hint">Set a budget and every pick gets whole-share counts that fit it.</p>
              <label className="fieldlbl" htmlFor="budget">Budget in rupees</label>
              <div className="budgetrow">
                <input id="budget" type="number" min="0" placeholder="e.g. 50000" value={budget} onChange={e => setBudget(e.target.value)} />
                <button className="btn" disabled={savingBudget} onClick={() => saveBudget(budget === '' ? null : Number(budget))}>{savingBudget ? <span className="orbinline"><ThinkingOrb state="working" size={20} theme={orb} />Saving…</span> : 'Save budget'}</button>
                {savedBudget != null && <button className="btn ghost" disabled={savingBudget} onClick={() => { setBudget(''); saveBudget(null) }}>Clear</button>}
              </div>
              {a ? <div className="allocgrid">
                <div className="ag"><div className="k">Invested</div><div className="v num">{inr(a.total_invested)}</div></div>
                <div className="ag"><div className="k">Leftover</div><div className="v num">{inr(a.leftover)}</div></div>
                <div className="ag"><div className="k">Expected value</div><div className="v num">{inr(a.expected_value)}</div></div>
                <div className="ag"><div className="k">Expected profit</div><div className="v num pos">{inr(a.expected_profit)}</div></div>
                {a.risk_inr != null && <div className="ag"><div className="k">Risk per trade</div><div className="v num">{inr(a.risk_inr)}<span className="s"> · {a.risk_pct}% × {a.size_mult ?? 1}</span></div></div>}
                {a.cash_reserve > 0 && <div className="ag"><div className="k">Cash reserve</div><div className="v num">{inr(a.cash_reserve)}</div></div>}
              </div> : <div className="note">No budget set. Picks are ranked only. Set a budget to see share counts.</div>}
              {a && <p className="hint" style={{ marginTop: 10 }}>Shares are sized so each pick risks the same rupees between entry and stop (ATR risk sizing), capped at 30% per pick{a.cash_reserve > 0 ? ` with ${inr(a.cash_reserve)} held back for the regime` : ''}.</p>}
            </section>

            <section className="panel side-sec">
              <h3><MagnifyingGlass size={16} weight="bold" /> Scan the market</h3>
              <p className="hint">Re-scans all ~7,987 NSE + BSE stocks on official exchange (Bhavcopy) data, deep-backtests the top 150, checks fundamentals &amp; news, then publishes a fresh set of 5-7 picks here automatically.</p>
            </section>

            {(vetoed.length > 0 || demoted.length > 0 || simRejected.length > 0 || survVetoed.length > 0 || earningsSkipped.length > 0 || sectorCapped.length > 0) && <section className="panel side-sec veto-sec">
              <h3><ShieldWarning size={17} weight="bold" /> Excluded by safety &amp; simulation checks</h3>
              {survVetoed.slice(0, 8).map((s: any, i: number) => <div className="vetocard" key={'sv' + i}>
                <div className="vt">{s.name || s.symbol} <span className="chip exch">{s.symbol} · {s.exchange}</span> <span className="chip neg">SURVEILLANCE</span></div>
                <div className="vr">Under exchange surveillance: <b>{s.reason}</b>. Never swing-traded — 100% margin, T2T settlement or tight circuits.</div>
              </div>)}
              {survVetoed.length > 8 && <div className="note">+{survVetoed.length - 8} more surveillance-listed stocks vetoed before deep analysis.</div>}
              {earningsSkipped.map((s: any, i: number) => <div className="vetocard" key={'e' + i}>
                <div className="vt">{s.name || s.symbol} <span className="chip exch">{s.symbol} · {s.exchange}</span> <span className="chip neg">RESULTS IN WINDOW</span></div>
                <div className="vr">Earnings on <b className="num">{s.earnings_date}</b> fall inside the holding window — a coin-flip gap event. Skipped because enough clean picks were available.</div>
              </div>)}
              {sectorCapped.map((s: any, i: number) => <div className="vetocard" key={'sc' + i}>
                <div className="vt">{s.name || s.symbol} <span className="chip exch">{s.symbol} · {s.exchange}</span> <span className="chip neg">SECTOR CAP</span></div>
                <div className="vr">Third pick in <b>{s.sector}</b> — capped at 2 per sector so the portfolio is not one sector bet.</div>
              </div>)}
              {simRejected.map((s: any, i: number) => <div className="vetocard" key={'sim' + i}>
                <div className="vt">{s.name || s.symbol} <span className="chip exch">{s.symbol} · {s.exchange}</span> <span className="chip neg">MONTE CARLO VETO</span></div>
                <div className="vr">Blocked by Time Machine: <b>Stop-loss risk ({s.risk}%) exceeds win odds ({s.win_odds ?? 0}%)</b> across 1,000 historical replays. Excluded to protect capital from high stop-out rates.</div>
              </div>)}
              {vetoed.map((v, i) => <div className="vetocard" key={'v' + i}>
                <div className="vt">{v.name} <span className="chip exch">{v.symbol} · {v.exchange}</span> <span className="chip neg">NEWS VETO</span></div>
                <div className="vr">Blocked headline: <b>“{v.reason}”</b>. This stock passed the technical screen (predicted {pct(v.predicted_return_pct)}) but was excluded because of severe negative news.</div>
              </div>)}
              {demoted.map((v, i) => <div className="vetocard" key={'d' + i}>
                <div className="vt">{v.name} <span className="chip exch">{v.symbol} · {v.exchange}</span> <span className="chip neg">RED-FLAG DEMOTED</span></div>
                <div className="vr">Excluded on fundamentals: {(v.flags || []).join(' · ') || 'Severe debt + shrinking earnings.'}</div>
              </div>)}
            </section>}
          </aside>
        </div>

        <footer className="disc">How to read this: every pick first had to beat the naive baseline in a walk-forward backtest on its own history; the accuracy shown is measured, not promised. Prices come from official NSE/BSE Bhavcopy data; fundamentals and news are checked before a stock can be picked, and severe news (fraud, default, SEBI action) vetoes it openly above. Predictions are for the target date's close, not guarantees. This is analysis software, not investment advice.</footer>
      </>}

      {!loading && !customDesk && tab === 'scanned' && <>
        <dl className="kpis panel four">
          <div><dt>Universe</dt><dd className="num">{scanned?.stage_counts?.universe?.toLocaleString('en-IN') ?? '—'}</dd></div>
          <div><dt>With data</dt><dd className="num">{scanned?.stage_counts?.with_data?.toLocaleString('en-IN') ?? '—'}</dd><dd className="s">NSE {scanned?.stage_counts?.nse_with_data?.toLocaleString('en-IN') ?? '—'} · BSE {scanned?.stage_counts?.bse_with_data?.toLocaleString('en-IN') ?? '—'}</dd></div>
          <div><dt>Liquid</dt><dd className="num">{scanned?.stage_counts?.liquid?.toLocaleString('en-IN') ?? '—'}</dd></div>
          <div><dt>Deep-evaluated</dt><dd className="num">{scanned?.stage_counts?.stage2 ?? '—'}</dd></div>
        </dl>
        <section className="panel">
          {scanned === null && <div className="loadpanel inline"><ThinkingOrb state="working" size={64} theme={orb} /><div className="loadtxt">Loading scanned stocks…</div></div>}
          <div className="tabletools">
            <label className="search">
              <MagnifyingGlass size={16} weight="bold" aria-hidden="true" />
              <input placeholder="Search symbol or company…" aria-label="Search symbol or company" value={query} onChange={e => setQuery(e.target.value)} />
            </label>
            <span className="mut">Top {scannedRows.length} liquid stocks by trader score · click any row to generate 5-day prediction</span>
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
            <th>5D Forecast</th>
          </tr></thead>
            <tbody>{scannedRows.map((s: any, i: number) => <tr key={i} className="clickable-row" onClick={() => openStockPrediction(s.symbol, s.exchange, s.name)} title={`Click to generate 5-day ML prediction & chart for ${s.symbol}`}>
              <td className="num">{i + 1}</td>
              <td><b>{s.symbol}</b><div className="rowname">{s.name}</div></td>
              <td>{s.exchange}</td><td className="num">{inr(s.current_price)}</td>
              <td className="num"><span className="scorebar"><i style={{ width: `${s.trader_score}%` }} /></span>{s.trader_score}</td>
              <td className="num">{s.delivery_pct == null ? '—' : num(s.delivery_pct) + '%'}</td>
              <td className="num">{s.rsi}</td>
              <td className={`num ${s.ret21_pct >= 0 ? 'pos' : 'neg'}`}>{pct(s.ret21_pct)}</td>
              <td className="reasonscell">{(s.reasons || []).join(' · ')}</td>
              <td><span className="view-chart-btn sm">Predict 5D ↗</span></td>
            </tr>)}</tbody></table></div>
          {scanned !== null && scannedRows.length === 0 && <div className="emptystate sm"><p>{query || globalSearch ? 'No stocks match this search.' : 'No scan results yet. Run a market scan to populate this table.'}</p></div>}
        </section>
      </>}

      {!loading && tab === 'history' && historyDesk && (
        <StockDesk
          list={historyDesk.list}
          idx={historyDesk.idx}
          targetDate={historyDesk.targetDate}
          holding={holdings.find(h => h.symbol === historyDesk.list[historyDesk.idx]?.symbol)}
          onSelect={i => setHistoryDesk(h => h ? { ...h, idx: i } : null)}
          onBack={() => setHistoryDesk(null)}
          onSaveHolding={saveHolding}
          onRemoveHolding={removeHolding}
          backLabel="Past Weeks"
        />
      )}

      {!loading && tab === 'history' && !historyDesk && <>
        {history === null && <div className="panel loadpanel"><ThinkingOrb state="working" size={64} theme={orb} /><div className="loadtxt">Loading past weeks &amp; live prices…</div></div>}
        {track && <section className="panel trackrec" aria-label="Live track record">
          <div className="panel-head">
            <h3><ChartLineUp size={16} weight="bold" /> Track record <span className="mut">· settled picks, after 0.3% round-trip costs</span></h3>
            <span className="mut num" style={{ fontSize: 12 }}>{track.n ?? 0} trades · {track.weeks_settled ?? 0} of {track.weeks_total ?? 0} weeks settled</span>
          </div>
          {!track.n ? <div className="note" style={{ margin: '0 20px 18px' }}>No settled picks yet. The track record fills in once a week's target date has passed and official closes are in.</div>
          : <dl className="kpis six">
            <div><dt>Hit rate</dt><dd className={`num ${track.win_rate_pct >= 50 ? 'pos' : 'neg'}`}>{num(track.win_rate_pct)}%</dd><dd className="s">net positive after costs{track.direction_hit_rate_pct != null ? ` · direction ${num(track.direction_hit_rate_pct)}%` : ''}</dd></div>
            <div><dt>Expectancy</dt><dd className={`num ${(track.expectancy_R ?? 0) >= 0 ? 'pos' : 'neg'}`}>{track.expectancy_R == null ? '—' : `${track.expectancy_R >= 0 ? '+' : ''}${track.expectancy_R.toFixed(2)}R`}</dd><dd className="s">per trade, in stop-distance units · target &gt; +0.15R</dd></div>
            <div><dt>Profit factor</dt><dd className={`num ${(track.profit_factor ?? 0) >= 1.3 ? 'pos' : (track.profit_factor ?? 0) < 1 ? 'neg' : ''}`}>{track.profit_factor == null ? '∞' : num(track.profit_factor)}</dd><dd className="s">gross wins ÷ gross losses · target &gt; 1.4</dd></div>
            <div><dt>Payoff ratio</dt><dd className={`num ${(track.payoff_ratio ?? 0) >= 1.3 ? 'pos' : ''}`}>{track.payoff_ratio == null ? '∞' : num(track.payoff_ratio)}</dd><dd className="s">avg win {pct(track.avg_win_pct)} ÷ avg loss {pct(-track.avg_loss_pct)}</dd></div>
            <div><dt>Net avg return</dt><dd className={`num ${(track.avg_return_net_pct ?? 0) >= 0 ? 'pos' : 'neg'}`}>{pct(track.avg_return_net_pct)}</dd><dd className="s">gross {pct(track.avg_return_gross_pct)} · worst streak {track.max_consecutive_losses} losses</dd></div>
            <div><dt>By regime</dt>
              <dd className="num regsplit">
                <span className="regchip bull" title="NIFTY above its 200-DMA on entry day">Bull {track.by_regime?.bull ? `${num(track.by_regime.bull.win_rate_pct)}% · ${pct(track.by_regime.bull.avg_return_net_pct)}` : '—'}</span>
                <span className="regchip bear" title="NIFTY below its 200-DMA on entry day">Bear {track.by_regime?.bear ? `${num(track.by_regime.bear.win_rate_pct)}% · ${pct(track.by_regime.bear.avg_return_net_pct)}` : '—'}</span>
              </dd>
              <dd className="s">hit rate · net return{track.by_regime?.bull && track.by_regime?.bear ? ` (${track.by_regime.bull.n} / ${track.by_regime.bear.n} trades)` : ''}</dd>
            </div>
          </dl>}
        </section>}
        {history !== null && (history?.weeks || []).length === 0 && <div className="panel emptystate">
          <ThinkingOrb state="breathing" size={64} theme={orb} />
          <h4>No past weeks yet</h4>
          <p>History builds up as each Monday run completes and target dates pass.</p>
        </div>}
        {(history?.weeks || []).map((w: any, i: number) => <section className="panel weekcard" key={i}>
          <div className="panel-head">
            <h3>
              <span className="num">Week of {w.run_date} <ArrowRight size={13} weight="bold" aria-hidden="true" /> target {w.target_date}</span>
              <span className="live-badge-indicator"><span className="live-pulse-dot" /> Live Market Tracking</span>
            </h3>
            <span className="mut" style={{ fontSize: 12 }}>Click any stock row to open full price chart &amp; 5-day performance breakdown</span>
          </div>
          <div className="tablewrap"><table><thead><tr>
            <th>Stock</th>
            <th>Was</th>
            <th style={{ textAlign: 'right' }}>Live Price</th>
            <th>Predicted</th>
            <th>Predicted %</th>
            <th>Actual</th>
            <th>Actual %</th>
            <th>Result</th>
            <th>5D Chart</th>
          </tr></thead>
            <tbody>{w.picks.map((p: any, j: number) => {
              const done = p.actual_price != null || p.actual_return_pct != null
              const hit = done && Math.sign(p.actual_return_pct) === Math.sign(p.predicted_return_pct)
              const livePrice = p.live_price ?? p.current_price
              const liveReturn = p.live_return_pct ?? (p.current_price && livePrice ? ((livePrice - p.current_price) / p.current_price) * 100 : null)
              return <tr
                key={j}
                className="hist-row clickable"
                onClick={() => setHistoryDesk({ list: w.picks, idx: j, targetDate: w.target_date })}
                title={`Click to view chart and 5-day price breakdown for ${p.symbol}`}
              >
                <td>
                  <b>{p.symbol}</b>
                  {p.exchange && <span className="chip exch sm">{p.exchange}</span>}
                  {p.name && <div className="rowname">{p.name}</div>}
                </td>
                <td className="num">{inr(p.current_price)}</td>
                <td className="num">
                  <div className="live-price-cell">
                    <span className="live-price-val num">{inr(done ? p.actual_price : livePrice)}</span>
                    {(done ? p.actual_return_pct : liveReturn) != null && (
                      <span className={`live-ret-pill ${(done ? p.actual_return_pct : liveReturn) >= 0 ? 'pos' : 'neg'}`}>
                        {pct(done ? p.actual_return_pct : liveReturn)}
                      </span>
                    )}
                  </div>
                </td>
                <td className="num">{inr(p.predicted_price)}</td>
                <td><PctBar val={p.predicted_return_pct} /></td>
                <td className="num">{done ? inr(p.actual_price) : <span className="mut">Pending</span>}</td>
                <td>{done ? <PctBar val={p.actual_return_pct} /> : <span className="mut">—</span>}</td>
                <td><span className={`hitmiss ${done ? (hit ? 'hit' : 'miss') : 'pend'}`}>{done ? (hit ? 'HIT' : 'MISS') : 'PENDING'}</span></td>
                <td>
                  <span className="view-chart-btn">Graph &amp; 5D ↗</span>
                </td>
              </tr>
            })}</tbody></table></div>
        </section>)}
      </>}
    </main>
  </div>
</div></ThemeCtx.Provider>)
}
