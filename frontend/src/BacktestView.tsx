import React, { useState, useEffect } from 'react'
import {
  Calendar,
  Play,
  CheckCircle,
  WarningCircle,
  Lightning,
  ChartLineUp,
  TrendUp,
  TrendDown,
  CaretDown,
  CaretUp,
  ArrowRight,
  ShieldCheck,
  Target,
  ArrowClockwise,
  Info,
  Cpu,
  Gauge,
  Scales
} from '@phosphor-icons/react'
import { ThinkingOrb } from 'thinking-orbs'

interface Trade {
  symbol: string
  entry_price: number
  exit_price: number
  stop_loss: number
  stop_loss_base?: number
  target: number
  net_return_pct: number
  gross_return_pct: number
  exit_reason: string
  days_held: number
  is_win: boolean
  status: 'WIN' | 'LOSS'
  date: string
  trader_score?: number
  predicted_return_pct?: number
  best_dir_acc?: number
  sim_win_prob_pct?: number
  sim_avg_r?: number
  rsi?: number
  adx?: number
  risk_reward?: number
  pe?: number | null
  debt_to_equity?: number | null
  patterns?: string[]
  sector?: string
}

interface WeekRow {
  week_index: number
  run_date: string
  target_date: string
  market_regime: string
  regime_200dma: string
  picks_count: number
  wins_count: number
  losses_count: number
  win_rate_pct: number
  weekly_net_pct: number
  nifty_net_pct: number
  alpha_pct: number
  trades: Trade[]
}

interface ExecutiveSummary {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate_pct: number
  max_drawdown_pct: number
  total_strategy_return_pct: number
  nifty_benchmark_return_pct: number
  outperformance_alpha_pct: number
  profit_factor: number
  payoff_ratio: number
  avg_win_pct: number
  avg_loss_pct: number
  best_week_pct: number
  worst_week_pct: number
  cagr_pct?: number
  sharpe_ratio?: number
  readiness_verdict: string
  readiness_explanation: string
}

interface BacktestResults {
  available: boolean
  generated?: string
  elapsed_seconds?: number
  params?: {
    weeks: number
    from_date: string
    to_date: string
    top_picks: number
    universe_size: number
    cost_per_side_pct: number
    round_trip_cost_pct: number
    metrics_evaluated?: string[]
  }
  executive_summary?: ExecutiveSummary
  weekly?: WeekRow[]
}

