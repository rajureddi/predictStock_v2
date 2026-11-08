import { useState, useMemo } from 'react'
import { ThinkingOrb } from 'thinking-orbs'
import {
  Briefcase, CaretRight, CheckCircle,
  Lightning, MagnifyingGlass, Rocket, ShieldCheck, Sparkle, TrendUp, Warning, X, XCircle
} from '@phosphor-icons/react'
import { C, Holding, inr, num, pct, ScoreRing, useOrb } from './lib'

export type ShortTermPick = {
  symbol: string
  name: string
  exchange: string
  yahoo: string
  current_price: number
  live_price?: number
  market_cap_cr: number
  piotroski_score: number
  piotroski_breakdown?: string[]
  altman_z: number
  altman_z_zone: string
  opm_pct?: number
  sales_growth_pct?: number
  profit_growth_pct?: number
  debt_to_equity: number
  roe_pct?: number
  pe?: number
  peg?: number
  sma20: number
  sma50: number
  rsi: number
  volume_ratio: number
  atr: number
  target: number
  target2: number
  stop_loss: number
  expected_gain_pct: number
  risk_reward: number
  compounding_cagr?: number
  target_1y?: number
  gain_1y_pct?: number
  target_3y?: number
  gain_3y_pct?: number
  multiple_3y?: number
  target_5y?: number
  gain_5y_pct?: number
  multiple_5y?: number
  headroom_multiple?: number
  divis_dna_score?: number
  multibagger_category?: string
  multibagger_thesis?: string
  criteria_passed: number
  total_criteria: number
  criteria_checks: Record<string, { pass: boolean; label: string; value: string }>
  grade: 'A+' | 'A' | 'B+'
  compounder_score: number
  horizon: string
  model_used: string
}

export type ShortTermReport = {
  last_scan: string | null
  total_screened: number
  qualifying_count: number
  picks: ShortTermPick[]
  criteria_summary?: Record<string, string>
}