export function BacktestView() {
  const [results, setResults] = useState<BacktestResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<any>(null)
  const [expandedWeek, setExpandedWeek] = useState<number | null>(null)

  // Default: Past 1 Year (52 Weeks ago to last Friday)
  const today = new Date()
  const oneYearAgo = new Date(today.getTime() - 365 * 24 * 60 * 60 * 1000)
  const defaultFrom = oneYearAgo.toISOString().split('T')[0]
  const defaultTo = today.toISOString().split('T')[0]

  const [fromDate, setFromDate] = useState<string>(defaultFrom)
  const [toDate, setToDate] = useState<string>(defaultTo)
  const [topPicks, setTopPicks] = useState<number>(5)
  const [activePreset, setActivePreset] = useState<'1y' | '6m' | '2y' | 'custom'>('1y')

  // Load existing results on mount
  const loadResults = async () => {
    try {
      const res = await fetch(`/api/backtest?_t=${Date.now()}`, { cache: 'no-store' })
      const data = await res.json()
      if (data && data.available) {
        setResults(data)
      }
    } catch (e) {
      console.error('Failed to load backtest results:', e)
    }
  }

  // Poll status when running
  useEffect(() => {
    loadResults()
    let intv: any = null

    const checkStatus = async () => {
      try {
        const res = await fetch(`/api/backtest/status?_t=${Date.now()}`, { cache: 'no-store' })
        const s = await res.json()
        setStatus(s)
        if (s.running) {
          setLoading(true)
        } else if (s.stage === 'done' || (!s.running && loading)) {
          setLoading(false)
          loadResults()
        }
      } catch {}
    }

    checkStatus()
    intv = setInterval(checkStatus, 1200)
    return () => clearInterval(intv)
  }, [loading])

  const triggerRun = async (fDate?: string, tDate?: string, wCount?: number) => {
    const finalFrom = fDate || fromDate
    const finalTo = tDate || toDate
    setResults(null) // clear old results so user sees live simulation in real-time
    setLoading(true)
    try {
      await fetch('/api/backtest/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_date: finalFrom,
          to_date: finalTo,
          weeks: wCount || (activePreset === '2y' ? 104 : activePreset === '6m' ? 26 : 52),
          top_picks: topPicks
        })
      })
    } catch (e) {
      console.error('Failed to trigger backtest:', e)
      setLoading(false)
    }
  }

  const startBacktest = () => triggerRun()

  const handlePresetSelect = (preset: '1y' | '6m' | '2y', autoRun = true) => {
    const now = new Date()
    let days = 365
    let w = 52
    if (preset === '6m') { days = 182; w = 26; }
    if (preset === '2y') { days = 730; w = 104; }
    const start = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
    const fDate = start.toISOString().split('T')[0]
    const tDate = now.toISOString().split('T')[0]
    setFromDate(fDate)
    setToDate(tDate)
    setActivePreset(preset)
    if (autoRun) {
      triggerRun(fDate, tDate, w)
    }
  }

  const ex = results?.executive_summary
  const isRunning = status?.running || loading

  return (
    <div className="backtest-desk" style={{ maxWidth: 1200, margin: '0 auto', paddingBottom: 60 }}>
      {/* Header Banner */}
      <section className="panel" style={{ padding: '24px 30px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ maxWidth: 740 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span className="chip pass" style={{ fontSize: 11, fontWeight: 700, padding: '3px 9px', letterSpacing: '0.4px' }}>
                <ChartLineUp size={14} weight="fill" /> COMPLETE PRODUCTION ENGINE BACKTEST
              </span>
              <span className="chip" style={{ fontSize: 11, background: 'rgba(255,94,26,0.1)', color: 'var(--info)', fontWeight: 600 }}>
                Technicals + Walk-Forward ML + Monte Carlo + Fundamentals + VIX Regime
              </span>
            </div>
            <h2 style={{ margin: '0 0 8px', fontSize: 24, fontWeight: 600, letterSpacing: '-0.025em' }}>
              Historical Prediction Proof (Monday-to-Friday Walk-Forward)
            </h2>
            <p style={{ margin: 0, color: 'var(--mut)', fontSize: 13.5, lineHeight: 1.6 }}>
              Replays our <b>exact production multi-metric prediction architecture</b> strictly point-in-time on past market data:
              Technical Breakout Filters (RSI, ADX, Support/Resistance, Delivery %), Out-of-Sample Walk-Forward Machine Learning,
              Market Regime &amp; India VIX Stop Widening, 500-Replay Time Machine Monte Carlo, and Debt Red-Flag Gates with <b>0.30% round-trip costs</b>.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                className="btn dark"
                disabled={isRunning}
                onClick={() => triggerRun()}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '11px 22px',
                  fontSize: 13.5,
                  fontWeight: 600,
                  background: isRunning ? 'var(--panel)' : 'var(--accent)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--r-sm)',
                  cursor: isRunning ? 'not-allowed' : 'pointer'
                }}
              >
                {isRunning ? (
                  <>
                    <ThinkingOrb state="working" size={20} theme="dark" />
                    <span>{status?.status_message || `Simulating Week ${status?.current_week || 1} of ${status?.total_weeks || 52}...`} ({status?.progress_pct || 0}%)</span>
                  </>
                ) : (
                  <>
                    <Lightning size={16} weight="fill" />
                    <span>
                      {activePreset === '1y'
                        ? 'Run 1-Year Backtest (52 Weeks)'
                        : activePreset === '6m'
                        ? 'Run 6-Month Backtest (26 Weeks)'
                        : activePreset === '2y'
                        ? 'Run 2-Year Backtest (104 Weeks)'
                        : `Run Backtest (${fromDate} → ${toDate})`}
                    </span>
                  </>
                )}
              </button>
              <button
                type="button"
                className="btn ghost sm"
                disabled={isRunning}
                onClick={loadResults}
                title="Refresh current results"
                style={{
                  padding: '10px 12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  fontSize: 12.5,
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)'
                }}
              >
                <ArrowClockwise size={15} />
                <span>Reload</span>
              </button>
            </div>
            <span style={{ fontSize: 11, color: 'var(--mut)' }}>
              {results?.params ? `Last Completed: ${results.params.weeks} Weeks (${results.params.from_date} to ${results.params.to_date})` : 'Ready to execute'}
            </span>
          </div>
        </div>

        {/* Date Controls & Parameters Strip */}
        <div style={{
          marginTop: 22,
          paddingTop: 18,
          borderTop: '1px solid var(--line)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16
        }}>
          {/* Date Pickers */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>From:</span>
              <input
                type="date"
                value={fromDate}
                disabled={isRunning}
                onChange={e => {
                  setFromDate(e.target.value)
                  setActivePreset('custom')
                }}
                style={{
                  padding: '5px 10px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  fontSize: 12
                }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>To:</span>
              <input
                type="date"
                value={toDate}
                disabled={isRunning}
                onChange={e => {
                  setToDate(e.target.value)
                  setActivePreset('custom')
                }}
                style={{
                  padding: '5px 10px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  fontSize: 12
                }}
              />
            </div>

            {/* Quick Presets with Instant Run */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 6 }}>
              <span style={{ fontSize: 11, color: 'var(--mut)', fontWeight: 600 }}>Quick Presets:</span>
              <button
                type="button"
                className="btn sm"
                disabled={isRunning}
                onClick={() => handlePresetSelect('1y', true)}
                title="Run Past 1 Year (52 Weeks) simulation immediately"
                style={{
                  padding: '5px 11px',
                  fontSize: 11.5,
                  fontWeight: 600,
                  borderRadius: 'var(--r-sm)',
                  background: activePreset === '1y' ? 'var(--accent)' : 'var(--panel)',
                  color: activePreset === '1y' ? '#fff' : 'var(--ink)',
                  border: '1px solid ' + (activePreset === '1y' ? 'var(--accent)' : 'var(--line)'),
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  cursor: isRunning ? 'not-allowed' : 'pointer'
                }}
              >
                <Play size={10} weight="fill" />
                <span>1 Year (52W)</span>
              </button>
              <button
                type="button"
                className="btn sm"
                disabled={isRunning}
                onClick={() => handlePresetSelect('6m', true)}
                title="Run Past 6 Months (26 Weeks) simulation immediately"
                style={{
                  padding: '5px 11px',
                  fontSize: 11.5,
                  fontWeight: 600,
                  borderRadius: 'var(--r-sm)',
                  background: activePreset === '6m' ? 'var(--accent)' : 'var(--panel)',
                  color: activePreset === '6m' ? '#fff' : 'var(--ink)',
                  border: '1px solid ' + (activePreset === '6m' ? 'var(--accent)' : 'var(--line)'),
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  cursor: isRunning ? 'not-allowed' : 'pointer'
                }}
              >
                <Play size={10} weight="fill" />
                <span>6 Months (26W)</span>
              </button>
              <button
                type="button"
                className="btn sm"
                disabled={isRunning}
                onClick={() => handlePresetSelect('2y', true)}
                title="Run Past 2 Years (104 Weeks) simulation immediately"
                style={{
                  padding: '5px 11px',
                  fontSize: 11.5,
                  fontWeight: 600,
                  borderRadius: 'var(--r-sm)',
                  background: activePreset === '2y' ? 'var(--accent)' : 'var(--panel)',
                  color: activePreset === '2y' ? '#fff' : 'var(--ink)',
                  border: '1px solid ' + (activePreset === '2y' ? 'var(--accent)' : 'var(--line)'),
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  cursor: isRunning ? 'not-allowed' : 'pointer'
                }}
              >
                <Play size={10} weight="fill" />
                <span>2 Years (104W)</span>
              </button>
            </div>
          </div>

          {/* Engine Parameters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--mut)' }}>Picks / Week:</span>
              <select
                value={topPicks}
                disabled={isRunning}
                onChange={e => setTopPicks(Number(e.target.value))}
                style={{
                  padding: '4px 8px',
                  borderRadius: 'var(--r-sm)',
                  border: '1px solid var(--line)',
                  background: 'var(--surface)',
                  color: 'var(--ink)',
                  fontSize: 12
                }}
              >
                <option value={3}>3 Stocks</option>
                <option value={5}>5 Stocks</option>
                <option value={6}>6 Stocks</option>
                <option value={10}>10 Stocks</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span
                className="chip"
                style={{
                  fontSize: 11,
                  padding: '4px 10px',
                  background: 'rgba(255,255,255,0.1)',
                  color: 'var(--up)',
                  fontWeight: 600,
                  border: '1px solid rgba(255,255,255,0.2)'
                }}
              >
                ✓ All 7 Multi-Metric Gates Active
              </span>
            </div>
          </div>
        </div>

        {/* Live Multi-Metric Progress Indicator when Running */}
        {isRunning && (
          <div style={{ marginTop: 20, padding: '16px', background: 'var(--surface)', borderRadius: 'var(--r-sm)', border: '1px solid var(--line)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ color: 'var(--accent)', fontWeight: 600, fontSize: 13 }}>
                {status?.status_message || `Simulating Week ${status?.current_week || 1} of ${status?.total_weeks || 52}...`}
              </span>
              <span className="num" style={{ fontWeight: 700, fontSize: 14 }}>{status?.progress_pct ?? 0}%</span>
            </div>
            <div style={{ width: '100%', height: 7, background: 'var(--line)', borderRadius: 4, overflow: 'hidden', marginBottom: 12 }}>
              <div
                style={{
                  width: `${status?.progress_pct ?? 0}%`,
                  height: '100%',
                  background: 'var(--accent)',
                  transition: 'width 0.4s ease'
                }}
              />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 11 }}>
              <span className="chip" style={{ background: 'var(--panel)', color: 'var(--mut)' }}>1. Market Regime &amp; VIX</span>
              <span className="chip" style={{ background: 'var(--panel)', color: 'var(--mut)' }}>2. Technical Breakout &amp; Delivery</span>
              <span className="chip" style={{ background: 'var(--panel)', color: 'var(--mut)' }}>3. Walk-Forward ML Forecast</span>
              <span className="chip" style={{ background: 'var(--panel)', color: 'var(--mut)' }}>4. Time Machine Monte Carlo 500 Replays</span>
              <span className="chip" style={{ background: 'var(--panel)', color: 'var(--mut)' }}>5. Fundamentals &amp; Debt Gate</span>
              <span className="chip" style={{ background: 'var(--panel)', color: 'var(--mut)' }}>6. 5-Day Trade Settlement</span>
            </div>
          </div>
        )}

        {status?.stage === 'error' && (
          <div style={{ marginTop: 20, padding: '16px', background: 'rgba(235,0,41,0.08)', borderRadius: 'var(--r-sm)', border: '1px solid rgba(235,0,41,0.25)', color: 'var(--down)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}>
              <WarningCircle size={18} weight="fill" />
              <span>Backtest Error Encountered:</span>
            </div>
            <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--ink)' }}>{status?.last_error || 'Execution encountered an issue'}</p>
          </div>
        )}
      </section>

      {/* Live Simulation Takeover Screen (Replaces old data while simulation is active) */}
      {isRunning && (
        <section className="panel" style={{ padding: '36px 30px', textAlign: 'center', marginBottom: 24, border: '1px solid var(--accent)' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
            <ThinkingOrb state="working" size={32} theme="dark" />
          </div>
          <h3 style={{ margin: '0 0 6px', fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>
            Simulating Past 52 Weeks Walk-Forward ({status?.current_week || 1} / {status?.total_weeks || 52})
          </h3>
          <p style={{ margin: '0 auto 20px', maxWidth: 580, color: 'var(--mut)', fontSize: 13.5, lineHeight: 1.6 }}>
            Currently evaluating <b>Week {status?.current_week || 1} ({status?.current_date || 'Point-in-Time'})</b> strictly point-in-time: Technical Breakout Filters, Walk-Forward ML Forecast, 300-Replay Monte Carlo Bootstrap, and Debt Gates with zero lookahead bias.
          </p>
          <div style={{ maxWidth: 640, margin: '0 auto 16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, fontWeight: 700, marginBottom: 8 }}>
              <span style={{ color: 'var(--accent)' }}>{status?.status_message || `Simulating Week ${status?.current_week || 1} of ${status?.total_weeks || 52}...`}</span>
              <span className="num" style={{ fontSize: 14 }}>{status?.progress_pct ?? 0}%</span>
            </div>
            <div style={{ width: '100%', height: 10, background: 'var(--line)', borderRadius: 5, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${status?.progress_pct ?? 0}%`,
                  height: '100%',
                  background: 'var(--accent)',
                  transition: 'width 0.4s ease'
                }}
              />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 10, fontSize: 11.5, color: 'var(--mut)' }}>
            <span className="chip" style={{ background: 'var(--surface)' }}>✓ Regime &amp; VIX Stop Widening</span>
            <span className="chip" style={{ background: 'var(--surface)' }}>✓ RSI &amp; Delivery Surge Filter</span>
            <span className="chip" style={{ background: 'var(--surface)' }}>✓ Out-of-Sample ML Cross-Validation</span>
            <span className="chip" style={{ background: 'var(--surface)' }}>✓ 300-Replay Time Machine Monte Carlo</span>
            <span className="chip" style={{ background: 'var(--surface)' }}>✓ 5-Day Holding Exit Settlement</span>
          </div>
          <div style={{ marginTop: 18, fontSize: 12, color: 'var(--mut)' }}>
            ⏳ Running all 52 historical weeks (~1.5 to 2 minutes total). The full 52-week audit report will automatically appear here once complete.
          </div>
        </section>
      )}

      {/* TOP SINGLE ANALYSIS: Model Readiness Banner */}
      {!isRunning && ex && (
        <section
          className="panel"
          style={{
            padding: '20px 24px',
            marginBottom: 20,
            background: ex.readiness_verdict.includes('PASSED') ? 'rgba(255,255,255,0.06)' : 'rgba(255,94,26,0.06)',
            borderColor: ex.readiness_verdict.includes('PASSED') ? 'rgba(255,255,255,0.25)' : 'rgba(255,94,26,0.25)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
            {ex.readiness_verdict.includes('PASSED') ? (
              <CheckCircle size={26} weight="fill" color="var(--up)" style={{ flexShrink: 0, marginTop: 2 }} />
            ) : (
              <WarningCircle size={26} weight="fill" color="var(--amber)" style={{ flexShrink: 0, marginTop: 2 }} />
            )}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.4px', textTransform: 'uppercase', color: 'var(--mut)' }}>
                  Model Real-World Testing Audit (All Production Gates Applied)
                </span>
                <span
                  className="chip"
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    background: ex.readiness_verdict.includes('PASSED') ? 'rgba(255,255,255,0.15)' : 'rgba(255,94,26,0.15)',
                    color: ex.readiness_verdict.includes('PASSED') ? 'var(--up)' : 'var(--amber)'
                  }}
                >
                  {ex.readiness_verdict}
                </span>
              </div>
              <p style={{ margin: 0, fontSize: 13.5, color: 'var(--ink)', lineHeight: 1.5 }}>
                {ex.readiness_explanation}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Beginner-Friendly Top KPI Cards */}
      {!isRunning && ex && (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 14, marginBottom: 22 }}>
          {/* Card 1: Win Rate */}
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--mut)', fontWeight: 600 }}>Win Rate</span>
              <Target size={16} weight="bold" color="var(--accent)" />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: ex.win_rate_pct >= 50 ? 'var(--up)' : 'var(--down)' }}>
              {ex.win_rate_pct}%
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--mut)', marginTop: 4 }}>
              <b>{ex.winning_trades} Wins</b> vs {ex.losing_trades} Losses (after costs)
            </div>
          </div>

          {/* Card 2: Total Trades */}
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--mut)', fontWeight: 600 }}>Total Trades Taken</span>
              <Calendar size={16} weight="bold" color="var(--mut)" />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>
              {ex.total_trades}
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--mut)', marginTop: 4 }}>
              Across {results?.weekly?.length || 52} weekly walk-forward cycles
            </div>
          </div>

          {/* Card 3: Deepest Capital Dip */}
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--mut)', fontWeight: 600 }}>Deepest Capital Dip</span>
              <TrendDown size={16} weight="bold" color="var(--down)" />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--down)' }}>
              {ex.max_drawdown_pct}%
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--mut)', marginTop: 4 }}>
              Largest temporary pullback from peak
            </div>
          </div>

          {/* Card 4: Strategy Return vs NIFTY */}
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--mut)', fontWeight: 600 }}>Total Return (Net)</span>
              <TrendUp size={16} weight="bold" color="var(--up)" />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: ex.total_strategy_return_pct >= 0 ? 'var(--up)' : 'var(--down)' }}>
              {ex.total_strategy_return_pct >= 0 ? '+' : ''}{ex.total_strategy_return_pct}%
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--mut)', marginTop: 4 }}>
              NIFTY 50: <b>{ex.nifty_benchmark_return_pct >= 0 ? '+' : ''}{ex.nifty_benchmark_return_pct}%</b> ({ex.outperformance_alpha_pct >= 0 ? `+${ex.outperformance_alpha_pct}% Alpha` : `${ex.outperformance_alpha_pct}%`})
            </div>
          </div>

          {/* Card 5: Profit Factor */}
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--mut)', fontWeight: 600 }}>Profit Factor</span>
              <ShieldCheck size={16} weight="bold" color="var(--info)" />
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: ex.profit_factor >= 1.25 ? 'var(--up)' : 'var(--ink)' }}>
              {ex.profit_factor}x
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--mut)', marginTop: 4 }}>
              ₹{ex.profit_factor} gained for every ₹1.00 lost
            </div>
          </div>
        </section>
      )}

      {/* Weekly Breakdown Table */}
      {!isRunning && results?.weekly && results.weekly.length > 0 && (
        <section className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Weekly Audit Log (52 Weeks Walk-Forward)</h3>
              <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--mut)' }}>
                Click on any weekly row to inspect every stock's entry, exit, stop-loss, target, and multi-metric prediction scores.
              </p>
            </div>
            <span className="chip" style={{ fontSize: 11 }}>
              {results.weekly.length} Audited Cycles
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5, textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'var(--surface)', borderBottom: '1px solid var(--line)', color: 'var(--mut)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                  <th style={{ padding: '10px 14px' }}>Week (Mon → Fri)</th>
                  <th style={{ padding: '10px 12px' }}>Market Regime</th>
                  <th style={{ padding: '10px 12px' }}>Picks</th>
                  <th style={{ padding: '10px 12px' }}>Hits (Wins)</th>
                  <th style={{ padding: '10px 12px' }}>Losses</th>
                  <th style={{ padding: '10px 12px' }}>Win Rate %</th>
                  <th style={{ padding: '10px 12px' }}>Strategy Net %</th>
                  <th style={{ padding: '10px 12px' }}>NIFTY %</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {results.weekly.map((w, i) => {
                  const isExpanded = expandedWeek === w.week_index
                  return (
                    <React.Fragment key={w.week_index}>
                      <tr
                        onClick={() => setExpandedWeek(isExpanded ? null : w.week_index)}
                        style={{
                          borderBottom: '1px solid var(--line)',
                          cursor: 'pointer',
                          background: isExpanded ? 'var(--surface)' : (i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)')
                        }}
                      >
                        <td style={{ padding: '11px 14px', fontWeight: 600 }}>
                          <span>{w.run_date}</span>
                          <ArrowRight size={11} style={{ margin: '0 5px' }} />
                          <span style={{ color: 'var(--mut)' }}>{w.target_date}</span>
                        </td>
                        <td style={{ padding: '11px 12px' }}>
                          <span
                            className="chip"
                            style={{
                              fontSize: 10.5,
                              padding: '2px 7px',
                              background: w.market_regime === 'Bull' ? 'rgba(255,255,255,0.1)' : 'rgba(255,94,26,0.1)',
                              color: w.market_regime === 'Bull' ? 'var(--up)' : 'var(--accent)',
                              fontWeight: 600
                            }}
                          >
                            {w.market_regime}
                          </span>
                        </td>
                        <td style={{ padding: '11px 12px', fontWeight: 600 }}>{w.picks_count} stocks</td>
                        <td style={{ padding: '11px 12px' }}>
                          <span style={{ color: 'var(--up)', fontWeight: 700 }}>{w.wins_count} Hits</span>
                        </td>
                        <td style={{ padding: '11px 12px' }}>
                          <span style={{ color: w.losses_count > 0 ? 'var(--down)' : 'var(--mut)', fontWeight: 600 }}>
                            {w.losses_count} Losses
                          </span>
                        </td>
                        <td style={{ padding: '11px 12px' }}>
                          <span style={{ fontWeight: 600, color: w.win_rate_pct >= 50 ? 'var(--up)' : 'var(--down)' }}>
                            {w.win_rate_pct}%
                          </span>
                        </td>
                        <td style={{ padding: '11px 12px', fontWeight: 700, color: w.weekly_net_pct >= 0 ? 'var(--up)' : 'var(--down)' }}>
                          {w.weekly_net_pct >= 0 ? '+' : ''}{w.weekly_net_pct}%
                        </td>
                        <td style={{ padding: '11px 12px', color: 'var(--mut)' }}>
                          {w.nifty_net_pct >= 0 ? '+' : ''}{w.nifty_net_pct}%
                        </td>
                        <td style={{ padding: '11px 12px', textAlign: 'right' }}>
                          <button
                            type="button"
                            className="btn ghost sm"
                            style={{ fontSize: 11, padding: '3px 8px' }}
                          >
                            {isExpanded ? <CaretUp size={13} /> : <CaretDown size={13} />}
                            <span style={{ marginLeft: 4 }}>{isExpanded ? 'Hide' : 'Inspect'}</span>
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Accordion: Multi-Metric Trades Log */}
                      {isExpanded && (
                        <tr style={{ background: 'var(--surface)' }}>
                          <td colSpan={9} style={{ padding: '14px 18px 20px' }}>
                            <div style={{ fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 10 }}>
                              Multi-Metric Trade &amp; Prediction Audit for Week of {w.run_date}:
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                              {w.trades.map((tr, idx) => (
                                <div
                                  key={idx}
                                  style={{
                                    padding: '12px 14px',
                                    borderRadius: 'var(--r-sm)',
                                    background: 'var(--panel)',
                                    border: '1px solid var(--line)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: 6
                                  }}
                                >
                                  {/* Header: Symbol & Net Result */}
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div>
                                      <b style={{ fontSize: 14 }}>{tr.symbol}</b>
                                      {tr.sector && (
                                        <span style={{ fontSize: 10, color: 'var(--mut)', marginLeft: 6 }}>
                                          ({tr.sector})
                                        </span>
                                      )}
                                    </div>
                                    <span
                                      className="chip"
                                      style={{
                                        fontSize: 11,
                                        fontWeight: 700,
                                        background: tr.is_win ? 'rgba(255,255,255,0.12)' : 'rgba(255,59,48,0.12)',
                                        color: tr.is_win ? 'var(--up)' : 'var(--down)'
                                      }}
                                    >
                                      {tr.is_win ? `+${tr.net_return_pct}%` : `${tr.net_return_pct}%`}
                                    </span>
                                  </div>

                                  {/* Trade Prices */}
                                  <div style={{ fontSize: 11.5, color: 'var(--ink)', display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Entry: <b>₹{tr.entry_price}</b></span>
                                    <span>Exit: <b>₹{tr.exit_price}</b></span>
                                  </div>
                                  <div style={{ fontSize: 11, color: 'var(--mut)', display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Stop: ₹{tr.stop_loss}</span>
                                    <span>Target: ₹{tr.target}</span>
                                  </div>
                                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink)', marginTop: 2 }}>
                                    {tr.exit_reason} ({tr.days_held}D held)
                                  </div>

                                  {/* Multi-Metric Prediction Engine Scores */}
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6, paddingTop: 6, borderTop: '1px dashed var(--line)', fontSize: 10 }}>
                                    {tr.trader_score != null && (
                                      <span className="chip" style={{ fontSize: 9.5, padding: '1px 6px', background: 'rgba(255,94,26,0.08)', color: 'var(--info)', fontWeight: 600 }}>
                                        Score: {tr.trader_score}/100
                                      </span>
                                    )}
                                    {tr.best_dir_acc != null && (
                                      <span className="chip" style={{ fontSize: 9.5, padding: '1px 6px', background: 'rgba(255,94,26,0.08)', color: '#FF5E1A', fontWeight: 600 }}>
                                        ML Acc: {tr.best_dir_acc}% ({tr.predicted_return_pct != null && tr.predicted_return_pct > 0 ? `+${tr.predicted_return_pct}%` : `${tr.predicted_return_pct}%`})
                                      </span>
                                    )}
                                    {tr.sim_win_prob_pct != null && (
                                      <span className="chip" style={{ fontSize: 9.5, padding: '1px 6px', background: 'rgba(255,94,26,0.08)', color: 'var(--amber)', fontWeight: 600 }}>
                                        TimeMachine: {tr.sim_win_prob_pct}% Win ({tr.sim_avg_r != null && tr.sim_avg_r > 0 ? `+${tr.sim_avg_r}R` : `${tr.sim_avg_r}R`})
                                      </span>
                                    )}
                                    {tr.rsi != null && (
                                      <span className="chip" style={{ fontSize: 9.5, padding: '1px 6px', background: 'var(--surface)', color: 'var(--mut)' }}>
                                        RSI {tr.rsi} · ADX {tr.adx}
                                      </span>
                                    )}
                                    {tr.pe != null && (
                                      <span className="chip" style={{ fontSize: 9.5, padding: '1px 6px', background: 'var(--surface)', color: 'var(--mut)' }}>
                                        P/E {tr.pe} {tr.debt_to_equity != null ? `· D/E ${tr.debt_to_equity}` : ''}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Empty State when no results loaded */}
      {!results?.weekly && !isRunning && (
        <section className="panel" style={{ padding: '40px', textAlign: 'center' }}>
          <ChartLineUp size={48} weight="light" color="var(--mut)" style={{ marginBottom: 12 }} />
          <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 600 }}>Ready to Validate Prediction Model</h3>
          <p style={{ margin: '0 auto 18px', maxWidth: 480, fontSize: 13, color: 'var(--mut)' }}>
            Click <b>"Run Full Multi-Metric Backtest"</b> above to test how our complete production engine (Technicals, ML, Monte Carlo, and Fundamentals) would have performed week-by-week across the past 52 weeks.
          </p>
          <button
            className="btn dark"
            onClick={startBacktest}
            style={{ padding: '9px 18px', fontSize: 13, fontWeight: 600 }}
          >
            Run Full Multi-Metric Backtest (52 Weeks)
          </button>
        </section>
      )}
    </div>
  )
}