export default function ShortTerm({
  report,
  scanState,
  onStartScan,
  onOpenStock,
  onSaveHolding,
  holdings
}: {
  report: ShortTermReport | null
  scanState: any
  onStartScan: () => void
  onOpenStock: (symbol: string, exchange: string, name: string) => void
  onSaveHolding: (p: any, shares: number, buy: number) => void
  holdings: Holding[]
}) {
  const orb = useOrb()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterCategory, setFilterCategory] = useState<'ALL' | '10x' | '5x' | 'A+'>('ALL')
  const [sortBy, setSortBy] = useState<'multiple' | 'score' | 'dna' | 'roe' | 'growth'>('multiple')
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null)

  const rawPicks = report?.picks || []

  const filteredPicks = useMemo(() => {
    let list = [...rawPicks]

    const q = searchQuery.trim().toLowerCase()
    if (q) {
      list = list.filter(p =>
        p.symbol.toLowerCase().includes(q) ||
        p.name.toLowerCase().includes(q) ||
        (p.multibagger_category || '').toLowerCase().includes(q) ||
        (p.multibagger_thesis || '').toLowerCase().includes(q)
      )
    }

    if (filterCategory === '10x') {
      list = list.filter(p => p.multibagger_category?.includes('10x') || (p.headroom_multiple ?? 0) >= 10)
    } else if (filterCategory === '5x') {
      list = list.filter(p => (p.multiple_5y ?? 0) >= 3.0 || p.multibagger_category?.includes('5x'))
    } else if (filterCategory === 'A+') {
      list = list.filter(p => p.grade === 'A+')
    }

    list.sort((a, b) => {
      if (sortBy === 'multiple') return (b.multiple_5y ?? 0) - (a.multiple_5y ?? 0)
      if (sortBy === 'score') return b.compounder_score - a.compounder_score
      if (sortBy === 'dna') return (b.divis_dna_score ?? 0) - (a.divis_dna_score ?? 0)
      if (sortBy === 'roe') return (b.roe_pct ?? 0) - (a.roe_pct ?? 0)
      if (sortBy === 'growth') return (b.profit_growth_pct ?? 0) - (a.profit_growth_pct ?? 0)
      return 0
    })
    return list
  }, [rawPicks, searchQuery, filterCategory, sortBy])

  // Aggregate stats
  const avgRoe = rawPicks.length
    ? rawPicks.reduce((s, p) => s + (p.roe_pct || 0), 0) / rawPicks.length
    : null
  const avg3yGain = rawPicks.length
    ? rawPicks.reduce((s, p) => s + (p.multiple_3y || 2.0), 0) / rawPicks.length
    : null
  const avg5yMultiple = rawPicks.length
    ? rawPicks.reduce((s, p) => s + (p.multiple_5y || 3.5), 0) / rawPicks.length
    : null
  const topCompounder = rawPicks[0]

  const isScanning = scanState?.running

  return (
    <div className="shortterm-desk">
      {/* Hero Header */}
      <section className="panel" style={{ padding: '26px 30px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 18 }}>
          <div style={{ maxWidth: 800 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <span className="chip pass" style={{ fontSize: 11, fontWeight: 700, padding: '3px 9px', letterSpacing: '0.4px' }}>
                <Rocket size={13} weight="fill" /> MULTIBAGGER DISCOVERY ENGINE
              </span>
              <span className="chip" style={{ fontSize: 11, background: 'rgba(255,94,26,0.1)', color: 'var(--accent)', fontWeight: 600 }}>
                The Divi's Lab Framework (₹40 → ₹2,000+)
              </span>
              {report?.last_scan && (
                <span className="chip" style={{ fontSize: 11, color: 'var(--mut)' }}>
                  Scanned: {report.last_scan}
                </span>
              )}
            </div>
            <h2 style={{ margin: '0 0 10px', fontSize: 25, fontWeight: 600, letterSpacing: '-0.025em' }}>
              Multibagger Quality Compounders
            </h2>
            <p style={{ margin: 0, color: 'var(--mut)', fontSize: 13.5, lineHeight: 1.6 }}>
              Identifies emerging Indian market leaders in the <b>₹500 Cr – ₹30,000 Cr</b> sweet spot before they become large-caps.
              Requires <b>Piotroski F-Score &gt; 7</b>, <b>Altman Z &gt; 3.0</b> (zero distress), <b>10%+ 10Y OPM / Sales / Profit Growth</b>,{' '}
              <b>D/E &lt; 1.0</b> (clean balance sheet), <b>ROE &gt; 15%</b>, and <b>PEG &lt; 1.0</b> for dual-engine EPS growth and P/E rerating.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
            <button
              className="btn dark"
              disabled={isScanning}
              onClick={onStartScan}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '11px 20px', fontSize: 14, fontWeight: 600 }}
            >
              {isScanning ? (
                <>
                  <ThinkingOrb state="working" size={20} theme={orb} />
                  <span>Scanning {scanState.current_symbol || 'Market'}… ({scanState.progress_pct ?? 0}%)</span>
                </>
              ) : (
                <>
                  <Rocket size={16} weight="bold" />
                  <span>Scan for Multibaggers</span>
                </>
              )}
            </button>
            {isScanning && (
              <span className="mut" style={{ fontSize: 11.5 }}>
                Found {scanState.found_count ?? 0} qualifying compounders…
              </span>
            )}
          </div>
        </div>

        {/* The 12-Factor Multibagger DNA Filter Strip */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--line)' }}>
          <span className="chip" style={{ fontSize: 11 }}>Cap: ₹500Cr – ₹30kCr (Sweet Spot)</span>
          <span className="chip" style={{ fontSize: 11 }}>Piotroski F-Score ≥ 7</span>
          <span className="chip" style={{ fontSize: 11 }}>Altman Z-Score ≥ 3.0 (Zero Distress)</span>
          <span className="chip" style={{ fontSize: 11 }}>OPM ≥ 10% (Pricing Power)</span>
          <span className="chip" style={{ fontSize: 11 }}>Sales Growth ≥ 10%</span>
          <span className="chip" style={{ fontSize: 11 }}>Profit Growth ≥ 10%</span>
          <span className="chip" style={{ fontSize: 11 }}>Debt / Equity &lt; 1.0</span>
          <span className="chip" style={{ fontSize: 11 }}>ROE ≥ 15%</span>
          <span className="chip" style={{ fontSize: 11 }}>PEG &lt; 1.0 (Rerating Runway)</span>
          <span className="chip" style={{ fontSize: 11 }}>Price &gt; 20-DMA Uptrend</span>
          <span className="chip" style={{ fontSize: 11 }}>RSI 45–68 (Accumulation)</span>
          <span className="chip" style={{ fontSize: 11 }}>Multi-Year Trajectory</span>
        </div>
      </section>

      {/* KPI Cards */}
      <dl className="kpis panel" style={{ marginBottom: 20 }}>
        <div>
          <dt>Discovered Compounders</dt>
          <dd className="num">{rawPicks.length}</dd>
          <dd className="s">Passed ₹500Cr–₹30kCr sweet spot</dd>
        </div>
        <div>
          <dt>Avg 3-Year Projection</dt>
          <dd className="num pos">{avg3yGain ? `${avg3yGain.toFixed(1)}x` : '—'}</dd>
          <dd className="s">Doubling horizon</dd>
        </div>
        <div>
          <dt>Avg 5-Year Runway</dt>
          <dd className="num acc">{avg5yMultiple ? `${avg5yMultiple.toFixed(1)}x` : '—'}</dd>
          <dd className="s">Multibagger trajectory</dd>
        </div>
        <div>
          <dt>Avg Return on Equity</dt>
          <dd className="num pos">{avgRoe ? pct(avgRoe) : '—'}</dd>
          <dd className="s">Reinvestment engine</dd>
        </div>
        <div>
          <dt>Top Divi's Lab Analog</dt>
          <dd className="num">{topCompounder ? topCompounder.symbol : '—'}</dd>
          <dd className="s">{topCompounder ? `${topCompounder.divis_dna_score}% DNA Match` : '—'}</dd>
        </div>
      </dl>

      {/* Search and Filter Control Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        {/* Search Section */}
        <div style={{ position: 'relative', minWidth: 260, flex: '1 1 300px', maxWidth: 440 }}>
          <MagnifyingGlass
            size={16}
            weight="bold"
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--mut)', pointerEvents: 'none' }}
          />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search multibaggers by ticker, company, or theme..."
            style={{
              width: '100%',
              padding: '9px 34px 9px 36px',
              borderRadius: 'var(--r-sm)',
              border: '1px solid var(--line)',
              background: 'var(--surface)',
              color: 'var(--ink)',
              fontSize: 13,
              outline: 'none',
              boxSizing: 'border-box',
              transition: 'border-color 0.15s ease'
            }}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: 8,
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--mut)',
                padding: 4,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Clear search"
            >
              <X size={14} weight="bold" />
            </button>
          )}
        </div>

        {/* Category Filter Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: 'var(--mut)', fontWeight: 500 }}>Category:</span>
          {(['ALL', '10x', '5x', 'A+'] as const).map(cat => (
            <button
              key={cat}
              className={`btn sm ${filterCategory === cat ? 'dark' : 'ghost'}`}
              onClick={() => setFilterCategory(cat)}
              style={{ fontSize: 12, padding: '5px 12px' }}
            >
              {cat === 'ALL' ? 'All Multibaggers' : cat === '10x' ? '10x Potential' : cat === '5x' ? '5x+ Compounders' : 'Grade A+'}
            </button>
          ))}
        </div>

        {/* Sort Dropdown & Matches Count */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="mut" style={{ fontSize: 12 }}>
            Showing <b>{filteredPicks.length}</b> of <b>{rawPicks.length}</b>
          </span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value as any)}
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--r-sm)',
              border: '1px solid var(--line)',
              background: 'var(--surface)',
              color: 'var(--ink)',
              fontSize: 12.5
            }}
          >
            <option value="multiple">5-Year Multibagger Potential (Multiple)</option>
            <option value="dna">Divi's Lab DNA Score</option>
            <option value="score">Quality Compounder Score</option>
            <option value="roe">ROE % (Capital Efficiency)</option>
            <option value="growth">Profit Growth %</option>
          </select>
        </div>
      </div>

      {/* Main List */}
      {filteredPicks.length === 0 ? (
        <section className="panel emptystate" style={{ padding: 48, textAlign: 'center' }}>
          <ThinkingOrb state={isScanning ? 'searching' : 'breathing'} size={64} theme={orb} />
          {searchQuery ? (
            <>
              <h4 style={{ margin: '14px 0 6px' }}>No matches for "{searchQuery}"</h4>
              <p style={{ maxWidth: 520, margin: '0 auto 16px', color: 'var(--mut)', fontSize: 13.5 }}>
                No qualifying compounder matches your search query in this category. Try clearing the search or checking another filter category.
              </p>
              <button className="btn ghost" onClick={() => { setSearchQuery(''); setFilterCategory('ALL') }}>
                Clear Search &amp; Filters
              </button>
            </>
          ) : (
            <>
              <h4 style={{ margin: '14px 0 6px' }}>{isScanning ? 'Scanning for Multibaggers…' : 'No compounders in list yet'}</h4>
              <p style={{ maxWidth: 520, margin: '0 auto 16px', color: 'var(--mut)', fontSize: 13.5 }}>
                {isScanning
                  ? 'Analyzing balance sheets, Piotroski scores, Altman Z solvency, and multi-year compounding runways…'
                  : 'Click "Scan for Multibaggers" above to execute the Divi\'s Lab framework across Indian equities.'}
              </p>
              {!isScanning && (
                <button className="btn dark" onClick={onStartScan}>
                  <Rocket size={15} weight="bold" /> Start Multibagger Scan
                </button>
              )}
            </>
          )}
        </section>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {filteredPicks.map(p => {
            const isExpanded = expandedSymbol === p.symbol
            const isHeld = holdings.some(h => h.symbol === p.symbol)
            const price = p.live_price ?? p.current_price
            const moveSinceEntry = p.current_price && price ? ((price - p.current_price) / p.current_price) * 100 : 0

            return (
              <section key={p.symbol} className="panel" style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
                  {/* Stock Identity & DNA Match */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <ScoreRing score={p.compounder_score} size={60} />
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <h3 style={{ margin: 0, fontSize: 19, fontWeight: 600 }}>{p.name}</h3>
                        <span className="chip exch sm">{p.symbol} · {p.exchange}</span>
                        <span className="chip pass" style={{ fontSize: 11, fontWeight: 700, background: 'rgba(30,158,90,0.14)' }}>
                          {p.multibagger_category || 'Multibagger Compounder'}
                        </span>
                        <span className="chip" style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', background: 'rgba(255,94,26,0.08)' }}>
                          <Sparkle size={12} weight="fill" /> {p.divis_dna_score}% Divi's Lab DNA
                        </span>
                        <span className="chip" style={{ fontSize: 11, color: 'var(--mut)' }}>
                          {p.criteria_passed} / {p.total_criteria} Criteria Passed
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 5, color: 'var(--mut)', fontSize: 12.5 }}>
                        <span>Market Cap: <b>₹{p.market_cap_cr.toLocaleString('en-IN')} Cr</b></span>
                        <span>Headroom: <b style={{ color: 'var(--accent)' }}>{p.headroom_multiple}x to Large-Cap</b></span>
                        <span>Piotroski: <b className="pos">{p.piotroski_score}/9</b></span>
                        <span>Altman Z: <b className="pos">{p.altman_z.toFixed(1)}</b></span>
                        <span>OPM: <b>{p.opm_pct != null ? `${p.opm_pct}%` : '—'}</b></span>
                        <span>ROE: <b className="pos">{p.roe_pct != null ? `${p.roe_pct}%` : '—'}</b></span>
                        <span>D/E: <b>{p.debt_to_equity.toFixed(2)}</b></span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <button
                      className="btn"
                      onClick={() => onOpenStock(p.symbol, p.exchange, p.name)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}
                    >
                      Deep Analysis &amp; Chart <CaretRight size={13} weight="bold" />
                    </button>
                    <button
                      className={`btn ${isHeld ? 'ghost' : 'dark'}`}
                      onClick={() => onSaveHolding(p, 1, price)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}
                    >
                      <Briefcase size={14} weight="bold" />
                      {isHeld ? 'In Portfolio' : '+ Add to Portfolio'}
                    </button>
                  </div>
                </div>

                {/* Multibagger Exponential Targets Strip */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: 12,
                  marginTop: 16,
                  padding: '14px 18px',
                  borderRadius: 'var(--r-sm)',
                  background: 'var(--surface2)',
                  border: '1px solid var(--line)'
                }}>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--mut)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Live Market Price
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }} className="num">
                      {inr(price)}
                      <span className="chip pass sm" style={{ marginLeft: 6, fontSize: 10, padding: '1px 5px' }}>LIVE</span>
                    </div>
                    <div style={{ fontSize: 11.5 }} className={`num ${moveSinceEntry >= 0 ? 'pos' : 'neg'}`}>
                      {pct(moveSinceEntry)} today
                    </div>
                  </div>

                  <div style={{ borderLeft: '1px solid var(--line)', paddingLeft: 14 }}>
                    <div style={{ fontSize: 11, color: 'var(--mut)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      1-Year Milestone
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }} className="num">
                      {inr(p.target_1y ?? p.target)}
                    </div>
                    <div style={{ fontSize: 11.5 }} className="num pos">
                      +{p.gain_1y_pct ?? 30}% (Initial compounding)
                    </div>
                  </div>

                  <div style={{ borderLeft: '1px solid var(--line)', paddingLeft: 14 }}>
                    <div style={{ fontSize: 11, color: 'var(--mut)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      3-Year Horizon (Doubling)
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }} className="num pos">
                      {inr(p.target_3y)}
                    </div>
                    <div style={{ fontSize: 11.5 }} className="num pos">
                      <b>{p.multiple_3y ? `${p.multiple_3y}x` : '2x'}</b> (+{p.gain_3y_pct}%)
                    </div>
                  </div>

                  <div style={{ borderLeft: '1px solid var(--line)', paddingLeft: 14 }}>
                    <div style={{ fontSize: 11, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                      5-Year Multibagger Horizon
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2, color: 'var(--accent)' }} className="num">
                      {inr(p.target_5y)}
                    </div>
                    <div style={{ fontSize: 11.5, color: 'var(--accent)', fontWeight: 600 }} className="num">
                      <b>{p.multiple_5y ? `${p.multiple_5y}x` : '4x+'}</b> (+{p.gain_5y_pct}%)
                    </div>
                  </div>
                </div>

                {/* Multibagger Thesis Callout */}
                {p.multibagger_thesis && (
                  <div style={{
                    marginTop: 12,
                    padding: '10px 14px',
                    borderRadius: 'var(--r-sm)',
                    background: 'rgba(255,94,26,0.04)',
                    borderLeft: '3px solid var(--accent)',
                    fontSize: 12.5,
                    lineHeight: 1.5,
                    color: 'var(--ink)'
                  }}>
                    <b>Multibagger Compounding Thesis:</b> {p.multibagger_thesis}
                  </div>
                )}

                {/* Criteria Checklist Strip */}
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, fontSize: 12 }}>
                    {Object.entries(p.criteria_checks).map(([k, c]) => (
                      <span
                        key={k}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '2px 8px',
                          borderRadius: 'var(--r-sm)',
                          background: c.pass ? 'var(--up-wash)' : 'var(--surface2)',
                          color: c.pass ? 'var(--up)' : 'var(--mut)',
                          fontSize: 11.5,
                          fontWeight: c.pass ? 600 : 400
                        }}
                      >
                        {c.pass ? <CheckCircle size={12} weight="bold" /> : <XCircle size={12} weight="regular" />}
                        {c.label}: <b>{c.value}</b>
                      </span>
                    ))}
                  </div>

                  <button
                    className="btn ghost sm"
                    onClick={() => setExpandedSymbol(isExpanded ? null : p.symbol)}
                    style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}
                  >
                    {isExpanded ? 'Hide Full Breakdown' : 'View Solvency & Piotroski Details'}
                  </button>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div style={{ marginTop: 14, padding: 16, borderRadius: 'var(--r-sm)', background: 'var(--surface2)', fontSize: 12.5 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
                      <div>
                        <h4 style={{ margin: '0 0 6px', fontSize: 13, color: 'var(--ink)' }}>Piotroski Quality Audit ({p.piotroski_score}/9)</h4>
                        <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--mut)', lineHeight: 1.65 }}>
                          {(p.piotroski_breakdown || []).map((b, i) => (
                            <li key={i}>{b}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 style={{ margin: '0 0 6px', fontSize: 13, color: 'var(--ink)' }}>Compounding &amp; Solvency Engine</h4>
                        <div style={{ color: 'var(--mut)', lineHeight: 1.65 }}>
                          <div>• Altman Z-Score: <b className="pos">{p.altman_z.toFixed(2)}</b> ({p.altman_z_zone})</div>
                          <div>• Debt / Equity: <b>{p.debt_to_equity.toFixed(2)}</b> (Clean Debt)</div>
                          <div>• Compounding CAGR: <b className="pos">+{p.compounding_cagr ?? 20}% / year</b></div>
                          <div>• PEG Ratio: <b>{p.peg != null ? p.peg.toFixed(2) : '—'}</b> (Rerating Runway)</div>
                          <div>• Market Cap Headroom: <b style={{ color: 'var(--accent)' }}>{p.headroom_multiple}x to ₹1 Lakh Cr</b></div>
                        </div>
                      </div>
                      <div>
                        <h4 style={{ margin: '0 0 6px', fontSize: 13, color: 'var(--ink)' }}>Entry Timing &amp; Technical Trend</h4>
                        <div style={{ color: 'var(--mut)', lineHeight: 1.65 }}>
                          <div>• Current Price: <b>{inr(price)}</b> vs 20-DMA <b>{inr(p.sma20)}</b></div>
                          <div>• 50-DMA: <b>{inr(p.sma50)}</b> (Golden Alignment)</div>
                          <div>• RSI(14): <b>{p.rsi}</b> (Sweet Spot Accumulation)</div>
                          <div>• Volume Ratio: <b>{p.volume_ratio}x</b> of 20-day average</div>
                          <div>• Initial Thesis Invalidation Stop: <b className="neg">{inr(p.stop_loss)}</b></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
